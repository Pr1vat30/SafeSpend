"""Business logic of authentication (SS1): RF_AUT_1, RF_AUT_2, RF_AUT_3, RNF_SE_1."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.api.dto.profile.schema import RegisterRequest, TokenResponse
from app.core.exceptions import ConflictError
from app.dao.profile.profile_dao import FinancialProfileDAO, UserDAO
from app.models.profile.profile_model import FinancialProfile, User
from app.service.profile import messages as msg
from app.service.profile import security
from app.service.profile.exceptions import AccountLockedError, UnauthorizedError

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION = timedelta(minutes=15)
ROME = ZoneInfo("Europe/Rome")  # times shown to the user are Italian time (RNF_AF_6)


def _now() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, users: UserDAO, profiles: FinancialProfileDAO):
        self.users = users
        self.profiles = profiles

    async def register(self, data: RegisterRequest) -> User:
        """RF_AUT_1: creates the user (password hashed) and an empty financial profile."""
        if await self.users.get_by_email(data.email) is not None:
            raise ConflictError(msg.EMAIL_ALREADY_REGISTERED)
        now = _now()
        user = await self.users.create(
            User(
                name=data.name,
                surname=data.surname,
                email=data.email,
                password=security.hash_password(data.password),
                privacy_accepted_at=now,
                disclaimer_accepted_at=now,
            )
        )
        await self.profiles.create(FinancialProfile(id_user=user.id_user))
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """RF_AUT_2: after 5 consecutive failures the account is locked for 15 minutes."""
        user = await self.users.get_by_email(email)
        if user is None:
            security.verify_password(password, security.DUMMY_HASH)  # same timing as a real user
            raise UnauthorizedError(msg.INVALID_CREDENTIALS)

        now = _now()
        if user.locked_until is not None and user.locked_until > now:
            raise AccountLockedError(self._locked_message(user.locked_until))

        if not security.verify_password(password, user.password):
            user.failed_login_attempts += 1
            locked = user.failed_login_attempts >= MAX_FAILED_ATTEMPTS
            if locked:
                user.failed_login_attempts = 0
                user.locked_until = now + LOCK_DURATION
            await self.users.update(user)
            await self.users.commit_now()  # keep the counter although the request fails
            if locked:
                raise AccountLockedError(self._locked_message(user.locked_until))
            raise UnauthorizedError(msg.INVALID_CREDENTIALS)

        user.failed_login_attempts = 0
        user.locked_until = None
        await self.users.update(user)
        token, expires_in = security.create_access_token(user.id_user, user.token_version)
        return TokenResponse(access_token=token, expires_in=expires_in)

    async def logout(self, user: User) -> None:
        """RF_AUT_3: increments token_version, so every token issued before is rejected."""
        user.token_version += 1
        await self.users.update(user)

    async def authenticate(self, token: str | None) -> User:
        """Returns the user of a valid, non-revoked token (used by every protected route)."""
        decoded = security.decode_access_token(token) if token else None
        if decoded is None:
            raise UnauthorizedError(msg.NOT_AUTHENTICATED)
        id_user, token_version = decoded
        user = await self.users.get_by_id(id_user)
        if user is None or user.token_version != token_version:
            raise UnauthorizedError(msg.NOT_AUTHENTICATED)
        return user

    @staticmethod
    def _locked_message(until: datetime | None) -> str:
        assert until is not None
        return msg.ACCOUNT_LOCKED.format(until=until.astimezone(ROME).strftime("%H:%M"))
