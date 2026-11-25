"""DAOs of SS1: queries on `_user` and `financial_profile`.

DAOs use `flush()`, never `commit()`: the `get_db` dependency commits once per request.
The only exception is `UserDAO.commit_now()`, see its docstring.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile.profile_model import FinancialProfile, User


class UserDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id_user: int) -> User | None:
        return await self.db.get(User, id_user)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, id_user: int) -> None:
        """Deletes the user; every other table is cleared by ON DELETE CASCADE (RF_AUT_4)."""
        await self.db.execute(delete(User).where(User.id_user == id_user))
        await self.db.flush()

    async def commit_now(self) -> None:
        """Commits immediately.

        Used only by login: a failed attempt must be saved (RF_AUT_2 counts them) even though the
        request then ends with an error, and `get_db` rolls back the session on errors.
        """
        await self.db.commit()


class FinancialProfileDAO:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id_user: int) -> FinancialProfile | None:
        return await self.db.get(FinancialProfile, id_user)

    async def create(self, profile: FinancialProfile) -> FinancialProfile:
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update(self, profile: FinancialProfile) -> FinancialProfile:
        await self.db.flush()
        await self.db.refresh(profile)
        return profile


class BalanceSnapshotReader:
    """Minimal access to `balance_snapshot` (owned by the reconciliation module, SS2/FF).

    SS1 needs it only for the initial setup (RF_AUT_5): to know whether the first reconciliation
    exists and to store it. Later reconciliations (RF_SAL_1) belong to the reconciliation module.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_snapshot(self, id_user: int) -> bool:
        result = await self.db.execute(
            text("SELECT EXISTS (SELECT 1 FROM balance_snapshot WHERE id_user = :id_user)"),
            {"id_user": id_user},
        )
        return bool(result.scalar_one())

    async def create_first_snapshot(self, id_user: int, balance: Decimal, on: date) -> None:
        """First reconciliation: real and calculated balance coincide, so no adjustment."""
        await self.db.execute(
            text(
                "INSERT INTO balance_snapshot "
                "(id_user, real_balance, calculated_balance, reconciliation_date) "
                "VALUES (:id_user, :balance, :balance, :on)"
            ),
            {"id_user": id_user, "balance": balance, "on": on},
        )
        await self.db.flush()


# Tables exported in the user's CSV (RNF_PV_3), with the columns to include. Passwords and
# internal counters are never exported.
EXPORT_TABLES: dict[str, list[str]] = {
    "transaction": [
        "id_transaction",
        "transaction_date",
        "type",
        "amount",
        "id_category",
        "description",
        "origin",
    ],
    "recurring_rule": [
        "id_recurring_rule",
        "name",
        "type",
        "amount",
        "frequency",
        "first_occurrence_date",
        "end_date",
        "status",
    ],
    "planned_transaction": [
        "id_planned_transaction",
        "name",
        "type",
        "amount",
        "planned_date",
        "description",
        "status",
    ],
    "goal": [
        "id_goal",
        "name",
        "target_amount",
        "deadline",
        "installment_frequency",
        "installment_amount",
        "status",
    ],
    "balance_snapshot": [
        "id_snapshot",
        "reconciliation_date",
        "real_balance",
        "calculated_balance",
    ],
    "category": ["id_category", "name", "type"],
}


class UserDataExportDAO:
    """Read-only queries for the CSV export of all the user's data (RNF_PV_3)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def rows(self, table: str, id_user: int) -> list[dict]:
        columns = EXPORT_TABLES[table]  # whitelist: table and column names never come from input
        query = text(
            f"SELECT {', '.join(columns)} FROM {table} WHERE id_user = :id_user ORDER BY 1"
        )
        result = await self.db.execute(query, {"id_user": id_user})
        return [dict(row._mapping) for row in result]
