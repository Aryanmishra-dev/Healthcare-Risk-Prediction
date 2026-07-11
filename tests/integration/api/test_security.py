import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime
from backend.app.main import app
from backend.app.auth.router import get_current_user, get_current_session_id
from backend.app.models.user import User

def mock_get_current_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow()
    )

def mock_get_current_session_id():
    return uuid4()

@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_session_id] = mock_get_current_session_id
    yield
    app.dependency_overrides.clear()

def test_get_sessions_empty(client: TestClient):
    response = client.get("/api/v1/security/sessions", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []

def test_get_login_history_empty(client: TestClient):
    response = client.get("/api/v1/security/login-history", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

def test_get_security_events_empty(client: TestClient):
    response = client.get("/api/v1/security/events", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0

def test_get_devices_empty(client: TestClient):
    response = client.get("/api/v1/security/devices", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    assert response.json() == []

def test_delete_session_not_found(client: TestClient):
    response = client.delete(f"/api/v1/security/sessions/{uuid4()}", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 404

def test_delete_all_sessions(client: TestClient):
    response = client.delete("/api/v1/security/sessions", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 204
