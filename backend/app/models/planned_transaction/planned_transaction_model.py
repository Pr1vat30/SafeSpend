"""ORM model of the `planned_transaction` table (see `database/schema.sql`)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Identity, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class PlannedTransactionModel(Base):
    __tablename__ = "planned_transaction"

    id_planned_transaction: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    # Foreign keys are declared in schema.sql (the source of truth). They are plain integers
    # here because the `_user` and `category` tables have no ORM model in this module.
    id_user: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_category: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    planned_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(140))
    origin: Mapped[str] = mapped_column(String(25), nullable=False, server_default="manual")
    status: Mapped[str] = mapped_column(String(25), nullable=False, server_default="planned")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
