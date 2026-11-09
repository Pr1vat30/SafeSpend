#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${PGDATABASE:-safespend}"

brew services start postgresql@18

until pg_isready >/dev/null 2>&1; do
  sleep 1
done

if ! psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1; then
  createdb "$DB_NAME"
fi

psql -v ON_ERROR_STOP=1 -d "$DB_NAME" -f "$(dirname "$0")/schema.sql"
echo "Ready: postgresql://localhost/$DB_NAME"
