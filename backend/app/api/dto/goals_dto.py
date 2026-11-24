from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


GoalStatusType = Literal["ACTIVE", "COMPLETED", "EXPIRED", "CANCELLED"]


class GoalCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nome dell'obiettivo")
    target_amount: Decimal = Field(..., gt=Decimal("0.00"), description="Importo target da raggiungere")
    saved_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Importo iniziale già accantonato")
    monthly_contribution: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Quota di accantonamento mensile")
    deadline: date = Field(..., description="Scadenza prevista")
    priority: int = Field(default=1, ge=1, le=5, description="Priorità (1 = massima)")
    create_recurring_rule: bool = Field(
        default=True,
        description="Se True, crea una RecurringRule mensile collegata all'accantonamento",
    )

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("La scadenza dell'obiettivo deve essere futura rispetto a oggi.")
        return v


class GoalUpdateDTO(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    monthly_contribution: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    deadline: Optional[date] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[GoalStatusType] = Field(default=None)


class GoalExtendDeadlineDTO(BaseModel):
    new_deadline: date = Field(..., description="Nuova data di scadenza prorogata (RF_OBI_4)")

    @field_validator("new_deadline")
    @classmethod
    def new_deadline_must_be_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("La nuova scadenza deve essere successiva alla data odierna.")
        return v


class GoalContributionDTO(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Importo da accantonare")


class GoalResponseDTO(BaseModel):
    id_goal: int
    name: str
    target_amount: Decimal
    saved_amount: Decimal
    remaining_amount: Decimal
    monthly_contribution: Decimal
    deadline: date
    priority: int
    status: str
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    estimated_completion_date: Optional[date] = Field(
        default=None,
        description="Data stimata di raggiungimento in base al contributo mensile (RF_OBI_3)",
    )
    is_overdue: bool = Field(
        default=False,
        description="True se la scadenza è passata senza aver raggiunto il target (RF_OBI_4)",
    )
    buffer_warning: Optional[str] = Field(
        default=None,
        description="Eventuale avviso se l'accantonamento viola il Safety Buffer (RF_OBI_2)",
    )
    id_recurring_rule: Optional[int] = None
    created_at: Optional[datetime] = None


class GoalListResponseDTO(BaseModel):
    goals: list[GoalResponseDTO]
    total_saved: Decimal
    total_target: Decimal