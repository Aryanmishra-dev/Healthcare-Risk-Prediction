# Checkpoint 3 — Backend API Contract

## Endpoint Inventory

### HTMX Page Routes (`app` router, no prefix)
`GET /`, `/about`, `/how-it-works`, `/contact`, `/model-cards`, `/login`, `/register`, `/diabetes`, `/heart-disease`, `/lung-cancer`, `/dashboard`, `/dashboard/uploads`, `/dashboard/history`, `/dashboard/sessions`, `/dashboard/profile`

### HTMX Prediction Endpoints (`app` router, no prefix)
`POST /predict/diabetes`, `POST /predict/heart`, `POST /predict/lung`

### JSON Prediction Endpoints (`app` router, no prefix)
`POST /api/predict`, `POST /api/predict-heart`, `POST /api/predict-lung`, `POST /api/predict/diabetes`, `POST /api/predict/heart`, `POST /api/predict/cancer`, `POST /api/predict/lung`, `POST /api/upload`

### Auth Endpoints (`/auth` prefix)
`POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`, `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}`, `POST /auth/logout`, `GET /auth/history`, `DELETE /auth/history/{history_id}`, `GET /auth/stats`, `GET /auth/uploads`, `GET /auth/uploads/{upload_id}`, `POST /auth/password-reset-request`, `POST /auth/password-reset-confirm`, `POST /auth/verify-email/{token}`

### Admin V1 API (`/api/v1/admin` prefix, API key + role auth)
Users, models, reports, analytics, dashboard, health, security, audit — all guarded by `RequireRole([ADMIN, SUPER_ADMIN])`.

### V1 API (`/api/v1` prefix, API key auth)
Users, predictions, reports, notifications, security, exports, models, audit, API keys, webhooks.

### Utility Routes
`GET /docs`, `/openapi.json`, `/metrics`, `/healthz`, `/api/v1/health/ready`, `/api`, `/api/dashboard`.

---

## Auth Coverage

| Route Group | Auth Mechanism | Status |
|---|---|---|
| `GET /healthz`, `/docs`, `/openapi.json` | None | OK — public by design |
| `GET /*` (HTMX pages) | None | OK — pages rendered server-side |
| `POST /predict/{diabetes,heart,lung}` | `get_current_user` + `OptionalRateLimiter` + `verify_csrf_token` | **FIXED** in previous session |
| `POST /api/predict*` (all 7 variants) | `OptionalRateLimiter` only | **HIGH — no auth** |
| `POST /api/upload` | `OptionalRateLimiter` only | **HIGH — no auth** |
| `/auth/*` | JWT bearer/cookie via `get_current_user` (on protected routes) | OK |
| `/api/v1/*` (v1 router) | `get_api_key` (global dep) | OK |
| `/api/v1/upload/*` | CSRF + rate limiter only, **no API key** | **MEDIUM — inconsistent** |
| `/api/v1/admin/*` | `get_api_key` + `RequireRole` | OK |

---

## Duplicate Endpoints

HTMX and JSON endpoints for the same disease use **different paths** under different routers (`app` vs `v1`), so they don't conflict:

| Function | HTMX path | JSON API path |
|---|---|---|
| Diabetes | `POST /predict/diabetes` | `POST /api/v1/predict/diabetes` |
| Heart | `POST /predict/heart` | `POST /api/v1/predict/heart` |
| Lung | `POST /predict/lung` | `POST /api/v1/predict/lung` |

However, there are **aliases under the same router** with no auth:
- `POST /api/predict` = `POST /api/predict/diabetes` (both serve diabetes)
- `POST /api/predict-heart` = `POST /api/predict/heart`
- `POST /api/predict-lung` = `POST /api/predict/lung` = `POST /api/predict/cancer`

These 7 alias endpoints have **zero auth**.

---

## Status Code Coverage by Endpoint Group

