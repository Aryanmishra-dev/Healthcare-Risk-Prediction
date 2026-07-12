# Release Candidate RC1 — Production Readiness Audit

**Project:** Healthcare Risk Prediction Platform
**Audit Date:** 2026-07-11
**Version:** 3.0.0
**Auditor:** Antigravity AI (automated deep-inspection audit)
**Test Suite:** 289 passed · 4 skipped · 0 failures (post-audit)

---

## 1. Executive Summary

The Healthcare Risk Prediction platform has been built across three major phases. It now encompasses:

- **Phase 1** — Authentication, RBAC, multi-disease ML prediction (Diabetes, Heart Disease, Lung Cancer)
- **Phase 2** — User Dashboard, Prediction History, Report Storage, Notification System, Session Security, Data Export
- **Phase 3** — Model Registry, SHAP Explainability, Model Monitoring, Drift Detection, A/B Testing framework

The audit was performed by inspecting every source file across `backend/app/`, `tests/`, `docs/`, migrations, `Dockerfile`, `.env`, and `requirements.txt`.

**One critical production-blocking bug was discovered and fixed during this audit:** The `PasswordResetToken` object was created but never added to the database session (`db.add(reset)` was absent from `auth/router.py`). This meant the password reset endpoint silently failed for all users — a critical security and UX regression.

**8 additional production blockers remain** that must be resolved before the application can be safely deployed.

> **Final Release Score: 67 / 100**
> **Verdict: NOT APPROVED for production deployment in current state.**

---

## 2. Architecture Review

### Strengths

- **Clean layered architecture**: routes → services → models. No business logic bleeds into route handlers.
- **Async-first**: All database operations use SQLAlchemy 2.0 `AsyncSession` with `asyncpg`. `pool_pre_ping=True` protects against stale connections.
- **Modular services**: Prediction, reports, notifications, exports, security are independently encapsulated.
- **Dependency injection**: All FastAPI dependencies use `Depends()`, enabling testability and mock injection.
- **Multi-stage Docker build**: Non-root user, gunicorn+UvicornWorker, HEALTHCHECK probe, correct `PYTHONPATH`.
- **Configuration management**: `pydantic-settings` with `.env` file loading; `.env` correctly gitignored.

### Issues

| Severity | Finding |
|----------|---------|
| 🔴 HIGH | **Synchronous file I/O in async route** — `main.py` line 818 calls `open(REGISTRY_PATH)` inside an async route handler (`@v1.get("/models")`). This blocks the event loop and degrades all concurrent requests during that read. |
| 🟡 MEDIUM | **Duplicate A/B testing implementations** — `ab_testing.py` (deterministic hash-based, production-grade champion/challenger) and `ab_testing_service.py` (simple random-split). Only the simple one has tests. Neither is wired to the live prediction endpoints. |
| 🟡 MEDIUM | **`prediction_pipeline.py` is unused** — A full `PredictionPipeline` service was created but the actual prediction endpoints in `main.py` still call the original `predict()`, `predict_heart_disease()`, `predict_lung_cancer()` functions directly, bypassing the pipeline. |
| 🟡 MEDIUM | **`parse_document()` blocks the event loop** — `document_pipeline.py` line 51 calls `parse_document()` (which uses PyMuPDF `fitz.open()` and Pillow `Image.open()`) directly inside an `async def` without `asyncio.to_thread()`. PDF/image processing will stall all concurrent requests for its duration. |
| 🟢 LOW | **`exports_data/` grows unbounded** — 20 user export directories accumulate locally with no TTL or cleanup job. Will exhaust disk in production. |
| 🟢 LOW | **Duplicate `requirements.txt`** — `backend/requirements.txt` and root `requirements.txt` diverge (`fastapi-cache2==0.2.1` vs `0.2.2`). Should be consolidated to one canonical file. |

---

## 3. Security Review

### Strengths

- **Bcrypt password hashing** via `passlib[bcrypt]`.
- **JWT + session validation**: Every authenticated request validates the session record in the database. Stolen tokens can be invalidated by revoking the session.
- **Refresh token rotation**: SHA-256 hashed refresh tokens rotated on every use. Old token is immediately revoked.
- **All sessions revoked on password change**.
- **Anti-enumeration on password reset**: Always returns success response regardless of whether the email exists.
- **Security headers middleware**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `HSTS: max-age=31536000; includeSubDomains`, `Referrer-Policy`.
- **Password strength validation**: Registration enforces min 8 chars, at least one uppercase, at least one digit.
- **`.env` gitignored correctly**.

