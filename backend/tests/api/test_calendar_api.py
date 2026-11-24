"""API tests of the income/expense calendar (RF_CG_1). The DAO is replaced by a fake one."""

import pytest

from app.api.controller.calendar.calendar_controller import get_calendar_service
from app.main import app
from app.service.calendar.calendar_service import CalendarService
from tests.calendar_fakes import FakeCalendarDAO, planned, rule


@pytest.fixture
def fake_dao():
    dao = FakeCalendarDAO(
        rules=[rule(id_recurring_rule=7)], planned=[planned(id_planned_transaction=4)]
    )
    app.dependency_overrides[get_calendar_service] = lambda: CalendarService(dao)
    return dao


async def test_get_calendar_returns_the_month(client, fake_dao):
    response = await client.get("/api/v1/calendar", params={"month": "2026-12"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == {
        "month": "2026-12",
        "total_income": "0.00",
        "total_expense": "200.00",
        "days": [
            {
                "date": "2026-12-10",
                "total_income": "0.00",
                "total_expense": "50.00",
                "entries": [
                    {
                        "source": "recurring",
                        "source_id": 7,
                        "name": "Palestra",
                        "type": "expense",
                        "amount": "50.00",
                        "id_category": 3,
                        "category_name": "Salute e Fitness",
                        "frequency": "monthly",
                        "is_installment": False,
                    }
                ],
            },
            {
                "date": "2026-12-20",
                "total_income": "0.00",
                "total_expense": "150.00",
                "entries": [
                    {
                        "source": "planned",
                        "source_id": 4,
                        "name": "Dentista",
                        "type": "expense",
                        "amount": "150.00",
                        "id_category": 3,
                        "category_name": "Salute e Fitness",
                        "frequency": None,
                        "is_installment": False,
                    }
                ],
            },
        ],
    }


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "dicembre", "2026-12-01"])
async def test_get_calendar_rejects_an_invalid_month(client, fake_dao, month):
    response = await client.get("/api/v1/calendar", params={"month": month})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert fake_dao.calls == []


async def test_get_calendar_requires_the_month(client, fake_dao):
    response = await client.get("/api/v1/calendar")

    assert response.status_code == 422
    assert fake_dao.calls == []
