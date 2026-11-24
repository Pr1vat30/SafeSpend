"""Income/expense calendar (RF_CG_1).

The calendar shows the recurring rules and the planned movements of a month. Occurrences of the
recurring rules are computed on request (automatic projection on the future calendar), so nothing
is written to the database.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.api.dto.calendar.schema import CalendarDay, CalendarEntry, CalendarMonth
from app.dao.calendar.calendar_dao import CalendarDAO, CalendarPlanned, CalendarRule

ZERO = Decimal("0.00")
FREQUENCIES = ("weekly", "monthly", "yearly")


def _clamped(year: int, month: int, day: int) -> date:
    """`day` of the given month, or its last day when the month is shorter (31 → 30 April)."""
    return date(year, month, min(day, monthrange(year, month)[1]))


def expand_occurrences(
    first: date, frequency: str, start: date, stop: date, end: date | None = None
) -> list[date]:
    """Dates of a recurring rule between `start` and `stop` (both included).

    Monthly and yearly rules keep the day of `first`: when a month is shorter they fall on its
    last day, and go back to the original day in the following months.
    """
    if frequency not in FREQUENCIES:
        raise ValueError(f"Unknown frequency: {frequency}")

    lower = max(start, first)
    upper = stop if end is None else min(stop, end)
    if lower > upper:
        return []

    if frequency == "weekly":
        # First date from `lower` on that is a whole number of weeks after `first`.
        current = lower + timedelta(days=(-(lower - first).days) % 7)
        dates = []
        while current <= upper:
            dates.append(current)
            current += timedelta(days=7)
        return dates

    if frequency == "monthly":
        candidates = []
        year, month = lower.year, lower.month
        while (year, month) <= (upper.year, upper.month):
            candidates.append(_clamped(year, month, first.day))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    else:  # yearly
        candidates = [
            _clamped(year, first.month, first.day) for year in range(lower.year, upper.year + 1)
        ]

    return [day for day in candidates if lower <= day <= upper]


def _rule_entry(rule: CalendarRule) -> CalendarEntry:
    return CalendarEntry(
        source="recurring",
        source_id=rule.id_recurring_rule,
        name=rule.name,
        type=rule.type,
        amount=rule.amount,
        id_category=rule.id_category,
        category_name=rule.category_name,
        frequency=rule.frequency,
        is_installment=rule.is_installment,
    )


def _planned_entry(planned: CalendarPlanned) -> CalendarEntry:
    return CalendarEntry(
        source="planned",
        source_id=planned.id_planned_transaction,
        name=planned.name,
        type=planned.type,
        amount=planned.amount,
        id_category=planned.id_category,
        category_name=planned.category_name,
    )


def _day(day: date, entries: list[CalendarEntry]) -> CalendarDay:
    """Entries of a day in a stable order (incomes first, then by name), with the day totals."""
    entries = sorted(entries, key=lambda e: (e.type != "income", e.name, e.source, e.source_id))
    return CalendarDay(
        date=day,
        total_income=sum((e.amount for e in entries if e.type == "income"), ZERO),
        total_expense=sum((e.amount for e in entries if e.type == "expense"), ZERO),
        entries=entries,
    )


class CalendarService:
    def __init__(self, dao: CalendarDAO):
        self.dao = dao

    async def get_month(self, user_id: int, year: int, month: int) -> CalendarMonth:
        """Recurring and planned incomes and expenses of the user in a month, grouped by day."""
        start = date(year, month, 1)
        stop = date(year, month, monthrange(year, month)[1])

        by_day: dict[date, list[CalendarEntry]] = defaultdict(list)
        for rule in await self.dao.find_active_rules(user_id, start, stop):
            occurrences = expand_occurrences(
                rule.first_occurrence_date, rule.frequency, start, stop, rule.end_date
            )
            for day in occurrences:
                by_day[day].append(_rule_entry(rule))
        for planned in await self.dao.find_planned(user_id, start, stop):
            by_day[planned.planned_date].append(_planned_entry(planned))

        days = [_day(day, by_day[day]) for day in sorted(by_day)]
        return CalendarMonth(
            month=f"{year:04d}-{month:02d}",
            total_income=sum((d.total_income for d in days), ZERO),
            total_expense=sum((d.total_expense for d in days), ZERO),
            days=days,
        )
