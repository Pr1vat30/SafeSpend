from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel


@dataclass(frozen=True)
class ProjectionSettings:
    safety_buffer: Decimal
    horizon_days: int
    estimated_variable_expenses: Decimal | None


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

    @asynccontextmanager
    async def projection_reader(self) -> AsyncIterator["CashFlowDAO"]:
        """Legge una proiezione da una fotografia coerente dei dati confermati."""
        bind = self.db.bind
        if bind is None:
            raise RuntimeError("La sessione del cashflow non è associata a un database.")

        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        read_engine = engine.execution_options(isolation_level="REPEATABLE READ")

        async with AsyncSession(read_engine, expire_on_commit=False) as session:
            async with session.begin():
                yield CashFlowDAO(session)

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