### Issues

| Severity | Finding |
|----------|---------|
| 🔴 **CRITICAL — FIXED** | **`PasswordResetToken` never persisted** — `auth/router.py` created the `PasswordResetToken` object but never called `db.add(reset)` before committing. The token was never written to the database, so every `POST /auth/password-reset-confirm` call would fail with "Invalid or expired token". **Fixed during audit by adding `db.add(reset)`.** |
| 🔴 HIGH | **Rate limiting silently disabled when Redis is unavailable** — `OptionalRateLimiter` returns `None` (no-op) when Redis is down. In production, a Redis outage fully unthrottles `/auth/login`, `/auth/register`, and `/auth/password-reset-request`, enabling brute-force and credential-stuffing attacks with no defence. |
| 🔴 HIGH | **`API_KEY` falls back to a random per-process key** — `dependencies.py` calls `secrets.token_hex(32)` when neither `API_KEY` nor `DEV_API_KEY` is set. On every worker restart or new worker spawn, a different key is generated, silently breaking all API clients with 401. |
| 🔴 HIGH | **Email provider is a development stub** — `EmailProvider.send()` logs to console only. Since password reset tokens are delivered exclusively via notification dispatch, users cannot receive reset tokens. The entire password reset user journey is broken in any environment without a real SMTP/SES integration. |
| 🔴 HIGH | **No Content Security Policy (CSP) header** — The HTMX frontend loads Alpine.js and HTMX from CDN. Without a CSP, a compromised CDN script can execute arbitrary JavaScript in the application, exfiltrating patient health data. Unacceptable for a healthcare application. |
| 🟡 MEDIUM | **Plaintext reset token in notification body** — `password_reset_request` passes `raw_token` directly in the message string (`f"Use token {raw_token} to reset your password."`). If notifications are forwarded to any third-party channel (email, webhook), the plaintext token is exposed. Should embed a signed URL instead. |
| 🟡 MEDIUM | **`verify_user_agent` is security theatre** — Checking `user-agent` for known bots (`python-requests`, `curl`) is trivially bypassed with any custom UA string. This provides no real protection but is applied to `/auth/register` and `/auth/login`, potentially blocking legitimate API clients. |
| 🟢 LOW | **Login schema accepts `min_length=1` password** — Inconsistent with registration's `min_length=8`. Does not bypass bcrypt but is confusing and could mask issues. |
| 🟢 LOW | **No `SameSite=Strict` on CSRF cookie** (HTMX form endpoints). |

---

## 4. Database Review

### Strengths

- SQLAlchemy 2.0 async-native: `AsyncSession`, `mapped_column`, typed `Mapped[]` columns throughout.
- Proper `ON DELETE CASCADE` and `ON DELETE SET NULL` semantics for all FK relationships.
- UUID primary keys for all user-facing entities.
- Alembic migration chain is linear and complete (9 migrations, zero branching).
- `pool_pre_ping=True` prevents stale connection errors.
- Soft delete support via `deleted_at` on user-facing models.

### Missing Indexes — Critical

The following high-frequency query columns have **no database index**, meaning every query performs a sequential scan:

| Table | Column | Used By |
|-------|--------|---------|
| `prediction_audit_logs` | `user_id` | History, dashboard, export — all user-scoped queries |
| `prediction_audit_logs` | `disease_model` | Filtered history (`?disease=diabetes`) |
| `prediction_audit_logs` | `created_at` | All `ORDER BY` and date-range queries |
| `user_sessions` | `user_id` | `GET /auth/sessions`, session validation on every request |
| `login_history` | `user_id` | Security dashboard |
| `security_events` | `user_id` | Security audit timeline |

### Other Issues

| Severity | Finding |
|----------|---------|
| 🟡 MEDIUM | **No connection pool sizing** — Default SQLAlchemy pool is 5 connections. A production deployment with > 5 concurrent DB requests will queue and degrade. Recommend `pool_size=10, max_overflow=20`. |
| 🟡 MEDIUM | **Migration chain is PostgreSQL-only from `0004` onward** — Uses `op.alter_column()` (PostgreSQL-specific DDL). Test suite runs `aiosqlite` for some test cases, so the migration chain cannot be exercised in the test environment. |
| 🟢 LOW | **`PredictionAuditLog.model_version_id` FK is always NULL** — Column is defined in the model and migration `0009`, but `save_prediction()` and `log_prediction_to_db()` never populate it. The FK is orphaned in practice. |
| 🟢 LOW | **No composite index** on `user_sessions(user_id, is_revoked, expires_at)` — this 3-way filter is applied on every authenticated request in `get_current_user`. |
| 🟢 LOW | **ER diagram is stale** — `docs/architecture/er_diagram.md` does not reflect the Phase 3 `model_versions` table or the new columns added to `prediction_audit_logs` in migrations `0004` and `0009`. |

