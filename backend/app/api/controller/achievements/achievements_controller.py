from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status

from app.api.dto.achievements.achievements_dto import (
    AchievementListResponseDTO,
    AchievementStatusDTO,
)

#from sqlalchemy.ext.asyncio import AsyncSession

# 1. Import dei DAO e Service reali
#from app.dao.achievement_dao import AchievementDAO
#from app.service.achievements_service import AchievementService

# 2. Import degli altri moduli da collegare in seguito alla loro creazione
#from app.core.security import get_current_user_id
#from app.db.session import get_db_session
#from app.dao.profile_dao import ProfileDAO
#from app.dao.snapshot_dao import BalanceSnapshotDAO
#from app.service.cashflow_engine import CashFlowEngine


#def get_achievement_service(
#    session: AsyncSession = Depends(get_db_session),
#) -> AchievementService:
#    return AchievementService(
#        achievement_dao=AchievementDAO(session),
#        snapshot_dao=BalanceSnapshotDAO(session),
#        profile_dao=ProfileDAO(session),
#        cashflow_engine=CashFlowEngine(session),
#    )


# -- DA RIMUOVERE, PROVVISORIO PER TESTING --
async def get_current_user_id() -> int:
    return 1

class MockAchievementService:
    @staticmethod
    async def get_user_achievements(user_id: int) -> list[AchievementStatusDTO]:
        _ = user_id  # Evita il warning di parametro non usato nello stub
        return [
            AchievementStatusDTO(
                id_achievement=1,
                name="Buffer intatto",
                description="Mantieni il saldo reale sopra il Safety Buffer per 30 giorni consecutivi.",
                badge_path="/badges/buffer_intact.svg",
                unlocked=True,
                unlocked_at=datetime.now(timezone.utc),
                progress_current=30,
                progress_target=30,
            ),
            AchievementStatusDTO(
                id_achievement=2,
                name="Saldo allineato",
                description="Esegui almeno una riconciliazione a settimana per 4 settimane consecutive.",
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
# -- DA RIMUOVERE PER TESTING --
    user_id: int = Depends(get_current_user_id),
    achievement_service: MockAchievementService = Depends(get_achievement_service),
) -> AchievementListResponseDTO:
#------------------------------

#async def get_user_achievements(
#    user_id: int = Depends(get_current_user_id),
#    achievement_service: AchievementService = Depends(get_achievement_service),  # <-- Aggiornato qui
#) -> AchievementListResponseDTO:
    items = await achievement_service.get_user_achievements(user_id)
    unlocked_count = sum(1 for item in items if item.unlocked)

    return AchievementListResponseDTO(
        achievements=items,
        unlocked_count=unlocked_count,
        total_count=len(items),
    )