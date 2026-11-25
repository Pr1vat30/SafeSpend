from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.dto.goals.goals_dto import (
    GoalCreateDTO,
    GoalExtendDeadlineDTO,
)
from app.models.goals.goal_model import Goal
from app.service.goals.goals_service import GoalService


@pytest.mark.asyncio
async def test_create_goal_active_and_progress() -> None:
    mock_dao = AsyncMock()
    mock_dao.create.side_effect = lambda g: Goal(
        id_goal=10,
        id_user=g.id_user,
        name=g.name,
        target_amount=g.target_amount,
        deadline=g.deadline,
        installment_frequency=g.installment_frequency,
        installment_amount=g.installment_amount,
        status=g.status,
        created_at=datetime(2026, 11, 25, 10, 0),
    )

    service = GoalService(goal_dao=mock_dao)
    payload = GoalCreateDTO(
        name="Fondo Emergenza",
        target_amount=Decimal("1000.00"),
        installment_frequency="monthly",
        installment_amount=Decimal("150.00"),
        deadline=date.today() + timedelta(days=180),
        create_recurring_rule=False,
    )

    res = await service.create_goal(user_id=1, payload=payload)

    assert res.id_goal == 10
    assert res.status == "active"
    assert res.saved_amount == Decimal("0.00")
    assert res.remaining_amount == Decimal("1000.00")
    assert res.progress_percentage == 0.0
    assert res.is_overdue is False


@pytest.mark.asyncio
async def test_extend_deadline_reactivates_expired_goal() -> None:
    past_deadline = date.today() - timedelta(days=5)
    existing_goal = Goal(
        id_goal=1,
        id_user=1,
        name="Viaggio",
        target_amount=Decimal("1200.00"),
        deadline=past_deadline,
        installment_frequency="monthly",
        installment_amount=Decimal("100.00"),
        status="expired",
        created_at=datetime(2026, 1, 10, 10, 0),
    )

    mock_dao = AsyncMock()
    mock_dao.get_by_id.return_value = existing_goal
    mock_dao.get_saved_amount.return_value = Decimal("400.00")
    mock_dao.get_linked_rule_id.return_value = None
    mock_dao.update.side_effect = lambda g: g

    service = GoalService(goal_dao=mock_dao)
    new_date = date.today() + timedelta(days=60)
    res = await service.extend_deadline(
        user_id=1,
        goal_id=1,
        payload=GoalExtendDeadlineDTO(new_deadline=new_date),
    )

    assert res.deadline == new_date
    assert res.status == "active"
    assert res.remaining_amount == Decimal("800.00")
    assert res.is_overdue is False


@pytest.mark.asyncio
async def test_extend_deadline_goal_not_found_raises_404() -> None:
    mock_dao = AsyncMock()
    mock_dao.get_by_id.return_value = None

    service = GoalService(goal_dao=mock_dao)

    with pytest.raises(HTTPException) as exc:
        await service.extend_deadline(
            user_id=1,
            goal_id=999,
            payload=GoalExtendDeadlineDTO(new_deadline=date.today() + timedelta(days=30)),
        )

    assert exc.value.status_code == 404
