"""Balance reconciliation business logic (`RF_SAL_1`, `RF_SAL_2`).

Compares the system's starting balance (`B0 = last_reconciled + transactions after that date`,
or the algebraic sum of all transactions up to `reconciliation_date` before any reconciliation)
with the user's real balance, records an immutable `BalanceSnapshot` and, when they differ,
creates an `adjustment` transaction (`origin='reconciliation'`).
"""

from datetime import date
from decimal import Decimal

from app.core.exceptions import AppException, NotFoundError
from app.dao.transaction.balance_snapshot_dao import BalanceSnapshotDAO
from app.dao.transaction.transaction_dao import TransactionDAO
from app.models.transaction.balance_snapshot_model import BalanceSnapshot
from app.service.profile.profile_service import today_rome
from app.service.transaction import messages

REMINDER_THRESHOLD_DAYS = 7


class ReconciliationService:
    def __init__(self, snapshot_dao: BalanceSnapshotDAO, transaction_dao: TransactionDAO):
        self.snapshot_dao = snapshot_dao
        self.transaction_dao = transaction_dao

    async def _calculated_balance_at(
        self, user_id: int, target_date: date
    ) -> tuple[Decimal, BalanceSnapshot | None]:
        """Compute B0 as of `target_date` per RAD §1.4 / RF_SAL_1."""
        latest = await self.snapshot_dao.get_latest(user_id)
        if latest is not None and target_date >= latest.reconciliation_date:
            delta = await self.transaction_dao.calculated_balance(
                user_id, up_to_date=target_date, after_date=latest.reconciliation_date
            )
            return (latest.real_balance + delta).quantize(Decimal("0.01")), latest
        calculated = await self.transaction_dao.calculated_balance(user_id, up_to_date=target_date)
        return calculated, latest

    async def preview(
        self, user_id: int, reconciliation_date: date | None = None
    ) -> tuple[date, Decimal, BalanceSnapshot | None, int | None, bool]:
        today = today_rome()
        target_date = reconciliation_date or today
        if target_date > today:
            raise AppException(messages.FUTURE_RECONCILIATION_DATE)
        calculated, latest = await self._calculated_balance_at(user_id, target_date)
        days_since = (today - latest.reconciliation_date).days if latest is not None else None
        reminder = days_since is not None and days_since > REMINDER_THRESHOLD_DAYS
        return target_date, calculated, latest, days_since, reminder

    async def reconcile(
        self,
        user_id: int,
        real_balance: Decimal,
        reconciliation_date: date,
        description: str | None = None,
    ) -> tuple[BalanceSnapshot, bool]:
        if reconciliation_date > today_rome():
            raise AppException(messages.FUTURE_RECONCILIATION_DATE)

        calculated, _ = await self._calculated_balance_at(user_id, reconciliation_date)
        difference = (real_balance - calculated).quantize(Decimal("0.01"))

        adjustment_id: int | None = None
        if difference != Decimal("0.00"):
            default_desc = messages.reconciliation_description(calculated, real_balance)
            adjustment = await self.transaction_dao.create(
                id_user=user_id,
                id_category=None,
                type="adjustment",
                origin="reconciliation",
                amount=difference,
                transaction_date=reconciliation_date,
                description=description or default_desc,
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
        current_balance, _ = await self._calculated_balance_at(user_id, today_rome())
        return snapshots, current_balance

    async def get_reconciliation(self, user_id: int, snapshot_id: int) -> BalanceSnapshot:
        snapshot = await self.snapshot_dao.get_by_id(user_id, snapshot_id)
        if snapshot is None:
            raise NotFoundError(messages.RECONCILIATION_NOT_FOUND)
        return snapshot
