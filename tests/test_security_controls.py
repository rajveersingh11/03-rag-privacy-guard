from dataclasses import replace
from types import SimpleNamespace

import pytest

from aegisVault.access.rbac import RBACPolicy
from aegisVault.entity.artifact_entity import OutputSanitizationArtifact, RouteDecisionArtifact
from aegisVault.entity.config_entity import (
    AegisVaultConfig,
    AppConfig,
    AuditConfig,
    CeleryConfig,
    DifferentialPrivacyConfig,
    GraphConfig,
    LLMConfig,
    OutputSanitizerConfig,
    PIIConfig,
    PathsConfig,
    RetrievalConfig,
    SemanticRouterConfig,
)
from aegisVault.guards.ingestion_scrubber import IngestionScrubber
from aegisVault.guards.output_sanitizer import OutputSanitizer
from aegisVault.guards.semantic_router import SemanticRouter
from aegisVault.pipeline.inference_pipeline import InferencePipeline
from aegisVault.utils.common import parse_metadata_list


def make_config(**overrides):
    cfg = AegisVaultConfig(
        app=AppConfig("AegisVault", "1.0.0", "127.0.0.1", 8000, False),
        paths=PathsConfig("./data", "./data/chroma_db", "./data/quarantine", "./data/audit_logs"),
        dp=DifferentialPrivacyConfig(1.0, 1.0, True),
        pii=PIIConfig(0.7, "quarantine", "redact", "redact", "tag", ["EMAIL_ADDRESS"]),
        semantic_router=SemanticRouterConfig(
            "guard", "facebook/bart-large-mnli", "cpu", 0.85,
            ["prompt_injection"], True,
        ),
        retrieval=RetrievalConfig(2, "test", "./data/chroma_db", "test-model", 0.5),
        graph=GraphConfig("bolt://local", "neo4j", "password", True, True),
        llm=LLMConfig("test-model", 0.0, 128, "Answer from context only."),
        output_sanitizer=OutputSanitizerConfig(["CANARY"], True, False),
        audit=AuditConfig(True, 30, "INFO"),
        celery=CeleryConfig("redis://local", "redis://local", "json", 1, "./data/quarantine"),
    )
    for key, value in overrides.items():
        cfg = replace(cfg, **{key: value})
    return cfg


def test_parse_metadata_list_handles_json_and_csv():
    assert parse_metadata_list('["employee", "manager"]') == ["employee", "manager"]
    assert parse_metadata_list("employee, manager") == ["employee", "manager"]
    assert parse_metadata_list(None) == []


def test_rbac_does_not_use_substring_acl_matching():
    policy = RBACPolicy()
    chunks = [{
        "page_content": "sensitive",
        "metadata": {
            "chunk_id": "c1",
            "tenant_id": "default",
            "sensitivity_class": "PUBLIC",
            "acl_roles": '["superadmin"]',
        },
    }]

    result = policy.filter_chunks(chunks, user_id="u1", user_roles=["admin"], tenant_id="default")

    assert result["allowed_chunks"] == []
    assert result["blocked_count"] == 1


def test_semantic_router_fail_closed_blocks_classifier_errors():
    cfg = SemanticRouterConfig("guard", "missing", "cpu", 0.85, ["prompt_injection"], True)
    router = SemanticRouter(cfg)
    router._get_classifier = lambda: (_ for _ in ()).throw(RuntimeError("model unavailable"))

    decision = router.route("normal question")

    assert decision.action == "block"
    assert decision.category == "security_classifier_unavailable"


def test_output_sanitizer_redacts_canary_without_pii_scan():
    sanitizer = OutputSanitizer(
        OutputSanitizerConfig(["CANARY-123"], True, False),
        PIIConfig(0.7, "quarantine", "redact", "redact", "tag", []),
    )

    result = sanitizer.sanitize("The token is CANARY-123", "trace")

    assert result.canary_leaked is True
    assert "CANARY-123" not in result.safe_response


def test_quarantine_encrypts_raw_content(tmp_path, monkeypatch):
    monkeypatch.setenv("QUARANTINE_ENCRYPTION_KEY", "unit-test-secret")
    scrubber = IngestionScrubber.__new__(IngestionScrubber)
    scrubber.quarantine_dir = tmp_path

    scrubber._quarantine("secret raw text", "doc1", "secrets")

    encrypted = next(tmp_path.glob("*.enc"))
    assert b"secret raw text" not in encrypted.read_bytes()


def test_inference_uses_graph_doc_ids_and_similarity_threshold(monkeypatch):
    cfg = make_config()

    class Graph:
        def get_authorized_doc_ids(self, user_roles, tenant_id, max_clearance):
            return ["allowed-doc"]

    class Vectorstore:
        def similarity_search_with_relevance_scores(self, query, k, filter=None):
            assert filter == {"doc_id": {"$in": ["allowed-doc"]}}
            return [
                (SimpleNamespace(page_content="allowed context", metadata={
                    "doc_id": "allowed-doc",
                    "tenant_id": "default",
                    "sensitivity_class": "PUBLIC",
                    "acl_roles": '["employee"]',
                }), 0.8),
                (SimpleNamespace(page_content="low score", metadata={
                    "doc_id": "allowed-doc",
                    "tenant_id": "default",
                    "sensitivity_class": "PUBLIC",
                    "acl_roles": '["employee"]',
                }), 0.2),
            ]

    class LLM:
        class chat:
            class completions:
                @staticmethod
                def create(model, messages, temperature, max_tokens):
                    assert "allowed context" in messages[-1]["content"]
                    assert "low score" not in messages[-1]["content"]
                    return SimpleNamespace(
                        choices=[SimpleNamespace(message=SimpleNamespace(content="safe answer"))]
                    )

    pipeline = InferencePipeline(cfg, Vectorstore(), LLM(), graph=Graph())
    pipeline.router.route = lambda query: RouteDecisionArtifact(
        query, True, "allow", None, 1.0, query
    )
    pipeline.sanitizer.sanitize = lambda response, trace_id: OutputSanitizationArtifact(
        response, response, False, 0, False, [], []
    )
    pipeline._audit = lambda *args, **kwargs: None

    result = pipeline.query("question", "u1", ["employee"], "default", top_k=2)

    assert result.safe_response == "safe answer"
    assert result.chunks_used == 1
