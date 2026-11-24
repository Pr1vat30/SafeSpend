from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AchievementStatusDTO(BaseModel):
    id_achievement: int = Field(..., description="Identificativo univoco dell'achievement")
    name: str = Field(..., max_length=100, description="Titolo del traguardo")
    description: str = Field(..., description="Descrizione della regola per sbloccarlo")
    badge_path: str = Field(..., description="Percorso relativo dell'icona/badge")
    unlocked: bool = Field(..., description="True se l'utente ha già sbloccato l'achievement")
    unlocked_at: Optional[datetime] = Field(
        default=None,
        description="Data e ora di conseguimento",
    )
    progress_current: int = Field(..., ge=0, description="Avanzamento attuale (es. giorni o settimane)")
    progress_target: int = Field(..., gt=0, description="Soglia richiesta per lo sblocco (es. 30 o 4)")


class AchievementListResponseDTO(BaseModel):
    achievements: list[AchievementStatusDTO]
    unlocked_count: int = Field(..., ge=0)
    total_count: int = Field(..., ge=0)