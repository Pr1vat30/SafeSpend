"""ORM models of SS1 (account and financial profile): tables `_user` and `financial_profile`."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common.base import Base


class User(Base):
    """Registered user (RF_AUT_1–4). `password` holds the Argon2 hash, never the plain text."""

    __tablename__ = "_user"

    id_user: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    surname: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(Text)
    privacy_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    disclaimer_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped["FinancialProfile"] = relationship(
        back_populates="user", uselist=False, lazy="raise", passive_deletes=True
    )


class FinancialProfile(Base):
    """Financial parameters of a user (RF_AUT_5, RF_CF_3, RF_CF_5, RNF_PV_2).

    Balance and STS are never stored here: they are computed by the Cash Flow Engine.
    `estimated_variable_expenses` is NULL when the user gave no estimate (different from 0).
    """

    __tablename__ = "financial_profile"

    id_user: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("_user.id_user", ondelete="CASCADE"), primary_key=True
    )
    safety_buffer: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    horizon_days: Mapped[int] = mapped_column(Integer, server_default="30")
    estimated_variable_expenses: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ai_consent: Mapped[bool] = mapped_column(Boolean, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")
