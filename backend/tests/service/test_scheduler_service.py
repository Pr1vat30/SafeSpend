"""Tests of the Scheduler logic with a fake DAO (no database needed).

Category Partition: rule state (new, in progress, ended), repeated runs (idempotence),
failure of one rule, planned expenses and incomes.
"""

from contextlib import asynccontextmanager
from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.dao.scheduler.scheduler_dao import RuleRow
from app.service.scheduler.run import seconds_until_next_run
from app.service.scheduler.scheduler_service import process_rule, run_daily

TODAY = date(2026, 12, 15)


def make_rule(rule_id=1, **overrides):
    base = {
        "id_recurring_rule": rule_id,
        "id_user": 1,
        "id_category": 10,
        "name": "Palestra",
        "type": "expense",
        "amount": Decimal("50.00"),
        "frequency": "monthly",
        "first_occurrence_date": date(2026, 10, 10),
        "end_date": None,
        "last_processed_occurrence_date": None,
    }
    return RuleRow(**{**base, **overrides})


class FakeDAO:
    """In-memory stand-in for SchedulerDAO: remembers the occurrences already registered."""

    def __init__(self, rules=None, fail_for=None, expenses=0, incomes=0):
        self.rules = rules or []
        self.fail_for = fail_for
        self.registered = set()
        self.progress = {}
        self.expenses = expenses
        self.incomes = incomes

    async def list_active_rules(self):
        return self.rules

    async def insert_occurrence(self, rule, occurrence_date):
        if rule.id_recurring_rule == self.fail_for:
            raise RuntimeError("database error")
        key = (rule.id_recurring_rule, occurrence_date)
        if key in self.registered:
            return False
        self.registered.add(key)
        return True

    async def update_rule_progress(self, rule_id, last_processed, terminate):
        self.progress[rule_id] = (last_processed, terminate)

    async def record_due_planned_expenses(self, today):
        return self.expenses

    async def mark_due_incomes_pending(self, today):
        return self.incomes


def make_uow(dao):
    @asynccontextmanager
    async def uow():
        yield dao

    return uow


# -- process_rule -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_new_rule_registers_every_due_occurrence_up_to_today():
    dao = FakeDAO()
    created, terminated = await process_rule(dao, make_rule(), TODAY)
    assert created == 3  # 10 Oct, 10 Nov, 10 Dec
    assert terminated is False
    assert dao.progress[1] == (date(2026, 12, 10), False)


@pytest.mark.asyncio
async def test_rule_in_progress_registers_only_the_new_occurrences():
    dao = FakeDAO()
    rule = make_rule(last_processed_occurrence_date=date(2026, 11, 10))
    created, _ = await process_rule(dao, rule, TODAY)
    assert created == 1
    assert dao.progress[1][0] == date(2026, 12, 10)


@pytest.mark.asyncio
async def test_rule_with_nothing_due_changes_nothing():
    dao = FakeDAO()
    rule = make_rule(last_processed_occurrence_date=date(2026, 12, 10))
    created, terminated = await process_rule(dao, rule, TODAY)
    assert (created, terminated) == (0, False)
    assert dao.progress == {}


@pytest.mark.asyncio
async def test_rule_starting_in_the_future_is_left_alone():
    dao = FakeDAO()
    created, _ = await process_rule(dao, make_rule(first_occurrence_date=date(2027, 1, 10)), TODAY)
    assert created == 0
    assert dao.progress == {}


@pytest.mark.asyncio
async def test_occurrence_already_registered_is_not_counted_twice():
    dao = FakeDAO()
    dao.registered.add((1, date(2026, 11, 10)))
    created, _ = await process_rule(dao, make_rule(), TODAY)
    assert created == 2  # the one of 10 Nov already existed


@pytest.mark.asyncio
async def test_rule_is_terminated_when_its_end_date_is_reached():
    dao = FakeDAO()
    rule = make_rule(end_date=date(2026, 12, 10))
    created, terminated = await process_rule(dao, rule, TODAY)
    assert (created, terminated) == (3, True)
    assert dao.progress[1] == (date(2026, 12, 10), True)


@pytest.mark.asyncio
async def test_rule_ended_with_nothing_left_to_register_is_still_terminated():
    dao = FakeDAO()
    rule = make_rule(end_date=date(2026, 12, 10), last_processed_occurrence_date=date(2026, 12, 10))
    created, terminated = await process_rule(dao, rule, TODAY)
    assert (created, terminated) == (0, True)
    assert dao.progress[1] == (date(2026, 12, 10), True)


@pytest.mark.asyncio
async def test_rule_with_future_end_date_stays_active():
    dao = FakeDAO()
    _, terminated = await process_rule(dao, make_rule(end_date=date(2027, 6, 10)), TODAY)
    assert terminated is False


# -- run_daily --------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_daily_sums_up_the_work_done():
    dao = FakeDAO(
        rules=[make_rule(1), make_rule(2, end_date=date(2026, 12, 10))], expenses=2, incomes=1
    )
    report = await run_daily(make_uow(dao), today=TODAY)
    assert report.rules_checked == 2
    assert report.occurrences_created == 6
    assert report.rules_terminated == 1
    assert report.planned_expenses_recorded == 2
    assert report.incomes_awaiting_confirmation == 1
    assert report.failures == 0


@pytest.mark.asyncio
async def test_run_daily_twice_does_not_register_anything_new():
    dao = FakeDAO(rules=[make_rule(1)])
    await run_daily(make_uow(dao), today=TODAY)
    second = await run_daily(make_uow(dao), today=TODAY)
    assert second.occurrences_created == 0


@pytest.mark.asyncio
async def test_run_daily_goes_on_when_one_rule_fails():
    dao = FakeDAO(rules=[make_rule(1), make_rule(2), make_rule(3)], fail_for=2)
    report = await run_daily(make_uow(dao), today=TODAY)
    assert report.failures == 1
    assert report.occurrences_created == 6  # rules 1 and 3 done
    assert (1, date(2026, 12, 10)) in dao.registered
    assert (3, date(2026, 12, 10)) in dao.registered


# -- time of the next run ---------------------------------------------------------------------

ROME = ZoneInfo("Europe/Rome")


def test_next_run_is_today_if_still_ahead():
    now = datetime(2026, 12, 15, 0, 0, tzinfo=ROME)
    assert seconds_until_next_run(now, time(0, 5)) == 300


def test_next_run_is_tomorrow_if_already_passed():
    now = datetime(2026, 12, 15, 12, 0, tzinfo=ROME)
    assert seconds_until_next_run(now, time(0, 5)) == 12 * 3600 + 300


def test_next_run_exactly_at_the_hour_waits_a_full_day():
    now = datetime(2026, 12, 15, 0, 5, tzinfo=ROME)
    assert seconds_until_next_run(now, time(0, 5)) == 24 * 3600
