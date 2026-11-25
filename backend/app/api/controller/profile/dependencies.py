"""Authentication dependency shared by every module.

Protect a route by adding a `CurrentUser` parameter:

    from app.api.controller.profile.dependencies import CurrentUser

    @router.get("/something")
    async def read_something(user: CurrentUser, service: Service):
        return APIResponse.ok(await service.list_for(user.id_user))

Every query must then filter on `user.id_user` (RNF_SE_3: a resource of another user → 404).
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.dependencies import DbSession
from app.dao.profile.profile_dao import (
    BalanceSnapshotReader,
    FinancialProfileDAO,
    UserDAO,
    UserDataExportDAO,
)
from app.models.profile.profile_model import User
from app.service.profile.auth_service import AuthService
from app.service.profile.profile_service import ProfileService

# auto_error=False: a missing token is reported with our APIResponse format (401), not FastAPI's.
_bearer = HTTPBearer(auto_error=False, description="Token JWT ottenuto da POST /auth/login")


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserDAO(db), FinancialProfileDAO(db))


def get_profile_service(db: DbSession) -> ProfileService:
    return ProfileService(
        UserDAO(db), FinancialProfileDAO(db), BalanceSnapshotReader(db), UserDataExportDAO(db)
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


async def get_current_user(
    auth: AuthServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """The authenticated user; 401 if the token is missing, invalid, expired or revoked."""
    return await auth.authenticate(credentials.credentials if credentials else None)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_bearer_token(
    _: CurrentUser,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """The raw token of an authenticated request (used by logout to revoke it)."""
    assert credentials is not None  # guaranteed by CurrentUser
    return credentials.credentials


BearerToken = Annotated[str, Depends(get_bearer_token)]
