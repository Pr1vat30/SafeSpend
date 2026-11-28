from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel


@dataclass(frozen=True)
class ProjectionSettings:
    safety_buffer: Decimal
    horizon_days: int
    estimated_variable_expenses: Decimal | None


@dataclass(frozen=True)
class ReconciledBalance:
    amount: Decimal
    reconciliation_date: date


@dataclass(frozen=True)
class PlannedMovement:
    id_planned_transaction: int
    name: str
    type: str
    amount: Decimal
    planned_date: date


class CashFlowDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_starting_balance(self, id_user: int, as_of: date) -> Decimal | None:
        query = text("""
            SELECT s.real_balance + COALESCE((
                SELECT SUM(
                    CASE WHEN t.type = 'expense' THEN -t.amount ELSE t.amount END
                )
                FROM "transaction" AS t
                WHERE t.id_user = s.id_user
                  AND t.transaction_date > s.reconciliation_date
                  AND t.transaction_date <= :as_of
            ), 0)
            FROM balance_snapshot AS s
            WHERE s.id_user = :id_user
              AND s.reconciliation_date <= :as_of
            ORDER BY s.reconciliation_date DESC, s.created_at DESC, s.id_snapshot DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {"id_user": id_user, "as_of": as_of})
        return result.scalar_one_or_none()

    async def get_first_reconciliation_date(self, id_user: int, as_of: date) -> date | None:
        query = text("""
            SELECT MIN(reconciliation_date)
            FROM balance_snapshot
            WHERE id_user = :id_user
              AND reconciliation_date <= :as_of
        """)

        result = await self.db.execute(query, {"id_user": id_user, "as_of": as_of})
        return result.scalar_one()

    async def get_daily_variable_expenses(
        self, id_user: int, start_date: date, as_of: date
    ) -> dict[tuple[date, int], Decimal]:
        query = text("""
            SELECT transaction_date, id_category, SUM(amount) AS total
            FROM "transaction"
            WHERE id_user = :id_user
              AND transaction_date >= :start_date
              AND transaction_date < :as_of
              AND type = 'expense'
              AND origin IN ('manual', 'ocr', 'planned')
            GROUP BY transaction_date, id_category
            ORDER BY transaction_date, id_category
        """)

        result = await self.db.execute(
            query,
            {"id_user": id_user, "start_date": start_date, "as_of": as_of},
        )
        return {(day, category_id): total for day, category_id, total in result}

    async def get_projection_settings(self, id_user: int) -> ProjectionSettings | None:
        query = text("""
            SELECT safety_buffer, horizon_days, estimated_variable_expenses
            FROM financial_profile
            WHERE id_user = :id_user
        """)

        result = await self.db.execute(query, {"id_user": id_user})
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return ProjectionSettings(
            safety_buffer=row["safety_buffer"],
            horizon_days=row["horizon_days"],
            estimated_variable_expenses=row["estimated_variable_expenses"],
        )

    async def get_recurring_rules(
        self, id_user: int, start_date: date, end_date: date
    ) -> list[RecurringRuleModel]:
        rule = RecurringRuleModel

        query = (
            select(rule)
            .where(
                rule.id_user == id_user,
                rule.status == "active",
                rule.first_occurrence_date <= end_date,
                or_(rule.end_date.is_(None), rule.end_date >= start_date),
                or_(
                    rule.last_processed_occurrence_date.is_(None),
                    rule.last_processed_occurrence_date < end_date,
                ),
            )
            .order_by(rule.first_occurrence_date, rule.id_recurring_rule)
        )

        result = await self.db.scalars(query)
        return list(result.all())

    async def get_income_rules(self, id_user: int, as_of: date) -> list[RecurringRuleModel]:
        rule = RecurringRuleModel

        query = select(rule).where(
            rule.id_user == id_user,
            rule.type == "income",
            rule.status == "active",
            or_(rule.end_date.is_(None), rule.end_date > as_of),
        )

        result = await self.db.scalars(query)
        return list(result.all())

    async def get_planned_transactions(
        self, id_user: int, start_date: date, end_date: date
    ) -> list[PlannedMovement]:
        query = text("""
            SELECT id_planned_transaction, name, type, amount, planned_date
            FROM planned_transaction
            WHERE id_user = :id_user
                AND planned_date BETWEEN :start_date AND :end_date
                AND (
                    status = 'planned'
                    OR (
                        type = 'income'
                        AND status = 'pending_confirmation'
                        AND planned_date = :start_date
                    )
                )
            ORDER BY planned_date, id_planned_transaction
        """)

        result = await self.db.execute(
            query,
            {"id_user": id_user, "start_date": start_date, "end_date": end_date},
        )
        return [PlannedMovement(**row) for row in result.mappings()]

    async def get_reconciled_balance(self, id_user: int, as_of: date) -> ReconciledBalance | None:
        query = text("""
            SELECT real_balance, reconciliation_date
            FROM balance_snapshot
            WHERE id_user = :id_user
              AND reconciliation_date <= :as_of
            ORDER BY reconciliation_date DESC, created_at DESC, id_snapshot DESC
            LIMIT 1
        """)

        result = await self.db.execute(query, {"id_user": id_user, "as_of": as_of})
        row = result.mappings().one_or_none()

        if row is None:
            return None

        return ReconciledBalance(
            amount=row["real_balance"],
            reconciliation_date=row["reconciliation_date"],
        )
