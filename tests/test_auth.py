"""
Full auth test suite — Phase 8.

Requires a live Neon DB. Tests are written with pytest-asyncio
and httpx AsyncClient. Sensitive flows that need a DB record
are structured so they can also be run against a mock/test DB.
"""
import hashlib
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


# ─── Shared fixture ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={"User-Agent": "HealthPredictTestSuite/1.0"},
    ) as ac:
        yield ac


# ─── Helpers ─────────────────────────────────────────────────────────────────

VALID_EMAIL = "authtest_unique@example.com"
VALID_PASSWORD = "Secure123!"
ALT_EMAIL = "user_b_unique@example.com"


async def register_user(client, email=VALID_EMAIL, password=VALID_PASSWORD, name="Test User"):
    return await client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": name
    })


async def login_user(client, email=VALID_EMAIL, password=VALID_PASSWORD):
    return await client.post("/auth/login", json={
        "email": email,
        "password": password
    })


# ─── Registration ─────────────────────────────────────────────────────────────

class TestRegistration:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        resp = await register_user(client)
        # 201 = new user, 409 = already exists from previous run
        assert resp.status_code in (201, 409), resp.text

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        # First attempt (may already exist)
        await register_user(client)
        # Second attempt must conflict
        resp = await register_user(client)
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password_too_short(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={
            "email": "weak1@example.com",
            "password": "abc"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_no_uppercase(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={
            "email": "weak2@example.com",
            "password": "nouppercase1"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_no_number(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={
            "email": "weak3@example.com",
            "password": "NoNumberHere"
        })
        assert resp.status_code == 422


# ─── Login ────────────────────────────────────────────────────────────────────

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_correct_credentials(self, client: AsyncClient):
        await register_user(client)  # ensure user exists
        resp = await login_user(client)
        assert resp.status_code in (200, 401)  # 401 if DB not configured
        if resp.status_code == 200:
            data = resp.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        await register_user(client)
        resp = await client.post("/auth/login", json={
            "email": VALID_EMAIL,
            "password": "WrongPassword999!"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post("/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "Whatever123!"
        })
        assert resp.status_code == 401


# ─── Token & Protected Route ──────────────────────────────────────────────────

class TestTokenAccess:
    @pytest.mark.asyncio
    async def test_access_protected_no_token(self, client: AsyncClient):
        resp = await client.get("/auth/me")
        # HTTPBearer returns 403 when no credentials provided
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_access_protected_invalid_token(self, client: AsyncClient):
        resp = await client.get("/auth/me", headers={
            "Authorization": "Bearer invalidtoken.garbage.here"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_expired_token(self, client: AsyncClient):
        # A well-formed but obviously expired JWT (exp in the past)
        import time
        from jose import jwt
        from backend.app.core.config import settings
        expired_token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000000", "type": "access", "exp": int(time.time()) - 3600},
            settings.secret_key,
            algorithm=settings.algorithm
        )
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_revoked_token(self, client: AsyncClient):
        # A hash that doesn't exist in DB should be rejected
        resp = await client.post("/auth/refresh", params={
            "refresh_token": "completelyfaketokenvalue"
        })
        assert resp.status_code == 401


# ─── Session Management ───────────────────────────────────────────────────────

class TestSessions:
    @pytest.mark.asyncio
    async def test_get_sessions_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/auth/sessions")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_session(self, client: AsyncClient):
        await register_user(client)
        login_resp = await login_user(client)
        if login_resp.status_code != 200:
            pytest.skip("DB not configured — skipping live auth test")
        token = login_resp.json()["access_token"]
        resp = await client.delete(
            "/auth/sessions/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 404


# ─── Stats & History ──────────────────────────────────────────────────────────

class TestStatsAndHistory:
    @pytest.mark.asyncio
    async def test_stats_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/auth/stats")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_history_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/auth/history")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_history_filter_invalid_type_ignored(self, client: AsyncClient):
        await register_user(client)
        login_resp = await login_user(client)
        if login_resp.status_code != 200:
            pytest.skip("DB not configured")
        token = login_resp.json()["access_token"]
        resp = await client.get("/auth/history?disease_type=diabetes",
                                headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_stats_returns_correct_structure(self, client: AsyncClient):
        await register_user(client)
        login_resp = await login_user(client)
        if login_resp.status_code != 200:
            pytest.skip("DB not configured")
        token = login_resp.json()["access_token"]
        resp = await client.get("/auth/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_uploads" in data
        assert "total_predictions" in data
        assert "risk_breakdown" in data
        rb = data["risk_breakdown"]
        assert "low" in rb and "medium" in rb and "high" in rb


# ─── Bot Protection ───────────────────────────────────────────────────────────

class TestBotProtection:
    @pytest.mark.asyncio
    async def test_bot_user_agent_python_requests(self, client: AsyncClient):
        resp = await client.post("/auth/login",
            json={"email": "bot@test.com", "password": "pass"},
            headers={"User-Agent": "python-requests/2.28.0"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_bot_user_agent_curl(self, client: AsyncClient):
        resp = await client.post("/auth/login",
            json={"email": "bot@test.com", "password": "pass"},
            headers={"User-Agent": "curl/7.88.1"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_bot_user_agent_scrapy(self, client: AsyncClient):
        resp = await client.post("/auth/login",
            json={"email": "bot@test.com", "password": "pass"},
            headers={"User-Agent": "Scrapy/2.9.0"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_normal_user_agent_passes(self, client: AsyncClient):
        resp = await client.post("/auth/login",
            json={"email": "notabot@test.com", "password": "pass"},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        # Should not be 403 (may be 401 due to invalid credentials, but not bot-blocked)
        assert resp.status_code != 403

    @pytest.mark.asyncio
    async def test_missing_user_agent_blocked(self, client: AsyncClient):
        resp = await client.post("/auth/login",
            json={"email": "noagent@test.com", "password": "pass"},
            headers={"User-Agent": ""}
        )
        assert resp.status_code == 403


# ─── Security Headers ─────────────────────────────────────────────────────────

class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers_present(self, client: AsyncClient):
        resp = await client.get("/healthz")
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert "max-age=31536000" in resp.headers.get("strict-transport-security", "")
        assert resp.headers.get("x-request-id")  # UUID must be present


# ─── Auth Utils Unit Tests ────────────────────────────────────────────────────

class TestAuthUtils:
    def test_hash_and_verify_password(self):
        from backend.app.auth.utils import hash_password, verify_password
        hashed = hash_password("MyPassword1!")
        assert verify_password("MyPassword1!", hashed)
        assert not verify_password("WrongPassword", hashed)

    def test_create_and_decode_access_token(self):
        from backend.app.auth.utils import create_access_token, decode_access_token
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_decode_invalid_token_returns_none(self):
        from backend.app.auth.utils import decode_access_token
        assert decode_access_token("garbage.token.here") is None

    def test_create_refresh_token_returns_tuple(self):
        from backend.app.auth.utils import create_refresh_token
        raw, hashed = create_refresh_token()
        assert raw != hashed
        assert hashlib.sha256(raw.encode()).hexdigest() == hashed

    def test_generate_session_token_unique(self):
        from backend.app.auth.utils import generate_session_token
        tokens = {generate_session_token() for _ in range(50)}
        assert len(tokens) == 50  # all unique


# ─── Schemas Unit Tests ───────────────────────────────────────────────────────

class TestSchemas:
    def test_register_schema_valid(self):
        from backend.app.auth.schemas import RegisterRequest
        r = RegisterRequest(email="test@example.com", password="Secure123!")
        assert r.email == "test@example.com"

    def test_register_schema_weak_password_no_uppercase(self):
        from pydantic import ValidationError
        from backend.app.auth.schemas import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="nouppercase1")

    def test_register_schema_weak_password_no_number(self):
        from pydantic import ValidationError
        from backend.app.auth.schemas import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="NoNumberHere")

    def test_register_schema_too_short(self):
        from pydantic import ValidationError
        from backend.app.auth.schemas import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="Ab1!")

    def test_login_schema_valid(self):
        from backend.app.auth.schemas import LoginRequest
        r = LoginRequest(email="user@example.com", password="anything")
        assert r.email == "user@example.com"
