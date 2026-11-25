"""ORM models for achievements (RF_PRE_6): tables `achievement` and `user_achievement`."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class Achievement(Base):
    """Catalog definition of an achievement badge."""

    __tablename__ = "achievement"

    id_achievement: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    badge_path: Mapped[str] = mapped_column(Text, nullable=False)
    criterion: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class UserAchievement(Base):
    """Association recording when a user unlocked a specific achievement."""

    __tablename__ = "user_achievement"

    id_user: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("_user.id_user", ondelete="CASCADE"), primary_key=True
    )
    id_achievement: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("achievement.id_achievement", ondelete="RESTRICT"),
        primary_key=True,
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