### Migration Chain

| Migration | Description | Status |
|-----------|-------------|--------|
| `f496bd7` | Initial schema | ✅ Valid |
| `0002` | Phase 2 user models | ✅ Valid |
| `0003` | Phase 2.2 user fields | ✅ Valid |
| `0004` | Phase 2.3 prediction history columns | ✅ Valid (PostgreSQL only) |
| `0005` | Phase 2.4 report storage | ✅ Valid |
| `0006` | Phase 2.5 notifications | ✅ Valid |
| `0007` | Phase 2.6 security tables | ✅ Valid |
| `0008` | Phase 2.7 data export | ✅ Valid (PostgreSQL only) |
| `0009` | Phase 3.1 model versions | ✅ Valid |

No orphaned migrations. No missing `down_revision` links. No unused migrations.

---

## 5. API Review

### Strengths

- Consistent REST conventions: GET / POST / PATCH / DELETE used appropriately.
- Pagination on all collection endpoints (predictions, reports, notifications).
- Ownership validation on all user-data endpoints — users cannot access other users' records.
- RBAC enforced: model management endpoints require `admin` role.
- OpenAPI documentation auto-generated at `/api/docs`.
- API versioned under `/api/v1/` with `X-API-Key` enforcement.
- All sensitive responses are Pydantic-validated (no raw model dumps).

### Issues

| Severity | Finding |
|----------|---------|
| 🔴 HIGH | **Dockerfile HEALTHCHECK points to `/health` (404)** — The health check is `curl -f http://localhost:8000/health` but the app exposes `/healthz` and `/api/v1/health/ready`. The probe will always return exit code 22 (HTTP 404), causing the container orchestrator (Docker Swarm, ECS, Kubernetes) to permanently mark the container as unhealthy and continuously restart it. |
| 🟡 MEDIUM | **3 dead/stub endpoints registered in `auth/router.py`** — `DELETE /auth/history/{id}` (always 404), `GET /auth/stats` (always returns zeros), `GET /auth/uploads/{id}` (always 404). These appear in OpenAPI docs and mislead consumers. |
| 🟡 MEDIUM | **Potential route conflict on `/api/v1/models`** — `main.py` defines `@v1.get("/models")` reading from a static JSON file, and then includes the models router which also registers routes under `/api/v1/models`. FastAPI registers the first-matched route; the shadow may suppress the new RBAC-protected registry endpoints. Needs verification. |
| 🟡 MEDIUM | **Model promote/rollback doesn't invalidate in-memory cache** — `POST /api/v1/models/promote/{id}` writes to the database but `ModelManager` holds an in-memory cache populated at startup. Promoting a model via API has zero effect on which model is actually used for predictions until the process restarts. |
| 🟢 LOW | **`GET /auth/history` duplicates `GET /api/v1/predictions/history`** — Same data, different schemas, two endpoints. Confusing to consumers. |
| 🟢 LOW | **SHAP endpoint returns 404 without distinction** — `GET /api/v1/predictions/{id}/explanation` returns 404 both when the prediction doesn't exist and when SHAP data was not captured. These are different conditions that clients need to distinguish. |
| 🟢 LOW | **No response caching on read-heavy endpoints** — `/api/v1/predictions/history` and `/api/v1/dashboard` perform fresh DB queries on every call. Adding ETag or short-lived Redis caching would improve responsiveness significantly. |

### Endpoint Completeness

All Phase 1–3 endpoints are reachable and correctly registered. No unreachable routes detected. No circular import issues detected between route modules.

---

## 6. MLOps Review

### Strengths

- `ModelVersion` model covers complete lifecycle: `Training → Staging → Production → Archived → Deprecated`.
- `ModelRegistryService` supports register, promote, rollback, archive, list, and metric comparison.
- SHAP values computed per-prediction and persisted to `prediction_audit_logs.shap_values`.
- `ModelMonitoringService` tracks per-disease inference count, latency p50/p99, and error rate.
- `ModelDriftService` provides drift event recording with severity classification.
- Production-grade A/B testing framework (`ab_testing.py`) with deterministic hash-based bucketing — consistent user assignment regardless of server restart.
- MLflow integration for experiment tracking.

