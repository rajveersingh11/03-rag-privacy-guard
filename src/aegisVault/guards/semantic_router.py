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

import re
from typing import List, Optional, Dict

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


class SemanticRouter:
    """
    Two-stage guard:
    1. Fast regex pre-filter (microseconds, catches obvious injections)
    2. Zero-shot NLI classifier (semantic understanding of intent)

    In production, replace stage 2 with Llama Guard microservice call.
    """

    def __init__(self, cfg: SemanticRouterConfig):
        self.cfg = cfg
        self._classifier = None   # lazy load
        logger.info("SemanticRouter initialised")

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
        return self._semantic_classify(query)

    # ── Stage 1: Regex pre-filter ──────────────────────────────────────

    def _fast_filter(self, query: str) -> bool:
        return any(p.search(query) for p in FAST_PATTERNS)

    # ── Stage 2: Semantic classification ──────────────────────────────

    def _semantic_classify(self, query: str) -> RouteDecisionArtifact:
        try:
            classifier = self._get_classifier()
            candidate_labels = [
                "safe question",
                "prompt injection attempt",
                "jailbreak attempt",
                "data extraction request",
                "system instruction override",
            ]
            result = classifier(
                query,
                candidate_labels=candidate_labels,
                hypothesis_template="This text is a {}.",
                multi_label=False,
            )

            top_label  = result["labels"][0]
            top_score  = result["scores"][0]
            is_safe    = (top_label == "safe question")

            # Map label → injection category
            category_map = {
                "prompt injection attempt":   "prompt_injection",
                "jailbreak attempt":          "jailbreak",
                "data extraction request":    "data_exfiltration",
                "system instruction override":"prompt_injection",
            }
            category = category_map.get(top_label) if not is_safe else None
            should_block = (
                not is_safe
                and top_score >= self.cfg.confidence_threshold
                and category in self.cfg.block_categories
            )

            action = "block" if should_block else ("flag" if not is_safe else "allow")

            if not is_safe:
                logger.warning(
                    f"Semantic classifier: label='{top_label}' "
                    f"score={top_score:.3f} action={action}"
                )

            return RouteDecisionArtifact(
                query=query,
                is_safe=is_safe or not should_block,
                action=action,
                category=category,
                confidence=round(float(top_score), 4),
                safe_query=query if action != "block" else None,
            )

        except Exception as e:
            # Fail-open with warning — don't block users on classifier errors
            logger.error(f"SemanticRouter classifier error: {e} — failing open")
            return RouteDecisionArtifact(
                query=query, is_safe=True,
                action="allow", category=None,
                confidence=0.0, safe_query=query,
            )

    # ── Lazy model loader ──────────────────────────────────────────────

    def _get_classifier(self):
        if self._classifier is None:
            from transformers import pipeline
            logger.info(f"Loading semantic classifier: {self.cfg.fallback_model}")
            self._classifier = pipeline(
                "zero-shot-classification",
                model=self.cfg.fallback_model,
                device=-1,
            )
        return self._classifier