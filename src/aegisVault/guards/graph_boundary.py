"""
Graph Boundary — Layer 3 (GraphRAG Multi-Tenant Isolation)
-----------------------------------------------------------
Implements a Neo4j knowledge graph layer alongside the vector store
to enforce logical multi-tenant access boundaries.

PDF Section 1.3: GraphRAG provides a secondary physical defense
against RBAC failure — each tenant's document nodes are structurally
isolated in the graph, not just filtered by metadata.
"""

from typing import List, Dict, Any, Optional
from aegisVault.entity.config_entity import GraphConfig
from aegisVault.utils.common import get_logger, sensitivity_index
from aegisVault.constants import ROLE_CLEARANCE, SENSITIVITY_LEVELS

logger = get_logger(__name__)


class GraphBoundary:
    """
    Manages tenant-isolated document nodes in Neo4j.
    Every document stored has:
      - A Tenant node (owner)
      - A Document node with sensitivity_class property
      - BELONGS_TO relationship between Document → Tenant
      - AUTHORIZED_FOR relationships between User roles → Documents

    Retrieval: only returns Document node IDs the querying user
    can access — used as a pre-filter for ChromaDB retrieval.
    """

    def __init__(self, cfg: GraphConfig):
        self.cfg = cfg
        self._driver = None
        logger.info("GraphBoundary initialised")

    # ── Connection ─────────────────────────────────────────────────────

    def _get_driver(self):
        if self._driver is None:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(
                self.cfg.neo4j_uri,
                auth=(self.cfg.neo4j_user, self.cfg.neo4j_password),
            )
            logger.info(f"Connected to Neo4j: {self.cfg.neo4j_uri}")
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()

    # ── Schema setup (run once on startup) ────────────────────────────

    def ensure_schema(self):
        logger.info("Ensuring Neo4j schema constraints...")
        driver = self._get_driver()
        with driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE")
            session.run("CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.sensitivity_class)")
        logger.info("Neo4j schema constraints ensured")

    # ── Register document in graph ─────────────────────────────────────

    def register_document(
        self,
        doc_id:           str,
        tenant_id:        str,
        sensitivity_class: str,
        acl_roles:        List[str],
        metadata:         Dict[str, Any],
    ):
        """Create Document node + BELONGS_TO tenant + AUTHORIZED_FOR roles."""
        driver = self._get_driver()
        with driver.session() as session:
            # Upsert tenant node
            session.run(
                "MERGE (t:Tenant {id: $tid})",
                tid=tenant_id,
            )
            # Upsert document node
            session.run(
                """
                MERGE (d:Document {doc_id: $doc_id})
                SET d.sensitivity_class = $sc,
                    d.tenant_id         = $tid,
                    d.source            = $source
                WITH d
                MATCH (t:Tenant {id: $tid})
                MERGE (d)-[:BELONGS_TO]->(t)
                """,
                doc_id=doc_id, sc=sensitivity_class,
                tid=tenant_id, source=metadata.get("source", "unknown"),
            )
            # Create AUTHORIZED_FOR edges for each role
            for role in acl_roles:
                session.run(
                    """
                    MERGE (r:Role {name: $role})
                    WITH r
                    MATCH (d:Document {doc_id: $doc_id})
                    MERGE (r)-[:AUTHORIZED_FOR]->(d)
                    """,
                    role=role, doc_id=doc_id,
                )
        logger.debug(f"Registered doc '{doc_id}' for tenant '{tenant_id}'")

    # ── Query: get authorized doc IDs for a user ──────────────────────

    def get_authorized_doc_ids(
        self,
        user_roles:    List[str],
        tenant_id:     str,
        max_clearance: str = "CONFIDENTIAL",
    ) -> List[str]:
        """
        Returns doc_ids the user can access based on:
        - Their roles (AUTHORIZED_FOR edges)
        - Their clearance level (sensitivity_class filter)
        - Tenant boundary (BELONGS_TO edge)
        """
        if not self.cfg.tenant_isolation:
            return []   # return empty → caller falls back to vector DB only

        clearance_idx = sensitivity_index(max_clearance)
        allowed_classes = SENSITIVITY_LEVELS[:clearance_idx + 1]

        driver = self._get_driver()
        with driver.session() as session:
            result = session.run(
                """
                MATCH (r:Role)-[:AUTHORIZED_FOR]->(d:Document)-[:BELONGS_TO]->(t:Tenant)
                WHERE r.name IN $roles
                  AND t.id = $tenant_id
                  AND d.sensitivity_class IN $allowed_classes
                RETURN DISTINCT d.doc_id AS doc_id
                """,
                roles=user_roles,
                tenant_id=tenant_id,
                allowed_classes=allowed_classes,
            )
            return [record["doc_id"] for record in result]