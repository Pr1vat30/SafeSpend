"""Life cycle of the alerts (RF_CG_3).

    (condition detected) ──▶ active ──(user reads it)──▶ read
    active / read ──(condition no longer true)──▶ resolved

At most one open (active or read) alert per user and type: when the condition is detected
again, the open alert is updated instead of creating a duplicate. Detecting the conditions
(risk level, impending expenses, STS drop) is a separate step; this service only stores
the result.

Raises exceptions from `app.core.exceptions`, never `HTTPException`.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime

from app.core.exceptions import ConflictError, NotFoundError
from app.dao.alert.alert_dao import AlertDAO
from app.models.alert.alert_model import AlertModel

ALERT_NOT_FOUND = "Avviso non trovato"
ALERT_ALREADY_RESOLVED = "L'avviso è già stato risolto"


class AlertService:
    def __init__(self, dao: AlertDAO, now: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.dao = dao
        self._now = now

    # -- used by the API ----------------------------------------------------------------------

    async def list_for_dashboard(self, user_id: int) -> list[AlertModel]:
        return await self.dao.find_active_and_read_by_user(user_id)

    async def mark_read(self, user_id: int, alert_id: int) -> AlertModel:
        alert = await self.dao.get_by_id_for_user(alert_id, user_id)
        if alert is None:
            # Also returned for alerts of other users, so their existence is not revealed.
            raise NotFoundError(ALERT_NOT_FOUND)
        if alert.status == "resolved":
            raise ConflictError(ALERT_ALREADY_RESOLVED)
        if alert.status == "read":
            return alert  # idempotent
        return await self.dao.update_status(alert, "read")

    # -- used by the system (Scheduler and recalculations) -------------------------------------

    async def raise_alert(
        self, user_id: int, alert_type: str, message: str, today: date
    ) -> AlertModel:
        """Open an alert of this type, or refresh the open one if the message changed.

        A refreshed alert goes back to `active` so the user notices the new message.
        """
        existing = await self.dao.find_existing_unresolved(user_id, alert_type)
        if existing is None:
            alert = AlertModel(
                id_user=user_id, type=alert_type, message=message, trigger_date=today
            )
            return await self.dao.add(alert)
        if existing.message != message:
            existing.message = message
            existing.trigger_date = today
            return await self.dao.update_status(existing, "active")
        return existing

    async def resolve_alert(self, user_id: int, alert_type: str) -> AlertModel | None:
        """Close the open alert of this type, if any, because its condition has ended."""
        existing = await self.dao.find_existing_unresolved(user_id, alert_type)
        if existing is None:
            return None
        return await self.dao.update_status(existing, "resolved", resolved_at=self._now())
