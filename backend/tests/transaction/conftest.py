"""Fixtures for the transaction module: real PostgreSQL, every test rolled back.

The CI starts PostgreSQL 18 on localhost:5433 and applies `database/schema.sql`. Locally run
`docker compose up -d db db-init` first. Without a database these tests are skipped.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.database import get_db
from app.config.settings import settings
from app.main import app

# Same statement as the seed in database/schema.sql, so the tests do not depend on it being applied.
SEED_DEFAULT_CATEGORIES = text(
    """
    INSERT INTO category (id_user, name, type, is_default)
    SELECT NULL, v.name, v.type, TRUE
    FROM (VALUES
              ('Alimentari', 'expense'), ('Casa', 'expense'), ('Trasporti', 'expense'),
              ('Salute', 'expense'), ('Abbigliamento', 'expense'), ('Svago', 'expense'),
              ('Altro', 'expense'), ('Stipendio', 'income'), ('Altro', 'income')
         ) AS v(name, type)
    WHERE NOT EXISTS (
        SELECT 1 FROM category c WHERE c.id_user IS NULL AND c.name = v.name AND c.type = v.type
    )
    """
)


@pytest.fixture
async def db_session():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        connection = await engine.connect()
    except Exception:
        await engine.dispose()
        pytest.skip("PostgreSQL non raggiungibile: avvia `docker compose up -d db db-init`")
    outer = await connection.begin()
    session = AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    await session.execute(SEED_DEFAULT_CATEGORIES)
    try:
        yield session
    finally:
        await session.close()
        await outer.rollback()
        await connection.close()
        await engine.dispose()


@pytest.fixture
async def db_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def make_user(db_session):
    async def _make_user() -> int:
        result = await db_session.execute(
            text(
                "INSERT INTO _user (name, surname, email, password, privacy_accepted_at,"
                " disclaimer_accepted_at) VALUES ('Test', 'User', :email, 'x', now(), now())"
                " RETURNING id_user"
            ),
            {"email": f"{uuid.uuid4()}@example.com"},
        )
        return result.scalar_one()

    return _make_user


@pytest.fixture
async def user_id(make_user) -> int:
    return await make_user()


@pytest.fixture
async def other_user_id(make_user) -> int:
    return await make_user()


@pytest.fixture
async def default_ids(db_session) -> dict[tuple[str, str], int]:
    """Ids of the default categories, keyed by (name, type)."""
    rows = await db_session.execute(
        text("SELECT name, type, id_category FROM category WHERE id_user IS NULL")
    )
    return {(name, type_): id_ for name, type_, id_ in rows.all()}
