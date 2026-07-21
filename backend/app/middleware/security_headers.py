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
import secrets
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Allowlisted external script origins used by the HTMX UI.
# These are the CDN hosts that deliver HTMX and Alpine.js.
_CDN_SCRIPT_HOSTS = "cdn.jsdelivr.net unpkg.com"
_CDN_STYLE_HOSTS = "cdn.jsdelivr.net fonts.googleapis.com"
_CDN_FONT_HOSTS = "fonts.gstatic.com"

# Build static CSP base (without nonce).  Nonce is added per-request.
_APP_ENV = os.environ.get("APP_ENV", "development")


def _build_csp(nonce: str) -> str:
    """Build the Content-Security-Policy header with the given nonce."""
    nonce_directive = f"'nonce-{nonce}'"
    if _APP_ENV == "production":
        # NOTE: 'unsafe-eval' is required by Alpine.js for dynamic expressions.
        # To remove it entirely, migrate from Alpine.js base to @alpinejs/csp
        # (see https://alpinejs.dev/advanced/csp).  Once migrated, the
        # eval-based magic properties and x-on syntax must be reviewed.
        return (
            "default-src 'self'; "
            f"script-src 'self' {nonce_directive} 'strict-dynamic' "
            f"'unsafe-eval' {_CDN_SCRIPT_HOSTS}; "
            f"style-src 'self' 'unsafe-inline' {_CDN_STYLE_HOSTS}; "
            "img-src 'self' data: blob:; "
            f"font-src 'self' {_CDN_FONT_HOSTS}; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none';"
        )
    return (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        f"{_CDN_SCRIPT_HOSTS} localhost:*; "
        f"style-src 'self' 'unsafe-inline' {_CDN_STYLE_HOSTS}; "
        "img-src 'self' data: blob:; "
        f"font-src 'self' {_CDN_FONT_HOSTS}; "
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

        # Generate a CSP nonce for this request.  Used by inline <script> tags
        # in the templates to bypass the strict production CSP.
        nonce = secrets.token_urlsafe(16)
        request.state.nonce = nonce

        response: Response = await call_next(request)

        h = response.headers

        # ── Request tracing ───────────────────────────────────────────────
        h.setdefault("X-Request-ID", request_id)

        # ── Content Security Policy ───────────────────────────────────────
        # Protects against XSS, data injection, and CDN-supply-chain attacks.
        # The nonce is injected per-request so inline scripts can execute.
        h.setdefault("Content-Security-Policy", _build_csp(nonce))

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
        # When all CDN resources are brought in-house, switch to
        # 'require-corp'.
        h.setdefault("Cross-Origin-Embedder-Policy", "unsafe-none")

        # ── Expect-CT ────────────────────────────────────────────────────────
        # Tells browsers to expect Certificate Transparency for this origin.
        # Deprecated but still observed by Chrome.
        h.setdefault("Expect-CT", "max-age=86400, enforce")

        # ── X-Permitted-Cross-Domain-Policies ────────────────────────────────
        # Restrict Adobe Flash/PDF from loading cross-domain content.
        h.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        return response
