"""Service layer for planned transactions (RF_CF_6).

Contains business logic: validation, rules, and coordination between DAOs.
"""

from datetime import date

from app.api.dto.planned_transaction.schema import (
    PlannedTransactionCreate,
    PlannedTransactionRead,
    PlannedTransactionUpdate,
)
from app.dao.planned_transaction.planned_transaction_dao import PlannedTransactionDAO


class PlannedTransactionService:
    def __init__(self, dao: PlannedTransactionDAO):
        self.dao = dao

    async def create(self, user_id: int, data: PlannedTransactionCreate) -> PlannedTransactionRead:
        # Validate category exists and is compatible with type
        category_type = await self.dao.get_category_type(data.id_category, user_id)
        if category_type is None:
            raise ValueError("Categoria inesistente o non accessibile")
        if category_type != "both" and category_type != data.type:
            raise ValueError("Tipo categoria incompatibile con il tipo movimento")

        from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel

        planned = PlannedTransactionModel(
            id_user=user_id,
            id_category=data.id_category,
            name=data.name,
            type=data.type,
            amount=data.amount,
            planned_date=data.planned_date,
            description=data.description,
            origin=data.origin,
            status="planned",
        )
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

    async def get(self, user_id: int, planned_id: int) -> PlannedTransactionRead | None:
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            return None
        return PlannedTransactionRead.model_validate(planned)

    async def update(
        self, user_id: int, planned_id: int, data: PlannedTransactionUpdate
    ) -> PlannedTransactionRead | None:
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            return None

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(planned, field, value)

        # If category or type changed, validate compatibility
        if "id_category" in update_data or "type" in update_data:
            new_type = update_data.get("type", planned.type)
            new_category = update_data.get("id_category", planned.id_category)
            category_type = await self.dao.get_category_type(new_category, user_id)
            if category_type is None:
                raise ValueError("Categoria inesistente o non accessibile")
            if category_type != "both" and category_type != new_type:
                raise ValueError("Tipo categoria incompatibile con il tipo movimento")

        planned = await self.dao.save(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def delete(self, user_id: int, planned_id: int) -> bool:
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            return False
        await self.dao.delete(planned)
        return True

    async def confirm_or_reject_income(
        self, user_id: int, planned_id: int, confirm: bool
    ) -> PlannedTransactionRead | None:
        """Confirm (confirm=True) or reject (confirm=False) a pending income."""
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            return None
        if planned.type != "income" or planned.status != "pending_confirmation":
            raise ValueError(
                "Solo gli incassi in attesa di conferma possono essere confermati o rifiutati"
            )

        if confirm:
            planned = await self.dao.confirm_income(planned)
        else:
            planned = await self.dao.reject_income(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def cancel(self, user_id: int, planned_id: int) -> PlannedTransactionRead | None:
        """Cancel a planned transaction (expense or income) before its date."""
        planned = await self.dao.get_by_id_for_user(planned_id, user_id)
        if planned is None:
            return None
        if planned.status in ("recorded", "cancelled"):
            raise ValueError("Movimento già registrato o annullato")

        planned = await self.dao.cancel_planned(planned)
        return PlannedTransactionRead.model_validate(planned)

    async def list_pending_incomes(self, user_id: int) -> list[PlannedTransactionRead]:
        """List pending confirmation incomes for the user."""
        planned_list = await self.dao.list_pending_incomes_for_user(user_id)
        return [PlannedTransactionRead.model_validate(p) for p in planned_list]
