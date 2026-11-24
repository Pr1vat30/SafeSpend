"""Test data and fake DAO shared by the calendar tests (RF_CG_1)."""

from datetime import date
from decimal import Decimal

from app.dao.calendar.calendar_dao import CalendarPlanned, CalendarRule


def rule(**overrides) -> CalendarRule:
    """Recurring rule of the scenario SC_RF_GES_10 (gym, 50 € on day 10), with `overrides`."""
    values = {
        "id_recurring_rule": 1,
        "name": "Palestra",
        "type": "expense",
        "amount": Decimal("50.00"),
        "frequency": "monthly",
        "first_occurrence_date": date(2026, 11, 10),
        "end_date": None,
        "is_installment": False,
        "id_category": 3,
        "category_name": "Salute e Fitness",
    }
    return CalendarRule(**(values | overrides))


def planned(**overrides) -> CalendarPlanned:
    """One-off planned expense (dentist, 150 € on 20 December 2026), with `overrides`."""
    values = {
        "id_planned_transaction": 1,
        "name": "Dentista",
        "type": "expense",
        "amount": Decimal("150.00"),
        "planned_date": date(2026, 12, 20),
        "id_category": 3,
        "category_name": "Salute e Fitness",
    }
    return CalendarPlanned(**(values | overrides))


class FakeCalendarDAO:
    """Returns fixed rules and planned movements, and records the requested periods."""

    def __init__(self, rules=(), planned=()):
        self.rules = list(rules)
        self.planned = list(planned)
        self.calls: list[tuple[str, int, date, date]] = []

    async def find_active_rules(self, user_id: int, start: date, stop: date):
        self.calls.append(("rules", user_id, start, stop))
        return self.rules

    async def find_planned(self, user_id: int, start: date, stop: date):
        self.calls.append(("planned", user_id, start, stop))
        return self.planned
