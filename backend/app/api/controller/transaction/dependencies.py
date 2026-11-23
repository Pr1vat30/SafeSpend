"""Dependencies of the transaction module.

TEMPORARY: the authentication module (feature/al-profile) is not in `main` yet, so the current
user is read from the `X-User-Id` header. Once authentication lands, replace the body of
`get_current_user_id` with the authenticated user and delete the header: every route already
receives the user id only through this dependency.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status


async def get_current_user_id(
    x_user_id: Annotated[int | None, Header(gt=0)] = None,
) -> int:
    if x_user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utente non autenticato")
    return x_user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
