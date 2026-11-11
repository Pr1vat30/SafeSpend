"""Common response envelope shared by every endpoint."""

from typing import Generic, TypeVar

from pydantic import BaseModel

from app.constants.messages import SUCCESS

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str | None = SUCCESS
    error: str | None = None
    data: T | None = None

    @classmethod
    def ok(cls, data: T | None = None, message: str = SUCCESS) -> "APIResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, error: str) -> "APIResponse[None]":
        return cls(success=False, message=None, error=error, data=None)
