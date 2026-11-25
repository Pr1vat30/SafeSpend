from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.service.achievements.achievements_service import AchievementService


@pytest.mark.asyncio
async def test_check_and_unlock_buffer_intact_30d() -> None:
    ref_date = date(2026, 11, 25)
    catalog = [
        SimpleNamespace(
            id_achievement=1,
            name="Buffer intatto",
            description="30 giorni sopra il buffer",
            badge_path="/badges/buffer.svg",
            criterion={"type": "buffer_intact_30d", "target": 30},
        )
    ]

    ach_dao = AsyncMock()
    ach_dao.get_all_definitions.return_value = catalog
    ach_dao.get_unlocked_map.return_value = {}
    ach_dao.unlock_if_not_exists.return_value = True

    profile_dao = AsyncMock()
    profile_dao.get.return_value = SimpleNamespace(safety_buffer=Decimal("1000.00"))

    daily_balances = {ref_date - timedelta(days=i): Decimal("1250.00") for i in range(30)}
    cashflow_engine = AsyncMock()
    cashflow_engine.get_historical_daily_balances.return_value = daily_balances

    snapshot_dao = AsyncMock()

    service = AchievementService(
        achievement_dao=ach_dao,
        snapshot_dao=snapshot_dao,
        profile_dao=profile_dao,
        cashflow_engine=cashflow_engine,
    )

    unlocked = await service.check_and_unlock_for_user(user_id=1, reference_date=ref_date)

    assert unlocked == [1]
    ach_dao.unlock_if_not_exists.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconciled_4_weeks_partial_progress() -> None:
    ref_date = date(2026, 11, 25)
    catalog = [
        SimpleNamespace(
            id_achievement=2,
            name="Saldo allineato",
            description="4 settimane riconciliate",
            badge_path="/badges/aligned.svg",
            criterion={"type": "reconciled_4_weeks", "target": 4},
        )
    ]

    ach_dao = AsyncMock()
    ach_dao.get_all_definitions.return_value = catalog
    ach_dao.get_unlocked_map.return_value = {}

    snapshot_dao = AsyncMock()
    snapshot_dao.find_between_dates.return_value = [
        SimpleNamespace(reconciliation_date=ref_date - timedelta(days=1)),
        SimpleNamespace(reconciliation_date=ref_date - timedelta(days=8)),
    ]

    service = AchievementService(
        achievement_dao=ach_dao,
        snapshot_dao=snapshot_dao,
        profile_dao=AsyncMock(),
        cashflow_engine=AsyncMock(),
    )

    statuses = await service.get_user_achievements(user_id=1)

    assert len(statuses) == 1
    assert statuses[0].unlocked is False
    assert statuses[0].progress_current == 2
    assert statuses[0].progress_target == 4
