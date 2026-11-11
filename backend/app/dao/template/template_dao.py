"""Template DAO. Copy to `app/dao/<module>/<module>_dao.py` and rename.

DAOs contain database queries only. Use `flush()`, never `commit()`:
the `get_db` dependency commits once per request.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class TemplateDAO:
    def __init__(self, db: AsyncSession):
        self.db = db
