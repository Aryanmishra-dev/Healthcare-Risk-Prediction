import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_current_tenant
from backend.app.auth.router import get_current_user
from backend.app.core.enums import UserRole
from backend.app.main import app
from backend.app.models.user import User


def mock_get_current_user():
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        role=UserRole.SUPER_ADMIN,
    )


MOCK_TENANT_ID = uuid.uuid4()


def mock_get_current_tenant():
    return MOCK_TENANT_ID


@pytest.fixture(autouse=True)
def override_auth_dependencies(monkeypatch):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_tenant] = mock_get_current_tenant

    from backend.app.services.authorization_service import AuthorizationService

    monkeypatch.setattr(AuthorizationService, "can", lambda *args, **kwargs: True)

    import sys

    auth_module = sys.modules.get("backend.app.auth.router")
    if not auth_module:
        import backend.app.auth.router  # noqa: F401

        auth_module = sys.modules["backend.app.auth.router"]

    async def mock_bearer(*args, **kwargs):
        from fastapi.security import HTTPAuthorizationCredentials

        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="dummy_token")

    monkeypatch.setattr(auth_module, "bearer", mock_bearer)

    async def mock_gcu(*args, **kwargs):
        return mock_get_current_user()

    monkeypatch.setattr(auth_module, "get_current_user", mock_gcu)

    yield
    app.dependency_overrides.clear()


@pytest.fixture
def created_key(client: TestClient) -> tuple:
    resp = client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "scopes": ["predictions", "reports"]},
        headers={"X-API-Key": "test-dev-api-key"},
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["raw_key"], data["id"]


