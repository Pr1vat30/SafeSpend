"""Read-only queries of the income/expense calendar (RF_CG_1).

The calendar owns no table: it reads `recurring_rule`, `planned_transaction` and `category`. They
are described here with lightweight `table()` constructs, which are not registered in
`Base.metadata`, so they don't clash with the ORM models of the transaction module.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Numeric,
    Select,
    String,
    TableClause,
    column,
    or_,
    select,
    table,
)
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

_planned_transaction = table(
    "planned_transaction",
    column("id_planned_transaction", BigInteger),
    column("id_user", BigInteger),
    column("id_category", BigInteger),
    column("name", String),
    column("type", String),
    column("amount", Numeric(12, 2)),
    column("planned_date", Date),
    column("status", String),
)

_category = table(
    "category",
    column("id_category", BigInteger),
    column("name", String),
)

# Incomes, expenses and goal allocations (`saving` rules of SS5): RF_CG_1 shows all of them.
RULE_TYPES = ("income", "expense", "saving")
# Every planned movement of the month except the `cancelled` ones: like the occurrences of the
# recurring rules, `recorded` movements stay on their day (the calendar does not read transactions,
# so nothing is shown twice).
PLANNED_STATUSES = ("planned", "pending_confirmation", "recorded")


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


@dataclass(frozen=True)
class CalendarPlanned:
    id_planned_transaction: int
    name: str
    type: str
    amount: Decimal
    planned_date: date
    id_category: int
    category_name: str | None


def _select_with_category(source: TableClause, *columns) -> Select:
    """`columns` of `source` plus the name of its category."""
    return select(*columns, _category.c.name.label("category_name")).select_from(
        source.outerjoin(_category, _category.c.id_category == source.c.id_category)
    )


class CalendarDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_active_rules(self, user_id: int, start: date, stop: date) -> list[CalendarRule]:
        """Active rules of the user (any type) that may fall between `start` and `stop`."""
        rule = _recurring_rule.c
        query = _select_with_category(
            _recurring_rule,
            rule.id_recurring_rule,
            rule.name,
            rule.type,
            rule.amount,
            rule.frequency,
            rule.first_occurrence_date,
            rule.end_date,
            rule.is_installment,
            rule.id_category,
        ).where(
            rule.id_user == user_id,
            rule.status == "active",
            rule.type.in_(RULE_TYPES),
            rule.first_occurrence_date <= stop,
            or_(rule.end_date.is_(None), rule.end_date >= start),
        )
        result = await self.db.execute(query)
        return [CalendarRule(**row) for row in result.mappings()]

    async def find_planned(self, user_id: int, start: date, stop: date) -> list[CalendarPlanned]:
        """Planned movements of the user between `start` and `stop`, except the cancelled ones."""
        planned = _planned_transaction.c
        query = _select_with_category(
            _planned_transaction,
            planned.id_planned_transaction,
            planned.name,
            planned.type,
            planned.amount,
            planned.planned_date,
            planned.id_category,
        ).where(
            planned.id_user == user_id,
            planned.status.in_(PLANNED_STATUSES),
            planned.planned_date.between(start, stop),
        )
        result = await self.db.execute(query)
        return [CalendarPlanned(**row) for row in result.mappings()]
