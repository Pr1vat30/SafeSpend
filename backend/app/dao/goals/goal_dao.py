"""DAO for `goal` (RF_OBI_1–4). Uses `flush()`, never `commit()`."""

from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goals.goal_model import Goal


class GoalDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_by_user(self, user_id: int) -> list[Goal]:
        result = await self.db.execute(
            select(Goal)
            .where(Goal.id_user == user_id)
            .order_by(Goal.deadline.asc(), Goal.id_goal.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, goal_id: int, user_id: int) -> Goal | None:
        result = await self.db.execute(
            select(Goal).where(Goal.id_goal == goal_id, Goal.id_user == user_id)
        )
        return result.scalar_one_or_none()

    async def get_saved_amount(self, goal_id: int, user_id: int) -> Decimal:
        """Computes saved amount from recurring saving occurrences linked to this goal."""
        result = await self.db.execute(
            text(
                "SELECT COALESCE(SUM(t.amount), 0) "
                "FROM transaction t "
                "JOIN recurring_rule r ON t.id_recurring_rule = r.id_recurring_rule "
                "WHERE r.id_goal = :goal_id AND t.id_user = :user_id"
            ),
            {"goal_id": goal_id, "user_id": user_id},
        )
        val = result.scalar_one()
        return Decimal(str(val))

    async def get_linked_rule_id(self, goal_id: int, user_id: int) -> int | None:
        result = await self.db.execute(
            text(
                "SELECT id_recurring_rule FROM recurring_rule "
                "WHERE id_goal = :goal_id AND id_user = :user_id"
            ),
            {"goal_id": goal_id, "user_id": user_id},
        )
        return result.scalar_one_or_none()

    async def create(self, goal: Goal) -> Goal:
        self.db.add(goal)
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def update(self, goal: Goal) -> Goal:
        await self.db.flush()
        await self.db.refresh(goal)
        return goal

    async def delete(self, goal: Goal) -> None:
        await self.db.delete(goal)
        await self.db.flush()
