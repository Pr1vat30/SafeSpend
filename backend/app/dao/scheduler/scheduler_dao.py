"""Queries used by the daily Scheduler. `flush`/commit are handled by the unit of work.

The Scheduler writes on tables owned by other modules (`transaction`, `planned_transaction`),
so it uses plain SQL instead of their ORM models. Every INSERT is idempotent: it relies on the
UNIQUE constraints of the schema (`uq_rule_occurrence`, `uq_transaction_planned`).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class RuleRow:
    """The columns of an active recurring rule that the Scheduler needs."""

    id_recurring_rule: int
    id_user: int
    id_category: int
    name: str
    type: str
    amount: Decimal
    frequency: str
    first_occurrence_date: date
    end_date: date | None
    last_processed_occurrence_date: date | None


class SchedulerDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active_rules(self) -> list[RuleRow]:
        result = await self.db.execute(
            text(
                "SELECT id_recurring_rule, id_user, id_category, name, type, amount, frequency, "
                "first_occurrence_date, end_date, last_processed_occurrence_date "
                "FROM recurring_rule WHERE status = 'active' ORDER BY id_recurring_rule"
            )
        )
        return [RuleRow(**row._mapping) for row in result]

    async def insert_occurrence(self, rule: RuleRow, occurrence_date: date) -> bool:
        """Register one occurrence as a transaction. False if it already existed."""
        # A 'saving' rule (goal contribution) is an expense for the balance.
        transaction_type = "expense" if rule.type == "saving" else rule.type
        result = await self.db.execute(
            text(
                'INSERT INTO "transaction" (id_user, id_category, id_recurring_rule, '
                "description, type, amount, transaction_date, occurrence_date, origin) "
                "VALUES (:uid, :cid, :rid, :descr, :type, :amount, :odate, :odate, 'recurring') "
                "ON CONFLICT (id_recurring_rule, occurrence_date) DO NOTHING "
                "RETURNING id_transaction"
            ),
            {
                "uid": rule.id_user,
                "cid": rule.id_category,
                "rid": rule.id_recurring_rule,
                "descr": rule.name,
                "type": transaction_type,
                "amount": rule.amount,
                "odate": occurrence_date,
            },
        )
        return result.first() is not None

    async def update_rule_progress(
        self, rule_id: int, last_processed: date | None, terminate: bool
    ) -> None:
        await self.db.execute(
            text(
                "UPDATE recurring_rule SET last_processed_occurrence_date = :last, "
                "status = CASE WHEN CAST(:terminate AS boolean) THEN 'terminated' ELSE status END "
                "WHERE id_recurring_rule = :rid"
            ),
            {"last": last_processed, "terminate": terminate, "rid": rule_id},
        )

    async def record_due_planned_expenses(self, today: date) -> int:
        """Turn the planned expenses whose date has come into transactions. Returns how many."""
        result = await self.db.execute(
            text(
                "WITH due AS ("
                "  SELECT id_planned_transaction, id_user, id_category, "
                "         COALESCE(description, name) AS descr, amount, planned_date "
                "  FROM planned_transaction "
                "  WHERE status = 'planned' AND type = 'expense' AND planned_date <= :today "
                "  FOR UPDATE"
                "), ins AS ("
                '  INSERT INTO "transaction" (id_user, id_category, id_planned_transaction, '
                "    description, type, amount, transaction_date, origin) "
                "  SELECT id_user, id_category, id_planned_transaction, descr, 'expense', "
                "    amount, planned_date, 'planned' FROM due "
                "  ON CONFLICT (id_planned_transaction) DO NOTHING "
                "  RETURNING id_planned_transaction"
                ") "
                "UPDATE planned_transaction p SET status = 'recorded' FROM due "
                "WHERE p.id_planned_transaction = due.id_planned_transaction"
            ),
            {"today": today},
        )
        return result.rowcount

    async def mark_due_incomes_pending(self, today: date) -> int:
        """Planned incomes whose date has come wait for the user's confirmation (RF_CF_6)."""
        result = await self.db.execute(
            text(
                "UPDATE planned_transaction SET status = 'pending_confirmation' "
                "WHERE status = 'planned' AND type = 'income' AND planned_date <= :today"
            ),
            {"today": today},
        )
        return result.rowcount
