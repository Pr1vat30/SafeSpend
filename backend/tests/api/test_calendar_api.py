"""API tests of the income/expense calendar (RF_CG_1). The DAO is replaced by a fake one."""

from datetime import date
from decimal import Decimal

import pytest

from app.api.controller.calendar.calendar_controller import get_calendar_service
from app.dao.calendar.calendar_dao import CalendarRule
from app.main import app
from app.service.calendar.calendar_service import CalendarService
from tests.service.test_calendar_service import FakeCalendarDAO

GYM = CalendarRule(
    id_recurring_rule=7,
    name="Palestra",
    type="expense",
    amount=Decimal("50.00"),
    frequency="monthly",
    first_occurrence_date=date(2026, 11, 10),
    end_date=None,
    is_installment=False,
    id_category=3,
    category_name="Salute e Fitness",
)


@pytest.fixture
def fake_dao():
    dao = FakeCalendarDAO([GYM])
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
        "total_expense": "50.00",
        "days": [
            {
                "date": "2026-12-10",
                "total_income": "0.00",
                "total_expense": "50.00",
                "entries": [
                    {
                        "id_recurring_rule": 7,
                        "name": "Palestra",
                        "type": "expense",
                        "amount": "50.00",
                        "frequency": "monthly",
                        "is_installment": False,
                        "id_category": 3,
                        "category_name": "Salute e Fitness",
                    }
                ],
            }
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
