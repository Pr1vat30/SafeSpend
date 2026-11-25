from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, status

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.goals.goals_dto import (
    GoalContributionDTO,
    GoalCreateDTO,
    GoalExtendDeadlineDTO,
    GoalListResponseDTO,
    GoalResponseDTO,
    GoalUpdateDTO,
)

# -- DA DECOMMENTARE PER COLLEGAMENTO REALE --
# from app.core.dependencies import DbSession
# from app.dao.goals.goal_dao import GoalDAO
# from app.service.goals.goals_service import GoalService
# from app.service.what_if_simulator import WhatIfSimulator
# from app.dao.recurring_rule_dao import RecurringRuleDAO
#
# def get_goal_service(db: DbSession) -> GoalService:
#     return GoalService(
#         goal_dao=GoalDAO(db),
#         what_if_simulator=WhatIfSimulator(db),
#         recurring_rule_dao=RecurringRuleDAO(db),
#     )
# ---------------------------------------------


# -- DA RIMUOVERE: STUB PROVVISORIO PER TESTING --
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
            installment_frequency="monthly",
            installment_amount=Decimal("150.00"),
            deadline=date.today() + timedelta(days=180),
            status="active",
            progress_percentage=37.5,
            estimated_completion_date=date.today() + timedelta(days=150),
            is_overdue=False,
            buffer_warning=None,
            id_recurring_rule=None,
            created_at=datetime.now(UTC),
        )
        return GoalListResponseDTO(
            goals=[sample],
            total_saved=Decimal("450.00"),
            total_target=Decimal("1200.00"),
        )

    @staticmethod
    async def create_goal(user_id: int, payload: GoalCreateDTO) -> GoalResponseDTO:
        _ = user_id
        return GoalResponseDTO(
            id_goal=2,
            name=payload.name,
            target_amount=payload.target_amount,
            saved_amount=Decimal("0.00"),
            remaining_amount=payload.target_amount,
            installment_frequency=payload.installment_frequency,
            installment_amount=payload.installment_amount,
            deadline=payload.deadline,
            status="active",
            progress_percentage=0.0,
            estimated_completion_date=payload.deadline,
            is_overdue=False,
            buffer_warning=None,
            id_recurring_rule=None,
            created_at=datetime.now(UTC),
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
            installment_frequency=payload.installment_frequency or "monthly",
            installment_amount=payload.installment_amount or Decimal("100.00"),
            deadline=payload.deadline or (date.today() + timedelta(days=120)),
            status=payload.status or "active",
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
            installment_frequency="monthly",
            installment_amount=Decimal("150.00"),
            deadline=payload.new_deadline,
            status="active",
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
            installment_frequency="monthly",
            installment_amount=Decimal("150.00"),
            deadline=date.today() + timedelta(days=180),
            status="completed" if remaining == Decimal("0.00") else "active",
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
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> GoalListResponseDTO:
    return await goal_service.list_goals(user.id_user)


@router.post(
    "",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un nuovo obiettivo di risparmio (RF_OBI_1, RF_OBI_2)",
)
async def create_goal(
    payload: GoalCreateDTO,
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> GoalResponseDTO:
    return await goal_service.create_goal(user.id_user, payload)


@router.patch(
    "/{goal_id}",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Modifica un obiettivo di risparmio esistente (RF_OBI_1)",
)
async def update_goal(
    goal_id: int,
    payload: GoalUpdateDTO,
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> GoalResponseDTO:
    return await goal_service.update_goal(user.id_user, goal_id, payload)


@router.post(
    "/{goal_id}/contribute",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Registra un versamento/accantonamento sull'obiettivo (RF_OBI_3)",
)
async def contribute_to_goal(
    goal_id: int,
    payload: GoalContributionDTO,
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> GoalResponseDTO:
    return await goal_service.add_contribution(user.id_user, goal_id, payload)


@router.post(
    "/{goal_id}/extend",
    response_model=GoalResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Proroga la scadenza di un obiettivo (RF_OBI_4)",
)
async def extend_goal_deadline(
    goal_id: int,
    payload: GoalExtendDeadlineDTO,
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> GoalResponseDTO:
    return await goal_service.extend_deadline(user.id_user, goal_id, payload)


@router.delete(
    "/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Elimina un obiettivo di risparmio (RF_OBI_1)",
)
async def delete_goal(
    goal_id: int,
    user: CurrentUser,
    goal_service: MockGoalService = Depends(get_goal_service),
) -> None:
    await goal_service.delete_goal(user.id_user, goal_id)
