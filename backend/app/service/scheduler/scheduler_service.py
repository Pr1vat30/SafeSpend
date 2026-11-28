"""Daily Scheduler (RF_CF_2, RF_CF_6, RNF_AF_6).

Once a day (and at every start, to recover from a stop) it:
1. registers every due occurrence of the active recurring rules as a transaction, once only;
2. ends the rules whose end date has passed;
3. registers the planned expenses whose date has come;
4. asks for confirmation of the planned incomes whose date has come.

Each rule is processed in its own database transaction: if one fails, the others go on and the
failed one is retried at the next run. The "day" is the Europe/Rome one.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config.logging import get_logger
from app.dao.scheduler.scheduler_dao import RuleRow, SchedulerDAO
from app.service.scheduler.occurrences import occurrences_between

logger = get_logger(__name__)

# A unit of work opens a database session, yields a SchedulerDAO and commits (or rolls back).
UnitOfWork = Callable[[], AbstractAsyncContextManager[SchedulerDAO]]


def rome_today() -> date:
    """Today's date in Europe/Rome, the reference time zone of the system (RNF_AF_6)."""
    return datetime.now(ZoneInfo("Europe/Rome")).date()


@dataclass
class SchedulerReport:
    day: date | None = None
    rules_checked: int = 0
    occurrences_created: int = 0
    rules_terminated: int = 0
    planned_expenses_recorded: int = 0
    incomes_awaiting_confirmation: int = 0
    failures: int = 0


async def process_rule(dao: SchedulerDAO, rule: RuleRow, today: date) -> tuple[int, bool]:
    """Register the due occurrences of one rule. Returns (created, terminated)."""
    due = occurrences_between(
        rule.first_occurrence_date,
        rule.frequency,
        rule.last_processed_occurrence_date,
        today,
        rule.end_date,
    )
    created = 0
    for occurrence_date in due:
        if await dao.insert_occurrence(rule, occurrence_date):
            created += 1

    # Every occurrence up to the end date has been handled once the end date is reached.
    terminated = rule.end_date is not None and rule.end_date <= today
    last_processed = due[-1] if due else rule.last_processed_occurrence_date
    if due or terminated:
        await dao.update_rule_progress(rule.id_recurring_rule, last_processed, terminated)
    return created, terminated


async def run_daily(unit_of_work: UnitOfWork, today: date | None = None) -> SchedulerReport:
    """One full pass of the Scheduler. Safe to run more than once a day (idempotent)."""
    today = today or rome_today()
    report = SchedulerReport(day=today)

    async with unit_of_work() as dao:
        rules = await dao.list_active_rules()

    for rule in rules:
        report.rules_checked += 1
        try:
            async with unit_of_work() as dao:
                created, terminated = await process_rule(dao, rule, today)
        except Exception:
            logger.exception(
                "Scheduler: errore sulla voce %s, riprovo al prossimo ciclo", rule.id_recurring_rule
            )
            report.failures += 1
            continue
        report.occurrences_created += created
        report.rules_terminated += int(terminated)

    try:
        async with unit_of_work() as dao:
            report.planned_expenses_recorded = await dao.record_due_planned_expenses(today)
            report.incomes_awaiting_confirmation = await dao.mark_due_incomes_pending(today)
    except Exception:
        logger.exception("Scheduler: errore sui movimenti pianificati, riprovo al prossimo ciclo")
        report.failures += 1

    logger.info("Scheduler %s: %s", today, report)
    return report
