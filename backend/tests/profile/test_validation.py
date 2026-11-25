"""Unit tests of SS1 validations, designed with Category Partition (RNF_OP_1).

No database needed.

Password (RF_AUT_1) — categories:
  length: < 8 | = 8 | > 8
  letters: none | at least one (ASCII or accented)
  digits: none | at least one
Amount (RF_CF_3, RF_AUT_5) — categories:
  sign: negative | zero | positive
  decimals: 0 | 1–2 | > 2
Consents (RF_AUT_1, RNF_LE_1): privacy / disclaimer / age of majority each true | false
Horizon (RF_CF_5): 30 | 60 | 90 | any other value
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.dto.profile.schema import (
    InitialSetupRequest,
    ProfileUpdate,
    RegisterRequest,
    check_amount,
    check_password_strength,
)
from app.service.profile import messages as msg


def _register(**overrides) -> dict:
    body = {
        "name": "Gilberto",
        "surname": "Rossi",
        "email": "gilberto@example.com",
        "password": "Password123",
        "privacy_accepted": True,
        "disclaimer_accepted": True,
        "is_adult": True,
    }
    body.update(overrides)
    return body


# --- Password -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "password",
    [
        "abcdef12",  # length = 8, letters, digits (boundary)
        "Password123",  # length > 8
        "èèèèèèè1",  # accented letters count as letters
    ],
)
def test_password_valid(password):
    assert check_password_strength(password) == password


@pytest.mark.parametrize(
    "password",
    [
        "abc1234",  # length 7 (< 8)
        "abcdefgh",  # no digit
        "12345678",  # no letter
        "________",  # neither letters nor digits
        "",  # empty
    ],
)
def test_password_invalid(password):
    with pytest.raises(ValueError, match="almeno 8 caratteri"):
        check_password_strength(password)


# --- Registration -------------------------------------------------------------------------


def test_register_normalizes_email_and_trims_names():
    data = RegisterRequest(**_register(email="  Gilberto@Example.COM ", name="  Gilberto "))
    assert data.email == "gilberto@example.com"
    assert data.name == "Gilberto"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("privacy_accepted", msg.MUST_ACCEPT_PRIVACY),
        ("disclaimer_accepted", msg.MUST_ACCEPT_DISCLAIMER),
        ("is_adult", msg.MUST_BE_ADULT),
    ],
)
def test_register_requires_every_consent(field, message):
    with pytest.raises(ValidationError, match=message):
        RegisterRequest(**_register(**{field: False}))


@pytest.mark.parametrize("email", ["non-una-email", "manca@dominio", "@example.com"])
def test_register_rejects_invalid_email(email):
    with pytest.raises(ValidationError):
        RegisterRequest(**_register(email=email))


@pytest.mark.parametrize("name", ["", "   "])
def test_register_rejects_blank_name(name):
    with pytest.raises(ValidationError, match=msg.FIELD_REQUIRED):
        RegisterRequest(**_register(name=name))


# --- Amounts ------------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "0.00", "300", "300.5", "1234.56"])
def test_amount_valid(value):
    assert check_amount(Decimal(value)) == Decimal(value)


def test_amount_none_means_not_given():
    assert check_amount(None) is None


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("-0.01", msg.AMOUNT_NOT_NEGATIVE),  # negative
        ("-300", msg.AMOUNT_NOT_NEGATIVE),
        ("10.123", msg.AMOUNT_TWO_DECIMALS),  # more than two decimals
        ("NaN", msg.AMOUNT_NOT_NEGATIVE),
        ("Infinity", msg.AMOUNT_NOT_NEGATIVE),
    ],
)
def test_amount_invalid(value, message):
    with pytest.raises(ValueError, match=message):
        check_amount(Decimal(value))


def test_setup_accepts_negative_balance_but_not_negative_buffer():
    data = InitialSetupRequest(current_balance=Decimal("-50.00"), safety_buffer=Decimal("300"))
    assert data.current_balance == Decimal("-50.00")
    with pytest.raises(ValidationError, match=msg.AMOUNT_NOT_NEGATIVE):
        InitialSetupRequest(current_balance=Decimal("100"), safety_buffer=Decimal("-1"))


# --- Profile update -----------------------------------------------------------------------


@pytest.mark.parametrize("days", [30, 60, 90])
def test_horizon_valid(days):
    assert ProfileUpdate(horizon_days=days).horizon_days == days


@pytest.mark.parametrize("days", [0, 29, 45, 120])
def test_horizon_invalid(days):
    with pytest.raises(ValidationError, match=msg.HORIZON_NOT_ALLOWED):
        ProfileUpdate(horizon_days=days)


def test_update_changes_contains_only_sent_fields():
    assert ProfileUpdate(ai_consent=True).changes() == {"ai_consent": True}
    assert ProfileUpdate(estimated_variable_expenses=None).changes() == {
        "estimated_variable_expenses": None
    }


@pytest.mark.parametrize("field", ["safety_buffer", "horizon_days", "ai_consent"])
def test_update_rejects_null_for_required_fields(field):
    with pytest.raises(ValidationError):
        ProfileUpdate(**{field: None})
