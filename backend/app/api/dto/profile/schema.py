"""DTOs of SS1: registration, login, profile, initial setup, account deletion."""

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.service.profile import messages as msg

_LETTER = re.compile(r"[^\W\d_]")  # any Unicode letter
_DIGIT = re.compile(r"\d")


def check_password_strength(password: str) -> str:
    """RF_AUT_1: at least 8 characters, at least one letter and one digit."""
    if len(password) < 8 or not _LETTER.search(password) or not _DIGIT.search(password):
        raise ValueError(msg.PASSWORD_TOO_WEAK)
    return password


def check_amount(value: Decimal | None) -> Decimal | None:
    """RF_CF_3 / RF_AUT_5: amount >= 0 with at most two decimals (RNF_IM_2)."""
    if value is None:
        return None
    if not value.is_finite() or value < 0:
        raise ValueError(msg.AMOUNT_NOT_NEGATIVE)
    if value.as_tuple().exponent < -2:  # type: ignore[operator]
        raise ValueError(msg.AMOUNT_TWO_DECIMALS)
    return value


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(msg.FIELD_REQUIRED)
    return value


# --- Authentication -------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """RF_AUT_1. Privacy, non-advice disclaimer and age of majority are mandatory (RNF_LE_1)."""

    name: str = Field(max_length=100)
    surname: str = Field(max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(max_length=128)
    privacy_accepted: bool
    disclaimer_accepted: bool
    is_adult: bool

    @field_validator("name", "surname")
    @classmethod
    def _names(cls, v: str) -> str:
        return _not_blank(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_password_strength(v)

    @field_validator("privacy_accepted")
    @classmethod
    def _privacy(cls, v: bool) -> bool:
        if not v:
            raise ValueError(msg.MUST_ACCEPT_PRIVACY)
        return v

    @field_validator("disclaimer_accepted")
    @classmethod
    def _disclaimer(cls, v: bool) -> bool:
        if not v:
            raise ValueError(msg.MUST_ACCEPT_DISCLAIMER)
        return v

    @field_validator("is_adult")
    @classmethod
    def _adult(cls, v: bool) -> bool:
        if not v:
            raise ValueError(msg.MUST_BE_ADULT)
        return v


class LoginRequest(BaseModel):
    """RF_AUT_2."""

    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_user: int
    name: str
    surname: str
    email: str
    created_at: datetime


# --- Profile -------------------------------------------------------------------------------


class FinancialProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    safety_buffer: Decimal
    horizon_days: int
    estimated_variable_expenses: Decimal | None
    ai_consent: bool
    updated_at: datetime


class ProfileRead(BaseModel):
    """GET /profile: user data, financial parameters and whether the initial setup is done."""

    user: UserRead
    financial_profile: FinancialProfileRead
    setup_completed: bool  # False until the first balance is entered (RF_AUT_5)


class InitialSetupRequest(BaseModel):
    """RF_AUT_5: current balance (first reconciliation), Safety Buffer, optional monthly estimate
    of variable expenses. The balance may be negative (overdraft)."""

    current_balance: Decimal = Field(max_digits=12, decimal_places=2)
    safety_buffer: Decimal
    estimated_variable_expenses: Decimal | None = None

    @field_validator("current_balance")
    @classmethod
    def _balance(cls, v: Decimal) -> Decimal:
        if not v.is_finite():
            raise ValueError(msg.AMOUNT_TWO_DECIMALS)
        return v

    @field_validator("safety_buffer", "estimated_variable_expenses")
    @classmethod
    def _amounts(cls, v: Decimal | None) -> Decimal | None:
        return check_amount(v)


class ProfileUpdate(BaseModel):
    """Partial update of the financial profile. Only the fields sent are changed.

    - safety_buffer: RF_CF_3
    - estimated_variable_expenses: RF_AUT_5 / RF_PRE_1 (send null to remove the estimate)
    - horizon_days: RF_CF_5 (30, 60 or 90)
    - ai_consent: RNF_PV_2 (explicit and revocable)
    """

    safety_buffer: Decimal | None = None
    estimated_variable_expenses: Decimal | None = None
    horizon_days: int | None = None
    ai_consent: bool | None = None

    @field_validator("safety_buffer", "estimated_variable_expenses")
    @classmethod
    def _amounts(cls, v: Decimal | None) -> Decimal | None:
        return check_amount(v)

    @field_validator("horizon_days")
    @classmethod
    def _horizon(cls, v: int | None) -> int | None:
        if v is not None and v not in (30, 60, 90):
            raise ValueError(msg.HORIZON_NOT_ALLOWED)
        return v

    @model_validator(mode="after")
    def _no_null_for_required(self) -> "ProfileUpdate":
        # Only estimated_variable_expenses may be explicitly set to null.
        for field in ("safety_buffer", "horizon_days", "ai_consent"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field}: {msg.FIELD_REQUIRED}")
        return self

    def changes(self) -> dict:
        """Only the fields actually sent by the client."""
        return {field: getattr(self, field) for field in self.model_fields_set}


class DeleteAccountRequest(BaseModel):
    """RF_AUT_4: the password confirms the deletion."""

    password: str = Field(max_length=128)
