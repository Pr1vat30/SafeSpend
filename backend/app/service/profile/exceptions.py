"""Domain exceptions of SS1, turned into APIResponse errors by app.core.exceptions."""

from fastapi import status

from app.core.exceptions import AppException


class UnauthorizedError(AppException):
    """Missing, invalid, expired or revoked token; wrong credentials."""

    status_code = status.HTTP_401_UNAUTHORIZED


class AccountLockedError(AppException):
    """Account locked for 15 minutes after 5 failed logins (RF_AUT_2)."""

    status_code = status.HTTP_423_LOCKED
