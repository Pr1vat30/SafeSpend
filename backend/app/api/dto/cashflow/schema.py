from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class DailyBalanceRead(BaseModel):
    date: date
    balance: Decimal


class ProjectionRead(BaseModel):
    daily_balances: list[DailyBalanceRead]
    minimum_balance: Decimal
    critical_date: date
    safe_to_spend: Decimal
    daily_safe_to_spend: Decimal
    risk_level: Literal["Sostenibile", "Attenzione", "Critico"]
    variable_expense_estimate_missing: bool = False
