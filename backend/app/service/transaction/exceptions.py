"""Domain exceptions specific to the transaction module."""

from fastapi import status

from app.core.exceptions import AppException


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
