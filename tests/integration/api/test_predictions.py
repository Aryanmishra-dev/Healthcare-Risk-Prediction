import uuid as _uuid
from datetime import datetime

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_current_tenant
from backend.app.auth.router import get_current_user
from backend.app.main import app
from backend.app.models.user import User


MOCK_TENANT_ID = _uuid.uuid4()
MOCK_USER_ID = _uuid.uuid4()


def mock_get_current_user(request: Request):
    user = User(
        id=MOCK_USER_ID,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )
    request.state.user = user
    return user


async def mock_get_current_tenant(request: Request) -> _uuid.UUID:
    return MOCK_TENANT_ID


@pytest.fixture(autouse=True)
def override_dependency():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
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
