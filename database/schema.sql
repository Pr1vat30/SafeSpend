DROP TABLE IF EXISTS user_data CASCADE;
DROP TABLE IF EXISTS achievements CASCADE;
DROP TABLE IF EXISTS goal CASCADE;
DROP TABLE IF EXISTS transaction CASCADE;
DROP TABLE IF EXISTS frequency CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS financial_profile CASCADE;
DROP TABLE IF EXISTS _user CASCADE;

CREATE TABLE _user (
    id_user BIGINT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(30) NOT NULL,
    surname VARCHAR(30) NOT NULL,
    nickname VARCHAR(30) NOT NULL UNIQUE,
    email VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_user PRIMARY KEY (id_user)
);

CREATE TABLE financial_profile (
    id_user BIGINT,
    balance NUMERIC(12,2) NOT NULL,
    safety_buffer NUMERIC(12,2) NOT NULL CHECK (safety_buffer >= 0.00),
    periodic_payments NUMERIC(12,3) NOT NULL DEFAULT 0 CHECK (periodic_payments >= 0.000),
    monthly_income NUMERIC(12,3) NOT NULL DEFAULT 0 CHECK (monthly_income >= 0.000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_financial_profile PRIMARY KEY (id_user),
    CONSTRAINT fk_profile_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE
);

CREATE TABLE category (
    id_category BIGINT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(50),
    description VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_category PRIMARY KEY (id_category)
);

CREATE TABLE frequency (
    id_frequency BIGINT GENERATED ALWAYS AS IDENTITY,
    transaction_count INTEGER NOT NULL CHECK (transaction_count >= 0),
    next_occurence_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_frequency PRIMARY KEY (id_frequency)
);

CREATE TABLE transaction (
    id_transaction BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_category BIGINT NOT NULL,
    id_frequency BIGINT,
    name VARCHAR(30),
    description VARCHAR(100),
    amount NUMERIC(12,3),

    CONSTRAINT pk_transaction PRIMARY KEY (id_transaction),
    CONSTRAINT fk_transaction_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_transaction_category FOREIGN KEY (id_category) REFERENCES category (id_category),
    CONSTRAINT fk_transaction_frequency FOREIGN KEY (id_frequency) REFERENCES frequency (id_frequency) ON DELETE SET NULL
);

CREATE TABLE goal (
    id_goal BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    name VARCHAR(30),
    description VARCHAR(100),
    amount NUMERIC(12,3) NOT NULL CHECK (amount > 0.000),
    amount_saved NUMERIC(12,3) NOT NULL DEFAULT 0.000 CHECK (amount_saved >= 0.000),

    CONSTRAINT pk_goal PRIMARY KEY (id_goal),
    CONSTRAINT fk_goal_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_goal_amount CHECK (amount_saved <= amount)
);

CREATE TABLE achievements (
    id_achievement BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    name VARCHAR(40) NOT NULL,
    description VARCHAR(40) NOT NULL,
    badge VARCHAR(100),
    completion_percent INTEGER NOT NULL CHECK (completion_percent BETWEEN 0 AND 100),
    completed BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_achievement PRIMARY KEY (id_achievement),
    CONSTRAINT fk_achievement_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE
);

CREATE TABLE user_data (
    id_user BIGINT NOT NULL UNIQUE,

    -- User Balance Details
    safety_buffer NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (safety_buffer >= 0.00),
    budget_sts NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (budget_sts >= 0.00),
    total_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,

    -- Income & Expenses Details
    total_expenses_this_week_count INTEGER NOT NULL DEFAULT 0 CHECK (total_expenses_this_week_count >= 0),
    total_expenses_last_week_count INTEGER NOT NULL DEFAULT 0 CHECK (total_expenses_last_week_count >= 0),
    total_expenses_this_week NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_expenses_this_week >= 0.00),
    total_expenses_last_week NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_expenses_last_week >= 0.00),
    total_income_this_week NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_income_this_week >= 0.00),
    total_income_last_week NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_income_last_week >= 0.00),
    total_active_debts NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_active_debts >= 0.00),
    total_weekly_debt_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00 CHECK (total_weekly_debt_balance >= 0.00),

    -- Goals Details
    active_savings_goals_count INTEGER NOT NULL DEFAULT 0 CHECK (active_savings_goals_count >= 0),
    completed_savings_goals_count INTEGER NOT NULL DEFAULT 0 CHECK (completed_savings_goals_count >= 0),
    goal_transactions_this_week_count INTEGER NOT NULL DEFAULT 0 CHECK (goal_transactions_this_week_count >= 0),
    goal_transactions_last_week_count INTEGER NOT NULL DEFAULT 0 CHECK (goal_transactions_last_week_count >= 0),

    -- Achievements Details - salvato come JSON/Array
    last_completed_achievements JSONB DEFAULT '[]'::jsonb,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_user_data PRIMARY KEY (id_user),
    CONSTRAINT fk_data_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE
);