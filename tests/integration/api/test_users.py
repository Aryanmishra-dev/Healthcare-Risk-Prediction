from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.router import get_current_user
from backend.app.main import app
from backend.app.models.user import User


def mock_get_current_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )


@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


def test_get_dashboard(client: TestClient):
    response = client.get(
        "/api/v1/users/dashboard", headers={"X-API-Key": "test-dev-api-key"}
    )
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "total_predictions" in data


def test_get_profile(client: TestClient):
    response = client.get(
        "/api/v1/users/profile", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 200
    assert "timezone" in response.json()


def test_update_profile(client: TestClient):
    response = client.patch(
        "/api/v1/users/profile",
        headers={"X-API-Key": "test-dev-api-key"},
        json={"timezone": "PST", "full_name": "Test Name"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "PST"
    assert data["full_name"] == "Test Name"


def test_get_settings(client: TestClient):
    response = client.get(
        "/api/v1/users/settings", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 200


def test_update_settings(client: TestClient):
    response = client.patch(
        "/api/v1/users/settings",
        headers={"X-API-Key": "test-dev-api-key"},
        json={"theme": "dark"},
    )
    assert response.status_code == 200
    assert response.json()["theme"] == "dark"


def test_get_account(client: TestClient):
    response = client.get(
        "/api/v1/users/account", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 200
    assert "active_sessions_count" in response.json()


def test_get_statistics(client: TestClient):
    response = client.get(
        "/api/v1/users/statistics", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 200
    assert "predictions_by_model" in response.json()
