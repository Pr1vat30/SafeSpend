"""Data access for recurring rules. Queries only: `flush()`, never `commit()`."""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel


class RecurringRuleDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, rule: RecurringRuleModel) -> RecurringRuleModel:
        self.db.add(rule)
        return await self.save(rule)

    async def save(self, rule: RecurringRuleModel) -> RecurringRuleModel:
        """Write pending changes and reload the row (picks up server-side defaults)."""
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def get_by_id_for_user(self, rule_id: int, user_id: int) -> RecurringRuleModel | None:
        """Return the rule only if it belongs to the user (isolation between users, RNF_SE_3)."""
        stmt = select(RecurringRuleModel).where(
            RecurringRuleModel.id_recurring_rule == rule_id,
            RecurringRuleModel.id_user == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_user(self, user_id: int, status: str | None = None):
        stmt = select(RecurringRuleModel).where(RecurringRuleModel.id_user == user_id)
        if status is not None:
            stmt = stmt.where(RecurringRuleModel.status == status)
        stmt = stmt.order_by(
            RecurringRuleModel.first_occurrence_date, RecurringRuleModel.id_recurring_rule
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete(self, rule: RecurringRuleModel) -> None:
        await self.db.delete(rule)
        await self.db.flush()

    async def get_category_type(self, category_id: int, user_id: int) -> str | None:
        """Type ('income', 'expense', 'both') of a category the user may use, else None.

        TEMPORARY: a plain query on `category` because that module has no DAO yet.
        Replace it with the category module's DAO once it exists.
        """
        row = await self.db.execute(
            text(
                "SELECT type FROM category "
                "WHERE id_category = :cid AND (is_default OR id_user = :uid)"
            ),
            {"cid": category_id, "uid": user_id},
        )
        return row.scalar_one_or_none()
