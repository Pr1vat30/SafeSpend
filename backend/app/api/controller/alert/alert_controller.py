"""Routes of the alerts (RF_CG_3). Controllers hold no business logic."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.alert.schema import AlertRead
from app.api.dto.common.response import APIResponse
from app.core.dependencies import DbSession
from app.dao.alert.alert_dao import AlertDAO
from app.service.alert.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def get_alert_service(db: DbSession) -> AlertService:
    return AlertService(AlertDAO(db))


Service = Annotated[AlertService, Depends(get_alert_service)]


@router.get("", response_model=APIResponse[list[AlertRead]])
async def list_alerts(user: CurrentUser, service: Service):
    """The open (active or read) alerts of the user, for the dashboard."""
    alerts = await service.list_for_dashboard(user.id_user)
    return APIResponse.ok([AlertRead.model_validate(a) for a in alerts])


@router.post("/{alert_id}/read", response_model=APIResponse[AlertRead])
async def mark_alert_read(alert_id: int, user: CurrentUser, service: Service):
    alert = await service.mark_read(user.id_user, alert_id)
    return APIResponse.ok(AlertRead.model_validate(alert))
