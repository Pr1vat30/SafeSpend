BEGIN;

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
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    nickname VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(254) NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_user PRIMARY KEY (id_user),
    CONSTRAINT chk_user_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_user_surname CHECK (btrim(surname) <> ''),
    CONSTRAINT chk_user_nickname CHECK (btrim(nickname) <> ''),
    CONSTRAINT chk_user_email CHECK (btrim(email) <> ''),
    CONSTRAINT chk_user_password CHECK (btrim(password) <> '')
);


CREATE TABLE financial_profile (
    id_user BIGINT,
    balance NUMERIC(12,2) NOT NULL,
    safety_buffer NUMERIC(12,2) NOT NULL DEFAULT 0,
    periodic_payments NUMERIC(12,2) NOT NULL DEFAULT 0,
    monthly_income NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_financial_profile PRIMARY KEY (id_user),
    CONSTRAINT fk_profile_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_profile_balance CHECK (balance <> 'NaN'::numeric),
    CONSTRAINT chk_profile_safety_buffer CHECK (safety_buffer >= 0 AND safety_buffer <> 'NaN'::numeric),
    CONSTRAINT chk_profile_periodic_payments CHECK (periodic_payments >= 0 AND periodic_payments <> 'NaN'::numeric),
    CONSTRAINT chk_profile_monthly_income CHECK (monthly_income >= 0 AND monthly_income <> 'NaN'::numeric)
);

CREATE TABLE category (
    id_category BIGINT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_category PRIMARY KEY (id_category),
    CONSTRAINT chk_category_name CHECK (btrim(name) <> '')
);

CREATE TABLE frequency (
    id_frequency BIGINT GENERATED ALWAYS AS IDENTITY,
    transaction_count INTEGER NOT NULL DEFAULT 0,
    frequency_type VARCHAR(10) NOT NULL,
    next_occurrence_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_frequency PRIMARY KEY (id_frequency),
    CONSTRAINT chk_frequency_count CHECK (transaction_count >= 0),
    CONSTRAINT chk_frequency_type CHECK (frequency_type IN ('daily', 'weekly', 'monthly', 'yearly')),
    CONSTRAINT chk_frequency_next_date CHECK (next_occurrence_date IS NULL OR end_date IS NULL OR next_occurrence_date <= end_date)
);

CREATE TABLE transaction (
    id_transaction BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_category BIGINT NOT NULL,
    id_frequency BIGINT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) NOT NULL,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_transaction PRIMARY KEY (id_transaction),
    CONSTRAINT fk_transaction_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_transaction_category FOREIGN KEY (id_category) REFERENCES category (id_category),
    CONSTRAINT fk_transaction_frequency FOREIGN KEY (id_frequency) REFERENCES frequency (id_frequency) ON DELETE SET NULL,
    CONSTRAINT chk_transaction_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_transaction_amount CHECK (amount <> 0 AND amount <> 'NaN'::numeric)
);


CREATE TABLE goal (
    id_goal BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    amount NUMERIC(12,2) NOT NULL,
    amount_saved NUMERIC(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_goal PRIMARY KEY (id_goal),
    CONSTRAINT fk_goal_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_goal_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_goal_amount CHECK (amount > 0 AND amount <> 'NaN'::numeric),
    CONSTRAINT chk_goal_amount_saved CHECK (amount_saved >= 0 AND amount_saved <> 'NaN'::numeric)
);

CREATE TABLE achievements (
    id_achievement BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    badge TEXT,
    completion_percent INTEGER NOT NULL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_achievement PRIMARY KEY (id_achievement),
    CONSTRAINT fk_achievement_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_achievement_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_achievement_description CHECK (btrim(description) <> ''),
    CONSTRAINT chk_achievement_percentage CHECK (completion_percent BETWEEN 0 AND 100),
    CONSTRAINT chk_achievement_completion CHECK (completed = (completion_percent = 100)),
    CONSTRAINT chk_achievement_completed_at CHECK ((completed AND completed_at IS NOT NULL) OR (NOT completed AND completed_at IS NULL)),
    CONSTRAINT chk_achievement_dates CHECK (completed_at IS NULL OR completed_at >= created_at)
);

CREATE TABLE user_data (
    id_user BIGINT,
    safety_buffer NUMERIC(12,2) NOT NULL DEFAULT 0,
    budget_sts NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_balance NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_expenses_this_week_count INTEGER NOT NULL DEFAULT 0,
    total_expenses_last_week_count INTEGER NOT NULL DEFAULT 0,
    total_expenses_this_week NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_expenses_last_week NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_income_this_week NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_income_last_week NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_active_debts NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_weekly_debt_balance NUMERIC(12,2) NOT NULL DEFAULT 0,
    active_savings_goals_count INTEGER NOT NULL DEFAULT 0,
    completed_savings_goals_count INTEGER NOT NULL DEFAULT 0,
    goal_transactions_this_week_count INTEGER NOT NULL DEFAULT 0,
    goal_transactions_last_week_count INTEGER NOT NULL DEFAULT 0,
    last_completed_achievements JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_user_data PRIMARY KEY (id_user),
    CONSTRAINT fk_data_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_data_safety_buffer CHECK (safety_buffer >= 0 AND safety_buffer <> 'NaN'::numeric),
    CONSTRAINT chk_data_budget_sts CHECK (budget_sts >= 0 AND budget_sts <> 'NaN'::numeric),
    CONSTRAINT chk_data_total_balance CHECK (total_balance <> 'NaN'::numeric),
    CONSTRAINT chk_data_counts CHECK (total_expenses_this_week_count >= 0 AND total_expenses_last_week_count >= 0 AND active_savings_goals_count >= 0 AND completed_savings_goals_count >= 0 AND goal_transactions_this_week_count >= 0 AND goal_transactions_last_week_count >= 0),
    CONSTRAINT chk_data_expenses CHECK (total_expenses_this_week >= 0 AND total_expenses_this_week <> 'NaN'::numeric AND total_expenses_last_week >= 0 AND total_expenses_last_week <> 'NaN'::numeric),
    CONSTRAINT chk_data_income CHECK (total_income_this_week >= 0 AND total_income_this_week <> 'NaN'::numeric AND total_income_last_week >= 0 AND total_income_last_week <> 'NaN'::numeric),
    CONSTRAINT chk_data_debts CHECK (total_active_debts >= 0 AND total_active_debts <> 'NaN'::numeric AND total_weekly_debt_balance >= 0 AND total_weekly_debt_balance <> 'NaN'::numeric),
    CONSTRAINT chk_data_achievements CHECK (jsonb_typeof(last_completed_achievements) = 'array')
);

COMMIT;