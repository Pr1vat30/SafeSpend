-- SafeSpend starter schema. Apply with: psql -d safespend -f database/schema.sql

CREATE TABLE IF NOT EXISTS categories (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS transactions (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id     BIGINT REFERENCES categories(id) ON DELETE SET NULL,
    description     TEXT NOT NULL,
    amount          NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS transactions_date_idx
    ON transactions (transaction_date DESC);
