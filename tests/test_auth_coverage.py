import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"User-Agent": "HealthPredictTest/1.0"},
    ) as ac:
        yield ac


async def register_user(
    client,
    email="coverage_test@example.com",
    password="Secure123!",
    name="Coverage Tester",
):
    return await client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": name},
    )


async def login_user(
    client, email="coverage_test@example.com", password="Secure123!"
):
    return await client.post(
        "/auth/login", json={"email": email, "password": password}
    )


async def get_token(client):
    await register_user(client)
    resp = await login_user(client)
    if resp.status_code == 200:
        return resp.json()["access_token"]
    return None


class TestHttpOnlyCookies:
    async def test_login_sets_httponly_cookies(self, client):
        await register_user(client)
        resp = await login_user(client)
        assert resp.status_code == 200
        cookies = resp.cookies
        assert "access_token" in cookies
        assert "refresh_token" in cookies

    async def test_access_me_via_cookie(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.get("/auth/me", cookies={"access_token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert data["email"] == "coverage_test@example.com"

    async def test_access_me_via_bearer_fallback(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    async def test_logout_clears_cookies(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.request(
            "POST",
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie

    async def test_refresh_missing_token_returns_401(self, client):
        resp = await client.post("/auth/refresh")
        assert resp.status_code == 401


class TestStatsAndHistory:
    async def test_stats_authenticated(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.get(
            "/auth/stats", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_uploads" in data
        assert "total_predictions" in data
        assert "risk_breakdown" in data
        assert isinstance(data["total_uploads"], int)
        assert isinstance(data["total_predictions"], int)

    async def test_delete_history_entry_not_found(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.delete(
            "/auth/history/999999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_delete_history_entry_invalid_auth(self, client):
        resp = await client.delete("/auth/history/1")
        assert resp.status_code in (401, 403)

    async def test_history_authenticated(self, client):
        token = await get_token(client)
        if token is None:
            pytest.skip("Could not obtain token")
        resp = await client.get(
            "/auth/history", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestPasswordReset:
    async def test_password_reset_request_valid_email(self, client):
        await register_user(client)
        resp = await client.post(
            "/auth/password-reset-request",
            json={"email": "coverage_test@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    async def test_password_reset_request_unknown_email(self, client):
        resp = await client.post(
            "/auth/password-reset-request",
            json={"email": "unknown@example.com"},
        )
        assert resp.status_code == 200

    async def test_password_reset_confirm_invalid_token(self, client):
        resp = await client.post(
            "/auth/password-reset-confirm",
            json={"token": "invalid-token", "new_password": "NewSecure123!"},
        )
        assert resp.status_code == 400


class TestSessionManagement:
    async def test_sessions_unauthenticated(self, client):
        resp = await client.get("/auth/sessions")
        assert resp.status_code in (401, 403)


class TestHealthCheck:
    async def test_healthz(self, client):
        resp = await client.get("/healthz")
        assert resp.status_code == 200

    async def test_healthz_returns_healthy_status(self, client):
        resp = await client.get("/healthz")
        data = resp.json()
        assert data.get("status") == "healthy"


class TestBotProtectionExtended:
    async def test_bot_user_agent_wget(self, client):
        resp = await client.post(
            "/auth/login",
            json={"email": "bot@test.com", "password": "pass"},
            headers={"User-Agent": "Wget/1.21"},
        )
        assert resp.status_code == 403

    async def test_normal_user_agent_not_blocked(self, client):
        resp = await client.post(
            "/auth/login",
            json={"email": "real@test.com", "password": "Secure123!"},
            headers={"User-Agent": "Mozilla/5.0 Chrome/120.0"},
        )
        assert resp.status_code != 403
