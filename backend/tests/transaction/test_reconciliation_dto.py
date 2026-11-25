"""Validation rules of the reconciliation DTOs (no database needed)."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.dto.transaction.reconciliation_schema import ReconciliationCreate


def build(**overrides) -> ReconciliationCreate:
    data = {"real_balance": "100.00", "reconciliation_date": date.today()}
    data.update(overrides)
    return ReconciliationCreate(**data)


@pytest.mark.parametrize("balance", ["0", "0.00", "-250.75", "1234.56"])
def test_valid_real_balance(balance):
    item = build(real_balance=balance)
    assert item.real_balance == Decimal(balance)
    assert item.description is None


@pytest.mark.parametrize("balance", ["10.001", "10000000000.00", "abc", "NaN", "Infinity"])
def test_invalid_real_balance(balance):
    with pytest.raises(ValidationError):
        build(real_balance=balance)


def test_future_reconciliation_date_is_rejected():
    with pytest.raises(ValidationError):
        build(reconciliation_date=date.today() + timedelta(days=1))


def test_today_and_past_reconciliation_dates_are_valid():
    assert build(reconciliation_date=date.today()).reconciliation_date == date.today()
    assert build(reconciliation_date=date(2020, 1, 1)).reconciliation_date == date(2020, 1, 1)


def test_description_is_trimmed_and_bounded():
    assert build(description="   ").description is None
    assert build(description="  Estratto conto  ").description == "Estratto conto"
    assert build(description="x" * 140).description == "x" * 140
    with pytest.raises(ValidationError):
        build(description="x" * 141)
