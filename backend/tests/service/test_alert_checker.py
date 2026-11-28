"""Unit tests of AlertChecker (UC_RF_CG_3) with fake DAO and projector.

Covers: condition true → alert opened, condition gone → alert resolved, calculation failed →
nothing changed (error flow 2.a1), configuration not completed → skipped, daily STS saved.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.dao.alert.alert_dao import PlannedExpenseRow, RecurringExpenseRow
from app.service.alert.alert_checker import AlertChecker, upcoming_expenses
from app.service.alert.alert_rules import ProjectionSnapshot
from app.service.alert.alert_service import AlertService
from tests.service.test_alert_service import FakeDAO as FakeAlertDAO

TODAY = date(2026, 11, 20)
USER = 1


class FakeDAO(FakeAlertDAO):
    def __init__(self, upcoming=None, previous_sts=None):
        super().__init__()
        self.upcoming = upcoming or []
        self.previous_sts = previous_sts
        self.saved_sts = {}

    async def find_planned_expenses(self, user_id, start, end):
        return [p for p in self.upcoming if start <= p.planned_date <= end]

    async def find_active_expense_rules(self, user_id, start, end):
        return []

    async def get_previous_daily_sts(self, user_id, today):
        return self.previous_sts

    async def save_daily_sts(self, user_id, today, daily_sts):
        self.saved_sts[(user_id, today)] = daily_sts


def snapshot(risk="Sostenibile", minimum="500", daily="20"):
    return ProjectionSnapshot(
        minimum_balance=Decimal(minimum),
        critical_date=date(2026, 11, 23),
        daily_safe_to_spend=Decimal(daily),
        risk_level=risk,
        safety_buffer=Decimal("200"),
    )


def make_checker(dao, result):
    async def projector(user_id, as_of):
        if isinstance(result, Exception):
            raise result
        return result

    service = AlertService(dao, now=lambda: datetime(2026, 11, 20, tzinfo=UTC))
    return AlertChecker(dao, service, projector)


def open_types(dao):
    return sorted(a.type for a in dao.alerts.values() if a.status in ("active", "read"))


async def test_true_conditions_open_alerts_and_sts_is_saved():
    insurance = PlannedExpenseRow("Assicurazione auto", Decimal("480"), date(2026, 11, 23))
    dao = FakeDAO(upcoming=[insurance], previous_sts=Decimal("10"))
    ok = await make_checker(dao, snapshot("Attenzione", "150", daily="5")).check_user(USER, TODAY)
    assert ok is True
    assert open_types(dao) == ["impending_expense", "risk_level", "sts_drop"]
    assert dao.saved_sts == {(USER, TODAY): Decimal("5")}


async def test_condition_no_longer_true_resolves_alert():
    dao = FakeDAO()
    await make_checker(dao, snapshot("Attenzione", "150")).check_user(USER, TODAY)
    assert open_types(dao) == ["risk_level"]
    await make_checker(dao, snapshot("Sostenibile", "240")).check_user(USER, TODAY)
    assert open_types(dao) == []


async def test_same_condition_next_day_creates_no_duplicate():
    dao = FakeDAO()
    checker = make_checker(dao, snapshot("Critico", "-50"))
    await checker.check_user(USER, TODAY)
    await checker.check_user(USER, date(2026, 11, 21))
    assert len(dao.alerts) == 1


async def test_calculation_failure_changes_nothing():
    dao = FakeDAO()
    await make_checker(dao, snapshot("Attenzione", "150")).check_user(USER, TODAY)
    before = {a.id_alert: a.status for a in dao.alerts.values()}
    ok = await make_checker(dao, RuntimeError("db down")).check_user(USER, TODAY)
    assert ok is False
    assert {a.id_alert: a.status for a in dao.alerts.values()} == before


async def test_configuration_not_completed_is_skipped():
    dao = FakeDAO()
    ok = await make_checker(dao, None).check_user(USER, TODAY)
    assert ok is True
    assert dao.alerts == {} and dao.saved_sts == {}


def rule(first, frequency="monthly", last_processed=None, end=None, name="Affitto"):
    return RecurringExpenseRow(name, Decimal("650"), frequency, first, end, last_processed)


def test_upcoming_expenses_merges_planned_and_rule_occurrences():
    planned = [PlannedExpenseRow("Dentista", Decimal("300"), date(2026, 11, 22))]
    rules = [rule(date(2026, 10, 21))]
    result = upcoming_expenses(planned, rules, TODAY, date(2026, 11, 23))
    assert [(e.name, e.due_date) for e in result] == [
        ("Affitto", date(2026, 11, 21)),
        ("Dentista", date(2026, 11, 22)),
    ]


def test_upcoming_expenses_skips_occurrences_already_registered():
    rules = [rule(date(2026, 11, 13), "weekly", last_processed=date(2026, 11, 20))]
    result = upcoming_expenses([], rules, TODAY, date(2026, 11, 27))
    assert [e.due_date for e in result] == [date(2026, 11, 27)]


def test_upcoming_expenses_respects_end_date_of_the_rule():
    rules = [rule(date(2026, 10, 21), end=date(2026, 11, 1))]
    assert upcoming_expenses([], rules, TODAY, date(2026, 11, 30)) == []
