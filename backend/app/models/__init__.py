"""Import every model here so metadata is complete (e.g. for future migrations)."""

from app.models.common.base import Base
from app.models.profile.profile_model import FinancialProfile, User  # noqa: F401

__all__ = ["Base"]
