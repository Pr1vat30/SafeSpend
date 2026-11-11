"""Template DTOs. Copy to `app/api/dto/<module>/schema.py` and rename."""

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    """Request body for creating a resource."""


class TemplateUpdate(BaseModel):
    """Request body for updating a resource (fields optional)."""


class TemplateRead(BaseModel):
    """Response body. `from_attributes` allows validating ORM objects directly."""

    model_config = ConfigDict(from_attributes=True)
