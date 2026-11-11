"""Database initialization script: creates the database if missing and applies schema.sql.

Cross-platform: works on Windows, macOS, and Linux without external tools like psql or brew.
Run via:
    uv run python -m app.core.init_db
"""

import asyncio
import sys
from pathlib import Path

import asyncpg
from sqlalchemy.engine import make_url

from app.config.settings import settings


def get_schema_path() -> Path:
    candidates = [
        Path(__file__).resolve().parents[3] / "database" / "schema.sql",
        Path.cwd().parent / "database" / "schema.sql",
        Path.cwd() / "database" / "schema.sql",
        Path.cwd() / "schema.sql",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Could not locate database/schema.sql. Searched paths:\n"
        + "\n".join(f" - {c}" for c in candidates)
    )


async def init_database() -> None:
    url = make_url(settings.DATABASE_URL)
    user = url.username or "postgres"
    password = url.password or ""
    host = url.host or "localhost"
    port = url.port or 5432
    db_name = url.database or "safespend"

    schema_file = get_schema_path()
    schema_sql = schema_file.read_text(encoding="utf-8")

    print(f"Connecting to PostgreSQL server at {host}:{port}...")

    # Step 1: Ensure database exists by connecting to 'postgres' administrative database
    try:
        admin_conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres",
            timeout=5,
        )
        try:
            exists = await admin_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
            if not exists:
                print(f"Database '{db_name}' does not exist. Creating it...")
                await admin_conn.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Database '{db_name}' created.")
            else:
                print(f"Database '{db_name}' already exists.")
        finally:
            await admin_conn.close()
    except Exception as exc:
        print(f"Note: Could not check/create database via 'postgres' admin db: {exc}")
        print(f"Attempting direct connection to '{db_name}'...")

    # Step 2: Connect to target database and apply schema
    try:
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=db_name,
            timeout=10,
        )
        try:
            print(f"Applying schema from {schema_file}...")
            await conn.execute(schema_sql)
            print(f"Schema applied successfully! Database '{db_name}' is ready.")
        finally:
            await conn.close()
    except Exception as exc:
        print(f"\nError: Failed to connect to database '{db_name}' at {host}:{port}: {exc}")
        print("\nTroubleshooting tips:")
        print("1. If using Docker, make sure the database container is running:")
        print("     docker compose up -d db")
        print("2. Check your backend/.env DATABASE_URL setting.")
        print(f"   Current target: postgresql://{user}:***@{host}:{port}/{db_name}")
        sys.exit(1)


def main() -> None:
    asyncio.run(init_database())


if __name__ == "__main__":
    main()
