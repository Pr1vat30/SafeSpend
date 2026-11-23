"""Transaction business logic: validation against categories, filters and totals.

Balance, Safe-to-Spend and projections are derived from the `transaction` table by the Cash Flow
Engine, so they stay correct after every insert, update or delete without being duplicated here.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import AppException, NotFoundError
from app.dao.transaction.category_dao import CategoryDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.models.transaction.transaction_model import Transaction
from app.service.transaction import messages


class TransactionService:
    def __init__(self, dao: TransactionDAO, category_dao: CategoryDAO):
        self.dao = dao
        self.category_dao = category_dao

    async def create_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount: Decimal,
        transaction_date: date,
        id_category: int,
        description: str | None,
    ) -> Transaction:
        await self._check_category(user_id, id_category, transaction_type)
        return await self.dao.create(
            id_user=user_id,
            type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            id_category=id_category,
            description=description,
            origin="manual",
        )

    async def list_transactions(
        self,
        user_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        transaction_type: str | None = None,
        category_id: int | None = None,
    ) -> tuple[list[Transaction], dict[str, Decimal]]:
        """Filtered transactions (most recent first) and the totals of that same set."""
        if date_from and date_to and date_from > date_to:
            raise AppException(messages.INVALID_PERIOD)
        items = await self.dao.list_filtered(
            user_id, date_from, date_to, transaction_type, category_id
        )
        totals = await self.dao.totals(user_id, date_from, date_to, transaction_type, category_id)
        return items, totals

    async def get_transaction(self, user_id: int, transaction_id: int) -> Transaction:
        transaction = await self.dao.get_by_id(user_id, transaction_id)
        if transaction is None:
            raise NotFoundError(messages.TRANSACTION_NOT_FOUND)
        return transaction

    async def update_transaction(
        self,
        user_id: int,
        transaction_id: int,
        transaction_type: str,
        amount: Decimal,
        transaction_date: date,
        id_category: int,
        description: str | None,
    ) -> Transaction:
        transaction = await self._get_editable(user_id, transaction_id)
        await self._check_category(user_id, id_category, transaction_type)
        return await self.dao.update(
            transaction,
            type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            id_category=id_category,
            description=description,
        )

    async def delete_transaction(self, user_id: int, transaction_id: int) -> None:
        transaction = await self._get_editable(user_id, transaction_id)
        await self.dao.delete(transaction)

    async def _get_editable(self, user_id: int, transaction_id: int) -> Transaction:
        transaction = await self.get_transaction(user_id, transaction_id)
        if transaction.type not in ("income", "expense"):
            raise AppException(messages.TRANSACTION_NOT_EDITABLE)
        return transaction

    async def _check_category(self, user_id: int, category_id: int, transaction_type: str) -> None:
        """The category must be a default one or the user's own, and fit the transaction type."""
        category = await self.category_dao.get_visible(user_id, category_id)
        if category is None:
            raise NotFoundError(messages.CATEGORY_NOT_FOUND)
        if category.type not in (transaction_type, "both"):
            raise AppException(messages.CATEGORY_TYPE_MISMATCH)
