"""
AegisVault Components
----------------------
Each component maps to one security layer from the 2026 PDF.

Layer 1 — ingestion_scrubber  : Presidio PII detection + redaction
Layer 1 — privacy_math        : Differential Privacy (Laplacian noise)
Layer 2 — semantic_router     : Agentic intent classification (injection guard)
Layer 3 — graph_boundary      : Neo4j multi-tenant GraphRAG isolation
Layer 5 — output_sanitizer    : Canary token check + output PII scrub
"""

from aegisVault.components.ingestion_scrubber import IngestionScrubber
from aegisVault.components.privacy_math       import DPEmbedder
from aegisVault.components.semantic_router    import SemanticRouter
from aegisVault.components.graph_boundary     import GraphBoundary
from aegisVault.components.output_sanitizer   import OutputSanitizer

__all__ = [
    "IngestionScrubber",
    "DPEmbedder",
    "SemanticRouter",
    "GraphBoundary",
    "OutputSanitizer",
]