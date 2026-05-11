import pytest
import os
from aegisVault.guards.ingestion_scrubber import IngestionScrubber
from aegisVault.entity.config_entity import PIIConfig

@pytest.fixture
def scrubber_config():
    return PIIConfig(
        confidence_threshold=0.7,
        on_critical="quarantine",
        on_high="redact",
        on_medium="redact",
        on_low="tag",
        entities_to_detect=["PERSON", "EMAIL_ADDRESS"],
        compliance_mode="none"
    )

def test_secret_scanner_quarantines(scrubber_config, tmp_path, monkeypatch):
    monkeypatch.setenv("QUARANTINE_ENCRYPTION_KEY", "gE4rQjW9H0yRzTqP4sD9NqgN4Q9XhK3yNfG6fH4fQkM=")
    scrubber = IngestionScrubber(scrubber_config, str(tmp_path))
    
    text_with_secret = "Here is my key: sk-123456789012345678901234567890123456789012345678"
    result = scrubber.scrub(text_with_secret)
    
    assert result.has_critical is True
    assert result.sensitivity_class == "TOP_SECRET"
    assert "QUARANTINED" in result.scrubbed_text
    
def test_missing_encryption_key_quarantine_fallback(scrubber_config, tmp_path, monkeypatch):
    # Ensure key is missing
    monkeypatch.delenv("QUARANTINE_ENCRYPTION_KEY", raising=False)
    scrubber = IngestionScrubber(scrubber_config, str(tmp_path))
    
    text_with_secret = "My aws key is AKIA1234567890123456"
    scrubber.scrub(text_with_secret, doc_id="test_doc")
    
    meta_file = tmp_path / "test_doc_secrets_detected.meta.json"
    assert meta_file.exists()
