"""
AegisVault Entity
------------------
Typed dataclasses for configs and pipeline artifacts.
All pipeline stages input/output these — no raw dicts.

Config entities  : map params.yaml sections to typed objects
Artifact entities: typed outputs from each pipeline stage
"""

from aegisVault.entity.config_entity import (
    AegisVaultConfig,
    DifferentialPrivacyConfig,
    PIIConfig,
    SemanticRouterConfig,
    RetrievalConfig,
    GraphConfig,
    LLMConfig,
    OutputSanitizerConfig,
    AuditConfig,
    CeleryConfig,
)
from aegisVault.entity.artifact_entity import (
    PIIScanArtifact,
    DPEmbeddingArtifact,
    IngestionArtifact,
    RouteDecisionArtifact,
    RetrievalArtifact,
    OutputSanitizationArtifact,
    InferenceArtifact,
)

__all__ = [
    # Config
    "AegisVaultConfig",
    "DifferentialPrivacyConfig",
    "PIIConfig",
    "SemanticRouterConfig",
    "RetrievalConfig",
    "GraphConfig",
    "LLMConfig",
    "OutputSanitizerConfig",
    "AuditConfig",
    "CeleryConfig",
    # Artifacts
    "PIIScanArtifact",
    "DPEmbeddingArtifact",
    "IngestionArtifact",
    "RouteDecisionArtifact",
    "RetrievalArtifact",
    "OutputSanitizationArtifact",
    "InferenceArtifact",
]