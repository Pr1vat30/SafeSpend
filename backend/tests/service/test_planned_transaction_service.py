"""Unit tests of PlannedTransactionService with a fake DAO (no database needed).

Covers RF_CF_6 (create, update, delete, confirm/reject income, cancel).
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.api.dto.planned_transaction.schema import (
    PlannedTransactionCreate,
    PlannedTransactionUpdate,
)
from app.service.planned_transaction.planned_transaction_service import PlannedTransactionService

TODAY = date(2026, 11, 24)
USER = 1


class FakeDAO:
    def __init__(self, category_types=None):
        self.planned = {}
        self.category_types = (
            category_types if category_types is not None else {10: "expense", 20: "income"}
        )
        self._next_id = 1

    async def add(self, p):
        p.id_planned_transaction = self._next_id
        p.created_at = datetime.now()
        self._next_id += 1
        self.planned[p.id_planned_transaction] = p
        return p

    async def save(self, p):
        return p

    async def get_by_id_for_user(self, pid, uid):
        p = self.planned.get(pid)
        return p if p and p.id_user == uid else None

    async def list_by_user(self, uid, status=None, type=None, date_from=None, date_to=None):
        res = [p for p in self.planned.values() if p.id_user == uid]
        if status:
            res = [p for p in res if p.status == status]
        if type:
            res = [p for p in res if p.type == type]
        if date_from:
            res = [p for p in res if p.planned_date >= date_from]
        if date_to:
            res = [p for p in res if p.planned_date <= date_to]
        return res

    async def delete(self, p):
        del self.planned[p.id_planned_transaction]

    async def get_category_type(self, cid, uid):
        return self.category_types.get(cid)

    async def confirm_income(self, p):
        p.status = "recorded"
        return p

    async def reject_income(self, p):
        p.status = "cancelled"
        return p

    async def cancel_planned(self, p):
        p.status = "cancelled"
        return p

    async def list_pending_incomes_for_user(self, uid):
        return [
            p
            for p in self.planned.values()
            if p.id_user == uid and p.status == "pending_confirmation" and p.type == "income"
        ]


def make_service(dao=None):
    return PlannedTransactionService(dao or FakeDAO())


def valid_create_data(**overrides):
    base = {
        "name": "Pranzo",
        "type": "expense",
        "amount": Decimal("15.50"),
        "id_category": 10,
        "planned_date": date(2026, 11, 30),
        "description": "Pranzo di lavoro",
    }
    return PlannedTransactionCreate(**{**base, **overrides})


@pytest.mark.asyncio
async def test_create_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    assert p.id_planned_transaction == 1
    assert p.name == "Pranzo"
    assert p.status == "planned"


@pytest.mark.asyncio
async def test_create_planned_with_wrong_category_type_rejected():
    service = make_service()
    with pytest.raises(ValueError, match="Tipo categoria incompatibile"):
        # Category 20 is income, but movement is expense
        await service.create(USER, valid_create_data(id_category=20))


@pytest.mark.asyncio
async def test_update_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())

    updated = await service.update(
        USER, p.id_planned_transaction, PlannedTransactionUpdate(amount=Decimal("20.00"))
    )
    assert updated.amount == Decimal("20.00")
    assert updated.name == "Pranzo"  # Unchanged


@pytest.mark.asyncio
async def test_cancel_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())

    cancelled = await service.cancel(USER, p.id_planned_transaction)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_confirm_income():
    service = make_service()
    # Manual creation of a pending income in the fake DAO
    from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel

    pending = PlannedTransactionModel(
        id_user=USER,
        id_category=20,
        name="Stipendio",
        type="income",
        amount=Decimal("2000.00"),
        planned_date=TODAY,
        status="pending_confirmation",
        origin="manual",
    )
    await service.dao.add(pending)

    confirmed = await service.confirm_or_reject_income(
        USER, pending.id_planned_transaction, confirm=True
    )
    assert confirmed.status == "recorded"


@pytest.mark.asyncio
async def test_reject_income():
    service = make_service()
    from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel

    pending = PlannedTransactionModel(
        id_user=USER,
        id_category=20,
        name="Regalo",
        type="income",
        amount=Decimal("50.00"),
        planned_date=TODAY,
        status="pending_confirmation",
        origin="manual",
    )
    await service.dao.add(pending)

    rejected = await service.confirm_or_reject_income(
        USER, pending.id_planned_transaction, confirm=False
    )
    assert rejected.status == "cancelled"


@pytest.mark.asyncio
async def test_confirm_only_pending_income_is_allowed():
    service = make_service()
    p = await service.create(USER, valid_create_data(type="expense"))  # status is 'planned'

    with pytest.raises(ValueError, match="Solo gli incassi in attesa di conferma"):
        await service.confirm_or_reject_income(USER, p.id_planned_transaction, confirm=True)


@pytest.mark.asyncio
async def test_delete_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())

    success = await service.delete(USER, p.id_planned_transaction)
    assert success is True
    assert len(await service.dao.list_by_user(USER)) == 0
