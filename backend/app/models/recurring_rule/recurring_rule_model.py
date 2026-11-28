"""ORM model of the `recurring_rule` table (see `database/schema.sql`)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Identity, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class RecurringRuleModel(Base):
    __tablename__ = "recurring_rule"

    id_recurring_rule: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    # Foreign keys are declared in schema.sql (the source of truth). They are plain integers
    # here because the `_user` and `category` tables have no ORM model in this module.
    id_user: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_category: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_goal: Mapped[int | None] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    first_occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    last_processed_occurrence_date: Mapped[date | None] = mapped_column(Date)
    is_installment: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
