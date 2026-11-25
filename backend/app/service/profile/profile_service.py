"""Business logic of the financial profile (SS1): RF_AUT_4, RF_AUT_5, RF_CF_3, RNF_PV_2–3."""

import csv
import io
from datetime import date, datetime
from decimal import Decimal

from app.api.dto.profile.schema import InitialSetupRequest, ProfileRead
from app.core.exceptions import ConflictError, NotFoundError
from app.dao.profile.profile_dao import (
    EXPORT_TABLES,
    BalanceSnapshotReader,
    FinancialProfileDAO,
    UserDAO,
    UserDataExportDAO,
)
from app.models.profile.profile_model import FinancialProfile, User
from app.service.profile import messages as msg
from app.service.profile import security
from app.service.profile.auth_service import ROME
from app.service.profile.exceptions import UnauthorizedError


def today_rome() -> date:
    return datetime.now(ROME).date()


class ProfileService:
    def __init__(
        self,
        users: UserDAO,
        profiles: FinancialProfileDAO,
        snapshots: BalanceSnapshotReader,
        export: UserDataExportDAO,
    ):
        self.users = users
        self.profiles = profiles
        self.snapshots = snapshots
        self.export = export

    async def _profile_of(self, user: User) -> FinancialProfile:
        profile = await self.profiles.get(user.id_user)
        if profile is None:  # created at registration: missing only if data were altered by hand
            raise NotFoundError(msg.PROFILE_NOT_FOUND)
        return profile

    async def get_profile(self, user: User) -> ProfileRead:
        profile = await self._profile_of(user)
        return ProfileRead.model_validate(
            {
                "user": user,
                "financial_profile": profile,
                "setup_completed": await self.snapshots.has_snapshot(user.id_user),
            }
        )

    async def is_setup_completed(self, user: User) -> bool:
        """RF_AUT_5: STS and simulations are available only after the first balance is entered.
        Other modules (dashboard, simulation) can call this before computing."""
        return await self.snapshots.has_snapshot(user.id_user)

    async def initial_setup(self, user: User, data: InitialSetupRequest) -> ProfileRead:
        """RF_AUT_5: first access. Saves the current balance as first reconciliation (RF_SAL_1),
        the Safety Buffer (RF_CF_3) and the optional monthly estimate of variable expenses."""
        if await self.snapshots.has_snapshot(user.id_user):
            raise ConflictError(msg.SETUP_ALREADY_DONE)
        profile = await self._profile_of(user)
        profile.safety_buffer = data.safety_buffer
        profile.estimated_variable_expenses = data.estimated_variable_expenses
        await self.profiles.update(profile)
        await self.snapshots.create_first_snapshot(user.id_user, data.current_balance, today_rome())
        return await self.get_profile(user)

    async def update_profile(self, user: User, changes: dict) -> ProfileRead:
        """Partial update: Safety Buffer (RF_CF_3), estimate (RF_PRE_1), horizon (RF_CF_5),
        AI consent (RNF_PV_2, revocable at any time).

        RF_CF_3 also asks for a confirmation when the new Safety Buffer brings STS to zero: that
        check needs the Cash Flow Engine (B-01, LT) and is added once it is available.
        """
        profile = await self._profile_of(user)
        for field, value in changes.items():
            setattr(profile, field, value)
        if changes:
            await self.profiles.update(profile)
        return await self.get_profile(user)

    async def delete_account(self, user: User, password: str) -> None:
        """RF_AUT_4: after password confirmation, deletes the user and, by cascade, every
        personal and financial record."""
        if not security.verify_password(password, user.password):
            raise UnauthorizedError(msg.WRONG_PASSWORD)
        await self.users.delete(user.id_user)

    async def export_csv(self, user: User) -> str:
        """RNF_PV_3: all the user's data in one CSV (Italian Excel format: `;`, decimal comma,
        dd/mm/yyyy). One section per table, separated by an empty line."""
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";", lineterminator="\r\n")

        profile = await self._profile_of(user)
        writer.writerow(["# account"])
        writer.writerow(["nome", "cognome", "email", "registrato_il"])
        writer.writerow([user.name, user.surname, user.email, _fmt(user.created_at)])
        writer.writerow([])
        writer.writerow(["# profilo_finanziario"])
        writer.writerow(
            ["safety_buffer", "orizzonte_giorni", "stima_spese_variabili_mensile", "consenso_ai"]
        )
        writer.writerow(
            [
                _fmt(profile.safety_buffer),
                profile.horizon_days,
                _fmt(profile.estimated_variable_expenses),
                "sì" if profile.ai_consent else "no",
            ]
        )

        for table, columns in EXPORT_TABLES.items():
            writer.writerow([])
            writer.writerow([f"# {table}"])
            writer.writerow(columns)
            for row in await self.export.rows(table, user.id_user):
                writer.writerow([_fmt(row[c]) for c in columns])
        return out.getvalue()


def _fmt(value) -> str:
    """Italian formats for the CSV: 1234,56 and dd/mm/yyyy."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return f"{value:.2f}".replace(".", ",")
    if isinstance(value, datetime):
        return value.astimezone(ROME).strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return str(value)
