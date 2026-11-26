"""Category ORM model (table `category` in `database/schema.sql`)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Identity, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class Category(Base):
    """Default categories have `id_user IS NULL`; custom ones belong to a user."""

    __tablename__ = "category"
    __mapper_args__ = {"eager_defaults": True}

    id_category: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_user: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False, default="expense")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
