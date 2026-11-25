"""Routes of the financial profile (SS1): /profile."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.controller.profile.dependencies import CurrentUser, ProfileServiceDep
from app.api.dto.common.response import APIResponse
from app.api.dto.profile.schema import (
    DeleteAccountRequest,
    InitialSetupRequest,
    ProfileRead,
    ProfileUpdate,
)
from app.service.profile import messages as msg

router = APIRouter(prefix=msg.PROFILE_PREFIX, tags=[msg.PROFILE_TAG])


@router.get("", response_model=APIResponse[ProfileRead])
async def get_profile(user: CurrentUser, service: ProfileServiceDep):
    """Account data, financial profile and `setup_completed` (RF_AUT_5)."""
    return APIResponse.ok(await service.get_profile(user))


@router.post("/setup", response_model=APIResponse[ProfileRead])
async def initial_setup(body: InitialSetupRequest, user: CurrentUser, service: ProfileServiceDep):
    """RF_AUT_5: first access. Current balance, Safety Buffer, optional monthly estimate of
    variable expenses. 409 if the initial balance was already entered."""
    return APIResponse.ok(await service.initial_setup(user, body), message=msg.SETUP_COMPLETED)


@router.patch("", response_model=APIResponse[ProfileRead])
async def update_profile(body: ProfileUpdate, user: CurrentUser, service: ProfileServiceDep):
    """Safety Buffer (RF_CF_3), estimate (RF_PRE_1), horizon (RF_CF_5), AI consent (RNF_PV_2)."""
    return APIResponse.ok(
        await service.update_profile(user, body.changes()), message=msg.PROFILE_UPDATED
    )


@router.get("/export", response_class=Response)
async def export_data(user: CurrentUser, service: ProfileServiceDep):
    """RNF_PV_3: downloads all the user's data as CSV."""
    content = await service.export_csv(user)
    return Response(
        content="﻿" + content,  # BOM: Excel opens UTF-8 accents correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="safespend_dati.csv"'},
    )


@router.delete("", response_model=APIResponse[None])
async def delete_account(body: DeleteAccountRequest, user: CurrentUser, service: ProfileServiceDep):
    """RF_AUT_4: deletes account and every personal and financial record after password
    confirmation. 401 if the password is wrong."""
    await service.delete_account(user, body.password)
    return APIResponse.ok(message=msg.ACCOUNT_DELETED)
