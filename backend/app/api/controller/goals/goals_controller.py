from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, status

from app.api.dto.goals.goals_dto import (
    GoalContributionDTO,
    GoalCreateDTO,
    GoalExtendDeadlineDTO,
    GoalListResponseDTO,
    GoalResponseDTO,
    GoalUpdateDTO,
)

# -- DA DECOMMENTARE PER COLLEGAMENTO REALE --
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.security import get_current_user_id
# from app.db.session import get_db_session
# from app.dao.goal_dao import GoalDAO
# from app.service.goals_service import GoalService
# from app.service.what_if_simulator import WhatIfSimulator
# from app.dao.recurring_rule_dao import RecurringRuleDAO
#
# def get_goal_service(session: AsyncSession = Depends(get_db_session)) -> GoalService:
#     return GoalService(
#         goal_dao=GoalDAO(session),
#         what_if_simulator=WhatIfSimulator(session),
#         recurring_rule_dao=RecurringRuleDAO(session),
#     )
# ---------------------------------------------


# -- DA RIMUOVERE: STUB PROVVISORIO PER TESTING --
async def get_current_user_id() -> int:
    return 1


class MockGoalService:
    @staticmethod
    async def list_goals(user_id: int) -> GoalListResponseDTO:
        _ = user_id
        sample = GoalResponseDTO(
            id_goal=1,
            name="Fondo Emergenza Vacanze",
            target_amount=Decimal("1200.00"),
            saved_amount=Decimal("450.00"),
            remaining_amount=Decimal("750.00"),
            monthly_contribution=Decimal("150.00"),
            deadline=date.today() + timedelta(days=180),
            priority=1,
            status="ACTIVE",
            progress_percentage=37.5,
            estimated_completion_date=date.today() + timedelta(days=150),
            is_overdue=False,
            buffer_warning=None,
            id_recurring_rule=None,
            created_at=datetime.now(timezone.utc),
        )
        return GoalListResponseDTO(
            goals=[sample],
            total_saved=Decimal("450.00"),
            total_target=Decimal("1200.00"),
        )

    @staticmethod
    async def create_goal(user_id: int, payload: GoalCreateDTO) -> GoalResponseDTO:
        _ = user_id
        remaining = max(payload.target_amount - payload.saved_amount, Decimal("0.00"))
        pct = round(min(float((payload.saved_amount / payload.target_amount) * 100), 100.0), 2)
        return GoalResponseDTO(
            id_goal=2,
            name=payload.name,
            target_amount=payload.target_amount,
            saved_amount=payload.saved_amount,
            remaining_amount=remaining,
            monthly_contribution=payload.monthly_contribution,
            deadline=payload.deadline,
            priority=payload.priority,
            status="ACTIVE",
            progress_percentage=pct,
            estimated_completion_date=payload.deadline,
            is_overdue=False,
            buffer_warning=None,
            id_recurring_rule=None,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def update_goal(user_id: int, goal_id: int, payload: GoalUpdateDTO) -> GoalResponseDTO:
        _ = user_id
        return GoalResponseDTO(
            id_goal=goal_id,
            name=payload.name or "Obiettivo Aggiornato",
            target_amount=payload.target_amount or Decimal("1000.00"),
            saved_amount=Decimal("450.00"),
            remaining_amount=Decimal("550.00"),
            monthly_contribution=payload.monthly_contribution or Decimal("100.00"),
            deadline=payload.deadline or (date.today() + timedelta(days=120)),
            priority=payload.priority or 1,
            status=payload.status or "ACTIVE",
            progress_percentage=45.0,
            estimated_completion_date=date.today() + timedelta(days=165),
            is_overdue=False,
        )

    @staticmethod
    async def extend_deadline(
        user_id: int, goal_id: int, payload: GoalExtendDeadlineDTO
    ) -> GoalResponseDTO:
        _ = user_id
        return GoalResponseDTO(
            id_goal=goal_id,
            name="Obiettivo Prorogato",
            target_amount=Decimal("1200.00"),
            saved_amount=Decimal("450.00"),
            remaining_amount=Decimal("750.00"),
            monthly_contribution=Decimal("150.00"),
            deadline=payload.new_deadline,
            priority=1,
            status="ACTIVE",
            progress_percentage=37.5,
            estimated_completion_date=payload.new_deadline,
            is_overdue=False,
        )

    @staticmethod
    async def add_contribution(
        user_id: int, goal_id: int, payload: GoalContributionDTO
    ) -> GoalResponseDTO:
        _ = user_id
        new_saved = Decimal("450.00") + payload.amount
        target = Decimal("1200.00")
        remaining = max(target - new_saved, Decimal("0.00"))
        pct = round(min(float((new_saved / target) * 100), 100.0), 2)
        return GoalResponseDTO(
            id_goal=goal_id,
            name="Fondo Emergenza Vacanze",
            target_amount=target,
            saved_amount=new_saved,
            remaining_amount=remaining,
            monthly_contribution=Decimal("150.00"),
            deadline=date.today() + timedelta(days=180),
            priority=1,
            status="COMPLETED" if remaining == Decimal("0.00") else "ACTIVE",
            progress_percentage=pct,
            estimated_completion_date=date.today() + timedelta(days=120),
            is_overdue=False,
        )

    @staticmethod
    async def delete_goal(user_id: int, goal_id: int) -> None:
        _ = (user_id, goal_id)


def get_goal_service() -> MockGoalService:
    return MockGoalService()
# ------------------------------------------------


router = APIRouter(
    prefix="/goals",
    tags=["Goals"],
)


@router.get(
    "",
    response_model=GoalListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Elenca gli obiettivi di risparmio dell'utente (RF_OBI_3)",
)
async def get_user_goals(
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> GoalListResponseDTO:
    return await goal_service.list_goals(user_id)


@router.post(
    "",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuovo obiettivo di risparmio (RF_OBI_1, RF_OBI_2)",
)
async def create_goal(
    payload: GoalCreateDTO,
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> GoalResponseDTO:
    return await goal_service.create_goal(user_id, payload)


@router.patch(
    "/{goal_id}",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Modifica un obiettivo di risparmio esistente (RF_OBI_1)",
)
async def update_goal(
    goal_id: int,
    payload: GoalUpdateDTO,
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> GoalResponseDTO:
    return await goal_service.update_goal(user_id, goal_id, payload)


@router.post(
    "/{goal_id}/contribute",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Registra un versamento/accantonamento sull'obiettivo (RF_OBI_3)",
)
async def contribute_to_goal(
    goal_id: int,
    payload: GoalContributionDTO,
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> GoalResponseDTO:
    return await goal_service.add_contribution(user_id, goal_id, payload)


@router.post(
    "/{goal_id}/extend",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Proroga la scadenza di un obiettivo (RF_OBI_4)",
)
async def extend_goal_deadline(
    goal_id: int,
    payload: GoalExtendDeadlineDTO,
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> GoalResponseDTO:
    return await goal_service.extend_deadline(user_id, goal_id, payload)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un obiettivo di risparmio (RF_OBI_1)",
)
async def delete_goal(
    goal_id: int,
    user_id: int = Depends(get_current_user_id),
    goal_service: MockGoalService = Depends(get_goal_service),
    # goal_service: GoalService = Depends(get_goal_service), DA DECOMMENTARE PER IMPLEMENTAZIONE REALE
) -> None:
    await goal_service.delete_goal(user_id, goal_id)