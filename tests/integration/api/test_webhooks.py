import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.tenant import Membership, Tenant
from backend.app.models.user import User
from tests.conftest import TestingSessionLocal

TEST_USER_ID = uuid4()
TEST_TENANT_ID = uuid4()


def mock_get_current_user():
    return User(
        id=TEST_USER_ID,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
    )


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_tenant():
    async def _setup():
        async with TestingSessionLocal() as db:
            existing = await db.execute(
                select(Tenant).where(Tenant.id == TEST_TENANT_ID)
            )
            if not existing.scalar_one_or_none():
                tenant = Tenant(
                    id=TEST_TENANT_ID,
                    name="Test Tenant",
                    slug=f"test-tenant-{TEST_TENANT_ID}",
                    is_active=True,
                )
                db.add(tenant)
                membership = Membership(
                    tenant_id=TEST_TENANT_ID,
                    user_id=TEST_USER_ID,
                    org_role="MEMBER",
                )
                db.add(membership)
                await db.commit()

    asyncio.run(_setup())
    yield


def test_list_webhooks_empty(client: TestClient):
    response = client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_create_webhook(client: TestClient):
    payload = {
        "url": "https://example.com/webhook",
        "events": ["prediction.completed", "report.ready"],
        "description": "Test webhook",
    }
    response = client.post(
        "/api/v1/webhooks",
        json=payload,
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == payload["url"]
    assert data["events"] == payload["events"]
    assert data["description"] == payload["description"]
    assert data["is_active"] is True
    assert data["retry_count"] == 3
    assert "id" in data
    assert "secret" not in data

    list_resp = client.get(
        "/api/v1/webhooks",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1


def test_get_webhook(client: TestClient):
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["prediction.completed"],
        },
        headers={"X-API-Key": "test-dev-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == webhook_id


def test_get_webhook_not_found(client: TestClient):
    response = client.get(
        f"/api/v1/webhooks/{uuid4()}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_update_webhook(client: TestClient):
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["prediction.completed"],
        },
        headers={"X-API-Key": "test-dev-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    response = client.patch(
        f"/api/v1/webhooks/{webhook_id}",
        json={"url": "https://updated.com/hook", "is_active": False},
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://updated.com/hook"
    assert data["is_active"] is False


def test_update_webhook_not_found(client: TestClient):
    response = client.patch(
        f"/api/v1/webhooks/{uuid4()}",
        json={"url": "https://test.com"},
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_delete_webhook(client: TestClient):
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["prediction.completed"],
        },
        headers={"X-API-Key": "test-dev-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 204

    get_resp = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert get_resp.status_code == 404


def test_delete_webhook_not_found(client: TestClient):
    response = client.delete(
        f"/api/v1/webhooks/{uuid4()}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_rotate_secret(client: TestClient):
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["prediction.completed"],
        },
        headers={"X-API-Key": "test-dev-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    response = client.post(
        f"/api/v1/webhooks/{webhook_id}/rotate-secret",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    assert "secret" in response.json()
    assert len(response.json()["secret"]) == 64


def test_rotate_secret_not_found(client: TestClient):
    response = client.post(
        f"/api/v1/webhooks/{uuid4()}/rotate-secret",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_list_webhook_events_empty(client: TestClient):
    create_resp = client.post(
        "/api/v1/webhooks",
        json={
            "url": "https://example.com/hook",
            "events": ["prediction.completed"],
        },
        headers={"X-API-Key": "test-dev-api-key"},
    )
    webhook_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/webhooks/{webhook_id}/events",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
