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
        app=AppConfig(name="AegisVault", version="1.0.0", host="127.0.0.1", port=8000, debug=False),
        paths=PathsConfig(data_dir="./data", chroma_dir="./data/chroma_db", quarantine_dir="./data/quarantine", audit_log_dir="./data/audit_logs"),
        dp=DifferentialPrivacyConfig(epsilon=1.0, sensitivity=1.0, enabled=True),
        pii=PIIConfig(confidence_threshold=0.7, on_critical="quarantine", on_high="redact", on_medium="redact", on_low="tag", entities_to_detect=["EMAIL_ADDRESS"], compliance_mode="none"),
        semantic_router=SemanticRouterConfig(
            model_id="guard", fallback_model="facebook/bart-large-mnli", device="cpu", confidence_threshold=0.85,
            block_categories=["prompt_injection"], fail_closed=True, classifier_backend="local_hf"
        ),
        retrieval=RetrievalConfig(top_k=2, chroma_collection="test", chroma_persist_dir="./data/chroma_db", embedding_model="test-model", similarity_threshold=0.5),
        graph=GraphConfig(neo4j_uri="bolt://local", neo4j_user="neo4j", neo4j_password="password", tenant_isolation=True, enforce_acl_on_nodes=True),
        llm=LLMConfig(model_id="test-model", temperature=0.0, max_tokens=128, system_prompt="Answer from context only."),
        output_sanitizer=OutputSanitizerConfig(canary_tokens=["CANARY"], alert_on_canary=True, re_scrub_output=False),
        audit=AuditConfig(scrub_before_log=True, retention_days=30, log_level="INFO"),
        celery=CeleryConfig(broker_url="redis://local", result_backend="redis://local", task_serializer="json", worker_concurrency=1, quarantine_dir="./data/quarantine"),
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
    cfg = SemanticRouterConfig(model_id="guard", fallback_model="missing", device="cpu", confidence_threshold=0.85, block_categories=["prompt_injection"], fail_closed=True, classifier_backend="local_hf")
    router = SemanticRouter(cfg)
    def mock_classify(query, cfg):
        raise RuntimeError("model unavailable")
    router._backend.classify = mock_classify

    decision = router.route("normal question")

    assert decision.action == "block"
    assert decision.category == "security_classifier_unavailable"


def test_output_sanitizer_redacts_canary_without_pii_scan():
    sanitizer = OutputSanitizer(
        OutputSanitizerConfig(canary_tokens=["CANARY-123"], alert_on_canary=True, re_scrub_output=False),
        PIIConfig(confidence_threshold=0.7, on_critical="quarantine", on_high="redact", on_medium="redact", on_low="tag", entities_to_detect=[], compliance_mode="none"),
    )

    result = sanitizer.sanitize("The token is CANARY-123", "trace")

    assert result.canary_leaked is True
    assert "CANARY-123" not in result.safe_response


def test_quarantine_encrypts_raw_content(tmp_path, monkeypatch):
    monkeypatch.setenv("QUARANTINE_ENCRYPTION_KEY", "gE4rQjW9H0yRzTqP4sD9NqgN4Q9XhK3yNfG6fH4fQkM=")
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
            assert filter == {
                "$and": [
                    {"tenant_id": "default"},
                    {"doc_id": {"$in": ["allowed-doc"]}}
                ]
            }
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
                def create(model, messages, temperature, max_tokens, **kwargs):
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
