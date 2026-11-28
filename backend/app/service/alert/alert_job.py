"""Entry points of the alert checks (RF_CG_3: "every day and after every data change").

- `run_alert_checks(today)`: called by the daily Scheduler, checks every configured user;
- `refresh_user_alerts(user_id)`: added as a FastAPI background task by the endpoints that
  change the data (it runs after the response, when the change is already committed).

Every user is checked in its own database transaction: a failure does not stop the others.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config.database import AsyncSessionLocal
from app.config.logging import get_logger
from app.dao.alert.alert_dao import AlertDAO
from app.service.alert.alert_checker import AlertChecker
from app.service.alert.alert_service import AlertService
from app.service.alert.cashflow_projector import make_projector

logger = get_logger(__name__)


def rome_today() -> date:
    return datetime.now(ZoneInfo("Europe/Rome")).date()


async def _check_one(user_id: int, today: date) -> bool:
    async with AsyncSessionLocal() as session:
        projector = make_projector(session)
        if projector is None:
            logger.warning("Alert: Cash Flow Engine non disponibile, verifica saltata")
            return False
        dao = AlertDAO(session)
        checker = AlertChecker(dao, AlertService(dao), projector)
        try:
            ok = await checker.check_user(user_id, today)
            await session.commit()
            return ok
        except Exception:
            await session.rollback()
            logger.exception("Alert: verifica fallita per l'utente %s", user_id)
            return False


async def run_alert_checks(today: date | None = None) -> int:
    """Check every configured user. Returns how many checks failed."""
    today = today or rome_today()
    async with AsyncSessionLocal() as session:
        user_ids = await AlertDAO(session).list_configured_user_ids()
    failures = 0
    for user_id in user_ids:
        if not await _check_one(user_id, today):
            failures += 1
    logger.info("Alert %s: %s utenti verificati, %s errori", today, len(user_ids), failures)
    return failures


async def refresh_user_alerts(user_id: int) -> None:
    """Check one user right after a change of their data (background task)."""
    await _check_one(user_id, rome_today())
