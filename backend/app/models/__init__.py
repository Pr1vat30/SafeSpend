"""Import every model here so metadata is complete (e.g. for future migrations)."""

from app.models.common.base import Base

__all__ = ["Base"]
