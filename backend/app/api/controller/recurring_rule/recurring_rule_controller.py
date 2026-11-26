"""Routes of the recurring rules (RF_CF_2). Controllers hold no business logic."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.common.response import APIResponse
from app.api.dto.recurring_rule.schema import (
    RecurringRuleCreate,
    RecurringRuleRead,
    RecurringRuleUpdate,
    RuleStatus,
)
from app.core.dependencies import DbSession
from app.dao.recurring_rule.recurring_rule_dao import RecurringRuleDAO
from app.service.recurring_rule.recurring_rule_service import RecurringRuleService

router = APIRouter(prefix="/recurring-rules", tags=["Recurring rules"])


def get_recurring_rule_service(db: DbSession) -> RecurringRuleService:
    return RecurringRuleService(RecurringRuleDAO(db))


Service = Annotated[RecurringRuleService, Depends(get_recurring_rule_service)]


@router.post("", response_model=APIResponse[RecurringRuleRead], status_code=status.HTTP_201_CREATED)
async def create_rule(body: RecurringRuleCreate, user: CurrentUser, service: Service):
    rule = await service.create(user.id_user, body)
    return APIResponse.ok(RecurringRuleRead.model_validate(rule))


@router.get("", response_model=APIResponse[list[RecurringRuleRead]])
async def list_rules(
    user: CurrentUser,
    service: Service,
    rule_status: Annotated[RuleStatus | None, Query(alias="status")] = None,
):
    rules = await service.list_for_user(user.id_user, rule_status)
    return APIResponse.ok([RecurringRuleRead.model_validate(r) for r in rules])


@router.get("/{rule_id}", response_model=APIResponse[RecurringRuleRead])
async def get_rule(rule_id: int, user: CurrentUser, service: Service):
    rule = await service.get(user.id_user, rule_id)
    return APIResponse.ok(RecurringRuleRead.model_validate(rule))


@router.patch("/{rule_id}", response_model=APIResponse[RecurringRuleRead])
async def update_rule(rule_id: int, body: RecurringRuleUpdate, user: CurrentUser, service: Service):
    rule = await service.update(user.id_user, rule_id, body)
    return APIResponse.ok(RecurringRuleRead.model_validate(rule))


@router.post("/{rule_id}/suspend", response_model=APIResponse[RecurringRuleRead])
async def suspend_rule(rule_id: int, user: CurrentUser, service: Service):
    rule = await service.suspend(user.id_user, rule_id)
    return APIResponse.ok(RecurringRuleRead.model_validate(rule))


@router.post("/{rule_id}/resume", response_model=APIResponse[RecurringRuleRead])
async def resume_rule(rule_id: int, user: CurrentUser, service: Service):
    rule = await service.resume(user.id_user, rule_id)
    return APIResponse.ok(RecurringRuleRead.model_validate(rule))


@router.delete("/{rule_id}", response_model=APIResponse[None])
async def delete_rule(rule_id: int, user: CurrentUser, service: Service):
    await service.delete(user.id_user, rule_id)
    return APIResponse.ok(None)
