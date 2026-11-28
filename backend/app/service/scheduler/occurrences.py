"""Due dates of recurring rules (RF_CF_2). Pure functions: no database, no clock.

The n-th occurrence is always computed from the FIRST occurrence (not from the previous one),
so a monthly rule starting on 31 January falls on 28/29 February and then goes back to 31 March.
The Cash Flow Engine can reuse these functions to place the occurrences in the projection.
"""

import calendar
from datetime import date, timedelta

_MAX_OCCURRENCES = 10_000  # safety net against endless loops (weekly for ~190 years)


def add_months(start: date, months: int) -> date:
    """Add calendar months, clamping the day (31 Jan + 1 month = 28/29 Feb)."""
    index = start.month - 1 + months
    year = start.year + index // 12
    month = index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def nth_occurrence(first: date, frequency: str, n: int) -> date:
    """Date of the n-th occurrence (n = 0 is the first one)."""
    if frequency == "weekly":
        return first + timedelta(weeks=n)
    if frequency == "monthly":
        return add_months(first, n)
    if frequency == "yearly":
        return add_months(first, 12 * n)
    raise ValueError(f"Frequenza sconosciuta: {frequency}")


def occurrences_between(
    first: date,
    frequency: str,
    after: date | None,
    upto: date,
    end: date | None = None,
) -> list[date]:
    """Due dates d with `after < d <= upto` and `d <= end` (no lower bound if `after` is None)."""
    limit = upto if end is None else min(upto, end)
    result: list[date] = []
    for n in range(_MAX_OCCURRENCES):
        due = nth_occurrence(first, frequency, n)
        if due > limit:
            break
        if after is None or due > after:
            result.append(due)
    return result
