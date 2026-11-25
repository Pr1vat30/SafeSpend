from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_goals_crud_and_actions_endpoints(client: AsyncClient) -> None:
    # 1. Lista obiettivi
    res_list = await client.get("/api/v1/goals")
    assert res_list.status_code == 200
    body_list = res_list.json()
    assert "goals" in body_list
    assert len(body_list["goals"]) >= 1

    # 2. Creazione nuovo obiettivo
    future_date = (date.today() + timedelta(days=90)).isoformat()
    res_create = await client.post(
        "/api/v1/goals",
        json={
            "name": "Nuovo Laptop",
            "target_amount": "1500.00",
            "saved_amount": "300.00",
            "monthly_contribution": "200.00",
            "deadline": future_date,
            "priority": 1,
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["name"] == "Nuovo Laptop"
    assert res_create.json()["progress_percentage"] == 20.0

    # 3. Contributo sull'obiettivo
    res_contrib = await client.post(
        "/api/v1/goals/1/contribute",
        json={"amount": "150.00"},
    )
    assert res_contrib.status_code == 200
    assert res_contrib.json()["saved_amount"] == "600.00"

    # 4. Proroga scadenza
    extended_date = (date.today() + timedelta(days=240)).isoformat()
    res_extend = await client.post(
        "/api/v1/goals/1/extend",
        json={"new_deadline": extended_date},
    )
    assert res_extend.status_code == 200
    assert res_extend.json()["deadline"] == extended_date

    # 5. Eliminazione
    res_delete = await client.delete("/api/v1/goals/1")
    assert res_delete.status_code == 204


@pytest.mark.asyncio
async def test_achievements_list_endpoint(client: AsyncClient) -> None:
    res = await client.get("/api/v1/achievements")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 2
    assert data["unlocked_count"] == 1
    assert len(data["achievements"]) == 2
