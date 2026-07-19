# CI aiosqlite Fix Report

## Root Cause

`tests/conftest.py:21-23` uses an in-memory SQLite database for tests:

```python
TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"
```

This requires the `aiosqlite` package. It was not installed in CI because:

1. `backend/requirements-dev.txt` did not include `aiosqlite`
2. The CI test job installed `backend/requirements.txt` only — which also does not include `aiosqlite`

The result was `ModuleNotFoundError: No module named 'aiosqlite'` when `tests/conftest.py` executed `create_async_engine(TEST_DATABASE_URL)`.

## Files Modified

| File | Change |
|------|--------|
| `backend/requirements-dev.txt` | Added `aiosqlite>=0.20.0` |
| `.github/workflows/ci.yml` | Changed test job from `pip install -r backend/requirements.txt pytest pytest-cov` to `pip install -r backend/requirements-dev.txt` |

## Dependency Changes

**Before** (`backend/requirements-dev.txt`):
```
-r requirements.txt
pytest==9.0.3
pytest-cov==7.1.0
pytest-asyncio==1.3.0
httpx==0.28.1
flake8==7.3.0
bandit==1.9.4
pip-audit==2.10.0
```

**After**:
```
-r requirements.txt
aiosqlite>=0.20.0
pytest==9.0.3
...
```

## CI Workflow Change

**Before** (line 95):
```yaml
run: pip install -r backend/requirements.txt pytest pytest-cov
```

**After**:
```yaml
run: pip install -r backend/requirements-dev.txt
```

This installs `aiosqlite` plus all dev dependencies (pytest, pytest-cov, etc.) in one step.

## Validation

| Check | Result |
|-------|--------|
| `pip install -r backend/requirements-dev.txt` | Installs all deps including aiosqlite |
| `python -c "import aiosqlite"` | ✅ Imports successfully |
| `pytest tests/` | ✅ 659 passed, 4 skipped |
| `black --check backend/` | ✅ 148 files unchanged |
| `flake8 backend/` | ✅ 0 errors |
| `mypy backend/` | ✅ 0 errors |
| `bandit -r backend/ -ll` | ✅ Exit 0 |
| `python -c "from backend.app.main import app"` | ✅ App imports |
| `docker build -t healthpredict-ai:test .` | ✅ Builds successfully |
