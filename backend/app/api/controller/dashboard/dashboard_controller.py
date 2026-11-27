from datetime import date

from fastapi import APIRouter

from app.api.controller.dashboard.dependencies import DashboardServiceDep
from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.common.response import APIResponse
from app.api.dto.dashboard.schema import DashboardRead

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=APIResponse[DashboardRead])
async def get_dashboard(user: CurrentUser, service: DashboardServiceDep):
    """Restituisce la dashboard finanziaria dell'utente autenticato (RF_CG_2)."""
    dashboard = await service.get_dashboard(id_user=user.id_user, as_of=date.today())
    return APIResponse.ok(dashboard)
