"""Tests of the due-date calculation of recurring rules (pure functions, no database).

Category Partition: frequency (weekly, monthly, yearly), month length (31st, 29th February),
bounds (after, upto, end) and empty results.
"""

from datetime import date

import pytest

from app.service.scheduler.occurrences import add_months, nth_occurrence, occurrences_between


def test_add_months_clamps_to_the_last_day_of_the_month():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)  # leap year
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)  # year change


def test_nth_occurrence_is_anchored_to_the_first_date():
    first = date(2026, 1, 31)
    assert nth_occurrence(first, "monthly", 1) == date(2026, 2, 28)
    assert nth_occurrence(first, "monthly", 2) == date(2026, 3, 31)  # back to the 31st
    assert nth_occurrence(date(2026, 11, 24), "weekly", 2) == date(2026, 12, 8)
    assert nth_occurrence(date(2028, 2, 29), "yearly", 1) == date(2029, 2, 28)
    assert nth_occurrence(date(2028, 2, 29), "yearly", 4) == date(2032, 2, 29)


def test_unknown_frequency_is_rejected():
    with pytest.raises(ValueError):
        nth_occurrence(date(2026, 1, 1), "daily", 1)


def test_monthly_rule_never_processed_includes_the_first_day():
    result = occurrences_between(date(2026, 10, 10), "monthly", None, date(2026, 12, 20))
    assert result == [date(2026, 10, 10), date(2026, 11, 10), date(2026, 12, 10)]


def test_after_excludes_the_already_processed_date():
    result = occurrences_between(
        date(2026, 10, 10), "monthly", date(2026, 11, 10), date(2026, 12, 20)
    )
    assert result == [date(2026, 12, 10)]


def test_upto_is_inclusive():
    assert occurrences_between(date(2026, 12, 10), "monthly", None, date(2026, 12, 10)) == [
        date(2026, 12, 10)
    ]


def test_end_date_limits_the_occurrences_and_is_inclusive():
    result = occurrences_between(
        date(2026, 10, 10), "monthly", None, date(2027, 6, 1), end=date(2026, 12, 10)
    )
    assert result == [date(2026, 10, 10), date(2026, 11, 10), date(2026, 12, 10)]


def test_first_occurrence_in_the_future_gives_nothing():
    assert occurrences_between(date(2027, 1, 10), "monthly", None, date(2026, 12, 20)) == []


def test_nothing_new_after_the_last_processed_date():
    assert (
        occurrences_between(date(2026, 10, 10), "monthly", date(2026, 12, 10), date(2026, 12, 20))
        == []
    )


def test_weekly_catch_up_after_a_stop_returns_every_missed_week():
    result = occurrences_between(date(2026, 11, 2), "weekly", date(2026, 11, 9), date(2026, 11, 30))
    assert result == [date(2026, 11, 16), date(2026, 11, 23), date(2026, 11, 30)]


def test_yearly_rule_on_29_february():
    result = occurrences_between(date(2024, 2, 29), "yearly", None, date(2026, 12, 31))
    assert result == [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)]
