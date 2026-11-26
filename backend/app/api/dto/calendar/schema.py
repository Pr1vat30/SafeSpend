"""DTOs of the income/expense calendar (RF_CG_1)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CalendarEntry(BaseModel):
    """One income, expense or goal allocation (`saving`) on a day of the calendar.

    `source_id` is the id of the recurring rule (`source="recurring"`) or of the planned movement
    (`source="planned"`). `frequency` is set only for recurring rules.
    """

    source: Literal["recurring", "planned"]
    source_id: int
    name: str
    type: Literal["income", "expense", "saving"]
    amount: Decimal
    id_category: int
    category_name: str | None = None
    frequency: Literal["weekly", "monthly", "yearly"] | None = None
    is_installment: bool = False


class CalendarDay(BaseModel):
    date: date
    total_income: Decimal
    total_expense: Decimal
    total_saving: Decimal
    entries: list[CalendarEntry]


class CalendarMonth(BaseModel):
    """Calendar of a month. `days` lists only the days with at least one entry."""

    month: str
    total_income: Decimal
    total_expense: Decimal
    total_saving: Decimal
    days: list[CalendarDay]
