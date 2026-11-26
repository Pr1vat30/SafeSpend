"""Transaction business logic: validation against categories, filters and totals.

INTEGRATION WITH THE CASH FLOW ENGINE (not in `main` yet; nothing is implemented or stubbed here)
Balance, Safe-to-Spend (STS) and projections are not computed by this module. The `transaction`
table is their input, and these are the only points where manual income/expense rows change:

- `create_transaction`, `update_transaction`, `delete_transaction` (this class);
- the request is committed once by `get_db` after the service returns, so any code that reads
  the table in a later request already sees the new data.

Today there is nothing to call. When the Cash Flow Engine is merged, one of two things applies:
1. it reads the table on demand: no change is needed in this module;
2. it keeps stored or cached results (balance, STS, alerts): call it from the three methods above,
   after the DAO call and inside the same request, passing `user_id` and the affected dates
   (the old and the new date on update). Inject it through the constructor, like the DAOs.

Category deletion (`CategoryService.delete_category`) only changes `id_category`: amounts, types
and dates stay the same, so it does not affect balance, STS or projections.
On the frontend, `app/transactions/page.tsx` reloads its list after every change; a screen that
shows STS or projections must be refreshed at the same points (marked with `CASH FLOW`).
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import AppException, NotFoundError
from app.dao.transaction.balance_snapshot_dao import BalanceSnapshotDAO
from app.dao.transaction.category_dao import CategoryDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.models.transaction.transaction_model import Transaction
from app.service.transaction import messages


class TransactionService:
    def __init__(
        self,
        dao: TransactionDAO,
        category_dao: CategoryDAO,
        snapshot_dao: BalanceSnapshotDAO | None = None,
    ):
        self.dao = dao
        self.category_dao = category_dao
        self.snapshot_dao = snapshot_dao

    async def create_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount: Decimal,
        transaction_date: date,
        id_category: int,
        description: str | None,
    ) -> tuple[Transaction, str]:
        await self._check_category(user_id, id_category, transaction_type)
        created = await self.dao.create(
            id_user=user_id,
            type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            id_category=id_category,
            description=description,
            origin="manual",
        )
        notice = await self._message_for_dates(
            user_id, messages.TRANSACTION_CREATED, transaction_date
        )
        return created, notice

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
    ) -> tuple[Transaction, str]:
        transaction = await self._get_editable(user_id, transaction_id)
        old_date = transaction.transaction_date
        await self._check_category(user_id, id_category, transaction_type)
        updated = await self.dao.update(
            transaction,
            type=transaction_type,
            amount=amount,
            transaction_date=transaction_date,
            id_category=id_category,
            description=description,
        )
        notice = await self._message_for_dates(
            user_id, messages.TRANSACTION_UPDATED, old_date, transaction_date
        )
        return updated, notice

    async def delete_transaction(self, user_id: int, transaction_id: int) -> str:
        transaction = await self._get_editable(user_id, transaction_id)
        old_date = transaction.transaction_date
        await self.dao.delete(transaction)
        return await self._message_for_dates(user_id, messages.TRANSACTION_DELETED, old_date)

    async def _message_for_dates(self, user_id: int, base_message: str, *dates: date) -> str:
        """RF_SAL_1: warn if a movement falls on or before the latest reconciliation date."""
        if self.snapshot_dao is None:
            return base_message
        latest = await self.snapshot_dao.get_latest(user_id)
        if latest is not None and any(d <= latest.reconciliation_date for d in dates):
            return messages.transaction_before_reconciliation(
                base_message, latest.reconciliation_date
            )
        return base_message

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
