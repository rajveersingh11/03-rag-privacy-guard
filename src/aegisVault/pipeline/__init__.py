"""
AegisVault Pipelines
---------------------
Two pipelines coordinate all security guards end-to-end.

IngestionPipeline  — offline/async, called by Celery worker
                     Layer 1 (scrub) → Layer 1 (DP embed) → ChromaDB + Neo4j

InferencePipeline  — real-time, called per user query
                     Layer 2 (route) → Layer 3 (RBAC) → LLM → Layer 5 (sanitize) → Layer 6 (audit)
"""

from .ingestion_pipeline import IngestionPipeline
from .inference_pipeline import InferencePipeline

__all__ = ["IngestionPipeline", "InferencePipeline"]