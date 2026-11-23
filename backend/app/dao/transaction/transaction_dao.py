"""Transaction DAO: database queries only. Uses `flush()`, never `commit()`.

Every query is scoped by `id_user`, so a user can never reach another user's rows.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction.transaction_model import Transaction


class TransactionDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _conditions(
        user_id: int,
        date_from: date | None,
        date_to: date | None,
        transaction_type: str | None,
        category_id: int | None,
    ) -> list:
        conditions = [Transaction.id_user == user_id]
        if date_from is not None:
            conditions.append(Transaction.transaction_date >= date_from)
        if date_to is not None:
            conditions.append(Transaction.transaction_date <= date_to)
        if transaction_type is not None:
            conditions.append(Transaction.type == transaction_type)
        if category_id is not None:
            conditions.append(Transaction.id_category == category_id)
        return conditions

    async def get_by_id(self, user_id: int, transaction_id: int) -> Transaction | None:
        stmt = (
            select(Transaction)
            .where(Transaction.id_user == user_id, Transaction.id_transaction == transaction_id)
            .execution_options(populate_existing=True)
        )
        return await self.db.scalar(stmt)

    async def list_filtered(
        self,
        user_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        transaction_type: str | None = None,
        category_id: int | None = None,
    ) -> list[Transaction]:
        """Most recent first."""
        stmt = (
            select(Transaction)
            .where(*self._conditions(user_id, date_from, date_to, transaction_type, category_id))
            .order_by(Transaction.transaction_date.desc(), Transaction.id_transaction.desc())
        )
        return list((await self.db.scalars(stmt)).all())

    async def totals(
        self,
        user_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        transaction_type: str | None = None,
        category_id: int | None = None,
    ) -> dict[str, Decimal]:
        """Sum of income and of expense over the filtered rows (adjustments are not counted)."""
        stmt = (
            select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0))
            .where(
                *self._conditions(user_id, date_from, date_to, transaction_type, category_id),
                Transaction.type.in_(("income", "expense")),
            )
            .group_by(Transaction.type)
        )
        sums = {"income": Decimal("0.00"), "expense": Decimal("0.00")}
        for row_type, total in (await self.db.execute(stmt)).all():
            sums[row_type] = Decimal(total)
        return sums

    async def create(self, **values) -> Transaction:
        transaction = Transaction(**values)
        self.db.add(transaction)
        await self.db.flush()
        return await self.get_by_id(transaction.id_user, transaction.id_transaction)

    async def update(self, transaction: Transaction, **values) -> Transaction:
        for field, value in values.items():
            setattr(transaction, field, value)
        await self.db.flush()
        return await self.get_by_id(transaction.id_user, transaction.id_transaction)

    async def delete(self, transaction: Transaction) -> None:
        await self.db.delete(transaction)
        await self.db.flush()
