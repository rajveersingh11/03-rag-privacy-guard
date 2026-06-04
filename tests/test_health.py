import pytest
from fastapi.testclient import TestClient
from aegisVault.app.main import app

client = TestClient(app)

def test_health_endpoints(monkeypatch):
    # Mock backing database and Redis check to fail
    from aegisVault.db import session
    import redis

    monkeypatch.setattr(session, "health_check", lambda: False)

    class MockedRedis:
        @classmethod
        def from_url(cls, *args, **kwargs):
            return cls()
        def ping(self):
            raise Exception("Connection Refused")
            
    monkeypatch.setattr(redis, "Redis", MockedRedis)

    # Live is always 200
    res = client.get("/live")
    assert res.status_code == 200
    
    # Degraded health when mock backing services are failing
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "degraded"
    
    res = client.get("/ready")
    assert res.status_code == 503
