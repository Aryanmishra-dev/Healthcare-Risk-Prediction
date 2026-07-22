# Production Verification Report

## 1. Docker Build

| Metric | Measured | Target |
|--------|----------|--------|
| Image size | **2.92 GB** | — |
| Build time (first) | **281 s** | — |
| Build time (cached) | **2 s** | — |

**Note:** 2.92 GB includes ~130 MB xgboost, ~40 MB nvidia-nccl, ~60 MB llvmlite, ~16 MB numpy, ~12 MB pandas, etc. The `python:3.11-slim` base is ~120 MB. Total is typical for ML-heavy Python images.

## 2. Memory Measurements

### Startup / Idle

| Phase | RSS (MB) | CPU (%) | PIDs |
|-------|----------|---------|------|
| First health check (t=1s) | **195** | 0.7 | 13 |
| After 30s idle | **287** | 0.3 | 25 |
| After warmup (first prediction, SHAP + models loaded) | **287** | 0.3 | 25 |

### Under Load

| Phase | Min (MB) | Max (MB) | Avg (MB) |
|-------|----------|----------|----------|
| 30 rapid fire requests | 287 | 287 | 287 |
| 100 requests @ 10 req/s | 287 | 287 | 287 |
| 500 requests (5×100) | 287 | 288 | 288 |
| After load (5s idle) | 288 | 288 | 288 |

### 30-Minute Leak Test

| Metric | Value |
|--------|-------|
| Start RAM | **287 MB** |
| End RAM (30 min) | **289 MB** |
| Net growth | **+1 MB** |
| Min | 287 MB |
| Max | 289 MB |
| Avg | 288 MB |
| CPU (idle) | 0.3% |
| PIDs | 25 |
| **Leak assessment** | **PASS** (no growth) |

## 3. Endpoint Verification

| Endpoint | Status | Response Time |
|----------|--------|---------------|
| GET / | 200 | 18 ms |
| GET /healthz | 200 | 2 ms |
| GET /health | 200 | 2 ms |
| GET /api | 200 | 2 ms |
| GET /health/database | 200 | 2 ms |
| GET /health/models | 503 (expected - models lazy loaded) | 2 ms |
| GET /model-cards | 200 | 2 ms |
| GET /how-it-works | 200 | 2 ms |
| GET /contact | 200 | 2 ms |
| GET /diabetes | 200 | 2 ms |
| GET /heart-disease | 200 | 2 ms |
| GET /lung-cancer | 200 | 2 ms |
| GET /dashboard | 200 | 2 ms |
| GET /auth/me | 200 | 6 ms |
| POST /auth/register | 201 | 223 ms |
| POST /auth/login | 200 | 178 ms |
| POST /api/predict/diabetes | 200 | 26 ms |
| POST /api/predict/heart | 200 | 12 ms |
| POST /api/predict-lung | 200 | 11 ms |
| POST /api/predict/cancer | 200 | 10 ms |
| POST /api/predict (generic) | 200 | 9 ms |
| GET /api/v1/models | 200 | 8 ms |
| GET /api/v1/models/current | 200 | 8 ms |
| GET /api/v1/models/health | 200 | 4 ms |
| GET /api/v1/predictions/history | 200 | 9 ms |
| GET /api/dashboard | 200 | 4 ms |

### Prediction Payloads Verified

| Disease | V1 Route | V2 Route (JWT) |
|---------|----------|----------------|
| Diabetes | 422 (schema mismatch) | 200 (19.0% Low) |
| Heart | 422 (schema mismatch) | 200 (17.1% Low) |
| Lung | 200 (38.7% Moderate) | — |
| Cancer | — | 200 (38.7% Moderate) |

**Note:** V1 prediction routes use a different schema (form-encoded, deprecated field names like `bp` instead of `blood_pressure`, CDC BRFSS age encoding 1-13). These return 422 with the standard JSON payloads, which is a **pre-existing** API design issue, not caused by our changes.

## 4. Load Test

### 100 Requests @ 10 req/s

| Metric | Value |
|--------|-------|
| Total time | 11.3 s |
| Errors | 0 |
| Avg latency | 26 ms |
| Min latency | 10 ms |
| Max latency | 54 ms |
| P95 latency | 32 ms |

### 500 Requests (5×100 with 4s gaps)

| Metric | Value |
|--------|-------|
| Total time | 78.0 s |
| Rate-limited | 210 (expected - rate limiter active) |
| Avg latency | 27 ms |
| P50 latency | 27 ms |
| P95 latency | 32 ms |
| P99 latency | 38 ms |
| Throughput (effective) | 6 req/s |

## 5. CI/CD Verification

| Check | Status |
|-------|--------|
| black | **PASS** (148 files unchanged) |
| isort | **PASS** (no changes needed) |
| flake8 | **PASS** (no errors) |
| .github/workflows/ci.yml | Complete (lint, type-check, security, test, migrations, docker) |

## 6. Render Deployment

`deployment/render.yaml` configured with:
- `plan: free`
- Health check path: `/healthz`
- Gunicorn: 1 worker, 120s timeout
- DB pool: `pool_size=2, max_overflow=4`
- Auto-migration at startup (table creation via `Base.metadata.create_all` on async engine)

**Status:** Skipped (no Render API credentials available in test environment). To deploy:
```
git push origin main
```
Render auto-deploys from GitHub when connected.

## 7. Configuration Changes Made

| File | Change |
|------|--------|
| `Dockerfile` | Added `data/interim/` directory creation; CMD respects `${PORT:-8000}`; pip cache cleaned |
| `backend/app/main.py` | Added auto table creation (via `Base.metadata.create_all`) at startup; models/SHAP load lazily |
| `backend/app/services/model_manager.py` | Fixed `_ensure_loaded` sync method (was using `asyncio.run()` in running loop, causing 503) |

## 8. Remaining Issues

| Issue | Severity | Detail |
|-------|----------|--------|
| V1 predict schema mismatch | Low | V1 routes expect form-encoded data with different field names (`bp`, BRFSS age 1-13) — pre-existing |
| `/health/models` returns 503 | Low | Expected — models are lazy-loaded, not pre-loaded at startup |
| Auth sessions endpoint 500 | Low | Pre-existing bug in session listing |
| Rate limiter resets on restart | Low | In-memory rate limiter without Redis; resets counters on each gunicorn restart |
| No Celery/Redis on Render Free | Low | Background tasks (webhook retries, audit retention) not automated |
| 100 req/s burst results in 429 | Low | Rate limiter caps at ~30 rapid requests before hitting limit |

## 9. Summary: Render Free Plan (512 MB RAM) Readiness

| Requirement | Measured | Limit | Verdict |
|-------------|----------|-------|---------|
| Startup RAM | **195 MB** | 512 MB | ✅ |
| Idle RAM | **287 MB** | 512 MB | ✅ (44% headroom) |
| Peak RAM | **289 MB** | 512 MB | ✅ (43% headroom) |
| Startup time | **<2s** | 30s (Render) | ✅ |
| First prediction | **~3s** (lazy load) | 120s (gunicorn timeout) | ✅ |
| Subsequent predictions | **10-30 ms** | — | ✅ |
| Memory leak (30 min) | **+1 MB** | <20 MB | ✅ |
| Docker HEALTHCHECK | /healthz | — | ✅ |
| PORT env var | `${PORT:-8000}` | Render | ✅ |
