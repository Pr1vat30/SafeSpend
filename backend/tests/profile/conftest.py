"""Fixtures of the profile tests that use PostgreSQL.

They need the database of `docker compose up -d db db-init` (locally) or the CI service. Every
test user has an email `test-<uuid>@example.com` and is deleted at the end of the test.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.database import get_db
from app.config.settings import settings
from app.main import app

TEST_EMAIL_PATTERN = "test-%@example.com"
PASSWORD = "Password123"


@pytest.fixture
async def engine():
    # NullPool: every test runs in its own event loop, so connections must not be reused.
    eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    try:
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await eng.dispose()
        pytest.skip("PostgreSQL non raggiungibile: avvia `docker compose up -d db db-init`")
    yield eng
    async with eng.begin() as conn:
        await conn.execute(
            text("DELETE FROM _user WHERE email LIKE :pattern"), {"pattern": TEST_EMAIL_PATTERN}
        )
    await eng.dispose()


@pytest.fixture
async def api(engine):
    """HTTP client whose requests use the test engine."""
    sessions = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async def _get_db():
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def sql(engine):
    """Runs a query directly on the database (to check what the API wrote)."""

    async def run(query: str, **params):
        async with engine.begin() as conn:
            return (await conn.execute(text(query), params)).all()

    return run


def new_email() -> str:
    return f"test-{uuid.uuid4().hex[:12]}@example.com"


def registration(email: str | None = None, **overrides) -> dict:
    body = {
        "name": "Gilberto",
        "surname": "Rossi",
        "email": email or new_email(),
        "password": PASSWORD,
        "privacy_accepted": True,
        "disclaimer_accepted": True,
        "is_adult": True,
    }
    body.update(overrides)
    return body


@pytest.fixture
async def user(api):
    """A registered user: dict with email, id and the Authorization header of a fresh login."""
    body = registration()
    created = await api.post("/api/v1/auth/register", json=body)
    assert created.status_code == 201, created.text
    login = await api.post(
        "/api/v1/auth/login", json={"email": body["email"], "password": PASSWORD}
    )
    token = login.json()["data"]["access_token"]
    return {
        "email": body["email"],
        "id": created.json()["data"]["id_user"],
        "headers": {"Authorization": f"Bearer {token}"},
    }
