"""Domain exceptions and the handlers that turn them into `APIResponse` errors.

Services raise these instead of `HTTPException`, so business logic stays HTTP-agnostic.
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.dto.common.response import APIResponse
from app.config.logging import get_logger
from app.constants.messages import INVALID_REQUEST_PAYLOAD, UNEXPECTED_ERROR

logger = get_logger(__name__)


class AppException(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT


def _error(status_code: int, message: str, details=None) -> JSONResponse:
    body = APIResponse.fail(message).model_dump()
    if details is not None:
        body["data"] = details
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException):
        return _error(exc.status_code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return _error(422, INVALID_REQUEST_PAYLOAD, exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return _error(status.HTTP_500_INTERNAL_SERVER_ERROR, UNEXPECTED_ERROR)
