"""Business logic of the planned transactions (RF_CF_6, UC_RF_CF_6).

Raises exceptions from `app.core.exceptions`, never `HTTPException` or `ValueError`: the
handlers in `core/exceptions.py` turn them into 400/404/409 responses (a `ValueError` would
become a 500).

Life cycle of a planned transaction:

    planned ──(date reached, expense: Scheduler)────────────▶ recorded
    planned ──(date reached, income: Scheduler)──▶ pending_confirmation
    pending_confirmation ──(user confirms)──▶ recorded   (a real income transaction is created)
    pending_confirmation ──(user rejects)───▶ cancelled
    pending_confirmation ──(user postpones)─▶ planned     (with a new future date)
    planned ──(user cancels)────────────────▶ cancelled
"""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.api.dto.planned_transaction.schema import (
    PlannedTransactionCreate,
    PlannedTransactionRead,
    PlannedTransactionUpdate,
)
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.dao.planned_transaction.planned_transaction_dao import PlannedTransactionDAO
from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel
from app.service.scheduler.occurrences import add_months

# Messages are local to the module: `constants/messages.py` is a shared file (PM approval needed).
PLANNED_NOT_FOUND = "Movimento pianificato non trovato"
CATEGORY_NOT_FOUND = "Categoria non trovata"
CATEGORY_INCOMPATIBLE = "La categoria non è compatibile con il tipo del movimento"
DATE_IN_PAST = "La data del movimento pianificato non può essere nel passato"
DATE_TOO_FAR = "La data del movimento pianificato deve essere entro 24 mesi da oggi"
ONLY_PLANNED_EDITABLE = "Si può modificare solo un movimento ancora pianificato"
ONLY_PENDING_INCOME = (
    "Solo gli incassi in attesa di conferma possono essere confermati, rifiutati o rinviati"
)
ONLY_PLANNED_CANCELLABLE = (
    "Si può annullare solo un movimento ancora pianificato: "
    "per un incasso in attesa usa la conferma o il rifiuto"
)
RECORDED_NOT_DELETABLE = (
    "Il movimento è già stato registrato come transazione e non può essere eliminato"
)

# RF_CF_6: planned transactions have a future date within 24 months.
MAX_MONTHS_AHEAD = 24

# Which category types may be used by a planned transaction of each type.
_ALLOWED_CATEGORY_TYPES = {"income": {"income", "both"}, "expense": {"expense", "both"}}


def rome_today() -> date:
    """Today's date in Europe/Rome, the reference time zone of the system (RNF_AF_6)."""
    return datetime.now(ZoneInfo("Europe/Rome")).date()


class PlannedTransactionService:
    def __init__(self, dao: PlannedTransactionDAO, today: Callable[[], date] = rome_today):
        self.dao = dao
        self._today = today

    async def create(self, user_id: int, data: PlannedTransactionCreate) -> PlannedTransactionRead:
        await self._check_category(user_id, data.id_category, data.type)
        self._check_date(data.planned_date)
        planned = PlannedTransactionModel(id_user=user_id, status="planned", **data.model_dump())
        planned = await self.dao.add(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def list_transactions(
        self,
        user_id: int,
        status: str | None = None,
        type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PlannedTransactionRead]:
        planned_list = await self.dao.list_by_user(user_id, status, type, date_from, date_to)
        return [PlannedTransactionRead.model_validate(p) for p in planned_list]

    async def list_pending_incomes(self, user_id: int) -> list[PlannedTransactionRead]:
        """Incomes whose date has come and that wait for the user's confirmation."""
        planned_list = await self.dao.list_pending_incomes_for_user(user_id)
        return [PlannedTransactionRead.model_validate(p) for p in planned_list]

    async def get(self, user_id: int, planned_id: int) -> PlannedTransactionRead:
        return PlannedTransactionRead.model_validate(await self._get_model(user_id, planned_id))

    async def update(
        self, user_id: int, planned_id: int, data: PlannedTransactionUpdate
    ) -> PlannedTransactionRead:
        planned = await self._get_model(user_id, planned_id)
        if planned.status != "planned":
            raise ConflictError(ONLY_PLANNED_EDITABLE)
        changes = data.model_dump(exclude_unset=True)

        # Validate everything before touching the object.
        if "type" in changes or "id_category" in changes:
            await self._check_category(
                user_id,
                changes.get("id_category", planned.id_category),
                changes.get("type", planned.type),
            )
        if "planned_date" in changes:
            self._check_date(changes["planned_date"])

        for field, value in changes.items():
            setattr(planned, field, value)
        planned = await self.dao.save(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def cancel(self, user_id: int, planned_id: int) -> PlannedTransactionRead:
        """Cancel a planned transaction before its date (it stays in the history)."""
        planned = await self._get_model(user_id, planned_id)
        if planned.status != "planned":
            raise ConflictError(ONLY_PLANNED_CANCELLABLE)
        planned = await self.dao.cancel_planned(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def delete(self, user_id: int, planned_id: int) -> None:
        planned = await self._get_model(user_id, planned_id)
        if planned.status == "recorded":
            raise ConflictError(RECORDED_NOT_DELETABLE)
        await self.dao.delete(planned)

    async def confirm_or_reject_income(
        self, user_id: int, planned_id: int, confirm: bool
    ) -> PlannedTransactionRead:
        """Confirm (a real income transaction is created) or reject a pending income."""
        planned = await self._get_model(user_id, planned_id)
        if planned.type != "income" or planned.status != "pending_confirmation":
            raise ConflictError(ONLY_PENDING_INCOME)

        if confirm:
            planned = await self.dao.confirm_income(planned)
        else:
            planned = await self.dao.reject_income(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def postpone_income(
        self, user_id: int, planned_id: int, new_date: date
    ) -> PlannedTransactionRead:
        """Move a pending income to a new date: it goes back into the projection (RF_CF_6)."""
        planned = await self._get_model(user_id, planned_id)
        if planned.type != "income" or planned.status != "pending_confirmation":
            raise ConflictError(ONLY_PENDING_INCOME)
        self._check_date(new_date)
        planned.planned_date = new_date
        planned.status = "planned"
        planned = await self.dao.save(planned)
        return PlannedTransactionRead.model_validate(planned)

    # -- helpers -----------------------------------------------------------------------------

    async def _get_model(self, user_id: int, planned_id: int) -> PlannedTransactionModel:
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            # Also returned for transactions of other users, so their existence is not revealed.
            raise NotFoundError(PLANNED_NOT_FOUND)
        return planned

    async def _check_category(self, user_id: int, category_id: int, planned_type: str) -> None:
        category_type = await self.dao.get_category_type(category_id, user_id)
        if category_type is None:
            raise NotFoundError(CATEGORY_NOT_FOUND)
        if category_type not in _ALLOWED_CATEGORY_TYPES[planned_type]:
            raise AppException(CATEGORY_INCOMPATIBLE)

    def _check_date(self, planned_date: date) -> None:
        today = self._today()
        if planned_date < today:
            raise AppException(DATE_IN_PAST)
        if planned_date > add_months(today, MAX_MONTHS_AHEAD):
            raise AppException(DATE_TOO_FAR)
