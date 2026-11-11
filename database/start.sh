#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${PGDATABASE:-safespend}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_PATH="$SCRIPT_DIR/schema.sql"

echo "Configuring PostgreSQL for SafeSpend..."

# 1. Start PostgreSQL service if using Homebrew (macOS) or systemctl (Linux)
if command -v brew >/dev/null 2>&1; then
  if brew list postgresql@18 >/dev/null 2>&1; then
    brew services start postgresql@18
  elif brew list postgresql >/dev/null 2>&1; then
    brew services start postgresql
  fi
elif command -v systemctl >/dev/null 2>&1; then
  sudo systemctl start postgresql 2>/dev/null || true
fi

# 2. Wait until PostgreSQL is responding
if command -v pg_isready >/dev/null 2>&1; then
  until pg_isready >/dev/null 2>&1; do
    sleep 1
  done
fi

# 3. Apply schema with psql or fallback to python init_db
if command -v psql >/dev/null 2>&1; then
  USER_FLAG=""
  if [ -n "${PGUSER:-}" ]; then
    USER_FLAG="-U $PGUSER"
  fi

  if ! psql $USER_FLAG -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1; then
    createdb $USER_FLAG "$DB_NAME" 2>/dev/null || true
  fi

  psql $USER_FLAG -v ON_ERROR_STOP=1 -d "$DB_NAME" -f "$SCHEMA_PATH"
  echo "Ready: postgresql://localhost/$DB_NAME"
else
  echo "psql not found. Initializing database using Python..."
  cd "$SCRIPT_DIR/../backend"
  if command -v uv >/dev/null 2>&1; then
    uv run python -m app.core.init_db
  else
    python3 -m app.core.init_db
  fi
fi
