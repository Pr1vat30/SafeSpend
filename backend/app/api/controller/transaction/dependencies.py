"""Dependencies of the transaction module.

TEMPORARY AUTHENTICATION: the Profile module (feature/al-profile) is not in `main` yet, so the
current user is read from the `X-User-Id` header. This is NOT a security mechanism: anyone can
send any id. It exists only so the module can run and be tested until authentication lands.

This file is the ONLY place in the backend that knows about the header. Controllers receive the
user through `CurrentUserId`, and services and DAOs receive a plain `user_id: int`, so none of
them has to change when the real authentication arrives.

HOW TO REPLACE IT with the definitive authentication:
1. Rewrite the body of `get_current_user_id` so it returns the id of the authenticated user
   (for example by depending on the dependency exposed by the Profile module). Keep the name and
   the return type (`int`): `CurrentUserId` and every route stay as they are.
2. Delete the header handling, the `UserLookupDAO` check and
   `app/dao/transaction/user_lookup_dao.py`.
3. Frontend: replace `authHeaders()` in `src/services/transaction-service.ts` with the
   credentials used by the project (any change to `src/lib/api-client.ts` goes in a `chore/` PR).
4. Tests: replace `headers()` in `tests/transaction/helpers.py` and the `test_*_user` cases.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.dependencies import DbSession
from app.dao.transaction.user_lookup_dao import UserLookupDAO


async def get_current_user_id(
    db: DbSession,
    x_user_id: Annotated[int | None, Header(gt=0)] = None,
) -> int:
    if x_user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utente non autenticato")
    # Without this check an unknown id would fail later with a foreign key error (HTTP 500).
    if not await UserLookupDAO(db).exists(x_user_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utente non trovato")
    return x_user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
