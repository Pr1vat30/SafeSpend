"""Unit tests of RecurringRuleService with a fake DAO (no database needed).

Category Partition: each test covers one class of input of UC_RF_CF_2 (valid, past date,
end date not after first, wrong category, rule of another user, invalid state transition).
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.dto.recurring_rule.schema import RecurringRuleCreate, RecurringRuleUpdate
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.service.recurring_rule.recurring_rule_service import RecurringRuleService

TODAY = date(2026, 11, 24)
USER = 1


class FakeDAO:
    """In-memory stand-in for RecurringRuleDAO."""

    def __init__(self, category_types=None):
        self.rules = {}
        self.category_types = category_types if category_types is not None else {10: "expense"}
        self._next_id = 1

    async def add(self, rule):
        rule.id_recurring_rule = self._next_id
        rule.status = rule.status or "active"
        rule.is_installment = bool(rule.is_installment)
        self._next_id += 1
        self.rules[rule.id_recurring_rule] = rule
        return rule

    async def save(self, rule):
        return rule

    async def get_by_id_for_user(self, rule_id, user_id):
        rule = self.rules.get(rule_id)
        return rule if rule is not None and rule.id_user == user_id else None

    async def list_by_user(self, user_id, status=None):
        return [r for r in self.rules.values() if r.id_user == user_id]

    async def delete(self, rule):
        del self.rules[rule.id_recurring_rule]

    async def get_category_type(self, category_id, user_id):
        return self.category_types.get(category_id)


def make_service(dao=None):
    return RecurringRuleService(dao or FakeDAO(), today=lambda: TODAY)


def valid_data(**overrides):
    base = {
        "name": "Palestra",
        "type": "expense",
        "amount": Decimal("50.00"),
        "id_category": 10,
        "frequency": "monthly",
        "first_occurrence_date": date(2026, 12, 10),
        "end_date": date(2027, 12, 10),
    }
    return RecurringRuleCreate(**{**base, **overrides})


# -- creation -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_valid_rule():
    service = make_service()
    rule = await service.create(USER, valid_data())
    assert rule.id_user == USER
    assert rule.amount == Decimal("50.00")
    assert rule.status == "active"


@pytest.mark.asyncio
async def test_create_first_occurrence_today_is_allowed():
    rule = await make_service().create(USER, valid_data(first_occurrence_date=TODAY))
    assert rule.first_occurrence_date == TODAY


@pytest.mark.asyncio
async def test_create_first_occurrence_in_past_is_rejected():
    with pytest.raises(AppException):
        await make_service().create(USER, valid_data(first_occurrence_date=date(2026, 11, 23)))


@pytest.mark.asyncio
async def test_create_end_date_equal_to_first_is_rejected():
    with pytest.raises(AppException):
        await make_service().create(USER, valid_data(end_date=date(2026, 12, 10)))


@pytest.mark.asyncio
async def test_create_without_end_date_is_allowed():
    rule = await make_service().create(USER, valid_data(end_date=None))
    assert rule.end_date is None


@pytest.mark.asyncio
async def test_create_unknown_category_is_not_found():
    with pytest.raises(NotFoundError):
        await make_service().create(USER, valid_data(id_category=999))


@pytest.mark.asyncio
async def test_create_category_incompatible_with_type_is_rejected():
    with pytest.raises(AppException):
        await make_service().create(USER, valid_data(type="income"))  # category 10 is 'expense'


@pytest.mark.asyncio
async def test_create_category_both_accepts_any_type():
    service = make_service(FakeDAO({10: "both"}))
    assert (await service.create(USER, valid_data(type="income"))).type == "income"


# -- DTO validation (importo, nome, frequenza) --------------------------------------------


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5"), Decimal("10.005")])
def test_dto_rejects_invalid_amount(amount):
    with pytest.raises(ValidationError):
        valid_data(amount=amount)


def test_dto_rejects_blank_name_and_unknown_frequency():
    with pytest.raises(ValidationError):
        valid_data(name="   ")
    with pytest.raises(ValidationError):
        valid_data(frequency="daily")


def test_dto_rejects_saving_type():
    with pytest.raises(ValidationError):
        valid_data(type="saving")


def test_update_dto_rejects_null_for_required_field():
    with pytest.raises(ValidationError):
        RecurringRuleUpdate(amount=None)


# -- access, update, suspend, delete ------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_of_another_user_is_not_found():
    service = make_service()
    rule = await service.create(USER, valid_data())
    with pytest.raises(NotFoundError):
        await service.get(2, rule.id_recurring_rule)


@pytest.mark.asyncio
async def test_update_amount():
    service = make_service()
    rule = await service.create(USER, valid_data())
    updated = await service.update(
        USER, rule.id_recurring_rule, RecurringRuleUpdate(amount=Decimal("60.00"))
    )
    assert updated.amount == Decimal("60.00")


@pytest.mark.asyncio
async def test_update_can_remove_end_date():
    service = make_service()
    rule = await service.create(USER, valid_data())
    updated = await service.update(USER, rule.id_recurring_rule, RecurringRuleUpdate(end_date=None))
    assert updated.end_date is None


@pytest.mark.asyncio
async def test_update_end_date_before_first_is_rejected():
    service = make_service()
    rule = await service.create(USER, valid_data())
    with pytest.raises(AppException):
        await service.update(
            USER, rule.id_recurring_rule, RecurringRuleUpdate(end_date=date(2026, 12, 1))
        )


@pytest.mark.asyncio
async def test_update_schedule_locked_after_first_processing():
    service = make_service()
    rule = await service.create(USER, valid_data())
    rule.last_processed_occurrence_date = date(2026, 12, 10)
    with pytest.raises(ConflictError):
        await service.update(USER, rule.id_recurring_rule, RecurringRuleUpdate(frequency="weekly"))


@pytest.mark.asyncio
async def test_rule_managed_by_goal_or_installments_cannot_be_modified():
    service = make_service()
    rule = await service.create(USER, valid_data())
    rule.is_installment = True
    with pytest.raises(ConflictError):
        await service.suspend(USER, rule.id_recurring_rule)
    with pytest.raises(ConflictError):
        await service.delete(USER, rule.id_recurring_rule)


@pytest.mark.asyncio
async def test_suspend_then_resume():
    service = make_service()
    rule = await service.create(USER, valid_data())
    assert (await service.suspend(USER, rule.id_recurring_rule)).status == "suspended"
    assert (await service.resume(USER, rule.id_recurring_rule)).status == "active"


@pytest.mark.asyncio
async def test_invalid_state_transitions_are_rejected():
    service = make_service()
    rule = await service.create(USER, valid_data())
    with pytest.raises(ConflictError):
        await service.resume(USER, rule.id_recurring_rule)  # already active
    await service.suspend(USER, rule.id_recurring_rule)
    with pytest.raises(ConflictError):
        await service.suspend(USER, rule.id_recurring_rule)  # already suspended


@pytest.mark.asyncio
async def test_terminated_rule_cannot_be_updated():
    service = make_service()
    rule = await service.create(USER, valid_data())
    rule.status = "terminated"
    with pytest.raises(ConflictError):
        await service.update(USER, rule.id_recurring_rule, RecurringRuleUpdate(name="Altro"))


@pytest.mark.asyncio
async def test_delete_removes_rule():
    service = make_service()
    rule = await service.create(USER, valid_data())
    await service.delete(USER, rule.id_recurring_rule)
    with pytest.raises(NotFoundError):
        await service.get(USER, rule.id_recurring_rule)
