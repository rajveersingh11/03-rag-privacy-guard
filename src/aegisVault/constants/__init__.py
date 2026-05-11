"""AegisVault — Project-wide constants."""

from pathlib import Path

# ── Root paths ────────────────────────────────────────────
ROOT_DIR          = Path(__file__).parent.parent.parent.parent
CONFIG_FILE_PATH  = ROOT_DIR / "config" / "config.yaml"
PARAMS_FILE_PATH  = ROOT_DIR / "params.yaml"

# ── Sensitivity levels (ordered low → high) ───────────────
SENSITIVITY_LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "TOP_SECRET"]

# ── Role → clearance mapping ───────────────────────────────
ROLE_CLEARANCE = {
    "anonymous":  "PUBLIC",
    "employee":   "INTERNAL",
    "manager":    "CONFIDENTIAL",
    "executive":  "RESTRICTED",
    "admin":      "TOP_SECRET",
}

# ── PII severity mapping ───────────────────────────────────
PII_SEVERITY = {
    "PERSON":           "medium",
    "EMAIL_ADDRESS":    "high",
    "PHONE_NUMBER":     "high",
    "CREDIT_CARD":      "critical",
    "US_SSN":           "critical",
    "US_PASSPORT":      "critical",
    "IN_PAN":           "critical",
    "IN_AADHAAR":       "critical",
    "MEDICAL_LICENSE":  "critical",
    "IP_ADDRESS":       "medium",
    "URL":              "low",
    "IBAN_CODE":        "critical",
    "CRYPTO":           "high",
}

GDPR_RELEVANT_ENTITIES = [
    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
    "IP_ADDRESS", "LOCATION", "DATE_TIME", "IBAN_CODE"
]

HIPAA_RELEVANT_ENTITIES = [
    "PERSON", "MEDICAL_LICENSE", "US_SSN", "PHONE_NUMBER",
    "EMAIL_ADDRESS", "LOCATION", "DATE_TIME", "US_DRIVER_LICENSE"
]

# ── Injection intent categories ────────────────────────────
INJECTION_CATEGORIES = [
    "prompt_injection",
    "jailbreak",
    "data_exfiltration",
    "pii_harvesting",
]