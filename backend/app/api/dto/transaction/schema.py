"""Transaction DTOs: input validation and response bodies."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TransactionType = Literal["income", "expense"]
CategoryType = Literal["income", "expense", "both"]


class TransactionCreate(BaseModel):
    """Request body for creating (and, in full, replacing) a transaction."""

    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    transaction_date: date
    id_category: int = Field(gt=0)
    description: str | None = Field(default=None, max_length=140)

    @field_validator("transaction_date")
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


class TransactionUpdate(TransactionCreate):
    """Request body for editing a transaction: same fields and rules as the insertion."""


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_transaction: int
    type: str
    amount: Decimal
    transaction_date: date
    id_category: int | None
    category_name: str | None
    description: str | None
    origin: str
    created_at: datetime


class TransactionTotals(BaseModel):
    income: Decimal
    expense: Decimal


class TransactionList(BaseModel):
    """Filtered transactions (most recent first) with the totals of the same set."""

    items: list[TransactionRead]
    totals: TransactionTotals
    count: int
