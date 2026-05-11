"""001_initial_schema

Revision ID: d9ab4ac0af5b
Revises: 
Create Date: 2026-05-11 16:55:07.561029

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ab4ac0af5b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
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
        violations      JSON,                       
        latency_ms      INT,
        model           VARCHAR(100),
        route_action    VARCHAR(20),
        route_category  VARCHAR(100),
        timestamp       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
        checksum        VARCHAR(64),
        
        INDEX idx_audit_user (user_id),
        INDEX idx_audit_tenant (tenant_id),
        INDEX idx_audit_ts (timestamp DESC)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS ingestion_log (
        id                  VARCHAR(36)  PRIMARY KEY,
        doc_id              VARCHAR(255) NOT NULL,
        tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
        source              VARCHAR(500),
        status              VARCHAR(20)  NOT NULL,
        reason              VARCHAR(100),
        chunks_stored       INT         DEFAULT 0,
        sensitivity_class   VARCHAR(50)  DEFAULT 'PUBLIC',
        pii_entities_found  JSON,                    
        text_modified       BOOLEAN     DEFAULT FALSE,
        acl_roles           JSON,                    
        ingested_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

        INDEX idx_ingest_doc (doc_id),
        INDEX idx_ingest_tenant (tenant_id),
        INDEX idx_ingest_status (status),
        INDEX idx_ingest_class (sensitivity_class)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS quarantine_log (
        id              VARCHAR(36)  PRIMARY KEY,
        doc_id          VARCHAR(255) NOT NULL,
        tenant_id       VARCHAR(255) DEFAULT 'default',
        reason          VARCHAR(100) NOT NULL,
        pii_types       JSON,                        
        file_path       VARCHAR(500),
        source          VARCHAR(500),
        quarantined_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

        INDEX idx_quarantine_reason (reason),
        INDEX idx_quarantine_ts (quarantined_at DESC)
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS canary_alerts (
        id              VARCHAR(36)  PRIMARY KEY,
        trace_id        VARCHAR(36),
        user_id         VARCHAR(255),
        tenant_id       VARCHAR(255),
        canary_token    VARCHAR(255) NOT NULL,
        query           TEXT,
        detected_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
    );
    """)

    op.execute("""
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
    """)

    op.execute("""
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
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS document_acl (
        id                  VARCHAR(36)  PRIMARY KEY,
        doc_id              VARCHAR(255) NOT NULL,
        tenant_id           VARCHAR(255) NOT NULL DEFAULT 'default',
        sensitivity_class   VARCHAR(50)  NOT NULL DEFAULT 'INTERNAL',
        allowed_roles       JSON,                    
        allowed_users       JSON,                    
        created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY (doc_id, tenant_id),
        INDEX idx_acl_doc (doc_id),
        INDEX idx_acl_tenant (tenant_id)
    );
    """)

    op.execute("""
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
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS dp_audit;")
    op.execute("DROP TABLE IF EXISTS document_acl;")
    op.execute("DROP TABLE IF EXISTS user_roles;")
    op.execute("DROP TABLE IF EXISTS injection_attempts;")
    op.execute("DROP TABLE IF EXISTS canary_alerts;")
    op.execute("DROP TABLE IF EXISTS quarantine_log;")
    op.execute("DROP TABLE IF EXISTS ingestion_log;")
    op.execute("DROP TABLE IF EXISTS audit_log;")
