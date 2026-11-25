"""Reconciliation DTOs: input validation and response bodies (`RF_SAL_1`, `RF_SAL_2`)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReconciliationCreate(BaseModel):
    """Request body for reconciling the system balance with the user's real balance."""

    real_balance: Decimal = Field(max_digits=12, decimal_places=2, allow_inf_nan=False)
    reconciliation_date: date = Field(default_factory=date.today)
    description: str | None = Field(default=None, max_length=140)

    @field_validator("reconciliation_date")
    @classmethod
    def date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La data non può essere futura")
        return value

    @field_validator("description")
    @classmethod
    def blank_description_is_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_snapshot: int
    real_balance: Decimal
    calculated_balance: Decimal
    difference: Decimal
    reconciliation_date: date
    id_adjustment_transaction: int | None
    created_at: datetime


class ReconciliationPreview(BaseModel):
    """Current calculated balance and latest snapshot before performing a reconciliation."""

    reconciliation_date: date
    calculated_balance: Decimal
    last_reconciliation: ReconciliationRead | None = None


class ReconciliationHistory(BaseModel):
    """User's reconciliation snapshots (most recent first) plus the current calculated balance."""

    items: list[ReconciliationRead]
    count: int
    current_calculated_balance: Decimal
