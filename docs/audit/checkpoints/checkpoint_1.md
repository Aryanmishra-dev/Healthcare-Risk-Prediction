# Checkpoint 1 — Static Code Audit

## Tools Run

| Tool | Result |
|---|---|
| `black --check .` | 235 files left unchanged — **PASS** |
| `isort --check-only .` | 5 files skipped (no `.py` extension issues) — **PASS** |
| `flake8 backend/ --exclude=__pycache__,migrations/versions` | **1 finding** (E501, see below) |
| `mypy backend/app/ --exclude=migrations/` | 129 source files — no issues — **PASS** |
| `ruff check backend/` | 5 findings (docstring style, magic value, global statement) — see below |

---

## Findings

### E501 — Line too long

| File | Line | Severity | Detail |
|---|---|---|---|
| `backend/migrations/env.py` | 87 | ~~**Low**~~ | ~~Typo fixed.~~ |

### Ruff docstring style — D212

| File | Line | Severity | Detail |
|---|---|---|---|
| `backend/app/api/dependencies.py` | 66 | **Low** | Multi-line docstring summary should start at first line (rate limiter class). |
| `backend/app/api/dependencies.py` | 119 | **Low** | Same issue in `HardenedRateLimiter` docstring. |

### PLW0603 — Global statement

| File | Line | Severity | Detail |
|---|---|---|---|
| `backend/app/api/dependencies.py` | 79 | **Low** | `global _fallback_logged_at` used to rate-limit a fallback warning log. Intentional pattern, not a bug. |

### PLR2004 — Magic value

| File | Line | Severity | Detail |
|---|---|---|---|
| `backend/app/api/dependencies.py` | 83 | **Low** | `60.0` compared directly instead of a named constant. Minor readability, not a bug. |

### Missing return type annotations on async functions

| File | Count | Severity | Detail |
|---|---|---|---|
| `backend/app/main.py` | **25 async functions** without `->` return type | **Medium** | Every `predict_diabetes_htmx`, `predict_heart_htmx`, `predict_lung_htmx`, `api_predict_*`, `v1_predict_*`, exception handlers, plus helper routes. Missing return types reduce IDE support and mypy coverage. |

Largest culprits: 3 HTMX prediction endpoints, 3 API JSON prediction endpoints, 3 audit endpoints, 3 v1-prefixed endpoints.

### Large file sizes / function sizes

| File | Lines | Severity | Detail |
|---|---|---|---|
| `backend/app/main.py` | **1468** | **Medium** | Single file contains all routes (HTMX pages, JSON API, v1 API, exception handlers, middleware setup, ML model registry). Violates single-responsibility — should split into route modules. |
| `backend/app/api/v1/routes/webhooks.py` | 278 | **Low** | Longest route file but within reason. |
| `backend/app/auth/router.py` | 650 | **Low** | Contains all auth endpoints in one file. |
| `api_root` function | 254 lines (line 766) | **Low** | Wraps multiple API endpoints in one function block. |
| `v1_root` function | 263 lines (line 1041) | **Low** | Same pattern — multiple endpoints bundled. |

### Blocking calls in async context

| File | Line | Severity | Detail |
|---|---|---|---|
| `backend/app/main.py` | 1056 | **Low** | `open(REGISTRY_PATH)` wrapped in `asyncio.to_thread(_read_registry)` — handled correctly. No other blocking IO found in async paths. |

### Naming consistency

- All models use `snake_case` — consistent.
- All routes use `snake_case` — consistent.
- One naming inconsistency: `_gauge_offset` local function vs `_clamp` — both prefixed with `_` but one uses abbreviation. No actionable issue.

### No debug prints, no TODOs/FIXMEs/XXXs/HACKs — clean

### Circular imports

- Verified: `from backend.app.main import app` succeeds. No circular import errors in the codebase.

---

## Summary

| Severity | Count | Blocks deploy? |
|---|---|---|
| **Critical** | 0 | Yes |
| **High** | 0 | Yes |
| **Medium** | 2 | No (tech debt) |
| **Low** | 6 | No (backlog) |

**Medium findings:**
1. `backend/app/main.py` — 1468 lines, should be split into route modules.
2. `backend/app/main.py` — 25 async functions missing return type annotations.

**Low findings:**
1. `backend/migrations/env.py:87` — E501 line too long + typo.
2. `backend/app/api/dependencies.py:66,119` — docstring D212 style issues.
3. `backend/app/api/dependencies.py:79` — global statement.
4. `backend/app/api/dependencies.py:83` — magic value `60.0`.