### Issues

| Severity | Finding |
|----------|---------|
| 🟡 MEDIUM | **Two A/B testing implementations coexist** — `ab_testing.py` (correct, deterministic, hash-based) and `ab_testing_service.py` (simple random assignment). Only `ab_testing_service.py` is tested (`test_models.py`). `ab_testing.py` is tested in isolation (`test_ab_testing.py`). Neither is integrated into the live prediction flow. |
| 🟡 MEDIUM | **`ModelManager` does not hot-reload on promotion** — Promoting a new model version via `POST /api/v1/models/promote/{id}` updates the database record but the in-memory `ModelManager` cache is only populated at startup. Serving traffic is unaffected until the process restarts. |
| 🟡 MEDIUM | **Monitoring and drift metrics are process-local** — Both `model_monitoring_service.py` and `model_drift_service.py` maintain counters in Python dictionaries. In a multi-worker gunicorn deployment, each worker maintains independent counters. `GET /api/v1/models/metrics` reflects only the queried worker's traffic. Aggregate metrics will be incorrect by a factor of N workers. |
| 🟡 MEDIUM | **MLflow tracking is filesystem-local** — `.env` configures `MLFLOW_TRACKING_URI=file://mlruns`. The `mlruns/` directory is written to the container filesystem, which is ephemeral. All experiment history is lost on every container restart or deployment. |
| 🟢 LOW | **`model_version_id` FK is always NULL** — `PredictionAuditLog.model_version_id` is defined but `save_prediction()` never sets it. The FK is decorative. |
| 🟢 LOW | **SHAP silently degrades** — `shap_explainer.py` catches all exceptions and returns `{"features": [], "shap_values": [], "base_value": 0.0}`. There is no error counter, no alerting, and no way to distinguish "SHAP unavailable" from "SHAP ran and returned zero features". |

---

## 7. Performance Review

### Strengths

- ML inference offloaded to a thread via `asyncio.to_thread()` with a 5-second timeout.
- `fastapi-cache2` in-memory caching on HTMX prediction result endpoints (1-hour TTL).
- Prometheus metrics instrumented for HTTP duration and prediction probability histograms.
- `pool_pre_ping=True` prevents costly reconnections on idle pool connections.

### Issues

| Severity | Finding |
|----------|---------|
| 🔴 HIGH | **Sync file I/O in async handler** — `main.py:818` calls `open(REGISTRY_PATH)` inside `async def`. Blocks the event loop for the duration of the file read. Under concurrent load, all other requests queue behind this. |
| 🔴 HIGH | **`parse_document()` blocks the event loop** — `document_pipeline.py:51` calls synchronous PyMuPDF/Pillow I/O inside `async def process_report_pipeline()` without `asyncio.to_thread()`. PDF parsing is CPU-bound and takes hundreds of milliseconds, blocking all requests during that window. |
| 🟡 MEDIUM | **No database connection pool sizing** — Default 5-connection pool. Under moderate load with multiple workers, connections will queue. All DB-bound requests will stack up. |
| 🟡 MEDIUM | **Notification written synchronously per prediction** — Each successful prediction dispatches a notification immediately, adding a DB write to the hot prediction path. Under high prediction throughput, this creates write contention on the `notifications` table. |
| 🟡 MEDIUM | **Gunicorn configured with 1 worker** — `Dockerfile CMD` passes `-w 1`. A single worker processes all requests serially for synchronous operations. Even with async, a single worker limits throughput severely. Needs at minimum 2–4 workers scaled to `2*CPU+1`. |
| 🟢 LOW | **No distributed caching** — `fastapi-cache2` uses in-memory (process-local) cache. Cached responses are not shared across workers. A promotion event does not invalidate cache on other workers. |
| 🟢 LOW | **SHAP computed twice** — The HTMX `/explain/*` endpoints recompute SHAP independently from the persisted values in `prediction_audit_logs.shap_values`. Should read from DB instead of recomputing. |

---

## 8. Technical Debt