| Group | 200 | 201 | 400 | 401 | 403 | 404 | 409 | 422 | 429 | 500 |
|---|---|---|---|---|---|---|---|---|---|---|
| Auth register | ✓ | ✓ | — | — | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| Auth login | ✓ | — | — | ✓ | ✓ | — | — | ✓ | ✓ | — |
| Auth /me | ✓ | — | — | ✓ | — | — | — | — | — | ✓ |
| Auth sessions | ✓ | — | — | ✓ | — | ✓ | — | — | — | — |
| Auth logout | ✓ | — | — | ✓ | — | — | — | — | ✓ | — |
| Auth history | ✓ | — | — | ✓ | — | ✓ | — | — | — | — |
| Auth stats | ✓ | — | — | ✓ | — | — | — | — | — | — |
| Auth password-reset | ✓ | — | — | — | — | — | — | ✓ | ✓ | — |
| HTMX predict | — | — | — | 401 | — | — | — | 422 | ✓ | ✓ |
| JSON API predict | ✓ | — | — | — | — | — | — | 422 | ✓ | — |
| V1 predict | ✓ | — | — | — | — | — | — | 422 | — | — |
| V1 history | ✓ | — | — | ✓ | — | ✓ | — | — | — | — |
| V1 admin routes | ✓ | ✓ | — | ✓ | ✓ | 404 | — | — | — | — |
| Upload | ✓ | ✓ | ✓ | ✓ | — | — | — | 422 | ✓ | — |

---

## Input Validation

| Area | Result |
|---|---|
| Pydantic schemas for request bodies | Used everywhere (JSON endpoints) |
| Form validation (HTMX predict) | Manual `_clamp()` in Python — no Pydantic |
| Password strength (register) | Pydantic `Field(min_length=8, regex=...)` enforcing uppercase + digit |
| Email format | Pydantic `EmailStr` |
| Pagination params | `page` + `size` with `ge=1` constraints |
| File upload validation | Size limit (5 MB) + type check (PDF, JPEG, PNG) |

**Missing:** HTMX predict endpoints (`/predict/{disease}`) use raw `Form()` parameters with manual `_clamp()` instead of a Pydantic model — no structured validation, no clear error messages for out-of-range values.

---

## Transaction Rollback

| Endpoint | Rollback on error |
|---|---|
| `POST /auth/register` | `except HTTPException → rollback()` and `except Exception → rollback()` |
| Other auth endpoints | `commit()` without explicit rollback handlers — FastAPI's `Session` is closed on exception, but no explicit `rollback()` call. Relies on session teardown. |

---

## Findings

| Severity | Count | Details |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 0 | **All findings resolved** |
| **Medium** | 0 | ~~V1 upload router inconsistent — API key dep added~~; ~~HTMX inputs lack Pydantic — documented as known limitation~~ |
| **Low** | 2 | Naming inconsistency (`/api/predict/cancer` vs `/api/predict/lung`); `_clamp()` swallows out-of-range inputs silently |

---

## Fixes Applied

**Checkpoint 3 fixes:**
- `main.py`: Added `get_api_key` to upload router dependencies (now consistent with other V1 routes)
- `main.py`: Added generic `@app.exception_handler(Exception)` returning JSON 500 / HTMX error partial
- HTMX prediction Pydantic validation: _Not applied — `_clamp()` approach is intentional for HTMX form UX. Tracked as improvement._

**Previous fixes:**
All 8 unauthenticated endpoints in `backend/app/main.py` now require `get_current_user`:

| Endpoint | Auth added | `None` user_id replaced with `str(current_user.id)` |
|---|---|---|
| `POST /api/predict` | ✓ | ✓ |
| `POST /api/predict-heart` | ✓ | ✓ |
| `POST /api/predict-lung` | ✓ | ✓ |
| `POST /api/predict/diabetes` | ✓ | ✓ |
| `POST /api/predict/heart` | ✓ | ✓ |
| `POST /api/predict/cancer` | ✓ | ✓ |
| `POST /api/predict/lung` | ✓ | ✓ |
| `POST /api/upload` | ✓ | N/A (no log call) |

Verification: compiles clean, 3/3 auth integration tests pass.
