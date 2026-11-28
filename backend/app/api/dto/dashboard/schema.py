from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.api.dto.cashflow.schema import ProjectionRead


class UpcomingExpenseRead(BaseModel):
    date: date
    name: str
    amount: Decimal
    source: Literal["recurring", "planned"]
    source_id: int


class DashboardAlertRead(BaseModel):
    id_alert: int
    type: Literal["risk_level", "impending_expense", "sts_drop"]
    message: str
    trigger_date: date
    status: Literal["active", "read"]


class DashboardRead(BaseModel):
    reconciled_balance: Decimal
    reconciliation_date: date
    safety_buffer: Decimal
    projection: ProjectionRead
    sts_from_planned_income: Decimal
    upcoming_expenses: list[UpcomingExpenseRead]
    alerts: list[DashboardAlertRead]
