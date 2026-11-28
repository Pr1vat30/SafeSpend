"""Adapter between the alerts and the Cash Flow Engine of the cashflow module (SS2).

It is the only place where the alerts depend on the cashflow module. Until that module is in
`main`, `make_projector` returns None and the alert checks are skipped with a warning.
"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.service.alert.alert_checker import Projector
from app.service.alert.alert_rules import ProjectionSnapshot


def make_projector(db: AsyncSession) -> Projector | None:
    try:
        from app.dao.cashflow.cashflow_dao import CashFlowDAO
        from app.service.cashflow.cashflow_service import CashFlowService
    except ImportError:
        return None

    dao = CashFlowDAO(db)
    engine = CashFlowService(dao)

    async def project(user_id: int, as_of: date) -> ProjectionSnapshot | None:
        settings = await dao.get_projection_settings(user_id)
        if settings is None:
            return None
        try:
            projection = await engine.calculate_cash_flow(user_id, as_of)
        except ConflictError:
            # Profile or starting balance missing: the initial configuration is not complete.
            return None
        return ProjectionSnapshot(
            minimum_balance=projection.minimum_balance,
            critical_date=projection.critical_date,
            daily_safe_to_spend=projection.daily_safe_to_spend,
            risk_level=projection.risk_level,
            safety_buffer=settings.safety_buffer,
        )

    return project
