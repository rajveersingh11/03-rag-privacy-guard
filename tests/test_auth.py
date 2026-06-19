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
    assert "api_key" not in res_data
    assert "aegis_session" in response.cookies
    
    # 2. Try to signup with the same username (should fail)
    response_dup = client.post("/auth/signup", json=signup_data)
    assert response_dup.status_code == 400
    assert "Username is already taken" in response_dup.json()["detail"]

    # 3. Log in with correct credentials
    login_data = {
        "username": "testadmin",
        "password": "securepassword123"
    }
    # Clear cookies first to simulate clean login
    client.cookies.clear()
    response_login = client.post("/auth/login", json=login_data)
    assert response_login.status_code == 200
    res_login = response_login.json()
    assert res_login["status"] == "success"
    assert res_login["username"] == "testadmin"
    assert res_login["role"] == "admin"
    assert "api_key" not in res_login
    assert "aegis_session" in response_login.cookies

    # 4. Access /auth/me with the session cookie
    response_me = client.get("/auth/me")
    assert response_me.status_code == 200
    res_me = response_me.json()
    assert res_me["username"] == "testadmin"
    assert res_me["role"] == "admin"
    assert res_me["tenant_id"] == "default"

    # 5. Log in with incorrect credentials
    bad_login_data = {
        "username": "testadmin",
        "password": "wrongpassword"
    }
    client.cookies.clear()
    response_bad = client.post("/auth/login", json=bad_login_data)
    assert response_bad.status_code == 401
    assert "Invalid username or password" in response_bad.json()["detail"]
    assert "aegis_session" not in response_bad.cookies

    # 6. Logout and verify session revocation
    session_token = response_login.cookies.get("aegis_session")
    csrf_token = response_login.cookies.get("aegis_csrf")
    client.cookies.set("aegis_session", session_token)
    client.cookies.set("aegis_csrf", csrf_token)
    response_logout = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert response_logout.status_code == 204
    
    response_me_after = client.get("/auth/me")
    assert response_me_after.status_code == 401


def test_csrf_protection():
    client = TestClient(app)
    
    # 1. Sign up to establish a session and get a CSRF token
    signup_data = {
        "username": "csrfadmin",
        "password": "securepassword123"
    }
    response = client.post("/auth/signup", json=signup_data)
    assert response.status_code == 200
    assert "aegis_session" in response.cookies
    assert "aegis_csrf" in response.cookies
    
    session_cookie = response.cookies.get("aegis_session")
    csrf_cookie = response.cookies.get("aegis_csrf")
    
    # 2. Try to logout without CSRF header (should fail with 403)
    client.cookies.clear()
    client.cookies.set("aegis_session", session_cookie)
    client.cookies.set("aegis_csrf", csrf_cookie)
    
    response_fail_no_header = client.post("/auth/logout")
    assert response_fail_no_header.status_code == 403
    assert "CSRF token verification failed" in response_fail_no_header.json()["detail"]
    
    # 3. Try to logout with wrong CSRF header (should fail with 403)
    response_fail_wrong_header = client.post("/auth/logout", headers={"X-CSRF-Token": "badtoken"})
    assert response_fail_wrong_header.status_code == 403
    assert "CSRF token verification failed" in response_fail_wrong_header.json()["detail"]
    
    # 4. Logout with correct CSRF header (should succeed with 204)
    response_success = client.post("/auth/logout", headers={"X-CSRF-Token": csrf_cookie})
    assert response_success.status_code == 204

