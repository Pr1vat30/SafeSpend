"""Routes of the income/expense calendar (RF_CG_1). Controllers hold no business logic."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dto.calendar.schema import CalendarMonth
from app.api.dto.common.response import APIResponse
from app.core.dependencies import DbSession
from app.dao.calendar.calendar_dao import CalendarDAO
from app.service.calendar.calendar_service import CalendarService

router = APIRouter(prefix="/calendar", tags=["Calendar"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def get_calendar_service(db: DbSession) -> CalendarService:
    return CalendarService(CalendarDAO(db))


Service = Annotated[CalendarService, Depends(get_calendar_service)]


def get_current_user_id() -> int:
    """TEMPORARY: fixed test user until the authentication module (profile) is merged.

    When it arrives, replace only the body of this function with the real dependency
    that returns the id of the authenticated user.
    """
    return 1


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


@router.get("", response_model=APIResponse[CalendarMonth])
async def get_calendar(
    service: Service,
    user_id: CurrentUserId,
    month: Annotated[str, Query(pattern=MONTH_PATTERN, description="Month as YYYY-MM")],
):
    """Recurring incomes and expenses of the month, grouped by day."""
    year, month_number = (int(part) for part in month.split("-"))
    return APIResponse.ok(await service.get_month(user_id, year, month_number))
