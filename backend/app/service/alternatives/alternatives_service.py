import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.api.dto.alternatives.alternatives_dto import (
    AlternativeSimulationRequest,
    AlternativeSimulationResponse,
    ImmediatePurchaseResult,
    InstallmentOptionInput,
    InstallmentPurchaseResult,
    PostponedPurchaseResult,
)

TWO_PLACES = Decimal("0.01")


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _add_months(start_date: date, months: int) -> date:
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _compute_taeg_percentage(
    net_financed: Decimal,
    total_monthly_payment: Decimal,
    months: int,
) -> Decimal:
    """Calcola il TAEG (tasso effettivo annuo) risolvendo il VAN = 0 tramite bisezione."""
    if net_financed <= Decimal("0.00") or total_monthly_payment * months <= net_financed:
        return Decimal("0.00")

    low = Decimal("0.0")
    high = Decimal("10.0")  # fino al 1000% mensile

    for _ in range(80):
        mid = (low + high) / Decimal("2")
        if mid == Decimal("0"):
            npv = total_monthly_payment * months - net_financed
        else:
            factor = (Decimal("1") + mid) ** (-months)
            npv = total_monthly_payment * (Decimal("1") - factor) / mid - net_financed

        if npv > Decimal("0"):
            low = mid
        else:
            high = mid

    monthly_irr = (low + high) / Decimal("2")
    annual_taeg = ((Decimal("1") + monthly_irr) ** 12 - Decimal("1")) * Decimal("100")
    return _round_money(annual_taeg)


