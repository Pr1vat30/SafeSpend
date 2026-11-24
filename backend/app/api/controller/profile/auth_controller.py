"""Routes of authentication (SS1): /auth/register, /auth/login, /auth/logout, /auth/me."""

from fastapi import APIRouter, status

from app.api.controller.profile.dependencies import AuthServiceDep, CurrentUser
from app.api.dto.common.response import APIResponse
from app.api.dto.profile.schema import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.service.profile import messages as msg

router = APIRouter(prefix=msg.AUTH_PREFIX, tags=[msg.AUTH_TAG])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=APIResponse[UserRead])
async def register(body: RegisterRequest, auth: AuthServiceDep):
    """RF_AUT_1: creates an account. 409 if the email is already registered."""
    user = await auth.register(body)
    return APIResponse.ok(UserRead.model_validate(user), message=msg.REGISTERED)


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(body: LoginRequest, auth: AuthServiceDep):
    """RF_AUT_2: returns a JWT valid 60 minutes. 401 wrong credentials, 423 account locked."""
    return APIResponse.ok(await auth.login(body.email, body.password), message=msg.LOGGED_IN)


@router.post("/logout", response_model=APIResponse[None])
async def logout(user: CurrentUser, auth: AuthServiceDep):
    """RF_AUT_3: revokes every token of the user; a new login is required."""
    await auth.logout(user)
    return APIResponse.ok(message=msg.LOGGED_OUT)


@router.get("/me", response_model=APIResponse[UserRead])
async def me(user: CurrentUser):
    """The authenticated user (useful to the frontend to check the session)."""
    return APIResponse.ok(UserRead.model_validate(user))
