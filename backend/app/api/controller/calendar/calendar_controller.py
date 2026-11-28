"""Routes of the income/expense calendar (RF_CG_1). Controllers hold no business logic."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.calendar.schema import CalendarMonth
from app.api.dto.common.response import APIResponse
from app.core.dependencies import DbSession
from app.dao.calendar.calendar_dao import CalendarDAO
from app.service.calendar.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])

# Year from 1000: `date` has no year 0, so "0000-05" would otherwise fail with a 500.
MONTH_PATTERN = r"^[1-9]\d{3}-(0[1-9]|1[0-2])$"


def get_calendar_service(db: DbSession) -> CalendarService:
    return CalendarService(CalendarDAO(db))


Service = Annotated[CalendarService, Depends(get_calendar_service)]


@router.get("", response_model=APIResponse[CalendarMonth])
async def get_calendar(
    service: Service,
    user: CurrentUser,
    month: Annotated[str, Query(pattern=MONTH_PATTERN, description="Month as YYYY-MM")],
):
    """Recurring and planned incomes, expenses and goal allocations of the month, by day."""
    year, month_number = (int(part) for part in month.split("-"))
    return APIResponse.ok(await service.get_month(user.id_user, year, month_number))
