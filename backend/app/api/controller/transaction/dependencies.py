"""Dependencies of the transaction module."""

from typing import Annotated

from fastapi import Depends

from app.api.controller.profile.dependencies import CurrentUser


def get_current_user_id(user: CurrentUser) -> int:
    """Return the id of the authenticated user from the Profile module."""
    return user.id_user


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
