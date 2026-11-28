"""Conditions of the alerts (RF_CG_3, UC_RF_CG_3 step 3). Pure functions: no database, no clock.

(a) `risk_level`: the risk level of the current projection is Attenzione or Critico;
(b) `impending_expense`: a recurring or planned expense greater than the daily STS is due
    within 3 days (today included);
(c) `sts_drop`: the daily STS fell by more than 30% compared with the previous day.

`evaluate` returns, for every alert type, the message to show (condition true) or None
(condition false, so an open alert of that type must be resolved).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

IMPENDING_DAYS = 3
STS_DROP_THRESHOLD = Decimal("0.30")
RISKY_LEVELS = ("Attenzione", "Critico")

ALERT_TYPES = ("risk_level", "impending_expense", "sts_drop")


@dataclass(frozen=True)
class ProjectionSnapshot:
    """The values of a Cash Flow projection that the alerts need."""

    minimum_balance: Decimal
    critical_date: date
    daily_safe_to_spend: Decimal
    risk_level: str  # "Sostenibile", "Attenzione" or "Critico"
    safety_buffer: Decimal


@dataclass(frozen=True)
class UpcomingExpense:
    """A future recurring occurrence or planned expense."""

    name: str
    amount: Decimal
    due_date: date


def format_euro(amount: Decimal) -> str:
    """Italian format: 1.500 €, 5,68 €, −250 € (no decimals for whole amounts)."""
    sign = "−" if amount < 0 else ""
    value = abs(amount).quantize(Decimal("0.01"))
    if value == value.to_integral_value():
        text = f"{int(value):,}".replace(",", ".")
    else:
        text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{text} €"


def format_day(day: date, today: date) -> str:
    """ "15" within the current month (as in the RAD examples), "15/12" otherwise."""
    if (day.year, day.month) == (today.year, today.month):
        return str(day.day)
    return f"{day.day}/{day.month:02d}"


def risk_message(
    projection: ProjectionSnapshot, expenses_on_critical_date: list[UpcomingExpense], today: date
) -> str | None:
    """Condition (a). The message names the biggest expense of the Critical Date, if any."""
    if projection.risk_level not in RISKY_LEVELS:
        return None
    day = format_day(projection.critical_date, today)
    balance = format_euro(projection.minimum_balance)
    if expenses_on_critical_date:
        biggest = max(expenses_on_critical_date, key=lambda e: e.amount)
        message = (
            f"«{biggest.name}» di {format_euro(biggest.amount)} del {day} "
            f"porta il saldo a {balance}"
        )
    else:
        message = f"Il {day} il saldo previsto scende a {balance}"
    if projection.risk_level == "Attenzione":
        message += f", sotto il tuo Safety Buffer di {format_euro(projection.safety_buffer)}"
    return message


def impending_message(
    projection: ProjectionSnapshot, upcoming: list[UpcomingExpense], today: date
) -> str | None:
    """Condition (b): expenses due within 3 days that are greater than the daily STS."""
    last_day = today + timedelta(days=IMPENDING_DAYS)
    due = [
        e
        for e in upcoming
        if today <= e.due_date <= last_day and e.amount > projection.daily_safe_to_spend
    ]
    if not due:
        return None
    due.sort(key=lambda e: (e.due_date, -e.amount))
    first = due[0]
    message = (
        f"«{first.name}» di {format_euro(first.amount)} scade il "
        f"{format_day(first.due_date, today)} e supera il tuo STS giornaliero di "
        f"{format_euro(projection.daily_safe_to_spend)}"
    )
    others = len(due) - 1
    if others == 1:
        message += " (e c'è un'altra uscita nei prossimi 3 giorni)"
    elif others > 1:
        message += f" (e ci sono altre {others} uscite nei prossimi 3 giorni)"
    return message


def sts_drop_message(previous_daily_sts: Decimal | None, current_daily_sts: Decimal) -> str | None:
    """Condition (c): (previous - current) / previous > 30%."""
    if previous_daily_sts is None or previous_daily_sts <= 0:
        return None
    drop = (previous_daily_sts - current_daily_sts) / previous_daily_sts
    if drop <= STS_DROP_THRESHOLD:
        return None
    return (
        f"Il tuo STS giornaliero è sceso da {format_euro(previous_daily_sts)} "
        f"a {format_euro(current_daily_sts)}"
    )


def evaluate(
    projection: ProjectionSnapshot,
    upcoming: list[UpcomingExpense],
    previous_daily_sts: Decimal | None,
    today: date,
) -> dict[str, str | None]:
    """Message per alert type; None means the condition is false."""
    on_critical_date = [e for e in upcoming if e.due_date == projection.critical_date]
    return {
        "risk_level": risk_message(projection, on_critical_date, today),
        "impending_expense": impending_message(projection, upcoming, today),
        "sts_drop": sts_drop_message(previous_daily_sts, projection.daily_safe_to_spend),
    }
