"""DTOs of the planned transactions (RF_CF_6)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

PlannedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=140)]
PlannedDescription = Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=140)]
# Mirrors NUMERIC(12,2): greater than zero, at most two decimals (RNF_IM_2).
Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
PlannedType = Literal["income", "expense"]
PlannedOrigin = Literal["manual", "alternative_simulator"]
PlannedStatus = Literal["planned", "pending_confirmation", "recorded", "cancelled"]


class PlannedTransactionCreate(BaseModel):
    """Request body for creating a planned transaction."""

    name: PlannedName
    type: PlannedType
    amount: Money
    id_category: int
    planned_date: date
    description: PlannedDescription = None
    origin: PlannedOrigin = "manual"


class PlannedTransactionUpdate(BaseModel):
    """Request body for updating a planned transaction: send only the fields to change."""

    name: PlannedName | None = None
    type: PlannedType | None = None
    amount: Money | None = None
    id_category: int | None = None
    planned_date: date | None = None
    description: PlannedDescription = None
    origin: PlannedOrigin | None = None

    @model_validator(mode="after")
    def _required_fields_not_null(self):
        required = ("name", "type", "amount", "id_category", "planned_date")
        for field in required:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} non può essere nullo")
        return self


class PlannedTransactionConfirm(BaseModel):
    """Request body for confirming or rejecting a pending income."""

    confirm: bool


class PlannedTransactionRead(BaseModel):
    """Response body. `from_attributes` allows validating ORM objects directly."""

    model_config = ConfigDict(from_attributes=True)

    id_planned_transaction: int
    id_category: int
    name: str
    type: str
    amount: Decimal
    planned_date: date
    description: str | None
    origin: str
    status: str
    created_at: datetime
