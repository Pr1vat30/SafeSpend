"""Category DTOs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dto.transaction.schema import CategoryType


class _CategoryName(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Il nome della categoria è obbligatorio")
        return value


class CategoryCreate(_CategoryName):
    type: CategoryType = "expense"


class CategoryUpdate(_CategoryName):
    """Only the name can change: the type is fixed because transactions depend on it."""


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_category: int
    name: str
    type: str
    is_default: bool
    created_at: datetime


class CategoryDeleted(BaseModel):
    reassigned_transactions: int
