"""Data access for alerts (SDD 4.8, AlertDAO). Queries only: `flush()`, never `commit()`."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert.alert_model import AlertModel

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
