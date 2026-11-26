"""BalanceSnapshot ORM model (table `balance_snapshot` in `database/schema.sql`)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.common.base import Base


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshot"
    __mapper_args__ = {"eager_defaults": True}

    id_snapshot: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id_user: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_adjustment_transaction: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("transaction.id_transaction", ondelete="SET NULL"), nullable=True
    )
    real_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    calculated_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reconciliation_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    @property
    def difference(self) -> Decimal:
        return self.real_balance - self.calculated_balance