class AlternativesService:
    """Simulatore in memoria delle alternative di acquisto (RF_PRE_3, RNF_AF_1)."""

    def simulate(
        self,
        request: AlternativeSimulationRequest,
        reference_date: date | None = None,
    ) -> AlternativeSimulationResponse:
        today = reference_date or date.today()
        immediate = self._evaluate_immediate(request)
        postponed = self._evaluate_postponed(request, today)
        installments = [
            self._evaluate_installment(request, opt) for opt in request.installment_options
        ]

        recommended = self._pick_recommendation(immediate, postponed, installments)

        return AlternativeSimulationResponse(
            item_name=request.item_name,
            amount=_round_money(request.amount),
            immediate=immediate,
            postponed=postponed,
            installments=installments,
            recommended_strategy=recommended,
        )

    def _evaluate_immediate(self, request: AlternativeSimulationRequest) -> ImmediatePurchaseResult:
        balance_after = _round_money(request.current_balance - request.amount)
        below_buffer = balance_after < request.safety_buffer
        feasible = balance_after >= Decimal("0.00") and not below_buffer
        shortfall = (
            _round_money(request.safety_buffer - balance_after) if below_buffer else Decimal("0.00")
        )

        if feasible:
            summary = f"Acquisto immediato sostenibile: saldo residuo di {balance_after} EUR."
        elif balance_after >= Decimal("0.00"):
            summary = (
                f"Saldo sufficiente ({balance_after} EUR), ma intacca la riserva "
                f"di sicurezza di {shortfall} EUR."
            )
        else:
            summary = f"Liquidità insufficiente: mancano {abs(balance_after)} EUR."

        return ImmediatePurchaseResult(
            feasible=feasible,
            balance_after=balance_after,
            below_safety_buffer=below_buffer,
            shortfall=shortfall,
            summary=summary,
        )

    def _evaluate_postponed(
        self, request: AlternativeSimulationRequest, today: date
    ) -> PostponedPurchaseResult:
        available_above_buffer = request.current_balance - request.safety_buffer
        amount_to_save = max(Decimal("0.00"), request.amount - available_above_buffer)

        if amount_to_save == Decimal("0.00"):
            return PostponedPurchaseResult(
                feasible=True,
                months_needed=0,
                estimated_purchase_date=today,
                monthly_allocation=Decimal("0.00"),
                summary="Hai già liquidità sufficiente sopra la soglia di sicurezza.",
            )

        if request.monthly_net_savings <= Decimal("0.00"):
            return PostponedPurchaseResult(
                feasible=False,
                months_needed=None,
                estimated_purchase_date=None,
                monthly_allocation=Decimal("0.00"),
                summary="Margine di risparmio mensile nullo o negativo: impossibile.",
            )

        # Accantonamento consigliato: max 70% del risparmio netto mensile
        sustainable_allocation = _round_money(request.monthly_net_savings * Decimal("0.70"))
        if sustainable_allocation <= Decimal("0.00"):
            sustainable_allocation = _round_money(request.monthly_net_savings)

        months_needed = int(
            (amount_to_save / sustainable_allocation).to_integral_value(rounding="ROUND_CEILING")
        )
        estimated_date = _add_months(today, months_needed)

        return PostponedPurchaseResult(
            feasible=True,
            months_needed=months_needed,
            estimated_purchase_date=estimated_date,
            monthly_allocation=sustainable_allocation,
            summary=(
                f"Accantonando {sustainable_allocation} EUR/mese raggiungi l'obiettivo "
                f"in {months_needed} mesi ({estimated_date.isoformat()})."
            ),
        )

    def _evaluate_installment(
        self,
        request: AlternativeSimulationRequest,
        option: InstallmentOptionInput,
    ) -> InstallmentPurchaseResult:
        n = option.months
        principal = request.amount

        if option.tan_percentage == Decimal("0.00"):
            base_installment = principal / Decimal(n)
        else:
            monthly_rate = (option.tan_percentage / Decimal("100")) / Decimal("12")
            factor = (Decimal("1") + monthly_rate) ** (-n)
            base_installment = principal * monthly_rate / (Decimal("1") - factor)

        monthly_payment = _round_money(base_installment + option.monthly_fee)
        total_fees = _round_money(option.upfront_fee + option.monthly_fee * Decimal(n))
        total_cost = _round_money(monthly_payment * Decimal(n) + option.upfront_fee)
        total_interest = _round_money(max(Decimal("0.00"), total_cost - principal - total_fees))

        # Il credito effettivamente ricevuto al netto delle spese iniziali
        net_credit = principal - option.upfront_fee
        taeg = _compute_taeg_percentage(net_credit, monthly_payment, n)

        sustainable = request.monthly_net_savings > Decimal(
            "0.00"
        ) and monthly_payment <= request.monthly_net_savings * Decimal("0.50")

        summary = (
            f"{n} rate da {monthly_payment} EUR/mese (TAN {option.tan_percentage}%, "
            f"TAEG {taeg}%, costo totale {total_cost} EUR)."
        )

        return InstallmentPurchaseResult(
            months=n,
            tan_percentage=_round_money(option.tan_percentage),
            taeg_percentage=taeg,
            monthly_installment=monthly_payment,
            total_interest=total_interest,
            total_fees=total_fees,
            total_cost=total_cost,
            sustainable=sustainable,
            summary=summary,
        )

    def _pick_recommendation(
        self,
        immediate: ImmediatePurchaseResult,
        postponed: PostponedPurchaseResult,
        installments: list[InstallmentPurchaseResult],
    ) -> str:
        if immediate.feasible:
            return "immediate"

        zero_interest_sustainable = [
            opt
            for opt in installments
            if opt.sustainable and opt.taeg_percentage == Decimal("0.00")
        ]
        if zero_interest_sustainable:
            return f"installments_{zero_interest_sustainable[0].months}m"

        if (
            postponed.feasible
            and postponed.months_needed is not None
            and postponed.months_needed <= 6
        ):
            return "postponed"

        sustainable_installments = sorted(
            [opt for opt in installments if opt.sustainable],
            key=lambda x: x.taeg_percentage,
        )
        if sustainable_installments:
            return f"installments_{sustainable_installments[0].months}m"

        if postponed.feasible:
            return "postponed"

        return "not_recommended"
