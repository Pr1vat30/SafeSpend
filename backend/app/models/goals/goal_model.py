"""ORM model for savings goals (RF_OBI_1–4): table `goals`."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class Goal(Base):
    """Savings goals belonging to a user (RF_OBI_1–4).

    `saved_amount` is never stored physically on `goals`: it is computed from the
    linked saving `recurring_rule` (or recorded occurrences/contributions).
    """

    __tablename__ = "goals"

    id_goal: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_user: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("_user.id_user", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    installment_frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    installment_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
