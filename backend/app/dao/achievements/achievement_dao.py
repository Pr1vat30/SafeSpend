"""DAO for `achievement` and `user_achievement` (RF_PRE_6). Uses `flush()`, never `commit()`."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievements.achievement_model import Achievement, UserAchievement


class AchievementDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Achievement]:
        result = await self.db.execute(
            select(Achievement).order_by(Achievement.id_achievement.asc())
        )
        return list(result.scalars().all())

    async def list_unlocked_by_user(self, id_user: int) -> dict[int, UserAchievement]:
        """Returns a map `{id_achievement: UserAchievement}` for the given user."""
        result = await self.db.execute(
            select(UserAchievement).where(UserAchievement.id_user == id_user)
        )
        return {row.id_achievement: row for row in result.scalars().all()}

    async def unlock(self, id_user: int, id_achievement: int) -> UserAchievement:
        """Idempotently unlocks an achievement for a user."""
        existing = await self.db.get(UserAchievement, (id_user, id_achievement))
        if existing is not None:
            return existing

        entry = UserAchievement(id_user=id_user, id_achievement=id_achievement)
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry
