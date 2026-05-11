"""
Semantic Router — Layer 2 (Agentic Intent Guard)
-------------------------------------------------
Replaces brittle regex injection detection with a semantic
classifier. Every user query is routed through this guard
BEFORE any vector DB retrieval occurs.

PDF Section 1.1: Deploy a quantized security LLM (Llama Guard
or fine-tuned classifier) as an independent microservice.

For production: swap HuggingFace pipeline for Llama Guard API call.
For development: uses a distilbert zero-shot classifier as fallback.
"""

import os
import re
import httpx
from typing import List, Optional, Dict, Protocol

from aegisVault.entity.artifact_entity import RouteDecisionArtifact
from aegisVault.entity.config_entity import SemanticRouterConfig
from aegisVault.constants import INJECTION_CATEGORIES
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)

# ── Fast regex pre-filter (catches obvious cases before model call) ───
FAST_PATTERNS = [
    re.compile(r'ignore (?:previous|all|prior) instructions', re.I),
    re.compile(r'disregard (?:previous|system) (?:prompt|instructions)', re.I),
    re.compile(r'you are now (?:DAN|jailbreak|unrestricted)', re.I),
    re.compile(r'reveal (?:your|the) (?:system prompt|instructions)', re.I),
    re.compile(r'print (?:all|the) (?:documents|context|chunks)', re.I),
    re.compile(r'act as (?:an? )?(?:unrestricted|unfiltered|evil)', re.I),
    re.compile(r'what (?:is|are) (?:your|the) (?:system|instructions)', re.I),
]

class ClassifierBackend(Protocol):
    def classify(self, query: str, cfg: SemanticRouterConfig) -> RouteDecisionArtifact:
        ...

class LocalHFClassifier:
    def __init__(self):
        self._classifier = None

    def classify(self, query: str, cfg: SemanticRouterConfig) -> RouteDecisionArtifact:
        if self._classifier is None:
            from transformers import pipeline
            logger.info(f"Loading semantic classifier: {cfg.fallback_model}")
            self._classifier = pipeline(
                "zero-shot-classification",
                model=cfg.fallback_model,
                device=-1,
            )
        candidate_labels = [
            "safe question",
            "prompt injection attempt",
            "jailbreak attempt",
            "data extraction request",
            "system instruction override",
        ]
        result = self._classifier(
            query,
            candidate_labels=candidate_labels,
            hypothesis_template="This text is a {}.",
            multi_label=False,
        )

        top_label  = result["labels"][0]
        top_score  = result["scores"][0]
        is_safe    = (top_label == "safe question")

        category_map = {
            "prompt injection attempt":   "prompt_injection",
            "jailbreak attempt":          "jailbreak",
            "data extraction request":    "data_exfiltration",
            "system instruction override":"prompt_injection",
        }
        category = category_map.get(top_label) if not is_safe else None
        should_block = (
            not is_safe
            and top_score >= cfg.confidence_threshold
            and category in cfg.block_categories
        )

        action = "block" if should_block else ("flag" if not is_safe else "allow")

        if not is_safe:
            logger.warning(
                f"LocalHFClassifier: label='{top_label}' score={top_score:.3f} action={action}"
            )

        return RouteDecisionArtifact(
            query=query,
            is_safe=is_safe or not should_block,
            action=action,
            category=category,
            confidence=round(float(top_score), 4),
            safe_query=query if action != "block" else None,
        )

class LlamaGuardClassifier:
    def classify(self, query: str, cfg: SemanticRouterConfig) -> RouteDecisionArtifact:
        endpoint = os.environ.get("LLAMA_GUARD_ENDPOINT")
        if not endpoint:
            raise RuntimeError("LLAMA_GUARD_ENDPOINT is not set")
            
        import asyncio
        async def _call():
            async with httpx.AsyncClient() as client:
                res = await client.post(endpoint, json={"query": query}, timeout=10.0)
                res.raise_for_status()
                return res.json()
                
        try:
            # We are running in a sync thread created by asyncio.to_thread, so we can run our own loop
            data = asyncio.run(_call())
        except RuntimeError:
            # If an event loop is somehow already running here
            response = httpx.post(endpoint, json={"query": query}, timeout=10.0)
            response.raise_for_status()
            data = response.json()
        
        is_safe = data.get("is_safe", True)
        category = data.get("category") if not is_safe else None
        confidence = float(data.get("confidence", 1.0))
        
        should_block = not is_safe and category in cfg.block_categories
        action = "block" if should_block else ("flag" if not is_safe else "allow")
        
        return RouteDecisionArtifact(
            query=query,
            is_safe=is_safe or not should_block,
            action=action,
            category=category,
            confidence=confidence,
            safe_query=query if action != "block" else None,
        )

class SemanticRouter:
    """
    Two-stage guard:
    1. Fast regex pre-filter (microseconds, catches obvious injections)
    2. Zero-shot NLI classifier (semantic understanding of intent)

    In production, replace stage 2 with Llama Guard microservice call.
    """

    def __init__(self, cfg: SemanticRouterConfig):
        self.cfg = cfg
        mode = getattr(cfg, "classifier_backend", "local_hf")
        if mode == "llama_guard":
            self._backend = LlamaGuardClassifier()
        else:
            self._backend = LocalHFClassifier()
        logger.info(f"SemanticRouter initialised with backend: {mode}")

    # ── Public entry point ─────────────────────────────────────────────

    def route(self, query: str) -> RouteDecisionArtifact:
        """
        Returns RouteDecisionArtifact with action: allow | block | flag
        """
        # Stage 1: Fast regex pre-filter
        fast_hit = self._fast_filter(query)
        if fast_hit:
            logger.warning(f"FAST_FILTER blocked: '{query[:60]}...'")
            return RouteDecisionArtifact(
                query=query, is_safe=False,
                action="block", category="prompt_injection",
                confidence=1.0, safe_query=None,
            )

        # Stage 2: Semantic classifier
        try:
            return self._backend.classify(query, self.cfg)
        except Exception as e:
            if self.cfg.fail_closed:
                logger.error(f"SemanticRouter classifier error: {e} - failing closed")
                return RouteDecisionArtifact(
                    query=query, is_safe=False,
                    action="block", category="security_classifier_unavailable",
                    confidence=0.0, safe_query=None,
                )
            logger.error(f"SemanticRouter classifier error: {e} - failing open")
            return RouteDecisionArtifact(
                query=query, is_safe=True,
                action="allow", category=None,
                confidence=0.0, safe_query=query,
            )

    # ── Stage 1: Regex pre-filter ──────────────────────────────────────

    def _fast_filter(self, query: str) -> bool:
        return any(p.search(query) for p in FAST_PATTERNS)
