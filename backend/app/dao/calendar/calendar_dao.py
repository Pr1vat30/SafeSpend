"""Read-only queries of the income/expense calendar (RF_CG_1).

The calendar owns no table: it reads `recurring_rule` and `category`. They are described here with
lightweight `table()` constructs, which are not registered in `Base.metadata`, so they don't clash
with the ORM model of the recurring rules module.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, Numeric, String, column, or_, select, table
from sqlalchemy.ext.asyncio import AsyncSession

_recurring_rule = table(
    "recurring_rule",
    column("id_recurring_rule", BigInteger),
    column("id_user", BigInteger),
    column("id_category", BigInteger),
    column("name", String),
    column("type", String),
    column("amount", Numeric(12, 2)),
    column("frequency", String),
    column("first_occurrence_date", Date),
    column("end_date", Date),
    column("is_installment", Boolean),
    column("status", String),
)

_category = table(
    "category",
    column("id_category", BigInteger),
    column("name", String),
)

# RF_CG_1 shows the incomes and expenses set by the user: `saving` rules are goal allocations
# planned by the system (SS5) and are left out.
CALENDAR_RULE_TYPES = ("income", "expense")


@dataclass(frozen=True)
class CalendarRule:
    id_recurring_rule: int
    name: str
    type: str
    amount: Decimal
    frequency: str
    first_occurrence_date: date
    end_date: date | None
    is_installment: bool
    id_category: int
    category_name: str | None


class CalendarDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_active_rules(self, user_id: int, start: date, stop: date) -> list[CalendarRule]:
        """Active income/expense rules of the user that may fall between `start` and `stop`."""
        rule = _recurring_rule.c
        query = (
            select(
                rule.id_recurring_rule,
                rule.name,
                rule.type,
                rule.amount,
                rule.frequency,
                rule.first_occurrence_date,
                rule.end_date,
                rule.is_installment,
                rule.id_category,
                _category.c.name.label("category_name"),
            )
            .select_from(
                _recurring_rule.outerjoin(_category, _category.c.id_category == rule.id_category)
            )
            .where(
                rule.id_user == user_id,
                rule.status == "active",
                rule.type.in_(CALENDAR_RULE_TYPES),
                rule.first_occurrence_date <= stop,
                or_(rule.end_date.is_(None), rule.end_date >= start),
            )
            .order_by(rule.id_recurring_rule)
        )
        result = await self.db.execute(query)
        return [CalendarRule(**row) for row in result.mappings()]
