# Performance Review — HealthPredict AI (RC2)

**Version:** 3.1.0 (RC2) | **Date:** 2026-07-12

---

## 1. Async Event Loop — Blocking Call Elimination

### Problem (RC1)
Two synchronous, CPU-bound operations were called directly inside `async def` functions, blocking the entire event loop for their duration:

| Location | Operation | Typical Latency |
|----------|-----------|----------------|
| `document_pipeline.py:51` | `parse_document()` (PyMuPDF/Pillow) | 200–2000 ms |
| `document_pipeline.py:87` | `extract_clinical_entities()` (NLP) | 50–500 ms |
| `main.py:818` | `open(REGISTRY_PATH)` file read | 1–10 ms |

During these operations, **zero other requests could be served** by the worker.

### Fix (RC2)

All three are now offloaded to the thread pool via `asyncio.to_thread()`:

```python
# Before (blocking)
raw_text = parse_document(file_bytes, report.mime_type)

# After (non-blocking)
raw_text = await asyncio.to_thread(parse_document, file_bytes, report.mime_type)
```

The event loop remains free to serve other requests while document processing runs in a thread pool worker.

---

## 2. Database — Connection Pool

### Problem (RC1)
`create_async_engine()` was called with default pool size of **5 connections**. Under modest load (> 5 concurrent DB-bound requests), connections would queue and response times would spike.

### Fix (RC2)

`backend/app/core/database.py`:

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,      # default: 10
    max_overflow=settings.db_max_overflow, # default: 20
    pool_pre_ping=True,
)
```

**Effective capacity:** 30 concurrent DB connections (10 base + 20 overflow).

Configurable via environment:
```bash
DB_POOL_SIZE=10       # base pool (persistent connections)
DB_MAX_OVERFLOW=20    # burst connections (closed when idle)
```

---

## 3. Database — Critical Indexes Added (Migration 0010)

### Problem (RC1)
Six high-frequency query columns had no database index. Every user-scoped query performed a **full sequential scan** of the table.

### Indexes Added

| Table | Column(s) | Query Pattern |
|-------|-----------|--------------|
| `prediction_audit_logs` | `user_id` | All history, dashboard, export queries |
| `prediction_audit_logs` | `disease_model` | Filtered history (`?disease=diabetes`) |
| `prediction_audit_logs` | `created_at` | All `ORDER BY` + date-range queries |
| `user_sessions` | `user_id` | `GET /auth/sessions`, session validation |
| `user_sessions` | `(user_id, is_revoked, expires_at)` | Composite for `get_current_user` |
| `login_history` | `user_id` | Security dashboard |
| `security_events` | `user_id` | Security audit timeline |

**Expected impact:** Query time on `prediction_audit_logs` with 100k records drops from ~300ms (sequential scan) to ~1ms (index scan) for user-scoped queries.

---

## 4. Gunicorn Workers

### Problem (RC1)
Dockerfile used `-w 1` (single worker). One synchronous operation serialised all requests.

### Fix (RC2)
Increased to `-w 2` (minimum for production). Scale to `2*$(nproc)+1` in orchestration:

```bash
# Kubernetes: recommended env-driven worker count
CMD ["sh", "-c", "gunicorn backend.app.main:app \
  -w ${WEB_CONCURRENCY:-2} \
  -k uvicorn.workers.UvicornWorker \
  ..."]
```

---

## 5. Remaining Performance Opportunities (Post-RC2)

| Item | Priority | Notes |
|------|----------|-------|
| Redis cache for prediction history | Medium | Currently in-memory, process-local |
| Model promote triggers in-memory reload | Medium | Currently requires process restart |
| Monitoring metrics backed by Redis | Medium | Currently process-local counters |
| SHAP `/explain/*` reads DB instead of recomputing | Low | Minor latency saving |
| MLflow persistent backend (S3) | High | Currently filesystem-ephemeral in containers |
| Export file TTL cleanup | Medium | `exports_data/` grows unbounded |
