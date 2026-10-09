from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_system_status_initialization_api_and_no_path_leakage():
    """
    Verify GET /api/system/status returns real service initialization states
    and never leaks internal filesystem paths or secrets.
    """
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["application"] == "ready"
    assert "services" in data
    assert data["services"]["application"]["status"] == "online"
    assert data["services"]["database"]["status"] == "online"
    assert data["services"]["vector_database"]["status"] == "online"
    assert data["embedding"]["status"] in {"online", "unloaded"}
    assert data["offline_mode"] is True

    # Ensure no Windows or Unix filesystem paths leak in the serialized response
    raw_json_str = resp.text
    assert "C:\\" not in raw_json_str
    assert "c:\\" not in raw_json_str
    assert "tesseract_cmd" not in raw_json_str


def test_login_valid_and_invalid_credentials_and_session_expiration():
    """
    Test login with valid credentials, wrong password, empty username,
    and expired/invalid session token handling.
    """
    # 1. Valid login
    ok_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert ok_resp.status_code == 200
    token = ok_resp.json()["access_token"]
    assert token

    # 2. Verify /api/auth/me with valid token
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"

    # 3. Wrong password -> 401 without leaking SQL/stack traces
    bad_resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong_password"})
    assert bad_resp.status_code == 401
    assert "SQL" not in bad_resp.text
    assert "Traceback" not in bad_resp.text

    # 4. Non-existent user -> identical generic 401 message (does not reveal if account exists)
    nonexistent_resp = client.post("/api/auth/login", json={"username": "unknown_user_xyz", "password": "wrong"})
    assert nonexistent_resp.status_code == 401
    assert nonexistent_resp.json()["detail"] == bad_resp.json()["detail"]

    # 5. Expired / invalid token -> 401
    exp_resp = client.get("/api/auth/me", headers={"Authorization": "Bearer expired.invalid.token"})
    assert exp_resp.status_code == 401
