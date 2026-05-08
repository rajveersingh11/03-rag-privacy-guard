"""
Artifact Entity
----------------
Typed dataclasses for pipeline outputs.
Every pipeline stage returns one of these — enables strict
typing across the ingestion and inference pipelines.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class PIIScanArtifact:
    original_text:      str
    scrubbed_text:      str
    entities_found:     List[Dict[str, Any]]
    has_critical:       bool
    sensitivity_class:  str
    was_modified:       bool


@dataclass
class DPEmbeddingArtifact:
    original_embedding:  List[float]
    noisy_embedding:     List[float]
    epsilon_used:        float
    noise_magnitude:     float


@dataclass
class IngestionArtifact:
    doc_id:              str
    status:              str           # ingested | quarantined | rejected
    reason:              Optional[str]
    chunks_stored:       int
    sensitivity_class:   str
    pii_entities_found:  List[str]
    text_modified:       bool
    timestamp:           datetime = field(default_factory=datetime.utcnow)


@dataclass
class RouteDecisionArtifact:
    query:            str
    is_safe:          bool
    action:           str             # allow | block | flag
    category:         Optional[str]   # prompt_injection | jailbreak | etc.
    confidence:       float
    safe_query:       Optional[str]   # sanitized query if flagged but allowed


@dataclass
class RetrievalArtifact:
    chunks:           List[Dict[str, Any]]
    blocked_count:    int
    user_clearance:   str


@dataclass
class OutputSanitizationArtifact:
    original_response:      str
    safe_response:          str
    was_modified:           bool
    pii_entities_removed:   int
    canary_leaked:          bool
    canary_tokens_found:    List[str]
    violations:             List[Dict[str, Any]]


@dataclass
class InferenceArtifact:
    trace_id:             str
    query:                str
    safe_response:        str
    chunks_used:          int
    rbac_blocked:         int
    pii_redacted:         int
    canary_leaked:        bool
    hallucination_risk:   str          # low | medium | high
    latency_ms:           int
    timestamp:            datetime = field(default_factory=datetime.utcnow)