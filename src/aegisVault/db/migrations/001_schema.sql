-- ============================================================
-- AegisVault — PostgreSQL Schema
-- Run once on fresh database:
--   psql $DATABASE_URL < db/migrations/001_schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Audit Log (Layer 6) ───────────────────────────────────────────────
-- Every query is logged here AFTER PII scrubbing.
-- This table is your compliance trail — never holds raw PII.
CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id        UUID        NOT NULL,
    user_id         VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(255) NOT NULL DEFAULT 'default',
    query           TEXT,                       -- PII-scrubbed before storage
    response        TEXT,                       -- PII-scrubbed before storage
    chunks_used     INT         DEFAULT 0,
    rbac_blocked    INT         DEFAULT 0,
    pii_redacted    INT         DEFAULT 0,
    canary_leaked   BOOLEAN     DEFAULT FALSE,
    violations      JSONB       DEFAULT '[]',
    latency_ms      INT,
    model           VARCHAR(100),
    route_action    VARCHAR(20),                -- allow | block | flag
    route_category  VARCHAR(100),              -- prompt_injection | jailbreak | etc.
    timestamp       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant    ON audit_log (tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts        ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_canary    ON audit_log (canary_leaked) WHERE canary_leaked = TRUE;
CREATE INDEX IF NOT EXISTS idx_audit_pii       ON audit_log (pii_redacted)  WHERE pii_redacted > 0;
CREATE INDEX IF NOT EXISTS idx_audit_blocked   ON audit_log (route_action)  WHERE route_action = 'block';

-- ── Ingestion Log ─────────────────────────────────────────────────────
-- Tracks every document ingested — status, PII found, sensitivity class.
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id              VARCHAR(255) NOT NULL,
    tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
    source              VARCHAR(500),
    status              VARCHAR(20)  NOT NULL,  -- ingested | quarantined | rejected | skipped
    reason              VARCHAR(100),
    chunks_stored       INT         DEFAULT 0,
    sensitivity_class   VARCHAR(50)  DEFAULT 'PUBLIC',
    pii_entities_found  TEXT[],
    text_modified       BOOLEAN     DEFAULT FALSE,
    acl_roles           TEXT[],
    ingested_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingest_doc       ON ingestion_log (doc_id);
CREATE INDEX IF NOT EXISTS idx_ingest_tenant    ON ingestion_log (tenant_id);
CREATE INDEX IF NOT EXISTS idx_ingest_status    ON ingestion_log (status);
CREATE INDEX IF NOT EXISTS idx_ingest_class     ON ingestion_log (sensitivity_class);

-- ── Quarantine Log ────────────────────────────────────────────────────
-- Documents rejected due to secrets or critical PII.
-- File path points to the quarantine directory copy.
CREATE TABLE IF NOT EXISTS quarantine_log (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id          VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(255) DEFAULT 'default',
    reason          VARCHAR(100) NOT NULL,      -- secrets_detected | critical_pii | prompt_injection
    pii_types       TEXT[],
    file_path       VARCHAR(500),
    source          VARCHAR(500),
    quarantined_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quarantine_reason ON quarantine_log (reason);
CREATE INDEX IF NOT EXISTS idx_quarantine_ts     ON quarantine_log (quarantined_at DESC);

-- ── Canary Alert Log ──────────────────────────────────────────────────
-- Fires when a canary token appears in an LLM response.
-- This is a CRITICAL security event — retrieval is leaking data.
CREATE TABLE IF NOT EXISTS canary_alerts (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id        UUID,
    user_id         VARCHAR(255),
    tenant_id       VARCHAR(255),
    canary_token    VARCHAR(255) NOT NULL,
    query           TEXT,                       -- query that triggered the leak
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ── Injection Attempts ────────────────────────────────────────────────
-- Logs every blocked or flagged query with injection signals.
CREATE TABLE IF NOT EXISTS injection_attempts (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id        UUID,
    user_id         VARCHAR(255),
    tenant_id       VARCHAR(255),
    raw_query       TEXT,
    action          VARCHAR(20)  NOT NULL,      -- block | flag
    category        VARCHAR(100),              -- prompt_injection | jailbreak | etc.
    confidence      FLOAT,
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inject_user   ON injection_attempts (user_id);
CREATE INDEX IF NOT EXISTS idx_inject_cat    ON injection_attempts (category);
CREATE INDEX IF NOT EXISTS idx_inject_ts     ON injection_attempts (detected_at DESC);

-- ── RBAC: User Roles ──────────────────────────────────────────────────
-- Maps user_id → roles for access control decisions.
CREATE TABLE IF NOT EXISTS user_roles (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     VARCHAR(255) NOT NULL,
    tenant_id   VARCHAR(255) NOT NULL DEFAULT 'default',
    role        VARCHAR(100) NOT NULL,
    granted_at  TIMESTAMPTZ DEFAULT NOW(),
    granted_by  VARCHAR(255),
    UNIQUE (user_id, tenant_id, role)
);

CREATE INDEX IF NOT EXISTS idx_roles_user   ON user_roles (user_id, tenant_id);

-- ── RBAC: Document ACL ────────────────────────────────────────────────
-- Explicit per-document access control entries.
CREATE TABLE IF NOT EXISTS document_acl (
    id                  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id              VARCHAR(255) NOT NULL,
    tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
    sensitivity_class   VARCHAR(50)  NOT NULL DEFAULT 'INTERNAL',
    allowed_roles       TEXT[]       NOT NULL DEFAULT '{}',
    allowed_users       TEXT[]       NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (doc_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_acl_doc     ON document_acl (doc_id);
CREATE INDEX IF NOT EXISTS idx_acl_tenant  ON document_acl (tenant_id);
CREATE INDEX IF NOT EXISTS idx_acl_class   ON document_acl (sensitivity_class);

-- ── Differential Privacy Audit ────────────────────────────────────────
-- Records DP noise stats per ingestion batch for compliance reporting.
CREATE TABLE IF NOT EXISTS dp_audit (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id          VARCHAR(255),
    epsilon         FLOAT       NOT NULL,
    sensitivity     FLOAT       NOT NULL,
    noise_l2_mean   FLOAT,
    cosine_sim_mean FLOAT,
    chunks_processed INT,
    audited_at      TIMESTAMPTZ DEFAULT NOW()
);