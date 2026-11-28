"""DTOs of the recurring rules (RF_CF_2)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

RuleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
# Mirrors NUMERIC(12,2): greater than zero, at most two decimals (RNF_IM_2).
Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
# 'saving' rules are created by the goals module, never directly by the user.
RuleType = Literal["income", "expense"]
Frequency = Literal["weekly", "monthly", "yearly"]
RuleStatus = Literal["active", "suspended", "terminated"]


class RecurringRuleCreate(BaseModel):
    """Request body for creating a recurring rule."""

    name: RuleName
    type: RuleType
    amount: Money
    id_category: int
    frequency: Frequency
    first_occurrence_date: date
    end_date: date | None = None


class RecurringRuleUpdate(BaseModel):
    """Request body for updating a rule: send only the fields to change."""

    name: RuleName | None = None
    type: RuleType | None = None
    amount: Money | None = None
    id_category: int | None = None
    frequency: Frequency | None = None
    first_occurrence_date: date | None = None
    end_date: date | None = None  # explicit null removes the end date

    @model_validator(mode="after")
    def _required_fields_not_null(self):
        required = ("name", "type", "amount", "id_category", "frequency", "first_occurrence_date")
        for field in required:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} non può essere nullo")
        return self


class RecurringRuleRead(BaseModel):
    """Response body. `from_attributes` allows validating ORM objects directly."""

    model_config = ConfigDict(from_attributes=True)

    id_recurring_rule: int
    id_category: int
    id_goal: int | None
    name: str
    type: str
    amount: Decimal
    frequency: str
    first_occurrence_date: date
    end_date: date | None
    last_processed_occurrence_date: date | None
    is_installment: bool
    status: str
    created_at: datetime
