"""
Ingestion Scrubber — Layer 1
-----------------------------
Uses Microsoft Presidio (enterprise-grade NER) to detect and
redact PII from raw document text BEFORE it is chunked and embedded.

Also runs a secret scanner for API keys, tokens, and credentials.
Documents with critical PII or secrets are quarantined, not embedded.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from aegisVault.entity.artifact_entity import PIIScanArtifact
from aegisVault.entity.config_entity import PIIConfig
from aegisVault.constants import PII_SEVERITY
from aegisVault.utils.common import get_logger, ensure_dir, hash_text

logger = get_logger(__name__)

# ── Secret patterns (run alongside Presidio) ─────────────────────────
SECRET_PATTERNS = {
    "openai_key":       re.compile(r'sk-[A-Za-z0-9]{48}'),
    "aws_key":          re.compile(r'(?:AKIA|AGPA|AIDA|AROA)[A-Z0-9]{16}'),
    "github_token":     re.compile(r'ghp_[A-Za-z0-9]{36}'),
    "jwt":              re.compile(r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'),
    "private_key":      re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'),
    "connection_string":re.compile(r'(?:mongodb|postgresql|mysql|redis):\/\/[^\s]+'),
    "password_field":   re.compile(r'(?:password|passwd|pwd)["\s:=]+[^\s"\']{8,}', re.I),
}


class IngestionScrubber:
    """
    Presidio-based PII scrubber for document ingestion.
    All PII is replaced with typed placeholders: <PERSON>, <EMAIL_ADDRESS>, etc.
    Secrets trigger quarantine regardless of policy settings.
    """

    def __init__(self, cfg: PIIConfig, quarantine_dir: str = "./data/quarantine"):
        self.cfg = cfg
        self.quarantine_dir = ensure_dir(quarantine_dir)
        self.analyzer  = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        logger.info("IngestionScrubber initialised with Presidio")

    # ── Public entry point ─────────────────────────────────────────────

    def scrub(self, text: str, doc_id: Optional[str] = None) -> PIIScanArtifact:
        doc_id = doc_id or hash_text(text)

        # Step 1: Secret scan (always blocks)
        secret_hits = self._scan_secrets(text)
        if secret_hits:
            logger.warning(f"[{doc_id}] SECRETS DETECTED: {[h['type'] for h in secret_hits]}")
            self._quarantine(text, doc_id, "secrets_detected")
            # Return with status embedded in sensitivity
            return PIIScanArtifact(
                original_text=text,
                scrubbed_text="[DOCUMENT QUARANTINED — SECRETS DETECTED]",
                entities_found=secret_hits,
                has_critical=True,
                sensitivity_class="TOP_SECRET",
                was_modified=True,
            )

        # Step 2: PII detection via Presidio
        results: List[RecognizerResult] = self.analyzer.analyze(
            text=text,
            entities=self.cfg.entities_to_detect,
            language="en",
            score_threshold=self.cfg.confidence_threshold,
        )

        if not results:
            return PIIScanArtifact(
                original_text=text, scrubbed_text=text,
                entities_found=[], has_critical=False,
                sensitivity_class="PUBLIC", was_modified=False,
            )

        # Step 3: Classify severity
        entities_found = [
            {
                "entity_type": r.entity_type,
                "start": r.start, "end": r.end,
                "score": round(r.score, 4),
                "severity": PII_SEVERITY.get(r.entity_type, "medium"),
            }
            for r in results
        ]
        has_critical = any(e["severity"] == "critical" for e in entities_found)

        # Step 4: Apply policy for critical PII
        if has_critical and self.cfg.on_critical == "quarantine":
            logger.warning(f"[{doc_id}] CRITICAL PII — quarantining")
            self._quarantine(text, doc_id, "critical_pii")
            return PIIScanArtifact(
                original_text=text,
                scrubbed_text="[DOCUMENT QUARANTINED — CRITICAL PII]",
                entities_found=entities_found,
                has_critical=True,
                sensitivity_class="RESTRICTED",
                was_modified=True,
            )

        # Step 5: Anonymize (replace PII with placeholders)
        operators = {
            e["entity_type"]: OperatorConfig("replace", {"new_value": f"<{e['entity_type']}>"})
            for e in entities_found
        }
        anonymized = self.anonymizer.anonymize(
            text=text, analyzer_results=results, operators=operators
        )
        scrubbed = anonymized.text

        sensitivity = self._classify(entities_found)
        logger.info(f"[{doc_id}] Scrubbed {len(entities_found)} entities | class={sensitivity}")

        return PIIScanArtifact(
            original_text=text,
            scrubbed_text=scrubbed,
            entities_found=entities_found,
            has_critical=has_critical,
            sensitivity_class=sensitivity,
            was_modified=scrubbed != text,
        )

    # ── Secret scanning ────────────────────────────────────────────────

    def _scan_secrets(self, text: str) -> List[Dict]:
        hits = []
        for name, pattern in SECRET_PATTERNS.items():
            for m in pattern.finditer(text):
                hits.append({
                    "type":     name,
                    "preview":  m.group()[:6] + "***",
                    "start":    m.start(),
                    "end":      m.end(),
                    "severity": "critical",
                })
        return hits

    # ── Quarantine ─────────────────────────────────────────────────────

    def _quarantine(self, text: str, doc_id: str, reason: str):
        path = self.quarantine_dir / f"{doc_id}_{reason}.txt"
        with open(path, "w") as f:
            f.write(f"REASON: {reason}\nDOC_ID: {doc_id}\n---\n{text}")
        logger.info(f"Quarantined → {path}")

    # ── Sensitivity classification ─────────────────────────────────────

    def _classify(self, entities: List[Dict]) -> str:
        if any(e["severity"] == "critical" for e in entities):
            return "RESTRICTED"
        if any(e["severity"] == "high" for e in entities):
            return "CONFIDENTIAL"
        if any(e["severity"] == "medium" for e in entities):
            return "INTERNAL"
        return "INTERNAL"