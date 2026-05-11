"""
Output Sanitizer — Layer 5
---------------------------
Last line of defense before the LLM response reaches the user.

1. Re-runs Presidio on the LLM output (LLMs can regenerate PII from context)
2. Scans for secrets the LLM may have reflected
3. Checks for canary token leakage (silent tripwire for retrieval breaches)
"""

from typing import List, Dict, Any

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from aegisVault.entity.artifact_entity import OutputSanitizationArtifact
from aegisVault.entity.config_entity import OutputSanitizerConfig, PIIConfig
from aegisVault.utils.common import get_logger

logger = get_logger(__name__)


class OutputSanitizer:
    """
    Scans and scrubs LLM output.
    Canary tokens: fake sensitive strings embedded in the vector store.
    If they appear in output → retrieval is leaking data it shouldn't.
    """

    def __init__(self, cfg: OutputSanitizerConfig, pii_cfg: PIIConfig):
        self.cfg = cfg
        self.pii_cfg = pii_cfg
        self.analyzer  = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        logger.info(f"OutputSanitizer initialised | canary_count={len(cfg.canary_tokens)}")

    def sanitize(self, response: str, trace_id: str = "") -> OutputSanitizationArtifact:
        violations: List[Dict[str, Any]] = []
        safe_text = response

        # ── Step 1: Canary token check ────────────────────────────────
        canary_hits = [t for t in self.cfg.canary_tokens if t in response]
        if canary_hits:
            logger.critical(
                f"[{trace_id}] CANARY LEAK DETECTED: {canary_hits} — "
                "retrieval is exposing data beyond authorization boundaries"
            )
            violations.append({"type": "canary_leak", "tokens": canary_hits})
            # Redact canary tokens from response
            for token in canary_hits:
                safe_text = safe_text.replace(token, "[REDACTED]")

        # ── Step 2: Re-scan for PII in LLM output ─────────────────────
        if self.cfg.re_scrub_output:
            results = self.analyzer.analyze(
                text=safe_text,
                entities=self.pii_cfg.entities_to_detect,
                language="en",
                score_threshold=self.pii_cfg.confidence_threshold,
            )
            if results:
                operators = {
                    r.entity_type: OperatorConfig(
                        "replace", {"new_value": f"<{r.entity_type}>"}
                    )
                    for r in results
                }
                anonymized = self.anonymizer.anonymize(
                    text=safe_text, analyzer_results=results, operators=operators
                )
                pii_count = len(results)
                safe_text = anonymized.text

                logger.warning(
                    f"[{trace_id}] OUTPUT PII: {pii_count} entities redacted "
                    f"from LLM response"
                )
                violations.append({"type": "output_pii", "count": pii_count})
            else:
                pii_count = 0
        else:
            pii_count = 0

        return OutputSanitizationArtifact(
            original_response=response,
            safe_response=safe_text,
            pii_redacted=pii_count,
            canary_leaked=len(canary_hits) > 0,
            hallucination_detected=False,  # default for now
            canary_tokens_found=canary_hits,
            violations=violations,
        )