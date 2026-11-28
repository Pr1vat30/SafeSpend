from calendar import monthrange
from datetime import date, timedelta

FREQUENCIES = ("weekly", "monthly", "yearly")


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def expand_occurrences(
    first: date, frequency: str, start: date, stop: date, end: date | None = None
) -> list[date]:
    if frequency not in FREQUENCIES:
        raise ValueError(f"Unknown frequency: {frequency}")

    lower = max(start, first)
    upper = stop if end is None else min(stop, end)
    if lower > upper:
        return []

    if frequency == "weekly":
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
    else:
        candidates = [
            _clamped(year, first.month, first.day) for year in range(lower.year, upper.year + 1)
        ]

    return [day for day in candidates if lower <= day <= upper]
