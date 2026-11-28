from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession


class DashboardDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_visible_alerts(
        self, id_user: int, *, session: AsyncSession | None = None
    ) -> list[RowMapping]:
        query = text("""
            SELECT id_alert, type, message, trigger_date, status
            FROM alert
            WHERE id_user = :id_user
              AND status IN ('active', 'read')
            ORDER BY trigger_date DESC, id_alert DESC
        """)

        db = self.db if session is None else session
        result = await db.execute(query, {"id_user": id_user})
        return list(result.mappings())
