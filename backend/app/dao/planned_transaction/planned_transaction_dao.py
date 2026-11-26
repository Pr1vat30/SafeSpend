"""Data access for planned transactions.

Queries only: `flush`/commit are handled by the unit of work.
"""

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.planned_transaction.planned_transaction_model import PlannedTransactionModel


class PlannedTransactionDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, planned: PlannedTransactionModel) -> PlannedTransactionModel:
        self.db.add(planned)
        return await self.save(planned)

    async def save(self, planned: PlannedTransactionModel) -> PlannedTransactionModel:
        """Write pending changes and reload the row (picks up server-side defaults)."""
        await self.db.flush()
        await self.db.refresh(planned)
        return planned

    async def get_by_id_for_user(
        self, planned_id: int, user_id: int
    ) -> PlannedTransactionModel | None:
        """Return the planned transaction only if it belongs to the user.

        Isolation between users (RNF_SE_3).
        """
        stmt = select(PlannedTransactionModel).where(
            PlannedTransactionModel.id_planned_transaction == planned_id,
            PlannedTransactionModel.id_user == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        status: str | None = None,
        type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PlannedTransactionModel]:
        stmt = select(PlannedTransactionModel).where(PlannedTransactionModel.id_user == user_id)
        if status is not None:
            stmt = stmt.where(PlannedTransactionModel.status == status)
        if type is not None:
            stmt = stmt.where(PlannedTransactionModel.type == type)
        if date_from is not None:
            stmt = stmt.where(PlannedTransactionModel.planned_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(PlannedTransactionModel.planned_date <= date_to)
        stmt = stmt.order_by(
            PlannedTransactionModel.planned_date, PlannedTransactionModel.id_planned_transaction
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete(self, planned: PlannedTransactionModel) -> None:
        await self.db.delete(planned)
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

    async def confirm_income(self, planned: PlannedTransactionModel) -> PlannedTransactionModel:
        """Confirm a pending income: mark as recorded. Idempotent."""
        if planned.status != "pending_confirmation":
            return planned
        planned.status = "recorded"
        return await self.save(planned)

    async def reject_income(self, planned: PlannedTransactionModel) -> PlannedTransactionModel:
        """Reject a pending income: mark as cancelled. Idempotent."""
        if planned.status != "pending_confirmation":
            return planned
        planned.status = "cancelled"
        return await self.save(planned)

    async def cancel_planned(self, planned: PlannedTransactionModel) -> PlannedTransactionModel:
        """Cancel a planned transaction (expense or income) before its date."""
        if planned.status in ("recorded", "cancelled"):
            return planned
        planned.status = "cancelled"
        return await self.save(planned)

    async def list_pending_incomes_for_user(self, user_id: int) -> list[PlannedTransactionModel]:
        """List pending confirmation incomes for the user (for the confirmation UI)."""
        stmt = (
            select(PlannedTransactionModel)
            .where(
                PlannedTransactionModel.id_user == user_id,
                PlannedTransactionModel.status == "pending_confirmation",
                PlannedTransactionModel.type == "income",
            )
            .order_by(PlannedTransactionModel.planned_date)
        )
        return list((await self.db.execute(stmt)).scalars().all())
