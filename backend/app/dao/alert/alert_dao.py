"""Data access for alerts (SDD 4.8, AlertDAO). Queries only: `flush()`, never `commit()`.

The checks read tables owned by other modules (`planned_transaction`, `recurring_rule`,
`financial_profile`) with plain SQL, like the Scheduler does, and keep the daily STS of the
last days in `daily_sts` to detect a drop compared with the previous day.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert.alert_model import AlertModel

DAILY_STS_KEPT_DAYS = 7


@dataclass(frozen=True)
class PlannedExpenseRow:
    name: str
    amount: Decimal
    planned_date: date


@dataclass(frozen=True)
class RecurringExpenseRow:
    name: str
    amount: Decimal
    frequency: str
    first_occurrence_date: date
    end_date: date | None
    last_processed_occurrence_date: date | None


# An alert is "open" while the dashboard shows it. The schema allows one open alert per user
# and type (unique index `uq_alert_user_type_open`).
OPEN_STATUSES = ("active", "read")


class AlertDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, alert: AlertModel) -> AlertModel:
        self.db.add(alert)
        return await self.save(alert)

    async def save(self, alert: AlertModel) -> AlertModel:
        """Write pending changes and reload the row (picks up server-side defaults)."""
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def get_by_id_for_user(self, alert_id: int, user_id: int) -> AlertModel | None:
        """Return the alert only if it belongs to the user (RNF_SE_3)."""
        stmt = select(AlertModel).where(
            AlertModel.id_alert == alert_id, AlertModel.id_user == user_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_active_and_read_by_user(self, user_id: int) -> list[AlertModel]:
        """The alerts to show in the dashboard, newest first."""
        stmt = (
            select(AlertModel)
            .where(AlertModel.id_user == user_id, AlertModel.status.in_(OPEN_STATUSES))
            .order_by(AlertModel.trigger_date.desc(), AlertModel.id_alert.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def find_existing_unresolved(self, user_id: int, alert_type: str) -> AlertModel | None:
        """The open alert of this type, if any: used to avoid duplicates."""
        stmt = select(AlertModel).where(
            AlertModel.id_user == user_id,
            AlertModel.type == alert_type,
            AlertModel.status.in_(OPEN_STATUSES),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def update_status(
        self, alert: AlertModel, new_status: str, resolved_at: datetime | None = None
    ) -> AlertModel:
        alert.status = new_status
        alert.resolved_at = resolved_at
        return await self.save(alert)

    # -- inputs of the checks -----------------------------------------------------------------

    async def list_configured_user_ids(self) -> list[int]:
        """Users who completed the initial configuration (entry condition of UC_RF_CG_3)."""
        result = await self.db.execute(text("SELECT id_user FROM financial_profile ORDER BY 1"))
        return list(result.scalars().all())

    async def find_planned_expenses(
        self, user_id: int, start: date, end: date
    ) -> list[PlannedExpenseRow]:
        """Planned expenses still to be registered, due in [start, end]."""
        result = await self.db.execute(
            text(
                "SELECT COALESCE(description, name) AS name, amount, planned_date "
                "FROM planned_transaction "
                "WHERE id_user = :uid AND type = 'expense' AND status = 'planned' "
                "AND planned_date BETWEEN :start AND :end"
            ),
            {"uid": user_id, "start": start, "end": end},
        )
        return [PlannedExpenseRow(**row) for row in result.mappings()]

    async def find_active_expense_rules(
        self, user_id: int, start: date, end: date
    ) -> list[RecurringExpenseRow]:
        """Active recurring expenses that may have an occurrence in [start, end]."""
        result = await self.db.execute(
            text(
                "SELECT name, amount, frequency, first_occurrence_date, end_date, "
                "last_processed_occurrence_date FROM recurring_rule "
                "WHERE id_user = :uid AND type = 'expense' AND status = 'active' "
                "AND first_occurrence_date <= :end AND (end_date IS NULL OR end_date >= :start)"
            ),
            {"uid": user_id, "start": start, "end": end},
        )
        return [RecurringExpenseRow(**row) for row in result.mappings()]

    async def get_previous_daily_sts(self, user_id: int, today: date) -> Decimal | None:
        """Last daily STS saved before today (normally yesterday's)."""
        result = await self.db.execute(
            text(
                "SELECT daily_sts FROM daily_sts WHERE id_user = :uid AND sts_date < :today "
                "ORDER BY sts_date DESC LIMIT 1"
            ),
            {"uid": user_id, "today": today},
        )
        return result.scalar_one_or_none()

    async def save_daily_sts(self, user_id: int, today: date, daily_sts: Decimal) -> None:
        """Keep the latest daily STS of today; older rows beyond a week are removed."""
        await self.db.execute(
            text(
                "INSERT INTO daily_sts (id_user, sts_date, daily_sts) VALUES (:uid, :day, :sts) "
                "ON CONFLICT (id_user, sts_date) DO UPDATE SET daily_sts = EXCLUDED.daily_sts"
            ),
            {"uid": user_id, "day": today, "sts": daily_sts},
        )
        await self.db.execute(
            text("DELETE FROM daily_sts WHERE id_user = :uid AND sts_date < :oldest"),
            {"uid": user_id, "oldest": today - timedelta(days=DAILY_STS_KEPT_DAYS)},
        )
