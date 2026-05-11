"""
Config Entity
--------------
Typed dataclasses for every config section in params.yaml.
ConfigManager parses YAML → these typed objects.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class DifferentialPrivacyConfig:
    epsilon: float
    sensitivity: float
    enabled: bool


@dataclass
class PIIConfig:
    confidence_threshold: float
    on_critical: str
    on_high: str
    on_medium: str
    on_low: str
    entities_to_detect: List[str]


@dataclass
class SemanticRouterConfig:
    model_id: str
    fallback_model: str
    device: str
    confidence_threshold: float
    block_categories: List[str]
    fail_closed: bool = True


@dataclass
class RetrievalConfig:
    top_k: int
    chroma_collection: str
    chroma_persist_dir: str
    embedding_model: str
    similarity_threshold: float


@dataclass
class GraphConfig:
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    tenant_isolation: bool
    enforce_acl_on_nodes: bool


@dataclass
class LLMConfig:
    model_id: str
    temperature: float
    max_tokens: int
    system_prompt: str


@dataclass
class OutputSanitizerConfig:
    canary_tokens: List[str]
    alert_on_canary: bool
    re_scrub_output: bool


@dataclass
class AuditConfig:
    scrub_before_log: bool
    retention_days: int
    log_level: str


@dataclass
class CeleryConfig:
    broker_url: str
    result_backend: str
    task_serializer: str
    worker_concurrency: int
    quarantine_dir: str


@dataclass
class AppConfig:
    name: str
    version: str
    host: str
    port: int
    debug: bool


@dataclass
class PathsConfig:
    data_dir: str
    chroma_dir: str
    quarantine_dir: str
    audit_log_dir: str


@dataclass
class AegisVaultConfig:
    """Root config object — holds all section configs."""
    app:              AppConfig
    paths:            PathsConfig
    dp:               DifferentialPrivacyConfig
    pii:              PIIConfig
    semantic_router:  SemanticRouterConfig
    retrieval:        RetrievalConfig
    graph:            GraphConfig
    llm:              LLMConfig
    output_sanitizer: OutputSanitizerConfig
    audit:            AuditConfig
    celery:           CeleryConfig
