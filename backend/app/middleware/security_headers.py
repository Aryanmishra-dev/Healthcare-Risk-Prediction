"""
Security headers middleware — production-hardened (RC2).

Injects all recommended security headers on every response:

  Content-Security-Policy          — HTMX/Alpine.js-compatible policy
  X-Content-Type-Options           — prevent MIME sniffing
  X-Frame-Options                  — clickjacking protection
  Referrer-Policy                  — minimal referrer leakage
  Strict-Transport-Security        — HSTS with preload flag
  Permissions-Policy               — disable unused browser capabilities
  Cross-Origin-Resource-Policy     — restrict cross-origin resource reads
  Cross-Origin-Opener-Policy       — isolate browsing context
  X-Request-ID                     — request tracing
"""

from __future__ import annotations

import os
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Allowlisted external script origins used by the HTMX UI.
# These are the CDN hosts that deliver HTMX and Alpine.js.
_CDN_SCRIPT_HOSTS = "cdn.jsdelivr.net unpkg.com"
_CDN_STYLE_HOSTS = "cdn.jsdelivr.net"

# Build CSP based on environment.  In production we lock down further.
_APP_ENV = os.environ.get("APP_ENV", "development")

if _APP_ENV == "production":
    # Production: strict CSP — only allow known CDN origins for scripts
    _CSP = (
        "default-src 'self'; "
        f"script-src 'self' {_CDN_SCRIPT_HOSTS}; "
        f"style-src 'self' 'unsafe-inline' {_CDN_STYLE_HOSTS}; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none';"
    )
else:
    # Development: slightly relaxed (allow localhost dev servers)
    _CSP = (
        "default-src 'self'; "
        f"script-src 'self' 'unsafe-inline' {_CDN_SCRIPT_HOSTS} localhost:*; "
        f"style-src 'self' 'unsafe-inline' {_CDN_STYLE_HOSTS}; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' localhost:* ws://localhost:*; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none';"
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers on every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)

        h = response.headers

        # ── Request tracing ───────────────────────────────────────────────
        h.setdefault("X-Request-ID", request_id)

        # ── Content Security Policy ───────────────────────────────────────
        # Protects against XSS, data injection, and CDN-supply-chain attacks.
        h.setdefault("Content-Security-Policy", _CSP)

        # ── Anti-sniffing ─────────────────────────────────────────────────
        h.setdefault("X-Content-Type-Options", "nosniff")

        # ── Clickjacking protection ───────────────────────────────────────
        h.setdefault("X-Frame-Options", "DENY")

        # ── Referrer leakage ──────────────────────────────────────────────
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # ── HSTS (only meaningful over HTTPS) ─────────────────────────────
        # max-age = 1 year; includeSubDomains; preload enables submission to
        # browser preload lists.  Never set this on plain-HTTP endpoints.
        h.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains; preload",
        )

        # ── Permissions Policy ────────────────────────────────────────────
        # Disable browser features the application does not use.
        h.setdefault(
            "Permissions-Policy",
            (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), "
                "accelerometer=(), gyroscope=()"
            ),
        )

        # ── Cross-Origin policies ─────────────────────────────────────────
        # CORP: prevent other origins from reading our resources
        h.setdefault("Cross-Origin-Resource-Policy", "same-origin")

        # COOP: isolate the browsing context from other windows
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        # COEP: 'unsafe-none' because we load CDN scripts that don't set CORP.
        # When all CDN resources are brought in-house, switch to 'require-corp'.
        h.setdefault("Cross-Origin-Embedder-Policy", "unsafe-none")

        return response