| Item | Priority | Effort |
|------|----------|--------|
| Implement real email delivery (SMTP/SendGrid/SES) in `EmailProvider` | 🔴 Critical | 1 day |
| Make rate limiting fail-closed (IP-based fallback when Redis down) | 🔴 Critical | 1 day |
| Add DB indexes on `prediction_audit_logs(user_id, disease_model, created_at)` | 🔴 Critical | 2–4 hours |
| Add DB index on `user_sessions(user_id)` | 🔴 Critical | 30 mins |
| Fix Dockerfile health check URL (`/health` → `/healthz`) | 🔴 Critical | 5 mins |
| Wrap `parse_document()` in `asyncio.to_thread()` | 🔴 Critical | 30 mins |
| Replace sync `open(REGISTRY_PATH)` in async route | 🔴 Critical | 1 hour |
| Enforce `API_KEY` env var at startup; remove random fallback | 🔴 Critical | 30 mins |
| Add Content Security Policy header to security middleware | 🔴 Critical | 2 hours |
| Configure MLflow with persistent backend (S3 or managed server) | 🟡 High | 1 day |
| Wire `prediction_pipeline.py` into actual prediction endpoints | 🟡 High | 1 day |
| Consolidate duplicate A/B testing; integrate into prediction flow | 🟡 High | 2–3 days |
| Populate `model_version_id` FK on each prediction | 🟡 High | 2 hours |
| Back monitoring/drift counters with Redis for multi-worker correctness | 🟡 High | 2 days |
| Add `pool_size=10, max_overflow=20` to DB engine config | 🟡 Medium | 5 mins |
| Increase gunicorn workers to `2*CPU+1` in Dockerfile | 🟡 Medium | 5 mins |
| Remove or implement 3 dead stub endpoints in `auth/router.py` | 🟡 Medium | 2 hours |
| Send password reset as signed URL, not plaintext token | 🟡 Medium | 2 hours |
| Implement export file TTL cleanup job | 🟡 Medium | 1 day |
| Add composite index `user_sessions(user_id, is_revoked, expires_at)` | 🟢 Low | 30 mins |
| Add indexes on `login_history(user_id)`, `security_events(user_id)` | 🟢 Low | 30 mins |
| Update ER diagram to include Phase 3 `model_versions` table | 🟢 Low | 1 hour |
| Consolidate root and `backend/requirements.txt` | 🟢 Low | 30 mins |
| SHAP `/explain/*` endpoints should read from DB, not recompute | 🟢 Low | 2 hours |
| Distinguish "prediction not found" from "SHAP unavailable" (404 vs 200 with null) | 🟢 Low | 1 hour |

---

## 9. Production Risks

| Risk | Likelihood | Impact | Status |
|------|------------|--------|--------|
| Rate limiting fully disabled if Redis unavailable | HIGH | CRITICAL — brute force attack surface opened | Unmitigated |
| Email delivery non-functional (dev stub) | HIGH | HIGH — users cannot reset passwords | Unmitigated |
| Event loop blocked by sync file/PDF I/O | MEDIUM | HIGH — latency spikes; request queuing under load | Unmitigated |
| Missing DB indexes on hot query columns | HIGH | HIGH — full table scans degrade at > 10k records | Unmitigated |
| Container health check always fails | HIGH | HIGH — orchestrator restarts healthy container in loop | Unmitigated |
| API_KEY random per-process when env var absent | LOW | HIGH — all v1 API clients break after restart | Unmitigated |
| No CSP header | HIGH | HIGH — healthcare data exfiltration via XSS from CDN | Unmitigated |
| MLflow data ephemeral in container | HIGH | MEDIUM — all experiment history lost on redeploy | Unmitigated |
| Multi-worker monitoring metrics incorrect | MEDIUM | MEDIUM — misleading dashboards; silent model degradation | Unmitigated |
| `exports_data/` grows unbounded | MEDIUM | MEDIUM — disk exhaustion | Unmitigated |
| Model promote via API has no effect until restart | MEDIUM | MEDIUM — operators believe new model is serving, but it isn't | Unmitigated |
| Password reset broken (token never saved to DB) | N/A | CRITICAL | **Fixed during audit** |

---

## 10. Recommended Improvements

### Before RC2 (Blockers — must fix before any production deployment)

