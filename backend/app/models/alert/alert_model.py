"""ORM model of the `alert` table (see `database/schema.sql`)."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class AlertModel(Base):
    __tablename__ = "alert"

    id_alert: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # The foreign key to `_user` is declared in schema.sql (the source of truth).
    id_user: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(String(25), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    status: Mapped[str] = mapped_column(String(15), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
