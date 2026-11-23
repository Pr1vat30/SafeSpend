"""Category routes: HTTP layer only, business rules live in `CategoryService`."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.controller.transaction.dependencies import CurrentUserId
from app.api.dto.common.response import APIResponse
from app.api.dto.transaction.category_schema import (
    CategoryCreate,
    CategoryDeleted,
    CategoryRead,
    CategoryUpdate,
)
from app.core.dependencies import DbSession
from app.dao.transaction.category_dao import CategoryDAO
from app.service.transaction import messages
from app.service.transaction.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


def get_category_service(db: DbSession) -> CategoryService:
    return CategoryService(CategoryDAO(db))


Service = Annotated[CategoryService, Depends(get_category_service)]


@router.get("", response_model=APIResponse[list[CategoryRead]])
async def list_categories(service: Service, user_id: CurrentUserId):
    """Default categories plus the custom ones of the current user."""
    categories = await service.list_categories(user_id)
    return APIResponse.ok([CategoryRead.model_validate(c) for c in categories])


@router.post("", response_model=APIResponse[CategoryRead], status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, service: Service, user_id: CurrentUserId):
    category = await service.create_category(user_id, payload.name, payload.type)
    return APIResponse.ok(CategoryRead.model_validate(category), messages.CATEGORY_CREATED)


@router.put("/{category_id}", response_model=APIResponse[CategoryRead])
async def rename_category(
    category_id: int, payload: CategoryUpdate, service: Service, user_id: CurrentUserId
):
    category = await service.rename_category(user_id, category_id, payload.name)
    return APIResponse.ok(CategoryRead.model_validate(category), messages.CATEGORY_RENAMED)


@router.delete("/{category_id}", response_model=APIResponse[CategoryDeleted])
async def delete_category(category_id: int, service: Service, user_id: CurrentUserId):
    """Delete a custom category: its transactions are reassigned to «Altro»."""
    reassigned = await service.delete_category(user_id, category_id)
    body = CategoryDeleted(reassigned_transactions=reassigned)
    return APIResponse.ok(body, messages.CATEGORY_DELETED)
