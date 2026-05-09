"""
Ingestion Pipeline — Async (Celery Worker)
-------------------------------------------
Offloads heavy NER/DP operations to a Celery background worker
so the FastAPI event loop never blocks during high-concurrency loads.

PDF Section 1.3: Asynchronous MLOps — offload Layer 1 scrubbing
to a distributed message queue (Celery/Redis).

Flow:
  POST /ingest → Celery task queued → worker picks up →
  Scrub → DP Embed → ChromaDB + Neo4j store
"""

import hashlib
from typing import List, Dict, Any, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..guards.ingestion_scrubber import IngestionScrubber
from ..guards.privacy_math import DPEmbedder
from ..guards.graph_boundary import GraphBoundary
from ..entity.artifact_entity import IngestionArtifact
from ..entity.config_entity import AegisVaultConfig
from ..utils.common import get_logger, hash_text, ensure_dir

logger = get_logger(__name__)


class IngestionPipeline:
    """
    Orchestrates the full ingestion flow:
      Layer 1: PII Scrub (Presidio) → Quarantine / Redact
      Layer 1: DP Embedding (Laplacian noise)
      Layer 3: Graph registration (Neo4j)
      Store: ChromaDB vector store
    """

    def __init__(
        self,
        config:       AegisVaultConfig,
        vectorstore,                     # Chroma vectorstore instance
        graph:        Optional[GraphBoundary] = None,
    ):
        self.cfg         = config
        self.vectorstore = vectorstore
        self.graph       = graph
        self.scrubber    = IngestionScrubber(
            cfg=config.pii,
            quarantine_dir=config.celery.quarantine_dir,
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=512, chunk_overlap=64,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        logger.info("IngestionPipeline ready")

    # ── Main entry point ───────────────────────────────────────────────

    def ingest(
        self,
        text:      str,
        metadata:  Dict[str, Any],
        tenant_id: str           = "default",
        acl_roles: List[str]     = None,
    ) -> IngestionArtifact:
        """
        Runs the full pipeline synchronously.
        In production this is called from the Celery task (worker.py).
        """
        acl_roles = acl_roles or ["employee"]
        doc_id = metadata.get("doc_id", hash_text(text))

        logger.info(f"[{doc_id}] Ingestion started | tenant={tenant_id}")

        # ── Layer 1a: PII Scrub ────────────────────────────────────────
        scan = self.scrubber.scrub(text, doc_id=doc_id)

        if "QUARANTINED" in scan.scrubbed_text:
            return IngestionArtifact(
                doc_id=doc_id, status="quarantined",
                reason=scan.entities_found[0]["type"] if scan.entities_found else "unknown",
                chunks_stored=0,
                sensitivity_class=scan.sensitivity_class,
                pii_entities_found=[e["entity_type"] for e in scan.entities_found
                                     if "entity_type" in e],
                text_modified=True,
            )

        # ── Layer 1b: Chunk ────────────────────────────────────────────
        chunks = self.splitter.split_text(scan.scrubbed_text)
        if not chunks:
            return IngestionArtifact(
                doc_id=doc_id, status="skipped", reason="empty_after_scrub",
                chunks_stored=0, sensitivity_class=scan.sensitivity_class,
                pii_entities_found=[], text_modified=scan.was_modified,
            )

        # ── Layer 1c: Build chunk metadata ────────────────────────────
        chunk_metas = [
            {
                **metadata,
                "chunk_id":          f"{doc_id}_chunk_{i}",
                "doc_id":            doc_id,
                "sensitivity_class": scan.sensitivity_class,
                "pii_found":         [e.get("entity_type","") for e in scan.entities_found],
                "acl_roles":         acl_roles,
                "tenant_id":         tenant_id,
                "pii_redacted":      scan.was_modified,
            }
            for i in range(len(chunks))
        ]

        # ── Layer 1d: Embed with DP noise + store ─────────────────────
        # DP noise is injected inside DPEmbedder.embed_documents()
        self.vectorstore.add_texts(chunks, metadatas=chunk_metas)

        # ── Layer 3: Register in knowledge graph ──────────────────────
        if self.graph and self.cfg.graph.tenant_isolation:
            self.graph.register_document(
                doc_id=doc_id,
                tenant_id=tenant_id,
                sensitivity_class=scan.sensitivity_class,
                acl_roles=acl_roles,
                metadata=metadata,
            )

        logger.info(
            f"[{doc_id}] Ingested {len(chunks)} chunks | "
            f"sensitivity={scan.sensitivity_class} | "
            f"pii_modified={scan.was_modified}"
        )

        return IngestionArtifact(
            doc_id=doc_id, status="ingested", reason=None,
            chunks_stored=len(chunks),
            sensitivity_class=scan.sensitivity_class,
            pii_entities_found=[e.get("entity_type","") for e in scan.entities_found],
            text_modified=scan.was_modified,
        )


# ══════════════════════════════════════════════════════════════════════
# __main__ — Run ingestion pipeline directly for local testing
#
# Usage:
#   python -m aegisVault.pipeline.ingestion_pipeline
#   python -m aegisVault.pipeline.ingestion_pipeline --file path/to/doc.txt
#   python -m aegisVault.pipeline.ingestion_pipeline --demo secrets
#
# Tests the full Layer 1 stack (PII scrub + DP embed + chunking)
# without needing Docker, Neo4j, or a real OpenAI key.
# Uses an in-memory ChromaDB mock so it runs fully offline.
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import json
    import sys
    from dataclasses import asdict
    from unittest.mock import MagicMock, patch

    # ── CLI args ───────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="AegisVault — Test Ingestion Pipeline locally"
    )
    parser.add_argument(
        "--demo",
        choices=["pii", "secrets", "clean", "critical"],
        default="pii",
        help="Which demo document to ingest (default: pii)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a .txt file to ingest instead of a demo document",
    )
    parser.add_argument(
        "--tenant",  default="demo_org",  help="Tenant ID (default: demo_org)"
    )
    parser.add_argument(
        "--roles",   default="employee",  help="Comma-separated ACL roles"
    )
    parser.add_argument(
        "--epsilon", type=float, default=1.0,
        help="Differential Privacy epsilon budget (default: 1.0)"
    )
    args = parser.parse_args()

    # ── Demo documents ─────────────────────────────────────────────────
    DEMO_DOCS = {
        "pii": {
            "text": (
                "Employee Report — Q3 2026\n\n"
                "Name: John Doe\n"
                "Email: john.doe@acmecorp.com\n"
                "Phone: +1-555-867-5309\n"
                "Date of Birth: 12/04/1985\n\n"
                "John has consistently exceeded his quarterly targets. "
                "His manager, Sarah Connor (sarah.c@acmecorp.com), "
                "recommends a 15% salary increase effective January 2027.\n\n"
                "Emergency contact: Jane Doe — +1-555-234-5678"
            ),
            "label": "Document with PII (names, emails, phones)",
        },
        "secrets": {
            "text": (
                "Infrastructure Notes — CONFIDENTIAL\n\n"
                "Production DB: postgresql://admin:P@ssw0rd!@prod-db.acme.com:5432/maindb\n"
                "OpenAI API Key: sk-abcdefghijklmnopqrstuvwxyz12345678901234567890ab\n"
                "AWS Access Key: AKIAIOSFODNN7EXAMPLE\n"
                "JWT Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyMTIzIn0.abc\n\n"
                "These credentials are rotated monthly. Do not commit to Git."
            ),
            "label": "Document with API keys and secrets (should be QUARANTINED)",
        },
        "clean": {
            "text": (
                "AcmeCorp Refund Policy — Version 3.2\n\n"
                "Customers may request a full refund within 30 days of purchase "
                "for any product that is defective or not as described. "
                "Digital goods are eligible for refund only if the download link "
                "was non-functional at the time of purchase. "
                "To initiate a refund, contact our support team via the Help Portal. "
                "Refunds are processed within 5-7 business days."
            ),
            "label": "Clean document (no PII, no secrets)",
        },
        "critical": {
            "text": (
                "Patient Record — RESTRICTED\n\n"
                "Patient: Alice Smith\n"
                "SSN: 123-45-6789\n"
                "Medical Record Number: MRN-00487263\n"
                "Diagnosis: Type 2 Diabetes (ICD-10: E11)\n"
                "Aadhaar: 2345 6789 0123\n"
                "PAN: ABCDE1234F\n\n"
                "This record is covered under HIPAA and DPDPA regulations."
            ),
            "label": "Document with CRITICAL PII (SSN, MRN, Aadhaar, PAN) — policy=quarantine",
        },
    }

    # ── Load config (override epsilon from CLI) ─────────────────────────
    print("\n" + "═" * 60)
    print("  AegisVault — Ingestion Pipeline Test Runner")
    print("═" * 60)

    try:
        from ..config.manager import get_config
        cfg = get_config()
        cfg.dp.epsilon = args.epsilon   # allow CLI override
    except Exception as e:
        print(f"⚠  Config load failed ({e}) — using defaults")
        # Build minimal config manually for offline testing
        from ..entity.config_entity import (
            AegisVaultConfig, DifferentialPrivacyConfig, PIIConfig,
            SemanticRouterConfig, RetrievalConfig, GraphConfig,
            LLMConfig, OutputSanitizerConfig, AuditConfig, CeleryConfig,
        )
        cfg = AegisVaultConfig(
            dp=DifferentialPrivacyConfig(epsilon=args.epsilon, sensitivity=1.0, enabled=True),
            pii=PIIConfig(
                confidence_threshold=0.7,
                on_critical="quarantine", on_high="redact",
                on_medium="redact", on_low="tag",
                entities_to_detect=[
                    "PERSON","EMAIL_ADDRESS","PHONE_NUMBER","CREDIT_CARD",
                    "US_SSN","IN_PAN","IN_AADHAAR","MEDICAL_LICENSE","IP_ADDRESS",
                ],
            ),
            semantic_router=SemanticRouterConfig(
                model_id="", fallback_model="", device="cpu",
                confidence_threshold=0.85, block_categories=[],
            ),
            retrieval=RetrievalConfig(
                top_k=5, chroma_collection="aegis_test",
                chroma_persist_dir="./data/chroma_db",
                embedding_model="text-embedding-3-small",
                similarity_threshold=0.4,
            ),
            graph=GraphConfig(
                neo4j_uri="", neo4j_user="", neo4j_password="",
                tenant_isolation=False, enforce_acl_on_nodes=False,
            ),
            llm=LLMConfig(model_id="gpt-4o", temperature=0.0,
                          max_tokens=1024, system_prompt=""),
            output_sanitizer=OutputSanitizerConfig(
                canary_tokens=["AEGIS-CANARY-ALPHA-7749"],
                alert_on_canary=True, re_scrub_output=True,
            ),
            audit=AuditConfig(scrub_before_log=True, retention_days=365,
                              log_level="INFO"),
            celery=CeleryConfig(
                broker_url="redis://localhost:6379/0",
                result_backend="redis://localhost:6379/0",
                task_serializer="json", worker_concurrency=4,
                quarantine_dir="./data/quarantine",
            ),
        )

    # ── Build mock vectorstore (in-memory, no Chroma/OpenAI needed) ────
    mock_vectorstore = MagicMock()
    stored_chunks = []
    def _capture_add(texts, metadatas=None):
        stored_chunks.extend(texts)
    mock_vectorstore.add_texts.side_effect = _capture_add

    # ── Select document ─────────────────────────────────────────────────
    if args.file:
        try:
            text = open(args.file, "r", encoding="utf-8").read()
            doc_label = f"File: {args.file}"
        except FileNotFoundError:
            print(f"❌  File not found: {args.file}")
            sys.exit(1)
    else:
        demo  = DEMO_DOCS[args.demo]
        text  = demo["text"]
        doc_label = demo["label"]

    # ── Print input info ────────────────────────────────────────────────
    print(f"\n📄  Document : {doc_label}")
    print(f"👤  Tenant   : {args.tenant}")
    print(f"🔑  Roles    : {args.roles}")
    print(f"🔒  DP ε     : {args.epsilon}")
    print(f"\n{'─'*60}")
    print("INPUT TEXT (first 300 chars):")
    print(text[:300] + ("..." if len(text) > 300 else ""))
    print(f"{'─'*60}\n")

    # ── Run pipeline ────────────────────────────────────────────────────
    print("⏳  Running ingestion pipeline...\n")

    pipeline = IngestionPipeline(
        config=cfg,
        vectorstore=mock_vectorstore,
        graph=None,   # skip Neo4j for local test
    )

    result = pipeline.ingest(
        text=text,
        metadata={"source": args.file or f"demo_{args.demo}", "doc_id": f"test_{args.demo}"},
        tenant_id=args.tenant,
        acl_roles=[r.strip() for r in args.roles.split(",")],
    )

    # ── Print results ────────────────────────────────────────────────────
    status_icon = {
        "ingested":    "✅",
        "quarantined": "🚫",
        "rejected":    "❌",
        "skipped":     "⚠️ ",
    }.get(result.status, "❓")

    print(f"{'═'*60}")
    print(f"  INGESTION RESULT")
    print(f"{'═'*60}")
    print(f"  Status          : {status_icon}  {result.status.upper()}")
    print(f"  Doc ID          : {result.doc_id}")
    print(f"  Sensitivity     : {result.sensitivity_class}")
    print(f"  Chunks stored   : {result.chunks_stored}")
    print(f"  Text modified   : {result.text_modified}")
    print(f"  PII found       : {result.pii_entities_found or 'none'}")
    if result.reason:
        print(f"  Reason          : {result.reason}")
    print(f"{'─'*60}")

    if stored_chunks:
        print(f"\n📦  STORED CHUNKS ({len(stored_chunks)} total):\n")
        for i, chunk in enumerate(stored_chunks[:3], 1):
            print(f"  Chunk {i}: {chunk[:120]}{'...' if len(chunk) > 120 else ''}")
        if len(stored_chunks) > 3:
            print(f"  ... and {len(stored_chunks)-3} more chunks")

    print(f"\n{'═'*60}\n")

