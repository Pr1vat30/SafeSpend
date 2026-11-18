BEGIN;

DROP TABLE IF EXISTS alert CASCADE;
DROP TABLE IF EXISTS planned_transaction CASCADE;
DROP TABLE IF EXISTS transaction CASCADE;
DROP TABLE IF EXISTS recurring_rule CASCADE;
DROP TABLE IF EXISTS goal CASCADE;
DROP TABLE IF EXISTS balance_snapshot CASCADE;
DROP TABLE IF EXISTS category CASCADE;
DROP TABLE IF EXISTS financial_profile CASCADE;
DROP TABLE IF EXISTS _user CASCADE;


CREATE TABLE _user (
    id_user BIGINT GENERATED ALWAYS AS IDENTITY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    email VARCHAR(254) NOT NULL UNIQUE,
    password TEXT NOT NULL,
    privacy_accepted_at TIMESTAMPTZ NOT NULL,
    disclaimer_accepted_at TIMESTAMPTZ NOT NULL,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_user PRIMARY KEY (id_user),
    CONSTRAINT chk_user_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_user_surname CHECK (btrim(surname) <> ''),
    CONSTRAINT chk_user_email CHECK (btrim(email) <> ''),
    CONSTRAINT chk_user_failed_attempts CHECK (failed_login_attempts >= 0)
);


CREATE TABLE financial_profile (
    id_user BIGINT,
    safety_buffer NUMERIC(12,2) NOT NULL DEFAULT 0,
    horizon_days INTEGER NOT NULL DEFAULT 30,
    estimated_variable_expenses NUMERIC(12,2) NOT NULL DEFAULT 0,
    ai_consent BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_financial_profile PRIMARY KEY (id_user),
    CONSTRAINT fk_profile_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_profile_safety_buffer CHECK (safety_buffer >= 0 AND safety_buffer <> 'NaN'::numeric),
    CONSTRAINT chk_profile_horizon CHECK (horizon_days IN (30, 60, 90)),
    CONSTRAINT chk_profile_variable_exp CHECK (estimated_variable_expenses >= 0 AND estimated_variable_expenses <> 'NaN'::numeric)
);

CREATE TABLE category (
    id_category BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(10) NOT NULL DEFAULT 'expense',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_category PRIMARY KEY (id_category),
    CONSTRAINT fk_category_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_category_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_category_type CHECK (type IN ('income', 'expense', 'both')),
    CONSTRAINT chk_category_system_user CHECK (
    (is_default = TRUE AND id_user IS NULL) OR
    (is_default = FALSE AND id_user IS NOT NULL)
    )
);

