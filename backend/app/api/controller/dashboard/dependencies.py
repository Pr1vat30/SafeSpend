from typing import Annotated

from fastapi import Depends

from app.core.dependencies import DbSession
from app.dao.cashflow.cashflow_dao import CashFlowDAO
from app.dao.dashboard.dashboard_dao import DashboardDAO
from app.service.dashboard.dashboard_service import DashboardService


def get_dashboard_service(db: DbSession) -> DashboardService:
    return DashboardService(CashFlowDAO(db), DashboardDAO(db))


DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]
