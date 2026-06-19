"""
Config Entity
--------------
Typed pydantic models for every config section in params.yaml.
ConfigManager parses YAML → these typed objects.
"""

from typing import List
from pydantic import BaseModel, model_validator


class DifferentialPrivacyConfig(BaseModel):
    epsilon: float
    sensitivity: float
    enabled: bool
    delta: float = 1e-5
    mechanism: str = "laplace"  # "laplace" or "gaussian"
    clipping_threshold: float = 1.0


class PIIConfig(BaseModel):
    confidence_threshold: float
    on_critical: str
    on_high: str
    on_medium: str
    on_low: str
    entities_to_detect: List[str]
    compliance_mode: str = "none"


class SemanticRouterConfig(BaseModel):
    model_id: str
    fallback_model: str
    device: str
    confidence_threshold: float
    block_categories: List[str]
    fail_closed: bool = True
    classifier_backend: str = "local_hf"


class RetrievalConfig(BaseModel):
    top_k: int
    chroma_collection: str
    chroma_persist_dir: str
    embedding_model: str
    similarity_threshold: float


class GraphConfig(BaseModel):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    tenant_isolation: bool
    enforce_acl_on_nodes: bool


class LLMConfig(BaseModel):
    model_id: str
    temperature: float
    max_tokens: int
    system_prompt: str


class OutputSanitizerConfig(BaseModel):
    canary_tokens: List[str]
    alert_on_canary: bool
    re_scrub_output: bool


class AuditConfig(BaseModel):
    scrub_before_log: bool
    retention_days: int
    log_level: str


class CeleryConfig(BaseModel):
    broker_url: str
    result_backend: str
    task_serializer: str
    worker_concurrency: int
    quarantine_dir: str


class AppConfig(BaseModel):
    name: str
    version: str
    host: str
    port: int
    debug: bool


class PathsConfig(BaseModel):
    data_dir: str
    chroma_dir: str
    quarantine_dir: str
    audit_log_dir: str


class AegisVaultConfig(BaseModel):
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
    
    @model_validator(mode='after')
    def validate_cross_configs(self) -> 'AegisVaultConfig':
        if self.graph.tenant_isolation and not self.graph.neo4j_uri:
            raise ValueError("NEO4J_URI must be set when tenant_isolation is enabled")
        if self.dp.enabled:
            if self.dp.epsilon <= 0:
                raise ValueError("DP epsilon must be > 0 when enabled")
            if self.dp.sensitivity <= 0:
                raise ValueError("DP sensitivity must be > 0 when enabled")
        return self
