"""Unit tests of AlertService with a fake DAO (no database needed).

Category Partition on the life cycle of RF_CG_3: new alert, same condition again (no
duplicate), changed message, resolution, reading, alert of another user, resolved alert.
"""

from datetime import UTC, date, datetime

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.service.alert.alert_service import AlertService

TODAY = date(2026, 11, 27)
NOW = datetime(2026, 11, 27, 9, 0, tzinfo=UTC)
USER = 1
OTHER_USER = 2


class FakeDAO:
    """In-memory stand-in for AlertDAO."""

    def __init__(self):
        self.alerts = {}
        self._next_id = 1

    async def add(self, alert):
        alert.id_alert = self._next_id
        alert.status = alert.status or "active"
        alert.resolved_at = None
        self._next_id += 1
        self.alerts[alert.id_alert] = alert
        return alert

    async def save(self, alert):
        return alert

    async def get_by_id_for_user(self, alert_id, user_id):
        a = self.alerts.get(alert_id)
        return a if a is not None and a.id_user == user_id else None

    async def find_active_and_read_by_user(self, user_id):
        return [
            a
            for a in self.alerts.values()
            if a.id_user == user_id and a.status in ("active", "read")
        ]

    async def find_existing_unresolved(self, user_id, alert_type):
        for a in self.alerts.values():
            if a.id_user == user_id and a.type == alert_type and a.status in ("active", "read"):
                return a
        return None

    async def update_status(self, alert, new_status, resolved_at=None):
        alert.status = new_status
        alert.resolved_at = resolved_at
        return alert


def make_service():
    return AlertService(FakeDAO(), now=lambda: NOW)


def open_alerts(service, user=USER):
    return [a for a in service.dao.alerts.values() if a.id_user == user and a.status != "resolved"]


# -- raising alerts -----------------------------------------------------------------------


async def test_raise_creates_active_alert():
    service = make_service()
    alert = await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    assert alert.status == "active"
    assert alert.trigger_date == TODAY


async def test_raise_same_condition_twice_creates_no_duplicate():
    service = make_service()
    first = await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    await service.mark_read(USER, first.id_alert)
    again = await service.raise_alert(USER, "risk_level", "Rischio critico", date(2026, 11, 28))
    assert again.id_alert == first.id_alert
    assert again.status == "read"  # the user already saw this exact message
    assert len(open_alerts(service)) == 1


async def test_raise_with_new_message_refreshes_and_reactivates():
    service = make_service()
    first = await service.raise_alert(USER, "risk_level", "Attenzione", TODAY)
    await service.mark_read(USER, first.id_alert)
    later = date(2026, 11, 28)
    again = await service.raise_alert(USER, "risk_level", "Rischio critico", later)
    assert again.id_alert == first.id_alert
    assert (again.status, again.message, again.trigger_date) == ("active", "Rischio critico", later)


async def test_different_types_are_independent():
    service = make_service()
    await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    await service.raise_alert(USER, "sts_drop", "STS in calo", TODAY)
    assert len(open_alerts(service)) == 2


async def test_raise_after_resolution_opens_a_new_alert():
    service = make_service()
    first = await service.raise_alert(USER, "sts_drop", "STS in calo", TODAY)
    await service.resolve_alert(USER, "sts_drop")
    second = await service.raise_alert(USER, "sts_drop", "STS in calo", TODAY)
    assert second.id_alert != first.id_alert


# -- resolving ----------------------------------------------------------------------------


async def test_resolve_closes_open_alert():
    service = make_service()
    await service.raise_alert(USER, "impending_expense", "Affitto tra 3 giorni", TODAY)
    resolved = await service.resolve_alert(USER, "impending_expense")
    assert (resolved.status, resolved.resolved_at) == ("resolved", NOW)
    assert await service.list_for_dashboard(USER) == []


async def test_resolve_without_open_alert_does_nothing():
    assert await make_service().resolve_alert(USER, "risk_level") is None


# -- reading (API) ------------------------------------------------------------------------


async def test_mark_read():
    service = make_service()
    alert = await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    assert (await service.mark_read(USER, alert.id_alert)).status == "read"


async def test_mark_read_twice_is_idempotent():
    service = make_service()
    alert = await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    await service.mark_read(USER, alert.id_alert)
    assert (await service.mark_read(USER, alert.id_alert)).status == "read"


async def test_mark_read_of_another_user_is_not_found():
    service = make_service()
    alert = await service.raise_alert(OTHER_USER, "risk_level", "Rischio critico", TODAY)
    with pytest.raises(NotFoundError):
        await service.mark_read(USER, alert.id_alert)


async def test_mark_read_missing_is_not_found():
    with pytest.raises(NotFoundError):
        await make_service().mark_read(USER, 99)


async def test_mark_read_resolved_rejected():
    service = make_service()
    alert = await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    await service.resolve_alert(USER, "risk_level")
    with pytest.raises(ConflictError):
        await service.mark_read(USER, alert.id_alert)


async def test_dashboard_shows_only_own_open_alerts():
    service = make_service()
    await service.raise_alert(USER, "risk_level", "Rischio critico", TODAY)
    await service.raise_alert(USER, "sts_drop", "STS in calo", TODAY)
    await service.resolve_alert(USER, "sts_drop")
    await service.raise_alert(OTHER_USER, "risk_level", "Altro utente", TODAY)
    alerts = await service.list_for_dashboard(USER)
    assert [a.type for a in alerts] == ["risk_level"]
