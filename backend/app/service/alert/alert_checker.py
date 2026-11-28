"""Check of the alert conditions for one user (UC_RF_CG_3, steps 2-4 and alternative flows).

1. compute the current projection with the Cash Flow Engine;
2. evaluate conditions (a), (b) and (c) of RF_CG_3 (`alert_rules.evaluate`);
3. open or refresh the alert of every true condition, resolve the others;
4. save today's daily STS, the reference for tomorrow's condition (c).

Error flow 2.a1: if the projection cannot be computed, nothing is created or changed and the
error is logged; the check is repeated at the next cycle. A user without a complete financial
profile (entry condition not met) is simply skipped.
"""

from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from app.config.logging import get_logger
from app.dao.alert.alert_dao import AlertDAO, PlannedExpenseRow, RecurringExpenseRow
from app.service.alert.alert_rules import (
    IMPENDING_DAYS,
    ProjectionSnapshot,
    UpcomingExpense,
    evaluate,
)
from app.service.alert.alert_service import AlertService
from app.service.scheduler.occurrences import occurrences_between

logger = get_logger(__name__)

# Returns the projection of a user as of a date, or None if it is not computable yet
# (initial configuration not completed). Any exception means "calculation failed".
Projector = Callable[[int, date], Awaitable[ProjectionSnapshot | None]]


def upcoming_expenses(
    planned: list[PlannedExpenseRow],
    rules: list[RecurringExpenseRow],
    start: date,
    end: date,
) -> list[UpcomingExpense]:
    """Planned expenses plus the not yet registered occurrences of the rules in [start, end]."""
    expenses = [UpcomingExpense(p.name, p.amount, p.planned_date) for p in planned]
    before_start = start - timedelta(days=1)
    for rule in rules:
        after = before_start
        if rule.last_processed_occurrence_date is not None:
            after = max(after, rule.last_processed_occurrence_date)
        for due in occurrences_between(
            rule.first_occurrence_date, rule.frequency, after, end, rule.end_date
        ):
            expenses.append(UpcomingExpense(rule.name, rule.amount, due))
    return sorted(expenses, key=lambda e: (e.due_date, e.name))


class AlertChecker:
    def __init__(self, dao: AlertDAO, service: AlertService, projector: Projector):
        self.dao = dao
        self.service = service
        self.projector = projector

    async def check_user(self, user_id: int, today: date) -> bool:
        """Run the check. Returns False if the projection could not be computed."""
        try:
            projection = await self.projector(user_id, today)
        except Exception:
            logger.exception("Alert: proiezione non calcolabile per l'utente %s", user_id)
            return False
        if projection is None:
            return True  # configuration not completed: no alert to show

        end = max(today + timedelta(days=IMPENDING_DAYS), projection.critical_date)
        upcoming = upcoming_expenses(
            await self.dao.find_planned_expenses(user_id, today, end),
            await self.dao.find_active_expense_rules(user_id, today, end),
            today,
            end,
        )
        previous = await self.dao.get_previous_daily_sts(user_id, today)

        for alert_type, message in evaluate(projection, upcoming, previous, today).items():
            if message is None:
                await self.service.resolve_alert(user_id, alert_type)
            else:
                await self.service.raise_alert(user_id, alert_type, message, today)

        await self.dao.save_daily_sts(user_id, today, projection.daily_safe_to_spend)
        return True
