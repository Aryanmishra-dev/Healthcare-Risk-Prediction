import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import Request as StarletteRequest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.dependencies import RequireRole
from backend.app.auth.router import get_current_user
from backend.app.main import app
from backend.app.models.tenant import Membership, Tenant
from backend.app.models.user import User
from tests.conftest import TestingSessionLocal

TEST_USER_ID = uuid4()
TEST_TENANT_ID = uuid4()
MOCK_USER = User(
    id=TEST_USER_ID,
    email="admin@test.com",
    full_name="Admin User",
    is_active=True,
    is_verified=True,
    role="admin",
    created_at=datetime.utcnow(),
)


def mock_get_current_user():
    return MOCK_USER


_original_require_role_call = RequireRole.__call__


@pytest.fixture(autouse=True)
def override_dependencies():
    app.dependency_overrides[get_current_user] = mock_get_current_user

    def _mock_require_role(self, request: StarletteRequest):
        request.state.user = MOCK_USER
        return MOCK_USER

    RequireRole.__call__ = _mock_require_role

    yield
    app.dependency_overrides.clear()
    RequireRole.__call__ = _original_require_role_call


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
                    org_role="ADMIN",
                )
                db.add(membership)
                await db.commit()

    asyncio.run(_setup())
    yield


def test_list_audit_events_empty(client: TestClient):
    response = client.get(
        "/api/v1/audit",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_audit_events_with_filters(client: TestClient):
    response = client.get(
        "/api/v1/audit?action=webhook.created&severity=info",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200


def test_get_stats(client: TestClient):
    response = client.get(
        "/api/v1/audit/stats?days=30",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 0
    assert data["date_range_days"] == 30


def test_get_stats_invalid_days(client: TestClient):
    response = client.get(
        "/api/v1/audit/stats?days=0",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 422


def test_export_csv(client: TestClient):
    response = client.get(
        "/api/v1/audit/export",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "id,timestamp,tenant_id" in response.text


def test_get_event_not_found(client: TestClient):
    response = client.get(
        f"/api/v1/audit/{uuid4()}",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 404


def test_retention_policies_empty(client: TestClient):
    response = client.get(
        "/api/v1/audit/retention/policies",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    assert response.json() == []


def test_set_retention_policy(client: TestClient):
    response = client.put(
        "/api/v1/audit/retention/policies",
        json={"action_pattern": "webhook.*", "retention_days": 90},
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action_pattern"] == "webhook.*"
    assert data["retention_days"] == 90
    assert "id" in data


def test_apply_retention(client: TestClient):
    response = client.post(
        "/api/v1/audit/retention/apply",
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_purged" in data
    assert "purged_by_pattern" in data
