"""Transaction routes: HTTP layer only, business rules live in `TransactionService`."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.controller.transaction.dependencies import CurrentUserId
from app.api.dto.common.response import APIResponse
from app.api.dto.transaction.schema import (
    TransactionCreate,
    TransactionList,
    TransactionRead,
    TransactionTotals,
    TransactionType,
    TransactionUpdate,
)
from app.core.dependencies import DbSession
from app.dao.transaction.balance_snapshot_dao import BalanceSnapshotDAO
from app.dao.transaction.category_dao import CategoryDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.service.transaction.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def get_transaction_service(db: DbSession) -> TransactionService:
    return TransactionService(TransactionDAO(db), CategoryDAO(db), BalanceSnapshotDAO(db))


Service = Annotated[TransactionService, Depends(get_transaction_service)]


@router.get("", response_model=APIResponse[TransactionList])
async def list_transactions(
    service: Service,
    user_id: CurrentUserId,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    transaction_type: Annotated[TransactionType | None, Query(alias="type")] = None,
    id_category: Annotated[int | None, Query(gt=0)] = None,
):
    """Transactions of the current user, most recent first, with income/expense totals."""
    items, totals = await service.list_transactions(
        user_id, date_from, date_to, transaction_type, id_category
    )
    body = TransactionList(
        items=[TransactionRead.model_validate(item) for item in items],
        totals=TransactionTotals(**totals),
        count=len(items),
    )
    return APIResponse.ok(body)


@router.post("", response_model=APIResponse[TransactionRead], status_code=status.HTTP_201_CREATED)
async def create_transaction(payload: TransactionCreate, service: Service, user_id: CurrentUserId):
    transaction, message = await service.create_transaction(
        user_id,
        payload.type,
        payload.amount,
        payload.transaction_date,
        payload.id_category,
        payload.description,
    )
    return APIResponse.ok(TransactionRead.model_validate(transaction), message)


@router.get("/{transaction_id}", response_model=APIResponse[TransactionRead])
async def get_transaction(transaction_id: int, service: Service, user_id: CurrentUserId):
    transaction = await service.get_transaction(user_id, transaction_id)
    return APIResponse.ok(TransactionRead.model_validate(transaction))


@router.put("/{transaction_id}", response_model=APIResponse[TransactionRead])
async def update_transaction(
    transaction_id: int, payload: TransactionUpdate, service: Service, user_id: CurrentUserId
):
    transaction, message = await service.update_transaction(
        user_id,
        transaction_id,
        payload.type,
        payload.amount,
        payload.transaction_date,
        payload.id_category,
        payload.description,
    )
    return APIResponse.ok(TransactionRead.model_validate(transaction), message)


@router.delete("/{transaction_id}", response_model=APIResponse[None])
async def delete_transaction(transaction_id: int, service: Service, user_id: CurrentUserId):
    message = await service.delete_transaction(user_id, transaction_id)
    return APIResponse.ok(None, message)
