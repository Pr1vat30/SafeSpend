"""Reconciliation routes: HTTP layer only, business rules live in `ReconciliationService`."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.controller.transaction.dependencies import CurrentUserId
from app.api.dto.common.response import APIResponse
from app.api.dto.transaction.reconciliation_schema import (
    ReconciliationCreate,
    ReconciliationHistory,
    ReconciliationPreview,
    ReconciliationRead,
)
from app.core.dependencies import DbSession
from app.dao.transaction.balance_snapshot_dao import BalanceSnapshotDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.service.transaction import messages
from app.service.transaction.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/reconciliations", tags=["Reconciliations"])


def get_reconciliation_service(db: DbSession) -> ReconciliationService:
    return ReconciliationService(BalanceSnapshotDAO(db), TransactionDAO(db))


Service = Annotated[ReconciliationService, Depends(get_reconciliation_service)]


@router.get("/preview", response_model=APIResponse[ReconciliationPreview])
async def preview_reconciliation(
    service: Service,
    user_id: CurrentUserId,
    reconciliation_date: Annotated[date | None, Query()] = None,
):
    """Calculated balance up to `reconciliation_date` and the latest reconciliation snapshot."""
    target_date, calculated, latest, days_since, reminder = await service.preview(
        user_id, reconciliation_date
    )
    body = ReconciliationPreview(
        reconciliation_date=target_date,
        calculated_balance=calculated,
        last_reconciliation=ReconciliationRead.model_validate(latest) if latest else None,
        days_since_last_reconciliation=days_since,
        reconciliation_reminder=reminder,
    )
    return APIResponse.ok(body)


@router.get("", response_model=APIResponse[ReconciliationHistory])
async def list_reconciliations(service: Service, user_id: CurrentUserId):
    """Reconciliation history of the current user (newest first) and current calculated balance."""
    items, current_balance = await service.list_reconciliations(user_id)
    body = ReconciliationHistory(
        items=[ReconciliationRead.model_validate(item) for item in items],
        count=len(items),
        current_calculated_balance=current_balance,
    )
    return APIResponse.ok(body)


@router.post(
    "", response_model=APIResponse[ReconciliationRead], status_code=status.HTTP_201_CREATED
)
async def create_reconciliation(
    payload: ReconciliationCreate, service: Service, user_id: CurrentUserId
):
    """Record a balance snapshot and, if needed, an adjustment transaction."""
    snapshot, adjusted = await service.reconcile(
        user_id, payload.real_balance, payload.reconciliation_date, payload.description
    )
    message = messages.RECONCILIATION_CREATED if adjusted else messages.RECONCILIATION_NO_ADJUSTMENT
    return APIResponse.ok(ReconciliationRead.model_validate(snapshot), message)


@router.get("/{snapshot_id}", response_model=APIResponse[ReconciliationRead])
async def get_reconciliation(snapshot_id: int, service: Service, user_id: CurrentUserId):
    snapshot = await service.get_reconciliation(user_id, snapshot_id)
    return APIResponse.ok(ReconciliationRead.model_validate(snapshot))
