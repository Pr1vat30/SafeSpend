"""Transaction ORM model (table `transaction` in `database/schema.sql`)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Identity, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common.base import Base
from app.models.transaction.category_model import Category


class Transaction(Base):
    __tablename__ = "transaction"
    __mapper_args__ = {"eager_defaults": True}

    id_transaction: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    id_user: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_category: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("category.id_category"), nullable=True
    )
    id_recurring_rule: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    id_planned_transaction: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    description: Mapped[str | None] = mapped_column(String(140), nullable=True)
    type: Mapped[str] = mapped_column(String(15), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    occurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    origin: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    category: Mapped[Category | None] = relationship(lazy="joined")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None
