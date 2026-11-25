from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

GoalStatusType = Literal["active", "completed", "suspended", "expired"]
GoalFrequencyType = Literal["weekly", "monthly"]


class GoalCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nome dell'obiettivo")
    target_amount: Decimal = Field(
        ..., gt=Decimal("0.00"), description="Importo target da raggiungere"
    )
    installment_frequency: GoalFrequencyType = Field(
        default="monthly", description="Frequenza di accantonamento ('weekly' o 'monthly')"
    )
    installment_amount: Decimal = Field(
        ..., gt=Decimal("0.00"), description="Quota di accantonamento per periodo"
    )
    deadline: date = Field(..., description="Scadenza prevista")
    create_recurring_rule: bool = Field(
        default=True,
        description="Se True, crea una RecurringRule di tipo 'saving' collegata all'obiettivo",
    )

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Il nome dell'obiettivo non può essere vuoto.")
        return stripped

    @field_validator("deadline")
    @classmethod
    def deadline_must_be_future(cls, v: date) -> date:
        if v <= date.today():
            raise ValueError("La scadenza dell'obiettivo deve essere futura rispetto a oggi.")
        return v

    @model_validator(mode="after")
    def installment_cannot_exceed_target(self) -> "GoalCreateDTO":
        if self.installment_amount > self.target_amount:
            raise ValueError("La rata di accantonamento non può superare l'importo target.")
        return self


class GoalUpdateDTO(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount: Decimal | None = Field(default=None, gt=Decimal("0.00"))
    installment_frequency: GoalFrequencyType | None = Field(default=None)
    installment_amount: Decimal | None = Field(default=None, gt=Decimal("0.00"))
    deadline: date | None = Field(default=None)
    status: GoalStatusType | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Il nome dell'obiettivo non può essere vuoto.")
        return v.strip() if v is not None else None


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
    saved_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal
    installment_frequency: GoalFrequencyType
    installment_amount: Decimal
    deadline: date
    status: GoalStatusType
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    estimated_completion_date: date | None = Field(
        default=None,
        description="Data stimata di raggiungimento in base alla rata periodica (RF_OBI_3)",
    )
    is_overdue: bool = Field(
        default=False,
        description="True se la scadenza è passata senza aver raggiunto il target (RF_OBI_4)",
    )
    buffer_warning: str | None = Field(
        default=None,
        description="Eventuale avviso se l'accantonamento viola il Safety Buffer (RF_OBI_2)",
    )
    id_recurring_rule: int | None = None
    created_at: datetime | None = None


class GoalListResponseDTO(BaseModel):
    goals: list[GoalResponseDTO]
    total_saved: Decimal
    total_target: Decimal
