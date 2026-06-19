import os
import pytest
from fastapi.testclient import TestClient

DB_FILE = "test_auth.db"

# Force SQLite database file for tests
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE}"

from aegisVault.app.main import app
from aegisVault.db import session

@pytest.fixture(autouse=True)
def setup_test_db():
    # Remove old DB file if it exists
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass
            
    # Reset the engine so it picks up the DB file
    session._engine = None
    session.SessionLocal = None
    session.init_db()
    yield
    
    # Clean up
    session._engine = None
    session.SessionLocal = None
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception:
            pass

def test_auth_signup_and_login():
    client = TestClient(app)
    
    # 1. Sign up a new user
    signup_data = {
        "username": "testadmin",
        "password": "securepassword123"
    }
    response = client.post("/auth/signup", json=signup_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["username"] == "testadmin"
    assert res_data["role"] == "admin"
    assert "api_key" in res_data
    
    # 2. Try to signup with the same username (should fail)
    response_dup = client.post("/auth/signup", json=signup_data)
    assert response_dup.status_code == 400
    assert "Username is already taken" in response_dup.json()["detail"]

    # 3. Log in with correct credentials
    login_data = {
        "username": "testadmin",
        "password": "securepassword123"
    }
    response_login = client.post("/auth/login", json=login_data)
    assert response_login.status_code == 200
    res_login = response_login.json()
    assert res_login["status"] == "success"
    assert res_login["username"] == "testadmin"
    assert res_login["role"] == "admin"
    assert "api_key" in res_login

    # 4. Log in with incorrect credentials
    bad_login_data = {
        "username": "testadmin",
        "password": "wrongpassword"
    }
    response_bad = client.post("/auth/login", json=bad_login_data)
    assert response_bad.status_code == 401
    assert "Invalid username or password" in response_bad.json()["detail"]
