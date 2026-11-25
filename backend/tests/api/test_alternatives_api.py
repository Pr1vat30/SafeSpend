import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_simulate_alternatives_endpoint_success(client: AsyncClient) -> None:
    payload = {
        "item_name": "Notebook",
        "amount": "1200.00",
        "current_balance": "1100.00",
        "monthly_net_savings": "500.00",
        "safety_buffer": "1000.00",
        "installment_options": [
            {
                "months": 12,
                "tan_percentage": "6.00",
                "upfront_fee": "20.00",
                "monthly_fee": "1.50",
            }
        ],
    }

    response = await client.post("/api/v1/alternatives/simulate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["item_name"] == "Notebook"
    assert data["immediate"]["feasible"] is False
    assert data["postponed"]["feasible"] is True
    assert data["postponed"]["months_needed"] == 4
    assert len(data["installments"]) == 1
    assert float(data["installments"][0]["taeg_percentage"]) > 6.0


@pytest.mark.asyncio
async def test_simulate_alternatives_validation_error(client: AsyncClient) -> None:
    payload = {
        "item_name": "Spesa non valida",
        "amount": "-50.00",
        "current_balance": "1000.00",
        "monthly_net_savings": "200.00",
    }

    response = await client.post("/api/v1/alternatives/simulate", json=payload)

    assert response.status_code == 422