class TestApiKeyCreation:
    def test_create_api_key(self, client: TestClient):
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "My Key", "scopes": ["predictions", "reports"]},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Key"
        assert "raw_key" in data
        assert len(data["raw_key"]) == 40
        assert data["key_prefix"] == data["raw_key"][:8]
        assert data["is_active"] is True
        assert data["scopes"] == ["predictions", "reports"]

    def test_create_api_key_default_scope(self, client: TestClient):
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Default Scope"},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["scopes"] == ["read-only"]

    def test_create_api_key_with_expiry(self, client: TestClient):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        response = client.post(
            "/api/v1/api-keys",
            json={"name": "Expiring Key", "expires_at": future},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["expires_at"] is not None

    def test_plaintext_key_only_returned_once(self, client: TestClient):
        client.post(
            "/api/v1/api-keys",
            json={"name": "One Time Key"},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        list_resp = client.get(
            "/api/v1/api-keys", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert list_resp.status_code == 200
        for k in list_resp.json():
            assert "raw_key" not in k, "raw_key leaked in list response"


class TestApiKeyRotation:
    def test_rotate_api_key(self, client: TestClient, created_key):
        old_raw, key_id = created_key

        rotate_resp = client.post(
            f"/api/v1/api-keys/{key_id}/rotate",
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert rotate_resp.status_code == 201
        new_data = rotate_resp.json()
        assert new_data["id"] != key_id
        assert "raw_key" in new_data
        assert new_data["raw_key"] != old_raw
        assert new_data["is_active"] is True
        assert new_data["name"] == "Test Key"
        assert new_data["scopes"] == ["predictions", "reports"]

    def test_rotated_key_is_revoked(self, client: TestClient, created_key):
        old_raw, key_id = created_key

        client.post(
            f"/api/v1/api-keys/{key_id}/rotate",
            headers={"X-API-Key": "test-dev-api-key"},
        )

        detail_resp = client.get(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["is_active"] is False

    def test_rotate_nonexistent_key_returns_404(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/api-keys/{fake_id}/rotate",
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert resp.status_code == 404


class TestApiKeyRevocation:
    def test_revoke_api_key(self, client: TestClient, created_key):
        _, key_id = created_key

        del_resp = client.delete(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert del_resp.status_code == 204

        get_resp = client.get(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert get_resp.json()["is_active"] is False

    def test_revoked_key_cannot_authenticate(self, client: TestClient, created_key):
        raw_key, key_id = created_key

        client.delete(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )

        auth_resp = client.get("/api/v1/", headers={"X-API-Key": raw_key})
        assert auth_resp.status_code == 401

    def test_revoke_nonexistent_key_returns_404(self, client: TestClient):
        fake_id = str(uuid.uuid4())
        resp = client.delete(
            f"/api/v1/api-keys/{fake_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert resp.status_code == 404


class TestScopeEnforcement:
    def test_key_created_with_scopes(self, client: TestClient):
        resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Scoped Key", "scopes": ["predictions", "models"]},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        data = resp.json()
        assert data["scopes"] == ["predictions", "models"]

    def test_admin_scope_grants_all(self, client: TestClient):
        resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Admin Key", "scopes": ["admin"]},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        data = resp.json()
        assert data["scopes"] == ["admin"]


class TestTenantIsolation:
    def _create_key_for_tenant(self, client, tenant_id, name="Isolated Key"):
        from backend.app.api.dependencies import get_current_tenant

        def mock_tenant_b():
            return tenant_id

        app.dependency_overrides[get_current_tenant] = mock_tenant_b
        try:
            resp = client.post(
                "/api/v1/api-keys",
                json={"name": name},
                headers={"X-API-Key": "test-dev-api-key"},
            )
            return resp
        finally:
            app.dependency_overrides[get_current_tenant] = mock_get_current_tenant

    def test_keys_from_different_tenants_are_isolated(self, client: TestClient):
        tenant_a = MOCK_TENANT_ID
        tenant_b = uuid.uuid4()

        resp_a1 = self._create_key_for_tenant(client, tenant_a, "Tenant A Key")
        assert resp_a1.status_code == 201

        resp_b1 = self._create_key_for_tenant(client, tenant_b, "Tenant B Key")
        assert resp_b1.status_code == 201

        def mock_tenant_a():
            return tenant_a

        app.dependency_overrides[get_current_tenant] = mock_tenant_a
        list_a = client.get(
            "/api/v1/api-keys", headers={"X-API-Key": "test-dev-api-key"}
        )
        app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
        names_a = [k["name"] for k in list_a.json()]
        assert "Tenant A Key" in names_a
        assert "Tenant B Key" not in names_a

    def test_tenant_a_cannot_revoke_tenant_b_key(self, client: TestClient):
        tenant_b = uuid.uuid4()

        resp_b = self._create_key_for_tenant(client, tenant_b, "B's Key")
        key_b_id = resp_b.json()["id"]

        def mock_tenant_a():
            return MOCK_TENANT_ID

        app.dependency_overrides[get_current_tenant] = mock_tenant_a
        del_resp = client.delete(
            f"/api/v1/api-keys/{key_b_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
        assert del_resp.status_code == 404


class TestExpiredKeys:
    def test_expired_key_is_rejected(self, client: TestClient):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Expired Key", "expires_at": past},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert create_resp.status_code == 201
        raw_key = create_resp.json()["raw_key"]

        auth_resp = client.get("/api/v1/", headers={"X-API-Key": raw_key})
        assert auth_resp.status_code == 401

    def test_expired_key_shows_in_list(self, client: TestClient):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        create_resp = client.post(
            "/api/v1/api-keys",
            json={"name": "Expired Listed", "expires_at": past},
            headers={"X-API-Key": "test-dev-api-key"},
        )
        key_id = create_resp.json()["id"]

        get_resp = client.get(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["is_active"] is True


class TestInvalidSignatures:
    V1_PATH = "/api/v1/"

    def test_invalid_key_is_rejected(self, client: TestClient):
        response = client.get(
            self.V1_PATH, headers={"X-API-Key": "invalid_key_value_here"}
        )
        assert response.status_code == 401

    def test_tampered_key_is_rejected(self, client: TestClient, created_key):
        raw_key, _ = created_key
        tampered = raw_key[:-1] + ("X" if raw_key[-1] != "X" else "Y")
        assert tampered != raw_key

        response = client.get(self.V1_PATH, headers={"X-API-Key": tampered})
        assert response.status_code == 401

    def test_empty_key_is_rejected(self, client: TestClient):
        response = client.get(self.V1_PATH, headers={"X-API-Key": ""})
        assert response.status_code == 401

    def test_missing_key_header_is_rejected(self, client: TestClient):
        response = client.get(self.V1_PATH)
        assert response.status_code == 401


class TestApiKeyListing:
    def test_list_keys(self, client: TestClient, created_key):
        _, key_id = created_key
        response = client.get(
            "/api/v1/api-keys", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(k["id"] == key_id for k in data)
        assert not any("raw_key" in k for k in data)

    def test_get_single_key(self, client: TestClient, created_key):
        _, key_id = created_key
        resp = client.get(
            f"/api/v1/api-keys/{key_id}", headers={"X-API-Key": "test-dev-api-key"}
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == key_id

    def test_get_nonexistent_key_returns_404(self, client: TestClient):
        resp = client.get(
            f"/api/v1/api-keys/{uuid.uuid4()}",
            headers={"X-API-Key": "test-dev-api-key"},
        )
        assert resp.status_code == 404


class TestKeyAuthentication:
    def test_dev_api_key_authenticates(self, client: TestClient):
        response = client.get("/api/v1/", headers={"X-API-Key": "test-dev-api-key"})
        assert response.status_code == 200
