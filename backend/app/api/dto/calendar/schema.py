"""DTOs of the income/expense calendar (RF_CG_1)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class CalendarEntry(BaseModel):
    """One occurrence of a recurring rule on a day of the calendar."""

    id_recurring_rule: int
    name: str
    type: Literal["income", "expense"]
    amount: Decimal
    frequency: Literal["weekly", "monthly", "yearly"]
    is_installment: bool
    id_category: int
    category_name: str | None = None


class CalendarDay(BaseModel):
    date: date
    total_income: Decimal
    total_expense: Decimal
    entries: list[CalendarEntry]


class CalendarMonth(BaseModel):
    """Calendar of a month. `days` lists only the days with at least one entry."""

    month: str
    total_income: Decimal
    total_expense: Decimal
    days: list[CalendarDay]
