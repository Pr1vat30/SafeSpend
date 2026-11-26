"""Database tests of the calendar queries (RF_CG_1), on the PostgreSQL of `database/schema.sql`.

Each test runs in a transaction that is rolled back, so the database is left unchanged. Without a
reachable database the tests are skipped locally, and fail in the CI (where `CI` is set).
"""

import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.dao.calendar.calendar_dao import CalendarDAO

DECEMBER = (date(2026, 12, 1), date(2026, 12, 31))


@pytest.fixture
async def db():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        connection = await engine.connect()
    except Exception as exc:
        await engine.dispose()
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Database not reachable: {exc}")

    transaction = await connection.begin()
    session = AsyncSession(bind=connection)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


async def insert(db: AsyncSession, sql: str, **values) -> int:
    return (await db.execute(text(sql), values)).scalar_one()


@pytest.fixture
async def user(db) -> dict[str, int]:
    """A new user with an expense category; returns their ids."""
    user_id = await insert(
        db,
        "INSERT INTO _user (name, surname, email, password, privacy_accepted_at,"
        " disclaimer_accepted_at) VALUES ('Gilberto', 'Test', 'calendar.dao@test.local', 'x',"
        " now(), now()) RETURNING id_user",
    )
    category_id = await insert(
        db,
        "INSERT INTO category (id_user, name, type) VALUES (:user, 'Salute e Fitness', 'both')"
        " RETURNING id_category",
        user=user_id,
    )
    return {"user": user_id, "category": category_id}


async def add_rule(db, user, name, *, type="expense", status="active", first, end=None) -> int:
    return await insert(
        db,
        "INSERT INTO recurring_rule (id_user, id_category, name, type, amount, frequency,"
        " first_occurrence_date, end_date, status) VALUES (:user, :category, :name, :type, 50,"
        " 'monthly', :first, :end, :status) RETURNING id_recurring_rule",
        user=user["user"],
        category=user["category"],
        name=name,
        type=type,
        first=first,
        end=end,
        status=status,
    )


async def add_planned(db, user, name, *, planned_date, status="planned", type="expense") -> int:
    return await insert(
        db,
        "INSERT INTO planned_transaction (id_user, id_category, name, type, amount,"
        " planned_date, status) VALUES (:user, :category, :name, :type, 150, :planned_date,"
        " :status) RETURNING id_planned_transaction",
        user=user["user"],
        category=user["category"],
        name=name,
        type=type,
        planned_date=planned_date,
        status=status,
    )


async def test_find_active_rules_keeps_only_the_active_rules_of_the_period(db, user):
    await add_rule(db, user, "Palestra", first=date(2026, 11, 10))
    await add_rule(db, user, "Stipendio", type="income", first=date(2026, 10, 27))
    await add_rule(db, user, "Inizia a fine mese", first=date(2026, 12, 31))
    await add_rule(db, user, "Finisce a inizio mese", first=date(2026, 1, 1), end=date(2026, 12, 1))
    await add_rule(db, user, "Accantonamento", type="saving", first=date(2026, 11, 1))
    # Left out: suspended, terminated, starts later, already ended.
    await add_rule(db, user, "Sospesa", status="suspended", first=date(2026, 11, 1))
    await add_rule(db, user, "Terminata", status="terminated", first=date(2026, 11, 1))
    await add_rule(db, user, "Inizia a gennaio", first=date(2027, 1, 1))
    await add_rule(db, user, "Finita a novembre", first=date(2026, 1, 1), end=date(2026, 11, 30))

    rules = await CalendarDAO(db).find_active_rules(user["user"], *DECEMBER)

    assert sorted(r.name for r in rules) == [
        "Accantonamento",
        "Finisce a inizio mese",
        "Inizia a fine mese",
        "Palestra",
        "Stipendio",
    ]
    gym = next(r for r in rules if r.name == "Palestra")
    assert gym.amount == Decimal("50.00")
    assert gym.frequency == "monthly"
    assert gym.first_occurrence_date == date(2026, 11, 10)
    assert gym.category_name == "Salute e Fitness"


async def test_find_planned_keeps_only_movements_still_to_happen_in_the_period(db, user):
    await add_planned(db, user, "Dentista", planned_date=date(2026, 12, 20))
    await add_planned(db, user, "Primo del mese", planned_date=date(2026, 12, 1))
    await add_planned(db, user, "Ultimo del mese", planned_date=date(2026, 12, 31))
    await add_planned(
        db,
        user,
        "Rimborso da confermare",
        type="income",
        status="pending_confirmation",
        planned_date=date(2026, 12, 10),
    )
    # Left out: already recorded, cancelled, outside the month.
    await add_planned(db, user, "Registrata", status="recorded", planned_date=date(2026, 12, 3))
    await add_planned(db, user, "Annullata", status="cancelled", planned_date=date(2026, 12, 4))
    await add_planned(db, user, "Novembre", planned_date=date(2026, 11, 30))
    await add_planned(db, user, "Gennaio", planned_date=date(2027, 1, 1))

    planned = await CalendarDAO(db).find_planned(user["user"], *DECEMBER)

    assert sorted(p.name for p in planned) == [
        "Dentista",
        "Primo del mese",
        "Rimborso da confermare",
        "Ultimo del mese",
    ]
    dentist = next(p for p in planned if p.name == "Dentista")
    assert dentist.amount == Decimal("150.00")
    assert dentist.planned_date == date(2026, 12, 20)
    assert dentist.category_name == "Salute e Fitness"


async def test_queries_return_only_the_movements_of_the_requested_user(db, user):
    await add_rule(db, user, "Palestra", first=date(2026, 11, 10))
    await add_planned(db, user, "Dentista", planned_date=date(2026, 12, 20))
    other_id = await insert(
        db,
        "INSERT INTO _user (name, surname, email, password, privacy_accepted_at,"
        " disclaimer_accepted_at) VALUES ('Altro', 'Utente', 'calendar.other@test.local', 'x',"
        " now(), now()) RETURNING id_user",
    )
    other = {"user": other_id, "category": user["category"]}
    await add_rule(db, other, "Affitto di un altro", first=date(2026, 11, 1))
    await add_planned(db, other, "Spesa di un altro", planned_date=date(2026, 12, 5))

    dao = CalendarDAO(db)
    assert [r.name for r in await dao.find_active_rules(user["user"], *DECEMBER)] == ["Palestra"]
    assert [p.name for p in await dao.find_planned(user["user"], *DECEMBER)] == ["Dentista"]
