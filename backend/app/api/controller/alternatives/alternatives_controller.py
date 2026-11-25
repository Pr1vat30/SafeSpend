from fastapi import APIRouter, Depends

from app.api.dto.alternatives.alternatives_dto import (
    AlternativeSimulationRequest,
    AlternativeSimulationResponse,
)
from app.service.alternatives.alternatives_service import AlternativesService

router = APIRouter(prefix="/alternatives", tags=["alternatives"])


def get_alternatives_service() -> AlternativesService:
    return AlternativesService()


@router.post("/simulate", response_model=AlternativeSimulationResponse)
async def simulate_purchase_alternatives(
    payload: AlternativeSimulationRequest,
    service: AlternativesService = Depends(get_alternatives_service),
) -> AlternativeSimulationResponse:
    """Confronta acquisto immediato, posticipato e a rate con calcolo del TAEG (RF_PRE_3)."""
    return service.simulate(payload)
