"""Income/expense calendar (RF_CG_1).

Occurrences are computed on request from the active recurring rules (automatic projection on the
future calendar), so nothing is written to the database.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.api.dto.calendar.schema import CalendarDay, CalendarEntry, CalendarMonth
from app.dao.calendar.calendar_dao import CalendarDAO, CalendarRule

ZERO = Decimal("0.00")


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
    lower = max(start, first)
    upper = stop if end is None else min(stop, end)
    if lower > upper:
        return []

    if frequency == "weekly":
        offset = -(lower - first).days % 7
        current = lower + timedelta(days=offset)
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
    elif frequency == "yearly":
        candidates = [
            _clamped(year, first.month, first.day) for year in range(lower.year, upper.year + 1)
        ]
    else:
        raise ValueError(f"Unknown frequency: {frequency}")

    return [day for day in candidates if lower <= day <= upper]


def _totals(entries: list[CalendarEntry]) -> tuple[Decimal, Decimal]:
    income = sum((e.amount for e in entries if e.type == "income"), ZERO)
    expense = sum((e.amount for e in entries if e.type == "expense"), ZERO)
    return income, expense


def _entry(rule: CalendarRule) -> CalendarEntry:
    return CalendarEntry(
        id_recurring_rule=rule.id_recurring_rule,
        name=rule.name,
        type=rule.type,
        amount=rule.amount,
        frequency=rule.frequency,
        is_installment=rule.is_installment,
        id_category=rule.id_category,
        category_name=rule.category_name,
    )


class CalendarService:
    def __init__(self, dao: CalendarDAO):
        self.dao = dao

    async def get_month(self, user_id: int, year: int, month: int) -> CalendarMonth:
        """Recurring incomes and expenses of the user in the given month, grouped by day."""
        start = date(year, month, 1)
        stop = date(year, month, monthrange(year, month)[1])
        rules = await self.dao.find_active_rules(user_id, start, stop)

        by_day: dict[date, list[CalendarEntry]] = defaultdict(list)
        for rule in rules:
            dates = expand_occurrences(
                rule.first_occurrence_date, rule.frequency, start, stop, rule.end_date
            )
            for day in dates:
                by_day[day].append(_entry(rule))

        days = []
        for day in sorted(by_day):
            entries = sorted(by_day[day], key=lambda e: (e.type, e.name, e.id_recurring_rule))
            income, expense = _totals(entries)
            days.append(
                CalendarDay(date=day, total_income=income, total_expense=expense, entries=entries)
            )

        all_entries = [entry for d in days for entry in d.entries]
        income, expense = _totals(all_entries)
        return CalendarMonth(
            month=f"{year:04d}-{month:02d}",
            total_income=income,
            total_expense=expense,
            days=days,
        )
