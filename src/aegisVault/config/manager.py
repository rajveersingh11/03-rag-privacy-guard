"""
Config Manager
--------------
Reads config.yaml + params.yaml and resolves ${ENV_VAR}
substitutions. Returns a typed AegisVaultConfig object.
"""

import os
import yaml
from pathlib import Path
from functools import lru_cache

from src.aegisVault.constants import CONFIG_FILE_PATH, PARAMS_FILE_PATH
from src.aegisVault.entity.config_entity import (
    AegisVaultConfig, DifferentialPrivacyConfig, PIIConfig,
    SemanticRouterConfig, RetrievalConfig, GraphConfig,
    LLMConfig, OutputSanitizerConfig, AuditConfig, CeleryConfig,
)


def _resolve_env(raw: str) -> str:
    """Replace ${VAR} placeholders with environment variable values."""
    for key, val in os.environ.items():
        raw = raw.replace(f"${{{key}}}", val)
    return raw


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        raw = f.read()
    return yaml.safe_load(_resolve_env(raw))


@lru_cache(maxsize=1)
def get_config() -> AegisVaultConfig:
    """Singleton config loader — cached after first call."""
    cfg  = _load_yaml(CONFIG_FILE_PATH)   # noqa: F841 (used for app/paths)
    p    = _load_yaml(PARAMS_FILE_PATH)

    return AegisVaultConfig(
        dp=DifferentialPrivacyConfig(**p["differential_privacy"]),
        pii=PIIConfig(**p["pii"]),
        semantic_router=SemanticRouterConfig(**p["semantic_router"]),
        retrieval=RetrievalConfig(**p["retrieval"]),
        graph=GraphConfig(**p["graph"]),
        llm=LLMConfig(**p["llm"]),
        output_sanitizer=OutputSanitizerConfig(**p["output_sanitizer"]),
        audit=AuditConfig(**p["audit"]),
        celery=CeleryConfig(**p["celery"]),
    )