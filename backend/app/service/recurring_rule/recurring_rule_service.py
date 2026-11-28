"""Business logic of the recurring rules (RF_CF_2, UC_RF_CF_2).

Raises exceptions from `app.core.exceptions`, never `HTTPException`.
"""

from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.api.dto.recurring_rule.schema import RecurringRuleCreate, RecurringRuleUpdate
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.dao.recurring_rule.recurring_rule_dao import RecurringRuleDAO
from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel

# Messages are local to the module: `constants/messages.py` is a shared file (PM approval needed).
RULE_NOT_FOUND = "Voce ricorrente non trovata"
CATEGORY_NOT_FOUND = "Categoria non trovata"
CATEGORY_INCOMPATIBLE = "La categoria non è compatibile con il tipo della voce"
FIRST_DATE_IN_PAST = "La prima occorrenza non può essere nel passato"
END_DATE_NOT_AFTER_FIRST = "La data di fine deve essere successiva alla prima occorrenza"
MANAGED_ELSEWHERE = "Questa voce è gestita da un obiettivo o da un piano a rate"
RULE_TERMINATED = "La voce è terminata e non può essere modificata"
SCHEDULE_LOCKED = (
    "Tipo, frequenza e prima occorrenza non si modificano dopo la prima registrazione: "
    "crea una nuova voce"
)
ONLY_ACTIVE_CAN_SUSPEND = "Si può sospendere solo una voce attiva"
ONLY_SUSPENDED_CAN_RESUME = "Si può riattivare solo una voce sospesa"

# Which category types may be used by a rule of each type.
_ALLOWED_CATEGORY_TYPES = {"income": {"income", "both"}, "expense": {"expense", "both"}}


def rome_today() -> date:
    """Today's date in Europe/Rome, the reference time zone of the system (RNF_AF_6)."""
    return datetime.now(ZoneInfo("Europe/Rome")).date()


class RecurringRuleService:
    def __init__(self, dao: RecurringRuleDAO, today: Callable[[], date] = rome_today):
        self.dao = dao
        self._today = today

    async def create(self, user_id: int, data: RecurringRuleCreate) -> RecurringRuleModel:
        await self._check_category(user_id, data.id_category, data.type)
        self._check_first_date(data.first_occurrence_date)
        self._check_end_date(data.first_occurrence_date, data.end_date)
        rule = RecurringRuleModel(id_user=user_id, **data.model_dump())
        return await self.dao.add(rule)

    async def list_for_user(self, user_id: int, status: str | None = None):
        return await self.dao.list_by_user(user_id, status)

    async def get(self, user_id: int, rule_id: int) -> RecurringRuleModel:
        rule = await self.dao.get_by_id_for_user(rule_id, user_id)
        if rule is None:
            # Also returned for rules of other users, so their existence is not revealed.
            raise NotFoundError(RULE_NOT_FOUND)
        return rule

    async def update(
        self, user_id: int, rule_id: int, data: RecurringRuleUpdate
    ) -> RecurringRuleModel:
        rule = await self._get_editable(user_id, rule_id)
        changes = data.model_dump(exclude_unset=True)

        # Changes apply only to future occurrences: what was already registered stays as is.
        if (
            rule.last_processed_occurrence_date is not None
            and {
                "type",
                "frequency",
                "first_occurrence_date",
            }
            & changes.keys()
        ):
            raise ConflictError(SCHEDULE_LOCKED)

        new_type = changes.get("type", rule.type)
        new_category = changes.get("id_category", rule.id_category)
        if "type" in changes or "id_category" in changes:
            await self._check_category(user_id, new_category, new_type)

        new_first = changes.get("first_occurrence_date", rule.first_occurrence_date)
        if "first_occurrence_date" in changes:
            self._check_first_date(new_first)
        self._check_end_date(new_first, changes.get("end_date", rule.end_date))

        for field, value in changes.items():
            setattr(rule, field, value)
        return await self.dao.save(rule)

    async def suspend(self, user_id: int, rule_id: int) -> RecurringRuleModel:
        rule = await self._get_editable(user_id, rule_id)
        if rule.status != "active":
            raise ConflictError(ONLY_ACTIVE_CAN_SUSPEND)
        rule.status = "suspended"
        return await self.dao.save(rule)

    async def resume(self, user_id: int, rule_id: int) -> RecurringRuleModel:
        rule = await self._get_editable(user_id, rule_id)
        if rule.status != "suspended":
            raise ConflictError(ONLY_SUSPENDED_CAN_RESUME)
        rule.status = "active"
        return await self.dao.save(rule)

    async def delete(self, user_id: int, rule_id: int) -> None:
        rule = await self.get(user_id, rule_id)
        if rule.is_installment or rule.id_goal is not None:
            raise ConflictError(MANAGED_ELSEWHERE)
        await self.dao.delete(rule)

    # -- helpers -----------------------------------------------------------------------------

    async def _get_editable(self, user_id: int, rule_id: int) -> RecurringRuleModel:
        rule = await self.get(user_id, rule_id)
        if rule.is_installment or rule.id_goal is not None:
            raise ConflictError(MANAGED_ELSEWHERE)
        if rule.status == "terminated":
            raise ConflictError(RULE_TERMINATED)
        return rule

    async def _check_category(self, user_id: int, category_id: int, rule_type: str) -> None:
        category_type = await self.dao.get_category_type(category_id, user_id)
        if category_type is None:
            raise NotFoundError(CATEGORY_NOT_FOUND)
        if category_type not in _ALLOWED_CATEGORY_TYPES[rule_type]:
            raise AppException(CATEGORY_INCOMPATIBLE)

    def _check_first_date(self, first: date) -> None:
        if first < self._today():
            raise AppException(FIRST_DATE_IN_PAST)

    @staticmethod
    def _check_end_date(first: date, end: date | None) -> None:
        if end is not None and end <= first:
            raise AppException(END_DATE_NOT_AFTER_FIRST)
