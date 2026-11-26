"""Validation rules of the transaction DTOs (no database needed)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.dto.transaction.category_schema import CategoryCreate
from app.api.dto.transaction.schema import TransactionCreate
from app.service.profile import profile_service
from app.service.profile.profile_service import today_rome


def build(**overrides) -> TransactionCreate:
    data = {
        "type": "expense",
        "amount": "10.00",
        "transaction_date": today_rome(),
        "id_category": 1,
    }
    data.update(overrides)
    return TransactionCreate(**data)


def test_valid_transaction_without_description():
    transaction = build()
    assert transaction.amount == Decimal("10.00")
    assert transaction.description is None


@pytest.mark.parametrize("amount", ["0", "-1", "-0.01", "10.001", "abc", "NaN", "Infinity"])
def test_invalid_amount(amount):
    with pytest.raises(ValidationError):
        build(amount=amount)


def test_amount_with_two_decimals_is_valid():
    assert build(amount="0.01").amount == Decimal("0.01")


def test_future_date_is_rejected():
    with pytest.raises(ValidationError):
        build(transaction_date=today_rome() + timedelta(days=1))


def test_today_and_past_dates_are_valid():
    assert build(transaction_date=today_rome()).transaction_date == today_rome()
    assert build(transaction_date=date(2020, 1, 1)).transaction_date == date(2020, 1, 1)


def test_rome_midnight_boundary_uses_europe_rome_not_utc(monkeypatch):
    """Between 00:00 and 02:00 Europe/Rome, UTC is still the previous day (RNF_AF_7)."""

    class FrozenDateTime:
        @classmethod
        def now(cls, tz=None):
            # 22:30 UTC in July is 00:30 of the next day in Europe/Rome (CEST, UTC+2).
            utc_now = datetime(2026, 7, 15, 22, 30, tzinfo=UTC)
            return utc_now.astimezone(tz) if tz else utc_now

    monkeypatch.setattr(profile_service, "datetime", FrozenDateTime)

    assert build(transaction_date=date(2026, 7, 16)).transaction_date == date(2026, 7, 16)
    with pytest.raises(ValidationError):
        build(transaction_date=date(2026, 7, 17))


def test_invalid_type_is_rejected():
    with pytest.raises(ValidationError):
        build(type="adjustment")


@pytest.mark.parametrize("missing", ["type", "amount", "transaction_date", "id_category"])
def test_required_fields(missing):
    data = {
        "type": "income",
        "amount": "5",
        "transaction_date": today_rome(),
        "id_category": 1,
    }
    del data[missing]
    with pytest.raises(ValidationError):
        TransactionCreate(**data)


def test_description_limit_and_blank():
    assert build(description="   ").description is None
    assert build(description="x" * 140).description == "x" * 140
    with pytest.raises(ValidationError):
        build(description="x" * 141)


def test_category_name_is_trimmed_and_required():
    assert CategoryCreate(name="  Hobby  ").name == "Hobby"
    with pytest.raises(ValidationError):
        CategoryCreate(name="   ")
    with pytest.raises(ValidationError):
        CategoryCreate(name="x" * 101)
