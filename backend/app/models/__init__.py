"""Import every model here so metadata is complete (e.g. for future migrations)."""

from app.models.achievements import Achievement, UserAchievement  # noqa: F401
from app.models.common.base import Base
from app.models.goals import Goal  # noqa: F401
from app.models.profile.profile_model import FinancialProfile, User  # noqa: F401

__all__ = ["Base"]
