"""Password hashing, JWT handling and logout revocation for SS1 (RNF_SE_1, RF_AUT_3).

Passwords are hashed with Argon2 (salt included in the hash). Access tokens are JWT signed with
JWT_SECRET_KEY and valid for ACCESS_TOKEN_EXPIRE_MINUTES (60). Each token has a unique id
(`jti`): at logout that id is added to an in-memory revocation list until the token expires, so
the token cannot be used again (RF_AUT_3) without adding tables to the data dictionary.
"""

import threading
import time
import uuid
from dataclasses import dataclass
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


@dataclass(frozen=True)
class TokenClaims:
    id_user: int
    jti: str
    expires_at: float  # Unix timestamp


def create_access_token(id_user: int) -> tuple[str, int]:
    """Returns the signed token and its validity in seconds."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(id_user),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> TokenClaims | None:
    """Returns the claims of a valid, unexpired and not revoked token, otherwise None."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "jti"]},
        )
        claims = TokenClaims(int(payload["sub"]), str(payload["jti"]), float(payload["exp"]))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
    if revoked_tokens.is_revoked(claims.jti):
        return None
    return claims


class RevokedTokens:
    """Ids of the tokens closed by logout, kept only until their natural expiry.

    SafeSpend runs as a single backend instance (modular monolith, RNF_SCA_1), so the list lives
    in the process memory. If the backend restarts the list is empty: a token closed before the
    restart would be accepted again until it expires (at most 60 minutes). The frontend deletes
    the token at logout in any case.
    """

    def __init__(self) -> None:
        self._expiry_by_jti: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: float) -> None:
        with self._lock:
            self._purge_expired()
            self._expiry_by_jti[jti] = expires_at

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            return jti in self._expiry_by_jti

    def _purge_expired(self) -> None:
        now = time.time()
        for jti in [j for j, exp in self._expiry_by_jti.items() if exp <= now]:
            del self._expiry_by_jti[jti]


revoked_tokens = RevokedTokens()
