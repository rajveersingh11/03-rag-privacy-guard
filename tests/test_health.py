import pytest
from fastapi.testclient import TestClient
from aegisVault.app.main import app

client = TestClient(app)

def test_health_endpoints(monkeypatch):
    # Live is always 200
    res = client.get("/live")
    assert res.status_code == 200
    
    # Degraded health without real redis/db
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "degraded"
    
    res = client.get("/ready")
    assert res.status_code == 503
