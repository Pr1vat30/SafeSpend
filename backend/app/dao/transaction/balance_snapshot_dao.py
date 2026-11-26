"""BalanceSnapshot DAO: database queries only. Uses `flush()`, never `commit()`.

Every query is scoped by `id_user`, so a user can never reach another user's snapshots.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction.balance_snapshot_model import BalanceSnapshot


class BalanceSnapshotDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int, snapshot_id: int) -> BalanceSnapshot | None:
        stmt = (
            select(BalanceSnapshot)
            .where(BalanceSnapshot.id_user == user_id, BalanceSnapshot.id_snapshot == snapshot_id)
            .execution_options(populate_existing=True)
        )
        return await self.db.scalar(stmt)

    async def get_latest(self, user_id: int) -> BalanceSnapshot | None:
        stmt = (
            select(BalanceSnapshot)
            .where(BalanceSnapshot.id_user == user_id)
            .order_by(
                BalanceSnapshot.reconciliation_date.desc(), BalanceSnapshot.id_snapshot.desc()
            )
            .limit(1)
        )
        return await self.db.scalar(stmt)

    async def list_by_user(self, user_id: int) -> list[BalanceSnapshot]:
        """Most recent first."""
        stmt = (
            select(BalanceSnapshot)
            .where(BalanceSnapshot.id_user == user_id)
            .order_by(
                BalanceSnapshot.reconciliation_date.desc(), BalanceSnapshot.id_snapshot.desc()
            )
        )
        return list((await self.db.scalars(stmt)).all())

    async def create(self, **values) -> BalanceSnapshot:
        snapshot = BalanceSnapshot(**values)
        self.db.add(snapshot)
        await self.db.flush()
        return await self.get_by_id(snapshot.id_user, snapshot.id_snapshot)
