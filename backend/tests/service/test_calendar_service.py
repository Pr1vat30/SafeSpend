"""Tests of the income/expense calendar (RF_CG_1): recurring rules (incomes, expenses and
goal allocations) and planned movements."""

from calendar import monthrange
from datetime import date
from decimal import Decimal

import pytest

from app.service.calendar.calendar_service import CalendarService, expand_occurrences
from tests.calendar_fakes import FakeCalendarDAO, planned, rule

# --- expand_occurrences ---------------------------------------------------------------------


def test_monthly_rule_on_day_10_in_every_future_month():
    """SC_RF_GES_10: the gym expense appears on day 10 of every future month."""
    first = date(2026, 11, 10)
    for year, month in ((2026, 12), (2027, 1), (2027, 2)):
        start, stop = date(year, month, 1), date(year, month, monthrange(year, month)[1])
        assert expand_occurrences(first, "monthly", start, stop) == [date(year, month, 10)]


def test_monthly_rule_on_day_31_falls_on_last_day_of_shorter_months():
    first = date(2027, 1, 31)
    occurrences = expand_occurrences(first, "monthly", date(2027, 1, 1), date(2027, 5, 31))
    assert occurrences == [
        date(2027, 1, 31),
        date(2027, 2, 28),
        date(2027, 3, 31),
        date(2027, 4, 30),
        date(2027, 5, 31),
    ]


def test_weekly_rule_crossing_two_months():
    first = date(2026, 11, 27)  # Friday
    occurrences = expand_occurrences(first, "weekly", date(2026, 12, 1), date(2026, 12, 31))
    assert occurrences == [date(2026, 12, d) for d in (4, 11, 18, 25)]


@pytest.mark.parametrize(
    ("year", "expected"),
    [(2027, date(2027, 2, 28)), (2028, date(2028, 2, 29))],
)
def test_yearly_rule_on_february_29(year, expected):
    first = date(2024, 2, 29)
    start, stop = date(year, 2, 1), date(year, 2, monthrange(year, 2)[1])
    assert expand_occurrences(first, "yearly", start, stop) == [expected]


def test_yearly_rule_only_in_its_month():
    first = date(2026, 3, 15)
    assert expand_occurrences(first, "yearly", date(2027, 4, 1), date(2027, 4, 30)) == []
    assert expand_occurrences(first, "yearly", date(2027, 3, 1), date(2027, 3, 31)) == [
        date(2027, 3, 15)
    ]


def test_end_date_in_the_middle_of_the_period_stops_the_rule():
    first = date(2026, 12, 1)
    end = date(2026, 12, 15)
    occurrences = expand_occurrences(first, "weekly", date(2026, 12, 1), date(2026, 12, 31), end)
    assert occurrences == [date(2026, 12, 1), date(2026, 12, 8), date(2026, 12, 15)]


def test_no_occurrence_before_the_first_date():
    first = date(2027, 1, 10)
    assert expand_occurrences(first, "monthly", date(2026, 12, 1), date(2026, 12, 31)) == []


@pytest.mark.parametrize("first", [date(2026, 12, 1), date(2027, 6, 1)])
def test_unknown_frequency_is_rejected_even_outside_the_period(first):
    with pytest.raises(ValueError):
        expand_occurrences(first, "daily", date(2026, 12, 1), date(2026, 12, 31))


# --- CalendarService.get_month --------------------------------------------------------------


async def december(dao: FakeCalendarDAO):
    """Calendar of December 2026 for user 1."""
    return await CalendarService(dao).get_month(user_id=1, year=2026, month=12)


async def test_get_month_groups_entries_by_day_with_totals():
    dao = FakeCalendarDAO(
        rules=[
            rule(),
            rule(
                id_recurring_rule=2,
                name="Stipendio",
                type="income",
                amount=Decimal("1500.00"),
                first_occurrence_date=date(2026, 10, 27),
                category_name="Stipendio",
            ),
            rule(
                id_recurring_rule=3,
                name="Netflix",
                amount=Decimal("12.99"),
                first_occurrence_date=date(2026, 1, 10),
                category_name="Abbonamenti",
            ),
        ]
    )
    calendar = await december(dao)

    period = (1, date(2026, 12, 1), date(2026, 12, 31))
    assert dao.calls == [("rules", *period), ("planned", *period)]
    assert calendar.month == "2026-12"
    assert calendar.total_income == Decimal("1500.00")
    assert calendar.total_expense == Decimal("62.99")

    assert [d.date for d in calendar.days] == [date(2026, 12, 10), date(2026, 12, 27)]
    day_10 = calendar.days[0]
    assert [e.name for e in day_10.entries] == ["Netflix", "Palestra"]
    assert day_10.total_expense == Decimal("62.99")
    assert day_10.total_income == Decimal("0.00")
    assert calendar.days[1].total_income == Decimal("1500.00")


async def test_get_month_counts_every_weekly_occurrence():
    dao = FakeCalendarDAO(
        rules=[
            rule(
                frequency="weekly", amount=Decimal("20.00"), first_occurrence_date=date(2026, 12, 2)
            )
        ]
    )
    calendar = await december(dao)

    assert len(calendar.days) == 5  # 2, 9, 16, 23, 30 December
    assert calendar.total_expense == Decimal("100.00")


async def test_get_month_shows_a_planned_movement_on_its_date():
    dao = FakeCalendarDAO(planned=[planned()])
    calendar = await december(dao)

    assert [d.date for d in calendar.days] == [date(2026, 12, 20)]
    (entry,) = calendar.days[0].entries
    assert entry.source == "planned"
    assert entry.source_id == 1
    assert entry.name == "Dentista"
    assert entry.frequency is None
    assert entry.is_installment is False
    assert calendar.total_expense == Decimal("150.00")


async def test_get_month_orders_a_day_by_type_then_name_with_the_totals():
    """Recurring and planned entries of the same day, goal allocations (RF_CG_1) included:
    incomes first, then expenses, then savings; by name within each type."""
    dao = FakeCalendarDAO(
        rules=[
            rule(),
            rule(
                id_recurring_rule=2,
                name="Accantonamento Vacanze",
                type="saving",
                amount=Decimal("100.00"),
                category_name="Risparmio",
            ),
        ],
        planned=[
            planned(planned_date=date(2026, 12, 10)),
            planned(
                id_planned_transaction=2,
                name="Rimborso",
                type="income",
                amount=Decimal("80.00"),
                planned_date=date(2026, 12, 10),
            ),
        ],
    )
    calendar = await december(dao)

    (day_10,) = calendar.days
    assert [(e.type, e.source, e.name) for e in day_10.entries] == [
        ("income", "planned", "Rimborso"),
        ("expense", "planned", "Dentista"),
        ("expense", "recurring", "Palestra"),
        ("saving", "recurring", "Accantonamento Vacanze"),
    ]
    assert day_10.total_income == calendar.total_income == Decimal("80.00")
    assert day_10.total_expense == calendar.total_expense == Decimal("200.00")
    assert day_10.total_saving == calendar.total_saving == Decimal("100.00")


async def test_get_month_without_movements_is_empty():
    calendar = await CalendarService(FakeCalendarDAO()).get_month(user_id=1, year=2027, month=2)

    assert calendar.days == []
    assert calendar.total_income == Decimal("0.00")
    assert calendar.total_expense == Decimal("0.00")
    assert calendar.total_saving == Decimal("0.00")
