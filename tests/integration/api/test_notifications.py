import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime
from backend.app.main import app
from backend.app.auth.router import get_current_user
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

@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()

def test_get_notifications_empty(client: TestClient):
    response = client.get("/api/v1/notifications", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []

def test_get_unread_count(client: TestClient):
    response = client.get("/api/v1/notifications/unread-count", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    assert response.json()["unread_count"] == 0

def test_mark_all_read(client: TestClient):
    response = client.patch("/api/v1/notifications/read-all", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 200
    
def test_get_notification_not_found(client: TestClient):
    response = client.get(f"/api/v1/notifications/{uuid4()}", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 404

def test_mark_read_not_found(client: TestClient):
    response = client.patch(f"/api/v1/notifications/{uuid4()}/read", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 404

def test_delete_notification_not_found(client: TestClient):
    response = client.delete(f"/api/v1/notifications/{uuid4()}", headers={"X-API-Key": "test-dev-api-key"})
    assert response.status_code == 404
