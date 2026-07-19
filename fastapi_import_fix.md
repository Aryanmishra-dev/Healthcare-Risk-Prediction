# FastAPI Import Fix Report

## Root Cause

FastAPI does not recognize `Request | None` (i.e., `Union[Request, None]`) as the special `Request` type during dependency analysis. When FastAPI's `analyze_param` encounters a parameter typed as `Request | None`, it fails to match it against the known special types and attempts to create a Pydantic model field from it, which crashes because `starlette.requests.Request` is not a valid Pydantic field type.

## Affected Files

| File | Lines | Pattern |
|------|-------|---------|
| `backend/app/auth/router.py` | 63, 111 | `request: Request \| None = None` |
| `backend/app/api/v1/routes/webhooks.py` | 77, 130, 173, 205, 256 | `request: Request \| None = None` |

## Affected Endpoints

- **auth/router.py**: `get_current_user()` dependency (used by `/me` and all protected routes)
- **auth/router.py**: `get_current_session_id()` dependency
- **webhooks.py**: `create_webhook()`, `update_webhook()`, `delete_webhook()`, `rotate_webhook_secret()`, `replay_webhook_event()`

## Why FastAPI Treated It as a Response Field

When FastAPI registers a route (e.g., `@router.get("/me", response_model=UserResponse)`), it:

1. Calls `get_dependant()` to analyze all parameters — both endpoint parameters and their sub-dependencies
2. Inside `get_dependant()`, calls `analyze_param()` for each parameter
3. `analyze_param()` checks if the parameter is a special type (`Request`, `Response`, etc.) using exact type matching
4. With `Request | None = None`, the type is `Union[Request, NoneType]` — **not** the exact `Request` class
5. The special type check **fails**, so `analyze_param()` tries to create a Pydantic field with `create_model_field()`
6. `create_model_field()` rejects `Request` as an invalid Pydantic field type, raising `FastAPIError`

The error appears at route registration time (import time), not at request time, because FastAPI eagerly validates all response models and dependency signatures during app initialization.

## Exact Fix

Change every `request: Request | None = None` to `request: Request = None` with a mypy ignore comment:

```python
# Before (causes FastAPIError):
async def get_current_user(
    request: Request | None = None,
    ...
):

# After (works correctly):
async def get_current_user(
    request: Request = None,  # type: ignore[assignment]
    ...
):
```

**Why this works:**
- FastAPI sees the exact `Request` type and handles it via special-case injection
- The `= None` default tells FastAPI the parameter is optional
- FastAPI internally handles default injection of `Request` even when `None`
- `# type: ignore[assignment]` suppresses mypy's "Incompatible types in assignment" warning for `None` assigned to `Request`

## Validation

| Check | Result |
|-------|--------|
| `python -c "from backend.app.main import app"` | ✅ APP IMPORT OK |
| `mypy backend/` | ✅ Success: no issues found |
| `flake8 backend/` | ✅ 0 errors |
| `black --check backend/` | ✅ 148 files unchanged |
| `pytest tests/` | ✅ 659 passed, 4 skipped |

## CI Impact

The `FastAPIError` during app import caused all jobs that depend on importing the FastAPI application to fail:

- **test** — could not import the app, all tests failed
- **migrations-check** — indirectly affected if any import chain triggered it

With this fix, the full CI pipeline should now execute successfully from test through docker-build.
