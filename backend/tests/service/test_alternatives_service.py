from datetime import date
from decimal import Decimal

from app.api.dto.alternatives.alternatives_dto import (
    AlternativeSimulationRequest,
    InstallmentOptionInput,
)
from app.service.alternatives.alternatives_service import AlternativesService


def test_immediate_purchase_feasible() -> None:
    service = AlternativesService()
    req = AlternativeSimulationRequest(
        item_name="Laptop",
        amount=Decimal("1000.00"),
        current_balance=Decimal("2500.00"),
        monthly_net_savings=Decimal("400.00"),
        safety_buffer=Decimal("1000.00"),
    )
    res = service.simulate(req, reference_date=date(2026, 11, 25))

    assert res.immediate.feasible is True
    assert res.immediate.balance_after == Decimal("1500.00")
    assert res.recommended_strategy == "immediate"


def test_postponed_and_taeg_calculation() -> None:
    service = AlternativesService()
    req = AlternativeSimulationRequest(
        item_name="Bicicletta elettrica",
        amount=Decimal("1200.00"),
        current_balance=Decimal("1100.00"),
        monthly_net_savings=Decimal("500.00"),
        safety_buffer=Decimal("1000.00"),
        installment_options=[
            InstallmentOptionInput(
                months=12,
                tan_percentage=Decimal("6.00"),
                upfront_fee=Decimal("20.00"),
                monthly_fee=Decimal("1.50"),
            )
        ],
    )
    res = service.simulate(req, reference_date=date(2026, 11, 25))

    assert res.immediate.feasible is False
    assert res.immediate.shortfall == Decimal("1100.00")
    assert res.postponed.feasible is True
    assert res.postponed.months_needed == 4
    assert res.postponed.estimated_purchase_date == date(2027, 3, 25)

    inst = res.installments[0]
    assert inst.tan_percentage == Decimal("6.00")
    assert inst.taeg_percentage > inst.tan_percentage
    assert inst.total_fees == Decimal("38.00")
    assert inst.sustainable is True