1. **~~FIXED~~: `db.add(reset)` in `password_reset_request()`** — added during audit.
2. **Real email provider**: Integrate SMTP, SendGrid, AWS SES, or equivalent. The development stub in `EmailProvider.send()` must be replaced before any user can complete a password reset.
3. **Fail-closed rate limiting**: When Redis is unavailable, fall back to an IP-based in-process throttle (e.g., `slowapi` with in-memory storage) rather than disabling rate limiting entirely. Auth endpoints must always be throttled.
4. **Database indexes**: Add the following indexes via a new Alembic migration:
   - `CREATE INDEX CONCURRENTLY ON prediction_audit_logs(user_id);`
   - `CREATE INDEX CONCURRENTLY ON prediction_audit_logs(disease_model);`
   - `CREATE INDEX CONCURRENTLY ON prediction_audit_logs(created_at DESC);`
   - `CREATE INDEX CONCURRENTLY ON user_sessions(user_id);`
5. **Dockerfile health check**: Change `HEALTHCHECK CMD curl -f http://localhost:8000/health` to `curl -f http://localhost:8000/healthz`.
6. **Async document parsing**: Wrap `parse_document()` call in `document_pipeline.py` with `asyncio.to_thread()`.
7. **Enforce API_KEY at startup**: If `API_KEY` is not set in production environment, log a critical error and refuse to start (or at minimum log a prominent warning and disable the `/api/v1` routes).
8. **Content Security Policy**: Add a strict CSP header to `SecurityHeadersMiddleware`:
   ```
   Content-Security-Policy: default-src 'self'; script-src 'self' cdn.jsdelivr.net unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:;
   ```

### High Priority (strongly recommended before production)

9. Replace the synchronous `open(REGISTRY_PATH)` file read in the async `/api/v1/models` legacy route with a query to the new `ModelRegistryService`.
10. Configure MLflow with a persistent backend: S3 artifact store + PostgreSQL tracking server. Document the `MLFLOW_TRACKING_URI` change in `.env.example`.
11. Add `pool_size=10, max_overflow=20` to the `create_async_engine()` call in `database.py`.
12. Increase gunicorn workers in `Dockerfile` to `2*$(nproc)+1` (minimum 2).
13. Remove or implement the 3 dead stub auth endpoints (`DELETE /auth/history/{id}`, `GET /auth/stats`, `GET /auth/uploads/{id}`).
14. Send password reset token as a signed URL (`/auth/password-reset-confirm?token=<raw_token>`) rather than embedding the plaintext token in a notification message.

---

## 11. Final Release Score

| Category | Score | Key Findings |
|----------|-------|-------------|
| Architecture | 75/100 | Clean layers; duplicate A/B; unused prediction pipeline |
| Security | 52/100 | Critical bug fixed; email stub; rate limit bypass; no CSP |
| Database | 62/100 | Missing 6 critical indexes; no pool sizing; migrations valid |
| API Design | 68/100 | Consistent; dead endpoints; health check mismatch; route conflict |
| MLOps | 70/100 | Well-designed registry; not wired to predictions; process-local metrics |
| Performance | 58/100 | Blocking sync in async paths; no pool; 1 gunicorn worker |
| Testing | 80/100 | 289 tests passing; good integration coverage; no load tests |
| Documentation | 72/100 | README solid; ER diagram stale; no operations runbook |
| Error Handling | 75/100 | HTTPExceptions consistent; SHAP silent degradation |
| Logging | 78/100 | structlog configured; audit trail complete; no log aggregation setup |
| Maintainability | 74/100 | Clean code; service duplication; two requirements files |
| **WEIGHTED TOTAL** | **67/100** | |

---

## Final Answer

### ❌ NO — This project is NOT approved for deployment to production.

**8 blocking issues must be resolved before RC2 approval:**

| # | Blocker | File |
|---|---------|------|
| 1 | ~~Password reset token never persisted to DB~~ | **FIXED: `auth/router.py`** |
| 2 | Email provider is a development stub — users cannot reset passwords | `services/notifications/providers/email.py` |
| 3 | Rate limiting silently disabled when Redis is unavailable — auth endpoints unthrottled | `api/dependencies.py` |
| 4 | Missing DB indexes on `prediction_audit_logs(user_id, disease_model, created_at)` | New Alembic migration required |
| 5 | Missing DB index on `user_sessions(user_id)` | New Alembic migration required |
| 6 | Dockerfile HEALTHCHECK points to `/health` (returns 404), not `/healthz` | `Dockerfile` |
| 7 | `parse_document()` blocks the async event loop — latency degrades all requests during PDF processing | `services/document_pipeline.py` |
| 8 | No Content Security Policy header — healthcare application with CDN-hosted JS is vulnerable to XSS | `middleware/security_headers.py` |

---

*Post-deployment monitoring tasks will be listed here once all blockers are resolved and RC2 is approved.*
