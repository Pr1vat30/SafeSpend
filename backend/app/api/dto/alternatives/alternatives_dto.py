from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class InstallmentOptionInput(BaseModel):
    months: int = Field(..., ge=2, le=120, description="Numero di rate mensili")
    tan_percentage: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="TAN annuo in percentuale (es. 6.50)",
    )
    upfront_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Spese iniziali / istruttoria una tantum",
    )
    monthly_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Spese fisse di incasso per singola rata",
    )


class AlternativeSimulationRequest(BaseModel):
    item_name: str = Field(..., min_length=1, max_length=120)
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Prezzo del bene/servizio")
    current_balance: Decimal = Field(..., description="Saldo disponibile attuale")
    monthly_net_savings: Decimal = Field(
        ...,
        description="Margine di risparmio mensile netto stimato (entrate - uscite fisse)",
    )
    safety_buffer: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Soglia minima di sicurezza da non intaccare",
    )
    postponed_target_date: date | None = Field(
        default=None,
        description="Data desiderata opzionale per l'acquisto posticipato",
    )
    installment_options: list[InstallmentOptionInput] = Field(
        default_factory=lambda: [
            InstallmentOptionInput(months=6, tan_percentage=Decimal("0.00")),
            InstallmentOptionInput(months=12, tan_percentage=Decimal("5.90")),
        ]
    )


class ImmediatePurchaseResult(BaseModel):
    feasible: bool
    balance_after: Decimal
    below_safety_buffer: bool
    shortfall: Decimal
    summary: str


class PostponedPurchaseResult(BaseModel):
    feasible: bool
    months_needed: int | None
    estimated_purchase_date: date | None
    monthly_allocation: Decimal
    summary: str


class InstallmentPurchaseResult(BaseModel):
    months: int
    tan_percentage: Decimal
    taeg_percentage: Decimal
    monthly_installment: Decimal
    total_interest: Decimal
    total_fees: Decimal
    total_cost: Decimal
    sustainable: bool
    summary: str


class AlternativeSimulationResponse(BaseModel):
    item_name: str
    amount: Decimal
    immediate: ImmediatePurchaseResult
    postponed: PostponedPurchaseResult
    installments: list[InstallmentPurchaseResult]
    recommended_strategy: str
