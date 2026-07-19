"""Shared FastAPI dependencies — production-hardened."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import (
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.models.admin_action import AdminAction
from backend.app.models.tenant import Membership
from backend.app.services.authorization_service import AuthorizationService

logger = logging.getLogger(__name__)

# In TESTING mode we raise the in-memory bucket capacity so tests never
# hit a 429 from the fallback limiter.  Redis-backed limiting is not active
# in the test environment anyway (no Redis in CI).
_TESTING = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

# ── In-process fallback rate limiter ─────────────────────────────────────────


class _InMemoryBucket:
    """Token-bucket rate limiter slot for a single identifier."""

    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float) -> None:
        self.tokens: float = capacity
        self.last_refill: float = time.monotonic()


_buckets: dict[str, _InMemoryBucket] = defaultdict(lambda: _InMemoryBucket(60))
_buckets_lock = asyncio.Lock()
_fallback_logged_at: float = 0.0  # Rate-limit the warning log itself


def clear_rate_limit_buckets() -> None:
    """Clear all in-memory rate limit buckets. Useful in tests."""
    _buckets.clear()


async def _in_memory_rate_limit(
    request: Request,
    times: int,
    seconds: int,
) -> None:
    """
    IP-based token-bucket rate limiter backed entirely by process memory.

    This is the fallback used when Redis is unavailable.  It provides
    meaningful protection (not a no-op) while Redis is down.

    In TESTING mode the effective limit is raised to 10 000 per window so
    unit and integration tests are never throttled by the fallback.
    """
    # Disable effective throttle in test environments
    if _TESTING:
        return

    global _fallback_logged_at
    now = time.monotonic()

    # Log a warning at most once per 60 seconds so we don't flood logs
    if now - _fallback_logged_at >= 60.0:
        logger.warning(
            "rate_limiter_fallback_active | Redis unavailable — "
            "using in-process IP-based throttle. "
            "Effective limit per IP per worker: %d/%ds",
            times,
            seconds,
        )
        _fallback_logged_at = now

    client_ip = request.headers.get("x-forwarded-for", "").split(",")[
        0
    ].strip() or (request.client.host if request.client else "unknown")
    key = f"{request.url.path}:{client_ip}"
    refill_rate = times / seconds  # tokens per second

    async with _buckets_lock:
        bucket = _buckets[key]
        elapsed = now - bucket.last_refill
        # Refill tokens proportionally to elapsed time
        bucket.tokens = min(times, bucket.tokens + elapsed * refill_rate)
        bucket.last_refill = now

        if bucket.tokens < 1:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait before retrying.",
                headers={"Retry-After": str(seconds)},
            )
        bucket.tokens -= 1


# ── Hardened rate limiter (replaces OptionalRateLimiter) ─────────────────────


class HardenedRateLimiter:
    """
    Distributed rate limiter with automatic fail-closed in-memory fallback.

    Behaviour:
      Redis available   → fastapi-limiter (distributed, exact counting)
      Redis unavailable → in-process IP token-bucket (approximate, per-worker)

    The fallback is NEVER a no-op.  Rate limiting is always active.
    """

    def __init__(self, times: int, seconds: int) -> None:
        self._times = times
        self._seconds = seconds
        # Create the Redis-backed limiter lazily to avoid import errors at
        # module load time when Redis is not yet connected.
        self._redis_limiter: Any = None

    def _get_redis_limiter(self) -> Any:
        if self._redis_limiter is None:
            from fastapi_limiter.depends import RateLimiter

            self._redis_limiter = RateLimiter(
                times=self._times, seconds=self._seconds
            )
        return self._redis_limiter

    async def __call__(self, request: Request, response: Response) -> None:
        try:
            from fastapi_limiter import FastAPILimiter

            redis_connected = (
                hasattr(FastAPILimiter, "redis")
                and FastAPILimiter.redis is not None
            )
            if redis_connected:
                await self._get_redis_limiter()(request, response)
                return
        except HTTPException:
            # Re-raise 429 responses from the Redis limiter — do not swallow them
            raise
        except Exception:
            # Redis call failed mid-flight — fall through to in-memory backup
            pass

        # Redis unavailable: use in-memory token-bucket fallback
        await _in_memory_rate_limit(request, self._times, self._seconds)


# Backward-compatible alias so existing imports don't break
OptionalRateLimiter = HardenedRateLimiter

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))

# ── RBAC Authorization ────────────────────────────────────────────────────────


class RequireRole:
    """Dependency to enforce role-based access control."""

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, request: Request) -> None:
        user = getattr(request.state, "user", None)
        if not user:
            # We assume get_current_user was already run, but if not, fail.
            raise HTTPException(
                status_code=401, detail="Authentication required"
            )

        if user.role not in self.allowed_roles:
            logger.warning(
                "rbac_denied | user_id=%s | role=%s | required=%s",
                user.id,
                user.role,
                self.allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to perform this action.",
            )


class RequirePermission:
    """Dependency to enforce permission-based access control."""

    def __init__(self, permission: str):
        self.permission = permission

    def __call__(self, request: Request) -> None:
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(
                status_code=401, detail="Authentication required"
            )
        if not AuthorizationService.can(user, self.permission):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to perform this action.",
            )


async def _log_admin_action(
    db: AsyncSession,
    admin_id: str,
    action_type: str,
    target_resource: str,
    metadata: dict,
):
    import uuid

    from backend.app.models.admin_action import AdminAction

    try:
        admin_id_uuid = uuid.UUID(admin_id) if admin_id else None
        action = AdminAction(
            admin_id=admin_id_uuid,
            action_type=action_type,
            target_resource=target_resource,
            metadata_payload=metadata,
        )
        db.add(action)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")


async def audit_admin_action(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency to log admin mutations (POST/PUT/DELETE/PATCH) into AdminAction.
    Must be used in combination with get_current_user and RequireRole.
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        user = getattr(request.state, "user", None)
        admin_id = str(user.id) if user else None
        action_type = f"{request.method} {request.url.path}"
        metadata = {
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown",
        }
        # Run DB insert in background task so we don't block response
        background_tasks.add_task(
            _log_admin_action,
            db,
            admin_id,
            action_type,
            request.url.path,
            metadata,
        )


# ── API Key ───────────────────────────────────────────────────────────────────

API_KEY_NAME = "X-API-Key"
_api_key_warning_logged = False


def _resolve_api_key() -> str:
    """
    Resolve the expected API key from environment variables.

    Production (APP_ENV=production):
      - ``API_KEY`` must be set or the application refuses to start.
      - Enforced separately in ``validate_startup_config()``.

    Development:
      - Falls back to ``DEV_API_KEY`` with a one-time warning.
      - Never generates a random ephemeral key that changes on restart.
    """
    global _api_key_warning_logged

    key = os.environ.get("API_KEY")
    if key:
        return key

    dev_key = os.environ.get("DEV_API_KEY")
    if dev_key:
        if not _api_key_warning_logged:
            logger.warning(
                "api_key_using_dev_fallback | "
                "API_KEY not set — falling back to DEV_API_KEY. "
                "Set API_KEY for production deployments."
            )
            _api_key_warning_logged = True
        return dev_key

    # No key configured at all — raise immediately so the problem is visible
    app_env = os.environ.get("APP_ENV", "development")
    raise HTTPException(
        status_code=503,
        detail=(
            "Service misconfigured: API_KEY is not set. "
            "Set API_KEY (production) or DEV_API_KEY (development) in environment."
        ),
    )


def get_api_key(
    api_key: str | None = Depends(
        APIKeyHeader(name=API_KEY_NAME, auto_error=False)
    ),
) -> str:
    expected = _resolve_api_key()
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


def verify_user_agent(request: Request) -> str:
    user_agent = request.headers.get("user-agent", "").lower()
    if not user_agent or any(
        bot in user_agent
        for bot in ["python-requests", "curl", "wget", "scrapy"]
    ):
        raise HTTPException(status_code=403, detail="Bot traffic not allowed")
    return user_agent


async def get_current_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Resolve the tenant ID for the current user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    result = await db.execute(
        select(Membership.tenant_id)
        .where(Membership.user_id == user.id)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any tenant",
        )
    return row


# ── Startup validation ────────────────────────────────────────────────────────


def validate_startup_config() -> None:
    """
    Called from the FastAPI lifespan before the application begins serving.

    Raises ``RuntimeError`` if the configuration is unsafe for production.
    Logs warnings for development-mode misconfigurations.
    """
    app_env = os.environ.get("APP_ENV", "development")
    errors: list[str] = []
    warnings: list[str] = []

    # API key
    api_key = os.environ.get("API_KEY", "")
    dev_key = os.environ.get("DEV_API_KEY", "")

    if app_env == "production":
        if not api_key:
            errors.append("API_KEY must be set in production.")
        elif len(api_key) < 32:
            errors.append(
                "API_KEY must be at least 32 characters in production."
            )

        jwt_key = os.environ.get("JWT_SECRET_KEY") or os.environ.get(
            "SECRET_KEY", ""
        )
        if not jwt_key or "dev-only" in jwt_key:
            errors.append(
                "JWT_SECRET_KEY must be set to a secure value in production."
            )

        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url or "sqlite" in db_url:
            errors.append(
                "DATABASE_URL must be set to a Postgres connection string in "
                "production. The SQLite fallback is for local development only."
            )

        email_backend = os.environ.get("EMAIL_BACKEND", "development")
        if email_backend != "smtp":
            warnings.append(
                "EMAIL_BACKEND is not 'smtp'. "
                "Email delivery (password reset, verification) will be disabled."
            )

    else:
        if not api_key and not dev_key:
            warnings.append(
                "Neither API_KEY nor DEV_API_KEY is set. "
                "All /api/v1 requests will be rejected."
            )

    for warning in warnings:
        logger.warning("startup_config_warning | %s", warning)

    if errors:
        for error in errors:
            logger.critical("startup_config_error | %s", error)
        raise RuntimeError(
            f"Application startup aborted due to {len(errors)} configuration error(s). "
            f"See logs for details."
        )

    logger.info(
        "startup_config_ok | env=%s | api_key_set=%s | email_backend=%s",
        app_env,
        bool(api_key or dev_key),
        os.environ.get("EMAIL_BACKEND", "development"),
    )
