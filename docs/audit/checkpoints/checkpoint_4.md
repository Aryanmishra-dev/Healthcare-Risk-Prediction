# Checkpoint 4 — Auth

## Auth Mechanisms Implemented

| Mechanism | Scope | Status |
|---|---|---|
| JWT bearer token (Authorization header) | All protected endpoints | ✓ |
| JWT cookie (access_token, HttpOnly) | HTMX page requests | ✓ |
| API Key (X-API-Key header) | `/api/v1/*` router | ✓ |
| CSRF Double Submit Cookie | HTMX form POSTs + `/api/v1/upload` | ✓ |
| Bot detection (User-Agent) | `/auth/register`, `/auth/login` | ✓ |
| Role-based access (RequireRole) | Admin routes | ✓ |

---

## Findings

### Critical

| # | Finding | Status |
|---|---|---|
| C1 | **Email verification tokens never created** | **Fixed** |

### High

| # | Finding | Status |
|---|---|---|
| H1 | **No per-email rate limiting on login** | **Fixed** |
| H2 | **Secure cookie flag depends on string comparison** | **Fixed** |
| H3 | **No `__Host-` prefix on cookies** | **Fixed** |

### Medium

| # | Finding | File(s) | Detail |
|---|---|---|---|
| M1 | **`revoked_at` not set in refresh flow** | `auth/router.py:322` | Old session is marked `is_revoked=True` but `revoked_at` stays `NULL`. The `is_active` property works regardless, but `revoked_at=NULL` on revoked sessions is semantically wrong. |
| M2 | **Password validator only checks uppercase + digit** | `auth/schemas.py:16-20` | `AAAAAAAA1` (8 chars, uppercase + digit) passes. No lowercase, special char, or entropy requirement. |
| M3 | **`unsafe-eval` in production CSP** | `middleware/security_headers.py:41` | Required by Alpine.js standard build. Comment notes `@alpinejs/csp` would fix it. |
| M4 | **No sliding session expiration** | `auth/router.py` | `last_activity` is updated but `expires_at` is fixed at session creation (7 days). Active users are logged out after 7 days regardless of activity. |

### Low

| # | Finding | File(s) | Detail |
|---|---|---|---|
| L1 | `last_activity` commits on every authed request | `auth/router.py:94-97` | Adds DB write load per request. Could be batched or deferred. |
| L2 | `X-Forwarded-For` rate limiter bypass risk | `api/dependencies.py:93-95` | First IP in chain is trusted. Spoofable if proxy doesn't strip it. |
| L3 | `generate_session_token()` is dead code | `auth/utils.py:101-103` | Never called anywhere. Session IDs come from JWT claims. |
| L4 | Duplicate schema definitions | `auth/schemas.py` vs `schemas/auth.py` | `UserResponse`, `LoginRequest`, `RegisterRequest` defined in two places with different fields. Risk of drift. |
| L5 | Auth `/auth/me` returns minimal user | `auth/schemas.py:34-37` | Only `id`, `email`, `full_name`. No `role`, `is_verified`, `created_at` — unlike `schemas/user.py`. |
| L6 | Bot detection is trivially spoofable | `api/dependencies.py:337-344` | Blocked UAs: python-requests, curl, wget, scrapy. A custom UA or browser UA passes. |

---

## Additional Security Observations

- Session fixation: **Not vulnerable** — new session created on every login, JWT is server-signed.
- Cross-user access: **Correctly implemented** — all user-scoped queries filter by `user_id`.
- Password hashing: **Bcrypt** — appropriate algorithm.
- JWT signing: **HS256** — acceptable for single-service architecture.
- Token refresh: **Proper rotation** — old token revoked before new one issued.
- Password reset: **Good** — all sessions revoked on reset, 30-min expiry, no user enumeration.

---

## Fixes Applied

| # | Fix | Details |
|---|---|---|
| C1 | Email verification token created during registration | `secrets.token_urlsafe(32)` → SHA-256 hash stored in `EmailVerificationToken` with 24h expiry. Raw token included in registration notification message. All in `auth/router.py:register()`. |
| H1 | Per-email rate limiting on login | Checks `LoginHistory` for 10+ failed attempts within 15-minute window per email. Returns 429 if exceeded. Added in `auth/router.py:login()`. Imports: `LoginHistory`, `func.count`. |
| H2 | `Secure` flag robustness | Changed from `settings.app_env == "production"` to `settings.app_env != "development"`. Covers staging, production, and any future non-dev env var values. |
| H3 | `__Host-` prefix on cookies | `__Host-` prefix added when `secure=True` (production). Falls back to plain `access_token`/`refresh_token` in dev. Server reads both names for backward compat. Cookie `delete_cookie` uses the same conditional prefix. |

## Summary

| Severity | Count | Blocks deploy? |
|---|---|---|
| **Critical** | 0 | Yes |
| **High** | 0 | Yes |
| **Medium** | 4 | No (tech debt) |
| **Low** | 6 | No (backlog) |
