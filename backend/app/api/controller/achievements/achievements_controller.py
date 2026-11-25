from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status

from app.api.controller.profile.dependencies import CurrentUser
from app.api.dto.achievements.achievements_dto import (
    AchievementListResponseDTO,
    AchievementStatusDTO,
)

# -- DA DECOMMENTARE PER COLLEGAMENTO REALE --
# from app.core.dependencies import DbSession
# from app.dao.achievement_dao import AchievementDAO
# from app.dao.profile.profile_dao import FinancialProfileDAO
# from app.dao.snapshot_dao import BalanceSnapshotDAO
# from app.service.achievements.achievements_service import AchievementService
# from app.service.cashflow_engine import CashFlowEngine
#
# def get_achievement_service(db: DbSession) -> AchievementService:
#     return AchievementService(
#         achievement_dao=AchievementDAO(db),
#         snapshot_dao=BalanceSnapshotDAO(db),
#         profile_dao=FinancialProfileDAO(db),
#         cashflow_engine=CashFlowEngine(db),
#     )
# ---------------------------------------------


# -- DA RIMUOVERE: STUB PROVVISORIO PER TESTING --
class MockAchievementService:
    @staticmethod
    async def get_user_achievements(user_id: int) -> list[AchievementStatusDTO]:
        _ = user_id
        return [
            AchievementStatusDTO(
                id_achievement=1,
                name="Buffer intatto",
                description="Mantieni il saldo sopra il Safety Buffer per 30 giorni consecutivi.",
                badge_path="/badges/buffer_intact.svg",
                unlocked=True,
                unlocked_at=datetime.now(UTC),
                progress_current=30,
                progress_target=30,
            ),
            AchievementStatusDTO(
                id_achievement=2,
                name="Saldo allineato",
                description="Fai almeno una riconciliazione a settimana per 4 settimane di fila.",
                badge_path="/badges/balance_aligned.svg",
                unlocked=False,
                unlocked_at=None,
                progress_current=2,
                progress_target=4,
            ),
        ]


def get_achievement_service() -> MockAchievementService:
    return MockAchievementService()


# ------------------------------------------


router = APIRouter(
    prefix="/achievements",
    tags=["Achievements"],
)


@router.get(
    "",
    response_model=AchievementListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Recupera gli achievement e i progressi dell'utente",
)
async def get_user_achievements(
    user: CurrentUser,
    achievement_service: MockAchievementService = Depends(get_achievement_service),
) -> AchievementListResponseDTO:
    items = await achievement_service.get_user_achievements(user.id_user)
    unlocked_count = sum(1 for item in items if item.unlocked)

    return AchievementListResponseDTO(
        achievements=items,
        unlocked_count=unlocked_count,
        total_count=len(items),
    )
