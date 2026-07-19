# Security Hardening Guide — HealthPredict AI (RC2)

**Version:** 3.1.0 (RC2) | **Date:** 2026-07-12

---

## Overview

This document describes the security controls implemented as part of the RC2 Production Hardening sprint. Every control maps directly to an RC1 audit blocker.

---

## 1. Email Delivery — Production SMTP

### Problem (RC1)
The `EmailProvider` was a development stub that only logged to console. Users could never receive password reset emails.

### Solution
A full email abstraction was implemented in `backend/app/services/email_service.py`:

| Backend | Activation | Behaviour |
|---------|-----------|-----------|
| `development` | `EMAIL_BACKEND=development` (default) | Logs to application logger |
| `smtp` | `EMAIL_BACKEND=smtp` | Sends via SMTP using `aiosmtplib` |

### Configuration

```bash
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=<your-sendgrid-api-key>
SMTP_USE_TLS=false          # false = STARTTLS (port 587); true = implicit TLS (port 465)
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
EMAIL_FROM_NAME=HealthPredict AI
APP_BASE_URL=https://yourdomain.com
```

### HTML Email Templates

All transactional emails use responsive HTML templates:

| Trigger | Template |
|---------|---------|
| User registration | Welcome + dashboard link |
| Password reset | Reset URL (30-min expiry) |
| Email verification | Verification URL |
| New login | IP + user-agent details, secure account link |
| Security events | Alert title + action link |
| Generic notifications | Title + message body |

### Password Reset URL

Reset tokens are now embedded in a signed URL:
```
{APP_BASE_URL}/auth/password-reset-confirm?token={raw_token}
```
The plaintext token is **never** placed in the visible notification message body.

---

## 2. Rate Limiting — Fail-Closed

### Problem (RC1)
`OptionalRateLimiter` returned `None` (no-op) when Redis was unavailable. A Redis outage silently disabled all rate limiting on auth endpoints, enabling brute-force and credential-stuffing attacks.

### Solution
`HardenedRateLimiter` in `backend/app/api/dependencies.py`:

```
Redis available   → fastapi-limiter (distributed, exact counting across workers)
Redis unavailable → In-memory IP token-bucket (per-worker, never a no-op)
```

**Key properties:**
- Rate limiting is **always active** — no code path produces a no-op
- Redis fallback logs a WARNING at most once per 60 seconds
- In-memory bucket uses `asyncio.Lock` for coroutine safety
- `TESTING=1` env var raises effective capacity for CI (tests never throttled)

### Applied to

| Endpoint | Limit |
|----------|-------|
| `POST /auth/login` | 60/min |
| `POST /auth/register` | 60/min |
| `POST /auth/logout` | 60/min |
| `POST /auth/password-reset-request` | 60/min |
| `POST /auth/password-reset-confirm` | 60/min |
| `POST /auth/refresh` | Inherits global |

---

## 3. Content Security Policy

### Problem (RC1)
No `Content-Security-Policy` header was set. The HTMX frontend loads scripts from CDN, creating XSS and supply-chain attack exposure.

### Solution
`backend/app/middleware/security_headers.py` now sets the following headers on every response:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' cdn.jsdelivr.net unpkg.com;
  style-src 'self' 'unsafe-inline' cdn.jsdelivr.net;
  img-src 'self' data: blob:;
  font-src 'self';
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  object-src 'none';

Permissions-Policy:
  camera=(), microphone=(), geolocation=(), payment=(), usb=(),
  magnetometer=(), accelerometer=(), gyroscope=()

Cross-Origin-Resource-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: unsafe-none  (required for CDN scripts)

Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
X-Request-ID: <uuid per request>
```

### CSP Environment Awareness
- **Production**: strict CDN-only allowlist
- **Development**: relaxed to allow `localhost:*` for dev tools

---

## 4. API Key Enforcement

### Problem (RC1)
When neither `API_KEY` nor `DEV_API_KEY` was set, `get_api_key()` called `secrets.token_hex(32)` to generate a random key. Every worker restart produced a different key, silently breaking all API clients.

### Solution
`get_api_key()` now:
1. Uses `API_KEY` if set
2. Falls back to `DEV_API_KEY` with a one-time WARNING log
3. Raises `HTTP 503` if neither is set (config error surfaced immediately)

`validate_startup_config()` is called in the FastAPI lifespan **before** accepting traffic. In `APP_ENV=production`:
- Missing `API_KEY` → `RuntimeError` (application refuses to start)
- Missing or insecure `JWT_SECRET_KEY` → `RuntimeError`
- `EMAIL_BACKEND != smtp` → WARNING (not a startup blocker, but clearly flagged)

---

## 5. File Upload Security

All uploaded files pass through `backend/app/utils/file_validation.py`:
- Extension allowlist: `.pdf`, `.jpg`, `.jpeg`, `.png`
- MIME type validation against extension
- Maximum file size enforced (configurable, default 5 MB)
- Filename sanitised via `os.path.basename()`

---

## 6. Session & JWT Security

- Session ID embedded in JWT payload (`sid` claim)
- Every authenticated request validates session record in DB
- Sessions can be individually revoked (logout single device)
- All sessions revoked on password change
- Refresh tokens are SHA-256 hashed before storage (never stored plaintext)
- Refresh token rotation on every use (old token immediately revoked)

---

## 7. Remaining Known Risks

| Risk | Mitigation Status |
|------|------------------|
| CDN supply-chain attack | Partially mitigated by CSP allowlist; full mitigation requires SRI hashes |
| Multi-worker in-memory rate limit inaccuracy | Accepted — each worker limits independently; Redis is the correct solution at scale |
| Email token enumeration | Token is UUID v4 (128-bit entropy); brute-force infeasible |
