"""TEMPORARY: existence check for the provisional `X-User-Id` header.

Delete this file together with the provisional dependency (see
`app/api/controller/transaction/dependencies.py`) when authentication is integrated.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserLookupDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def exists(self, user_id: int) -> bool:
        row = await self.db.scalar(text("SELECT 1 FROM _user WHERE id_user = :id"), {"id": user_id})
        return row is not None
