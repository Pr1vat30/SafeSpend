"""Category DAO: database queries only. Uses `flush()`, never `commit()`."""

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction.category_model import Category
from app.models.transaction.transaction_model import Transaction


class CategoryDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_visible(self, user_id: int) -> list[Category]:
        """Default categories plus the categories created by the user."""
        stmt = (
            select(Category)
            .where(or_(Category.id_user.is_(None), Category.id_user == user_id))
            .order_by(Category.type, Category.is_default.desc(), func.lower(Category.name))
        )
        return list((await self.db.scalars(stmt)).all())

    async def get_visible(self, user_id: int, category_id: int) -> Category | None:
        stmt = select(Category).where(
            Category.id_category == category_id,
            or_(Category.id_user.is_(None), Category.id_user == user_id),
        )
        return await self.db.scalar(stmt)

    async def get_default(self, name: str, category_type: str) -> Category | None:
        stmt = select(Category).where(
            Category.id_user.is_(None), Category.name == name, Category.type == category_type
        )
        return await self.db.scalar(stmt)

    async def find_by_name(self, user_id: int, name: str) -> list[Category]:
        """Visible categories with the same name (case-insensitive)."""
        stmt = select(Category).where(
            func.lower(Category.name) == name.lower(),
            or_(Category.id_user.is_(None), Category.id_user == user_id),
        )
        return list((await self.db.scalars(stmt)).all())

    async def create(self, user_id: int, name: str, category_type: str) -> Category:
        category = Category(id_user=user_id, name=name, type=category_type, is_default=False)
        self.db.add(category)
        await self.db.flush()
        return category

    async def rename(self, category: Category, name: str) -> Category:
        category.name = name
        await self.db.flush()
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)
        await self.db.flush()

    async def reassign_transactions(
        self, user_id: int, from_category_id: int, transaction_type: str, to_category_id: int
    ) -> int:
        """Move the user's transactions of one type to another category. Returns the row count."""
        stmt = (
            update(Transaction)
            .where(
                Transaction.id_user == user_id,
                Transaction.id_category == from_category_id,
                Transaction.type == transaction_type,
            )
            .values(id_category=to_category_id)
            .execution_options(synchronize_session=False)
        )
        result = await self.db.execute(stmt)
        return result.rowcount

    async def count_references(self, category_id: int) -> tuple[int, int]:
        """Recurring rules and planned transactions (rules, planned) that still use the category."""
        row = await self.db.execute(
            text(
                "SELECT (SELECT count(*) FROM recurring_rule WHERE id_category = :id),"
                " (SELECT count(*) FROM planned_transaction WHERE id_category = :id)"
            ),
            {"id": category_id},
        )
        rules, planned = row.one()
        return int(rules), int(planned)
