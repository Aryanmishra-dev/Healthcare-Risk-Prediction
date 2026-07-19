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


def test_get_history_empty(client: TestClient):
    response = client.get(
        "/api/v1/predictions/history",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


# Since we don't have predictions in the mock DB for this user, we will just test the mock DB works.
def test_favorite_prediction_not_found(client: TestClient):
    response = client.post(
        "/api/v1/predictions/999/favorite",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_delete_prediction_not_found(client: TestClient):
    response = client.delete(
        "/api/v1/predictions/999", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 404


def test_get_prediction_not_found(client: TestClient):
    response = client.get(
        "/api/v1/predictions/99999", headers={"X-API-Key": "test-dev-api-key"}
    )
    assert response.status_code == 404


def test_explanation_not_found(client: TestClient):
    response = client.get(
        "/api/v1/predictions/99999/explanation",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_unfavorite_prediction_not_found(client: TestClient):
    response = client.delete(
        "/api/v1/predictions/999/favorite",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404
