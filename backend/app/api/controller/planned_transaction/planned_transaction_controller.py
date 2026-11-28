"""Routes of the planned transactions (RF_CF_6). Controllers hold no business logic."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.common.response import APIResponse
from app.api.dto.planned_transaction.schema import (
    PlannedStatus,
    PlannedTransactionConfirm,
    PlannedTransactionCreate,
    PlannedTransactionPostpone,
    PlannedTransactionRead,
    PlannedTransactionUpdate,
    PlannedType,
)
from app.core.dependencies import DbSession
from app.dao.planned_transaction.planned_transaction_dao import PlannedTransactionDAO
from app.service.planned_transaction.planned_transaction_service import PlannedTransactionService

router = APIRouter(prefix="/planned-transactions", tags=["Planned transactions"])


def get_planned_transaction_service(db: DbSession) -> PlannedTransactionService:
    return PlannedTransactionService(PlannedTransactionDAO(db))


Service = Annotated[PlannedTransactionService, Depends(get_planned_transaction_service)]


@router.post(
    "", response_model=APIResponse[PlannedTransactionRead], status_code=status.HTTP_201_CREATED
)
async def create_planned(body: PlannedTransactionCreate, user: CurrentUser, service: Service):
    planned = await service.create(user.id_user, body)
    return APIResponse.ok(planned)


@router.get("", response_model=APIResponse[list[PlannedTransactionRead]])
async def list_planned(
    user: CurrentUser,
    service: Service,
    planned_status: Annotated[PlannedStatus | None, Query(alias="status")] = None,
    planned_type: Annotated[PlannedType | None, Query(alias="type")] = None,
    date_from: Annotated[date | None, Query(alias="dateFrom")] = None,
    date_to: Annotated[date | None, Query(alias="dateTo")] = None,
):
    """Filters are optional; dates use the ISO format (2026-12-31)."""
    planned_list = await service.list_transactions(
        user.id_user, planned_status, planned_type, date_from, date_to
    )
    return APIResponse.ok(planned_list)


@router.get("/pending-incomes", response_model=APIResponse[list[PlannedTransactionRead]])
async def list_pending_incomes(user: CurrentUser, service: Service):
    """List pending confirmation incomes for the current user."""
    planned_list = await service.list_pending_incomes(user.id_user)
    return APIResponse.ok(planned_list)


@router.get("/{planned_id}", response_model=APIResponse[PlannedTransactionRead])
async def get_planned(planned_id: int, user: CurrentUser, service: Service):
    planned = await service.get(user.id_user, planned_id)
    return APIResponse.ok(planned)


@router.patch("/{planned_id}", response_model=APIResponse[PlannedTransactionRead])
async def update_planned(
    planned_id: int,
    body: PlannedTransactionUpdate,
    user: CurrentUser,
    service: Service,
):
    planned = await service.update(user.id_user, planned_id, body)
    return APIResponse.ok(planned)


@router.post("/{planned_id}/confirm", response_model=APIResponse[PlannedTransactionRead])
async def confirm_or_reject_income(
    planned_id: int,
    body: PlannedTransactionConfirm,
    user: CurrentUser,
    service: Service,
):
    """Confirm (confirm=true) or reject (confirm=false) a pending income."""
    planned = await service.confirm_or_reject_income(user.id_user, planned_id, body.confirm)
    return APIResponse.ok(planned)


@router.post("/{planned_id}/postpone", response_model=APIResponse[PlannedTransactionRead])
async def postpone_income(
    planned_id: int,
    body: PlannedTransactionPostpone,
    user: CurrentUser,
    service: Service,
):
    """Move a pending income to a new date ("Conferma l'incasso o sposta la data")."""
    planned = await service.postpone_income(user.id_user, planned_id, body.new_date)
    return APIResponse.ok(planned)


@router.post("/{planned_id}/cancel", response_model=APIResponse[PlannedTransactionRead])
async def cancel_planned(planned_id: int, user: CurrentUser, service: Service):
    """Cancel a transaction that is still planned (before its date)."""
    planned = await service.cancel(user.id_user, planned_id)
    return APIResponse.ok(planned)


@router.delete("/{planned_id}", response_model=APIResponse[None])
async def delete_planned(planned_id: int, user: CurrentUser, service: Service):
    await service.delete(user.id_user, planned_id)
    return APIResponse.ok(None)
