"""Balance reconciliation business logic (`RF_SAL_1`, `RF_SAL_2`).

Compares the balance calculated from the user's transactions with the user's real balance,
records an immutable `BalanceSnapshot` and, when they differ, creates an `adjustment`
transaction (`origin='reconciliation'`) so future calculations start from the real balance.

Note on Cash Flow Engine integration: creating an adjustment writes a row to `transaction`
within the same request/transaction (`get_db` commits once at the end). If the Cash Flow
Engine caches balance/STS/projections, refresh it after `reconcile` in the same way as
`TransactionService`.
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import AppException, NotFoundError
from app.dao.transaction.balance_snapshot_dao import BalanceSnapshotDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.models.transaction.balance_snapshot_model import BalanceSnapshot
from app.service.transaction import messages


class ReconciliationService:
    def __init__(self, snapshot_dao: BalanceSnapshotDAO, transaction_dao: TransactionDAO):
        self.snapshot_dao = snapshot_dao
        self.transaction_dao = transaction_dao

    async def preview(
        self, user_id: int, reconciliation_date: date | None = None
    ) -> tuple[date, Decimal, BalanceSnapshot | None]:
        target_date = reconciliation_date or date.today()
        if target_date > date.today():
            raise AppException(messages.FUTURE_RECONCILIATION_DATE)
        calculated = await self.transaction_dao.calculated_balance(user_id, target_date)
        latest = await self.snapshot_dao.get_latest(user_id)
        return target_date, calculated, latest

    async def reconcile(
        self,
        user_id: int,
        real_balance: Decimal,
        reconciliation_date: date,
        description: str | None = None,
    ) -> tuple[BalanceSnapshot, bool]:
        if reconciliation_date > date.today():
            raise AppException(messages.FUTURE_RECONCILIATION_DATE)

        calculated = await self.transaction_dao.calculated_balance(user_id, reconciliation_date)
        difference = (real_balance - calculated).quantize(Decimal("0.01"))

        adjustment_id: int | None = None
        if difference != Decimal("0.00"):
            adjustment = await self.transaction_dao.create(
                id_user=user_id,
                id_category=None,
                type="adjustment",
                origin="reconciliation",
                amount=difference,
                transaction_date=reconciliation_date,
                description=description
                or messages.reconciliation_description(calculated, real_balance),
            )
            adjustment_id = adjustment.id_transaction

        snapshot = await self.snapshot_dao.create(
            id_user=user_id,
            id_adjustment_transaction=adjustment_id,
            real_balance=real_balance.quantize(Decimal("0.01")),
            calculated_balance=calculated,
            reconciliation_date=reconciliation_date,
        )
        return snapshot, adjustment_id is not None

    async def list_reconciliations(self, user_id: int) -> tuple[list[BalanceSnapshot], Decimal]:
        snapshots = await self.snapshot_dao.list_by_user(user_id)
        current_balance = await self.transaction_dao.calculated_balance(user_id, date.today())
        return snapshots, current_balance

    async def get_reconciliation(self, user_id: int, snapshot_id: int) -> BalanceSnapshot:
        snapshot = await self.snapshot_dao.get_by_id(user_id, snapshot_id)
        if snapshot is None:
            raise NotFoundError(messages.RECONCILIATION_NOT_FOUND)
        return snapshot