CREATE TABLE goal (
    id_goal BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    target_amount NUMERIC(12,2) NOT NULL,
    deadline DATE NOT NULL,
    installment_frequency VARCHAR(10) NOT NULL,
    installment_amount NUMERIC(12,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_goal PRIMARY KEY (id_goal),
    CONSTRAINT fk_goal_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_goal_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_goal_target_amount CHECK (target_amount > 0 AND target_amount <> 'NaN'::numeric),
    CONSTRAINT chk_goal_installment_amount CHECK (installment_amount > 0 AND installment_amount <= target_amount AND installment_amount <> 'NaN'::numeric),
    CONSTRAINT chk_goal_installment_frequency CHECK (installment_frequency IN ('weekly', 'monthly')),
    CONSTRAINT chk_goal_status CHECK (status IN ('active', 'completed', 'suspended', 'expired'))
);

CREATE TABLE recurring_rule (
    id_recurring_rule BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_category BIGINT NOT NULL,
    id_goal BIGINT,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(10) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    frequency VARCHAR(10) NOT NULL,
    first_occurrence_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_recurring_rule PRIMARY KEY (id_recurring_rule),
    CONSTRAINT fk_rule_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_rule_category FOREIGN KEY (id_category) REFERENCES category (id_category),
    CONSTRAINT fk_rule_goal FOREIGN KEY (id_goal) REFERENCES goal (id_goal) ON DELETE SET NULL,
    CONSTRAINT chk_rule_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_rule_type CHECK (type IN ('income', 'expense', 'saving')),
    CONSTRAINT chk_rule_amount CHECK (amount > 0 AND amount <> 'NaN'::numeric),
    CONSTRAINT chk_rule_frequency CHECK (frequency IN ('weekly', 'monthly', 'yearly')),
    CONSTRAINT chk_rule_dates CHECK (end_date IS NULL OR first_occurrence_date <= end_date),
    CONSTRAINT chk_rule_status CHECK (status IN ('active', 'suspended', 'terminated'))
);

CREATE TABLE planned_transaction (
    id_planned_transaction BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_category BIGINT NOT NULL,
    name VARCHAR(140) NOT NULL,
    type VARCHAR(10) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    planned_date DATE NOT NULL,
    status VARCHAR(25) NOT NULL DEFAULT 'planned',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_planned_transaction PRIMARY KEY (id_planned_transaction),
    CONSTRAINT fk_planned_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_planned_category FOREIGN KEY (id_category) REFERENCES category (id_category),
    CONSTRAINT chk_planned_name CHECK (btrim(name) <> ''),
    CONSTRAINT chk_planned_type CHECK (type IN ('income', 'expense')),
    CONSTRAINT chk_planned_amount CHECK (amount > 0 AND amount <> 'NaN'::numeric),
    CONSTRAINT chk_planned_status CHECK (status IN ('planned', 'pending_confirmation', 'recorded', 'cancelled'))
);

CREATE TABLE transaction (
    id_transaction BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_category BIGINT,
    id_recurring_rule BIGINT,
    id_planned_transaction BIGINT,
    description VARCHAR(140),
    type VARCHAR(15) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    transaction_date DATE NOT NULL,
    origin VARCHAR(20) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_transaction PRIMARY KEY (id_transaction),
    CONSTRAINT fk_transaction_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_transaction_category FOREIGN KEY (id_category) REFERENCES category (id_category),
    CONSTRAINT fk_transaction_rule FOREIGN KEY (id_recurring_rule) REFERENCES recurring_rule (id_recurring_rule) ON DELETE SET NULL,
    CONSTRAINT fk_transaction_planned FOREIGN KEY (id_planned_transaction) REFERENCES planned_transaction (id_planned_transaction) ON DELETE SET NULL,
    CONSTRAINT chk_transaction_type CHECK (type IN ('income', 'expense', 'adjustment')),
    CONSTRAINT chk_transaction_amount CHECK (amount <> 0 AND amount <> 'NaN'::numeric),
    CONSTRAINT chk_transaction_origin CHECK (origin IN ('manual', 'ocr', 'recurring', 'planned', 'reconciliation')),

    CONSTRAINT uq_rule_occurrence UNIQUE (id_recurring_rule, transaction_date)
);

CREATE TABLE balance_snapshot (
    id_snapshot BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    id_adjustment_transaction BIGINT, 
    real_balance NUMERIC(12,2) NOT NULL,
    calculated_balance NUMERIC(12,2) NOT NULL,
    reconciliation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_balance_snapshot PRIMARY KEY (id_snapshot),
    CONSTRAINT fk_snapshot_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT fk_snapshot_transaction FOREIGN KEY (id_adjustment_transaction) REFERENCES transaction (id_transaction) ON DELETE SET NULL,
    CONSTRAINT chk_snapshot_real_balance CHECK (real_balance <> 'NaN'::numeric),
    CONSTRAINT chk_snapshot_calc_balance CHECK (calculated_balance <> 'NaN'::numeric)
);

CREATE TABLE alert (
    id_alert BIGINT GENERATED ALWAYS AS IDENTITY,
    id_user BIGINT NOT NULL,
    type VARCHAR(25) NOT NULL,
    message TEXT NOT NULL,
    trigger_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(15) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,

    CONSTRAINT pk_alert PRIMARY KEY (id_alert),
    CONSTRAINT fk_alert_user FOREIGN KEY (id_user) REFERENCES _user (id_user) ON DELETE CASCADE,
    CONSTRAINT chk_alert_type CHECK (type IN ('risk_level', 'impending_expense', 'sts_drop')),
    CONSTRAINT chk_alert_status CHECK (status IN ('active', 'read', 'resolved')),
    CONSTRAINT chk_alert_message CHECK (btrim(message) <> '')
);

CREATE INDEX idx_transaction_user_date ON transaction (id_user, transaction_date DESC);
CREATE INDEX idx_recurring_user_status ON recurring_rule (id_user, status);
CREATE INDEX idx_planned_user_date ON planned_transaction (id_user, planned_date, status);
CREATE INDEX idx_alert_user_status ON alert (id_user, status);
CREATE INDEX idx_snapshot_user_date ON balance_snapshot (id_user, reconciliation_date DESC);

COMMIT;