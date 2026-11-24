"""Password hashing and JWT handling for SS1 (RNF_SE_1).

Passwords are hashed with Argon2 (salt included in the hash). Access tokens are JWT signed with
JWT_SECRET_KEY, valid for ACCESS_TOKEN_EXPIRE_MINUTES (60), and carry the user's token_version
so that logout can revoke them (RF_AUT_3).
"""

from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.config.settings import settings

_password_hash = PasswordHash((Argon2Hasher(),))

# Hash of a random password, verified when the email does not exist so that the response time
# does not reveal which emails are registered.
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hash.verify(password, hashed)


def create_access_token(id_user: int, token_version: int) -> tuple[str, int]:
    """Returns the signed token and its validity in seconds."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(id_user),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> tuple[int, int] | None:
    """Returns (id_user, token_version), or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "ver"]},
        )
        return int(payload["sub"]), int(payload["ver"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
