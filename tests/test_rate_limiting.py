import pytest
from fastapi.testclient import TestClient
from aegisVault.app.main import app

client = TestClient(app)

def test_rate_limit_query_endpoint(monkeypatch):
    # Bypass auth and pipeline logic to just test rate limit
    monkeypatch.setenv("API_KEYS", "test-key")
    monkeypatch.setenv("API_KEY", "test-key")
    
    from aegisVault.app.deps import init_api_keys
    init_api_keys()
    
    from unittest.mock import MagicMock
    mock_pipeline = MagicMock()
    mock_pipeline.query.return_value = MagicMock(
        trace_id="test", safe_response="ok", chunks_used=0, rbac_blocked=0, pii_redacted=0, canary_leaked=False, latency_ms=0
    )
    app.state.inference_pipeline = mock_pipeline
    
    headers = {"X-API-Key": "test-key"}
    body = {
        "query": "Hello",
        "user_id": "u1",
        "user_roles": ["employee"],
        "tenant_id": "default"
    }

    # Hit the endpoint multiple times to trigger rate limit (60/min)
    # Fast approach: we could lower the limit in tests, but testing 61 requests is okay for a unit test
    # Actually, let's just make 61 requests using TestClient
    responses = []
    for _ in range(61):
        responses.append(client.post("/query", json=body, headers=headers))
        
    # At least one should be 429
    assert any(r.status_code == 429 for r in responses)
