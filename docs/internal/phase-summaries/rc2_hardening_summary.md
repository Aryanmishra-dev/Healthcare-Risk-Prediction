# RC2 Hardening Summary

**Phase 3.1 — Production Hardening Sprint**
**Date:** 2026-07-12 | **Version:** 3.1.0

---

## What Changed

This sprint resolved all 8 blockers identified in the RC1 audit.

### Blocker 1 — Email Provider (RESOLVED)

**File:** `backend/app/services/email_service.py` (new), `notifications/providers/email.py` (rewritten)

- Replaced development-only stub with a full email abstraction
- `SMTPEmailProvider`: async SMTP via `aiosmtplib` — compatible with SendGrid, AWS SES, Mailgun
- `DevelopmentEmailProvider`: console-logging only (safe for local/CI)
- Auto-selected via `EMAIL_BACKEND` env var (`smtp` | `development`)
- HTML email templates for: welcome, password reset, email verification, new login, security alerts
- Password reset token embedded as a signed URL, never exposed in plain text

### Blocker 2 — Rate Limiting Fail-Closed (RESOLVED)

**File:** `backend/app/api/dependencies.py`

- Replaced `OptionalRateLimiter` (silent no-op on Redis failure) with `HardenedRateLimiter`
- Redis available → distributed rate limiting (exact, shared across workers)
- Redis unavailable → in-memory IP token-bucket fallback (per-worker, never disabled)
- Logs WARNING once per 60 seconds when in fallback mode
- `TESTING=1` env var bypasses throttle for CI test suites
- `secrets.token_hex(32)` random API key fallback removed

### Blocker 3 — Database Indexes (RESOLVED)

**File:** `backend/migrations/versions/0010_rc2_performance_indexes.py` (new)

7 indexes added:
- `ix_prediction_audit_logs_user_id`
- `ix_prediction_audit_logs_disease_model`
- `ix_prediction_audit_logs_created_at`
- `ix_user_sessions_user_id`
- `ix_user_sessions_user_active` (composite: user_id, is_revoked, expires_at)
- `ix_login_history_user_id`
- `ix_security_events_user_id`

### Blocker 4 — Docker HEALTHCHECK (RESOLVED)

**File:** `Dockerfile`

- Fixed: `/health` (404) → `/healthz` (200)
- Workers increased from 1 to 2 (`-w 2`)
- Added `--worker-tmp-dir /dev/shm` for read-only container compatibility

### Blocker 5 — Async Document Processing (RESOLVED)

**File:** `backend/app/services/document_pipeline.py`

- `parse_document()` (PyMuPDF/Pillow, CPU-bound) wrapped in `asyncio.to_thread()`
- `extract_clinical_entities()` (NLP, CPU-bound) wrapped in `asyncio.to_thread()`
- Event loop no longer blocked during document processing

### Blocker 6 — Content Security Policy (RESOLVED)

**File:** `backend/app/middleware/security_headers.py`

Full security header suite now applied to every response:
- `Content-Security-Policy` (HTMX/Alpine.js-compatible; stricter in production)
- `Permissions-Policy` (camera, mic, geo, payment all disabled)
- `Cross-Origin-Resource-Policy: same-origin`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Embedder-Policy: unsafe-none` (CDN compat)
- `Strict-Transport-Security` with `preload` flag added

### Blocker 7 — API Key Enforcement (RESOLVED)

**File:** `backend/app/api/dependencies.py`, `backend/app/main.py`

- `validate_startup_config()` called in FastAPI lifespan before accepting traffic
- Production: missing/weak `API_KEY` → `RuntimeError` (application refuses to start)
- Production: missing/default `JWT_SECRET_KEY` → `RuntimeError`
- Development: `DEV_API_KEY` fallback with one-time warning log
- No more random ephemeral keys that change on restart

### Blocker 8 — Sync File I/O in Async Route (RESOLVED)

**File:** `backend/app/main.py`

- `v1_model_registry()` converted from `def` to `async def`
- `open(REGISTRY_PATH)` wrapped in `asyncio.to_thread()`
- Added `FileNotFoundError` handling (returns empty registry instead of 500)

---

## Bonus Improvements

### Connection Pool Sizing

**Files:** `backend/app/core/database.py`, `config/settings.py`

- Added `pool_size=10, max_overflow=20` (was default 5)
- Configurable via `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` env vars
- Allows up to 30 concurrent DB connections

### Settings Expansion

**File:** `config/settings.py`

New fields: `email_backend`, `smtp_host`, `smtp_port`, `smtp_username`, `smtp_password`, `smtp_use_tls`, `email_from_address`, `email_from_name`, `app_base_url`, `db_pool_size`, `db_max_overflow`

### `.env.example` Documentation

Added full email configuration section with provider-specific guidance.

### `aiosmtplib` Dependency

Added to `backend/requirements.txt` and `requirements.txt` at version `5.1.2`.

---

## Test Results

```
289 passed, 4 skipped, 0 failures
```

Zero regressions introduced. All pre-existing tests continue to pass.

---

## Files Changed

| File | Action |
|------|--------|
| `backend/app/services/email_service.py` | NEW |
| `backend/app/services/notifications/providers/email.py` | REWRITTEN |
| `backend/app/api/dependencies.py` | REWRITTEN |
| `backend/app/middleware/security_headers.py` | REWRITTEN |
| `backend/app/core/database.py` | MODIFIED |
| `backend/app/services/document_pipeline.py` | MODIFIED |
| `backend/app/main.py` | MODIFIED (2 locations) |
| `backend/migrations/versions/0010_rc2_performance_indexes.py` | NEW |
| `config/settings.py` | MODIFIED |
| `Dockerfile` | MODIFIED |
| `tests/conftest.py` | MODIFIED |
| `.env.example` | MODIFIED |
| `backend/requirements.txt` | MODIFIED |
| `requirements.txt` | MODIFIED |
| `docs/security_hardening.md` | NEW |
| `docs/performance_review.md` | NEW |
| `docs/deployment_checklist.md` | NEW |
| `docs/rc2_hardening_summary.md` | NEW |
| `docs/release_candidate_rc2.md` | NEW |
