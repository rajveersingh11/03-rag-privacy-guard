-- ============================================================
-- AegisVault — MySQL Schema
-- Run once on fresh database:
--   mysql -u $USER -p $DB_NAME < db/migrations/001_schema.sql
-- ============================================================

-- ── Audit Log (Layer 6) ───────────────────────────────────────────────
-- Every query is logged here AFTER PII scrubbing.
CREATE TABLE IF NOT EXISTS audit_log (
    id              VARCHAR(36)  PRIMARY KEY,
    trace_id        VARCHAR(36)  NOT NULL,
    user_id         VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(255) NOT NULL DEFAULT 'default',
    query           TEXT,
    response        TEXT,
    chunks_used     INT         DEFAULT 0,
    rbac_blocked    INT         DEFAULT 0,
    pii_redacted    INT         DEFAULT 0,
    canary_leaked   BOOLEAN     DEFAULT FALSE,
    violations      JSON,                       -- MySQL JSON type
    latency_ms      INT,
    model           VARCHAR(100),
    route_action    VARCHAR(20),
    route_category  VARCHAR(100),
    timestamp       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_tenant (tenant_id),
    INDEX idx_audit_ts (timestamp DESC)
);

-- ── Ingestion Log ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                  VARCHAR(36)  PRIMARY KEY,
    doc_id              VARCHAR(255) NOT NULL,
    tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
    source              VARCHAR(500),
    status              VARCHAR(20)  NOT NULL,
    reason              VARCHAR(100),
    chunks_stored       INT         DEFAULT 0,
    sensitivity_class   VARCHAR(50)  DEFAULT 'PUBLIC',
    pii_entities_found  JSON,                    -- Replaced TEXT[] with JSON
    text_modified       BOOLEAN     DEFAULT FALSE,
    acl_roles           JSON,                    -- Replaced TEXT[] with JSON
    ingested_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_ingest_doc (doc_id),
    INDEX idx_ingest_tenant (tenant_id),
    INDEX idx_ingest_status (status),
    INDEX idx_ingest_class (sensitivity_class)
);

-- ── Quarantine Log ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quarantine_log (
    id              VARCHAR(36)  PRIMARY KEY,
    doc_id          VARCHAR(255) NOT NULL,
    tenant_id       VARCHAR(255) DEFAULT 'default',
    reason          VARCHAR(100) NOT NULL,
    pii_types       JSON,                        -- Replaced TEXT[] with JSON
    file_path       VARCHAR(500),
    source          VARCHAR(500),
    quarantined_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_quarantine_reason (reason),
    INDEX idx_quarantine_ts (quarantined_at DESC)
);

-- ── Canary Alert Log ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS canary_alerts (
    id              VARCHAR(36)  PRIMARY KEY,
    trace_id        VARCHAR(36),
    user_id         VARCHAR(255),
    tenant_id       VARCHAR(255),
    canary_token    VARCHAR(255) NOT NULL,
    query           TEXT,
    detected_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ── Injection Attempts ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS injection_attempts (
    id              VARCHAR(36)  PRIMARY KEY,
    trace_id        VARCHAR(36),
    user_id         VARCHAR(255),
    tenant_id       VARCHAR(255),
    raw_query       TEXT,
    action          VARCHAR(20)  NOT NULL,
    category        VARCHAR(100),
    confidence      FLOAT,
    detected_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_inject_user (user_id),
    INDEX idx_inject_cat (category),
    INDEX idx_inject_ts (detected_at DESC)
);

-- ── RBAC: User Roles ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_roles (
    id          VARCHAR(36)  PRIMARY KEY,
    user_id     VARCHAR(255) NOT NULL,
    tenant_id   VARCHAR(255) NOT NULL DEFAULT 'default',
    role        VARCHAR(100) NOT NULL,
    granted_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    granted_by  VARCHAR(255),
    UNIQUE KEY (user_id, tenant_id, role),
    INDEX idx_roles_user (user_id, tenant_id)
);

-- ── RBAC: Document ACL ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_acl (
    id                  VARCHAR(36)  PRIMARY KEY,
    doc_id              VARCHAR(255) NOT NULL,
    tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
    sensitivity_class   VARCHAR(50)  NOT NULL DEFAULT 'INTERNAL',
    allowed_roles       JSON,                    -- Replaced TEXT[] with JSON
    allowed_users       JSON,                    -- Replaced TEXT[] with JSON
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (doc_id, tenant_id),
    INDEX idx_acl_doc (doc_id),
    INDEX idx_acl_tenant (tenant_id)
);

-- ── Differential Privacy Audit ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dp_audit (
    id              VARCHAR(36)  PRIMARY KEY,
    doc_id          VARCHAR(255),
    epsilon         FLOAT       NOT NULL,
    sensitivity     FLOAT       NOT NULL,
    noise_l2_mean   FLOAT,
    cosine_sim_mean FLOAT,
    chunks_processed INT,
    audited_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
