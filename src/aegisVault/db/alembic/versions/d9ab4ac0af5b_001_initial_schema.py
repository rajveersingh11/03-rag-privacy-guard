"""Create the complete AegisVault schema.

Revision ID: d9ab4ac0af5b
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9ab4ac0af5b"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_users_tenant", "users", ["tenant_id"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_auth_sessions_user", "auth_sessions", ["user_id"])
    op.create_index("idx_auth_sessions_expires", "auth_sessions", ["expires_at"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("query", sa.Text()),
        sa.Column("response", sa.Text()),
        sa.Column("chunks_used", sa.Integer(), server_default="0"),
        sa.Column("rbac_blocked", sa.Integer(), server_default="0"),
        sa.Column("pii_redacted", sa.Integer(), server_default="0"),
        sa.Column("canary_leaked", sa.Boolean(), server_default=sa.false()),
        sa.Column("violations", sa.JSON()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("model", sa.String(100)),
        sa.Column("route_action", sa.String(20)),
        sa.Column("route_category", sa.String(100)),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("checksum", sa.String(64)),
    )
    op.create_index("idx_audit_user", "audit_log", ["user_id"])
    op.create_index("idx_audit_tenant", "audit_log", ["tenant_id"])
    op.create_index("idx_audit_ts", "audit_log", ["timestamp"])

    op.create_table(
        "ingestion_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("doc_id", sa.String(255), nullable=False),
        sa.Column("document_hash", sa.String(64), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("source", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(100)),
        sa.Column("chunks_stored", sa.Integer(), server_default="0"),
        sa.Column("sensitivity_class", sa.String(50), server_default="PUBLIC"),
        sa.Column("pii_entities_found", sa.JSON()),
        sa.Column("text_modified", sa.Boolean(), server_default=sa.false()),
        sa.Column("acl_roles", sa.JSON()),
        sa.Column("provenance", sa.JSON()),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ingest_doc", "ingestion_log", ["doc_id"])
    op.create_index("idx_ingest_hash", "ingestion_log", ["document_hash"])
    op.create_index("idx_ingest_tenant", "ingestion_log", ["tenant_id"])
    op.create_index("idx_ingest_status", "ingestion_log", ["status"])

    op.create_table(
        "quarantine_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("doc_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), server_default="default"),
        sa.Column("reason", sa.String(100), nullable=False),
        sa.Column("pii_types", sa.JSON()),
        sa.Column("file_path", sa.String(500)),
        sa.Column("source", sa.String(500)),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_quarantine_reason", "quarantine_log", ["reason"])

    op.create_table(
        "canary_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36)),
        sa.Column("user_id", sa.String(255)),
        sa.Column("tenant_id", sa.String(255)),
        sa.Column("canary_token", sa.String(255), nullable=False),
        sa.Column("query", sa.Text()),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "injection_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36)),
        sa.Column("user_id", sa.String(255)),
        sa.Column("tenant_id", sa.String(255)),
        sa.Column("raw_query", sa.Text()),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("confidence", sa.Float()),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_inject_user", "injection_attempts", ["user_id"])
    op.create_index("idx_inject_cat", "injection_attempts", ["category"])

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("granted_by", sa.String(255)),
        sa.UniqueConstraint("user_id", "tenant_id", "role", name="uq_user_role_tenant"),
    )
    op.create_index("idx_roles_user", "user_roles", ["user_id", "tenant_id"])

    op.create_table(
        "document_acl",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("doc_id", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("sensitivity_class", sa.String(50), nullable=False, server_default="INTERNAL"),
        sa.Column("allowed_roles", sa.JSON()),
        sa.Column("allowed_users", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("doc_id", "tenant_id", name="uq_document_tenant"),
    )
    op.create_index("idx_acl_doc", "document_acl", ["doc_id"])
    op.create_index("idx_acl_tenant", "document_acl", ["tenant_id"])

    op.create_table(
        "dp_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("doc_id", sa.String(255)),
        sa.Column("epsilon", sa.Float(), nullable=False),
        sa.Column("sensitivity", sa.Float(), nullable=False),
        sa.Column("noise_l2_mean", sa.Float()),
        sa.Column("cosine_sim_mean", sa.Float()),
        sa.Column("chunks_processed", sa.Integer()),
        sa.Column("audited_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "dp_audit",
        "document_acl",
        "user_roles",
        "injection_attempts",
        "canary_alerts",
        "quarantine_log",
        "ingestion_log",
        "audit_log",
        "auth_sessions",
        "users",
    ):
        op.drop_table(table)
