"""Unit tests of PlannedTransactionService with a fake DAO (no database needed).

Category Partition: each test covers one class of input of UC_RF_CF_6 (valid, past date,
wrong or missing category, transaction of another user, invalid state transition).
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.api.dto.planned_transaction.schema import (
    PlannedTransactionCreate,
    PlannedTransactionUpdate,
)
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel
from app.service.planned_transaction.planned_transaction_service import PlannedTransactionService

TODAY = date(2026, 11, 24)
USER = 1
OTHER_USER = 2


class FakeDAO:
    """In-memory stand-in for PlannedTransactionDAO."""

    def __init__(self, category_types=None):
        self.planned = {}
        self.transactions = []  # rows that the real DAO inserts into `transaction`
        self.category_types = (
            category_types
            if category_types is not None
            else {10: "expense", 20: "income", 30: "both"}
        )
        self._next_id = 1

    async def add(self, p):
        p.id_planned_transaction = self._next_id
        p.created_at = datetime.now()
        p.origin = p.origin or "manual"
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
        self.transactions.append(
            {
                "id_planned_transaction": p.id_planned_transaction,
                "type": "income",
                "amount": p.amount,
            }
        )
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
    return PlannedTransactionService(dao or FakeDAO(), today=lambda: TODAY)


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


async def add_with_status(service, status, type_="income", user=USER, category=20):
    """Put a planned transaction in a given state, as the Scheduler would."""
    p = PlannedTransactionModel(
        id_user=user,
        id_category=category,
        name="Stipendio",
        type=type_,
        amount=Decimal("2000.00"),
        planned_date=TODAY,
        status=status,
        origin="manual",
    )
    return await service.dao.add(p)


# -- creation -----------------------------------------------------------------------------


async def test_create_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    assert p.id_planned_transaction == 1
    assert p.name == "Pranzo"
    assert p.status == "planned"
    assert p.origin == "manual"


async def test_create_with_category_both_is_accepted():
    service = make_service()
    p = await service.create(USER, valid_create_data(id_category=30, type="income"))
    assert p.type == "income"


async def test_create_today_is_accepted():
    service = make_service()
    p = await service.create(USER, valid_create_data(planned_date=TODAY))
    assert p.planned_date == TODAY


async def test_create_in_the_past_rejected():
    service = make_service()
    with pytest.raises(AppException, match="nel passato"):
        await service.create(USER, valid_create_data(planned_date=date(2026, 11, 23)))


async def test_create_with_wrong_category_type_rejected():
    service = make_service()
    with pytest.raises(AppException, match="non è compatibile"):
        await service.create(USER, valid_create_data(id_category=20))  # income category


async def test_create_with_missing_category_rejected():
    service = make_service()
    with pytest.raises(NotFoundError):
        await service.create(USER, valid_create_data(id_category=99))


def test_create_with_non_positive_amount_rejected_by_dto():
    with pytest.raises(ValueError):
        valid_create_data(amount=Decimal("0"))


# -- read and isolation between users (RNF_SE_3) ------------------------------------------


async def test_get_of_another_user_is_not_found():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    with pytest.raises(NotFoundError):
        await service.get(OTHER_USER, p.id_planned_transaction)


async def test_get_missing_is_not_found():
    with pytest.raises(NotFoundError):
        await make_service().get(USER, 42)


async def test_list_filters_by_type():
    service = make_service()
    await service.create(USER, valid_create_data())
    await service.create(USER, valid_create_data(type="income", id_category=20))
    incomes = await service.list_transactions(USER, type="income")
    assert [p.type for p in incomes] == ["income"]


# -- update -------------------------------------------------------------------------------


async def test_update_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    updated = await service.update(
        USER, p.id_planned_transaction, PlannedTransactionUpdate(amount=Decimal("20.00"))
    )
    assert updated.amount == Decimal("20.00")
    assert updated.name == "Pranzo"  # unchanged


async def test_update_date_in_the_past_rejected_and_nothing_changes():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    with pytest.raises(AppException):
        await service.update(
            USER,
            p.id_planned_transaction,
            PlannedTransactionUpdate(amount=Decimal("99.00"), planned_date=date(2026, 1, 1)),
        )
    assert service.dao.planned[p.id_planned_transaction].amount == Decimal("15.50")


async def test_update_type_incompatible_with_category_rejected():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    with pytest.raises(AppException, match="non è compatibile"):
        await service.update(
            USER, p.id_planned_transaction, PlannedTransactionUpdate(type="income")
        )


@pytest.mark.parametrize("status", ["pending_confirmation", "recorded", "cancelled"])
async def test_update_not_planned_rejected(status):
    service = make_service()
    p = await add_with_status(service, status)
    with pytest.raises(ConflictError):
        await service.update(
            USER, p.id_planned_transaction, PlannedTransactionUpdate(amount=Decimal("1.00"))
        )


def test_update_null_required_field_rejected_by_dto():
    with pytest.raises(ValueError):
        PlannedTransactionUpdate(name=None)


# -- cancel and delete --------------------------------------------------------------------


async def test_cancel_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    cancelled = await service.cancel(USER, p.id_planned_transaction)
    assert cancelled.status == "cancelled"


@pytest.mark.parametrize("status", ["pending_confirmation", "recorded", "cancelled"])
async def test_cancel_not_planned_rejected(status):
    service = make_service()
    p = await add_with_status(service, status)
    with pytest.raises(ConflictError):
        await service.cancel(USER, p.id_planned_transaction)


async def test_delete_planned_transaction():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    await service.delete(USER, p.id_planned_transaction)
    assert await service.dao.list_by_user(USER) == []


async def test_delete_recorded_rejected():
    service = make_service()
    p = await add_with_status(service, "recorded")
    with pytest.raises(ConflictError):
        await service.delete(USER, p.id_planned_transaction)


async def test_delete_of_another_user_is_not_found():
    service = make_service()
    p = await service.create(USER, valid_create_data())
    with pytest.raises(NotFoundError):
        await service.delete(OTHER_USER, p.id_planned_transaction)
    assert p.id_planned_transaction in service.dao.planned


# -- confirmation of incomes --------------------------------------------------------------


async def test_confirm_income_creates_transaction():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation")
    confirmed = await service.confirm_or_reject_income(
        USER, pending.id_planned_transaction, confirm=True
    )
    assert confirmed.status == "recorded"
    assert service.dao.transactions == [
        {
            "id_planned_transaction": pending.id_planned_transaction,
            "type": "income",
            "amount": Decimal("2000.00"),
        }
    ]


async def test_reject_income_creates_no_transaction():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation")
    rejected = await service.confirm_or_reject_income(
        USER, pending.id_planned_transaction, confirm=False
    )
    assert rejected.status == "cancelled"
    assert service.dao.transactions == []


async def test_confirm_planned_expense_rejected():
    service = make_service()
    p = await service.create(USER, valid_create_data(type="expense"))
    with pytest.raises(ConflictError, match="Solo gli incassi in attesa"):
        await service.confirm_or_reject_income(USER, p.id_planned_transaction, confirm=True)


async def test_confirm_twice_rejected():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation")
    await service.confirm_or_reject_income(USER, pending.id_planned_transaction, confirm=True)
    with pytest.raises(ConflictError):
        await service.confirm_or_reject_income(USER, pending.id_planned_transaction, confirm=True)
    assert len(service.dao.transactions) == 1


async def test_confirm_income_of_another_user_is_not_found():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation", user=OTHER_USER)
    with pytest.raises(NotFoundError):
        await service.confirm_or_reject_income(USER, pending.id_planned_transaction, confirm=True)


async def test_list_pending_incomes():
    service = make_service()
    await add_with_status(service, "pending_confirmation")
    await add_with_status(service, "planned")
    pending = await service.list_pending_incomes(USER)
    assert [p.status for p in pending] == ["pending_confirmation"]


# -- postponing a pending income and 24-month limit (RF_CF_6) -----------------------------


async def test_postpone_pending_income_goes_back_to_planned():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation")
    new_date = date(2026, 12, 5)
    moved = await service.postpone_income(USER, pending.id_planned_transaction, new_date)
    assert (moved.status, moved.planned_date) == ("planned", new_date)


async def test_postpone_to_the_past_rejected():
    service = make_service()
    pending = await add_with_status(service, "pending_confirmation")
    with pytest.raises(AppException, match="nel passato"):
        await service.postpone_income(USER, pending.id_planned_transaction, date(2026, 11, 1))


async def test_postpone_not_pending_rejected():
    service = make_service()
    p = await service.create(USER, valid_create_data(type="income", id_category=20))
    with pytest.raises(ConflictError):
        await service.postpone_income(USER, p.id_planned_transaction, date(2026, 12, 5))


async def test_date_exactly_24_months_ahead_is_accepted():
    service = make_service()
    p = await service.create(USER, valid_create_data(planned_date=date(2028, 11, 24)))
    assert p.planned_date == date(2028, 11, 24)


async def test_date_beyond_24_months_rejected():
    service = make_service()
    with pytest.raises(AppException, match="24 mesi"):
        await service.create(USER, valid_create_data(planned_date=date(2028, 11, 25)))
