# Architecture Review: Healthcare-Risk-Prediction

## 1. Audit Module Boundaries

**Files reviewed:** `audit_service.py`, `audit_retention_service.py`, `audit.py` (routes), `webhook_delivery_service.py`, `security_service.py`

### Finding: Verified — with one issue

The three audit files (`audit_service.py`, `audit_retention_service.py`, `audit.py`) follow single-responsibility boundaries correctly:

| File | Role | Cross-cutting concerns? |
|---|---|---|
| `backend/app/services/audit_service.py` | Write/query/export audit events | No overlap with webhook or security services |
| `backend/app/services/audit_retention_service.py` | CRUD retention policies + purge logic | No overlap |
| `backend/app/api/v1/routes/audit.py` | HTTP layer delegating to both services | No overlap |

No logic from `audit_service.py` is duplicated in `webhook_delivery_service.py` or `security_service.py` — those are entirely different domains (webhook delivery orchestration and user session management respectively).

**Issue — Duplicated constant:**
- `DEFAULT_RETENTION_DAYS = 365` is defined in both:
  - `backend/app/services/audit_service.py:16` (imported but never used there)
  - `backend/app/services/audit_retention_service.py:13` (actively used at line 65)
  
  `audit_service.py` does not reference its own definition, making it dead code drift.

**Route bypasses service layer:**
- `audit.py:121` calls `db.get(AuditEvent, event_id)` directly instead of delegating to `audit_service.query(…)`. This bypasses any future service-layer caches, hooks, or authorization checks.

---

## 2. Service Single Responsibility

**Files reviewed:** All 11 service files listed.

### Finding: Verified — each service has a clear, single purpose

| Service | Responsibility | Assessment |
|---|---|---|
| `webhook_service.py` | CRUD for webhook subscriptions | ✅ Pure CRUD |
| `webhook_delivery_service.py` | Delivery orchestration, retry logic, event history | ✅ Focused — though also queries events (line 89), which is a minor query concern mixed with command |
| `webhook_security_service.py` | HMAC signing, secret generation/rotation | ✅ Pure security helper |
| `audit_service.py` | Audit event write + query + export + stats | ✅ Cohesive — all audit-related; export/stats are natural extensions |
| `audit_retention_service.py` | Retention policy CRUD + purge execution | ✅ Cohesive |
| `api_key_service.py` | API key lifecycle (create, validate, revoke, rotate) | ✅ Cohesive |
| `authorization_service.py` | Permission definitions + RBAC checks | ✅ Pure policy logic |
| `quota_service.py` | Tenant quota management + Redis caching | ✅ Cohesive (caching is an optimization, not a separate concern) |
| `rate_limit_service.py` | Redis-backed rate limiting with in-memory fallback | ✅ Focused — but imports `QuotaService` for default limits (line 108), a minor coupling |
| `usage_analytics_service.py` | Usage tracking + endpoint/daily breakdowns | ✅ Cohesive |
| `security_service.py` | Session management + login history + security events | ✅ Cohesive |

**Minor concern:** `audit_service` mixes write (`log`, `log_mutation`), read (`query`), and presentation (`export_csv`, `get_stats`) concerns. This could be split into `AuditWriter` / `AuditReader` as the project grows, but remains manageable today.

---

## 3. Circular Dependencies

**Files reviewed:** `dependencies.py`, `auth/router.py`, all service files, all route files.

### Finding: Verified with annotations

**No hard circular import chains exist** — the import graph is acyclic at module load time. However, **3 soft circular patterns** (lazy imports inside methods) were found, indicating areas where refactoring would improve isolation:

| File | Line | Lazy import | Why |
|---|---|---|---|
| `webhook_security_service.py` | 30 | `from backend.app.services.webhook_service import WebhookService` | `webhook_service.py:8` imports `webhook_security_service` at module level → if this import were also module-level, it would be a true cycle |
| `webhook_delivery_service.py` | 97, 128 | `from backend.app.services.webhook_service import WebhookService` | `webhook_delivery_service.py` does not import `webhook_service` at module level — this is one-directional and safe |
| `rate_limit_service.py` | 108, 199 | `from backend.app.services.quota_service import QuotaService` | `quota_service.py` does not import `rate_limit_service` — one-directional and safe |

The `webhook_service` → `webhook_security_service` → (lazy) `webhook_service` pattern (`backend/app/services/webhook_service.py:8` ↔ `backend/app/services/webhook_security_service.py:30`) is the only reciprocal dependency. It works at runtime because `webhook_security_service.rotate_secret` imports lazily, but it is architecturally fragile.

**Import flow:**
```
auth/router.py
  → dependencies.py
  → core/database.py (get_db)
  → core/enums.py (UserRole)
  → models/tenant.py (Membership)
  → services/authorization_service.py

route files
  → auth/router.py (get_current_user)
  → dependencies.py (RequireRole, get_current_tenant)
  → core/database.py (get_db)
```

`dependencies.py` does **not** import from `auth/router.py`, so the `dependencies.py` ↔ `auth/router.py` relationship is strictly one-way.

---

## 4. Dependency Injection Consistency

**Files reviewed:** `audit.py`, `webhooks.py`, `api_keys.py`, `users.py`, `predictions.py`, `security.py`, `reports.py`, `notifications.py`, `exports.py`

### Finding: Configuration Reviewed — two inconsistent patterns for Tenant ID

**Consistent patterns (verified across all route files):**

| Dependency | Source module | Used consistently? |
|---|---|---|
| `get_current_user` | `backend.app.auth.router` | ✅ All routes use this identical import |
| `get_db` | `backend.app.core.database` | ✅ All routes use this identical import |
| `RequireRole` | `backend.app.api.dependencies` | ✅ All admin routes use this |
| `RequirePermission` | `backend.app.api.dependencies` | ✅ Used in `api_keys.py` |
| `params: XxxQueryParams = Depends()` | Inline in routes | ✅ Used in reports, predictions, notifications, security |

**Inconsistent — Tenant ID resolution (3 implementations):**

| Implementation | File | Lines | Behavior |
|---|---|---|---|
| `Depends(get_current_tenant)` | `backend/app/api/dependencies.py` | 347–369 | Raises 403 if no tenant; returns `uuid.UUID` |
| `_get_tenant_id()` (local) | `backend/app/api/v1/routes/webhooks.py` | 33–45 | Raises 403 if no tenant; returns `UUID` |
| `_get_tenant_id()` (local) | `backend/app/api/v1/routes/audit.py` | 33–41 | Returns `None` for admin/super_admin; returns `Optional[UUID]` |

`get_current_tenant` from `dependencies.py` is only used by `api_keys.py`. The `webhooks.py` and `audit.py` routes define their own local versions, each querying `select(Membership.tenant_id)...limit(1)`. This triplication is the single largest DI inconsistency in the codebase.

**Audit route parameter ordering inconsistency:**
- `audit.py:55` uses `current_user: User = Depends(get_current_user)` as the second-to-last parameter before `db`
- `webhooks.py:53` uses `current_user: User = Depends(get_current_user)` in the same position
- `api_keys.py:29` places `current_user` first, then `tenant_id`, then `db`
- Most routes follow the pattern: `current_user` → `db` (last), but the order of `params` vs `current_user` vs `db` varies

---

## 5. Duplicate Logic

### Finding: Not Verified — 4 distinct duplication classes found

#### 5a. Tenant ID Resolution (triplicated)

Three implementations of `select(Membership.tenant_id)...limit(1)`:
- `backend/app/api/v1/routes/webhooks.py:33-45`
- `backend/app/api/v1/routes/audit.py:33-41`
- `backend/app/api/dependencies.py:347-369`

The `dependencies.py` version is a shared DI function, yet only `api_keys.py` uses it.

#### 5b. Pagination formula (11 occurrences)

The expression `math.ceil(total / size) if total > 0 else 0` appears verbatim or near-verbatim in:

- `backend/app/api/v1/routes/webhooks.py:60`
- `backend/app/api/v1/routes/webhooks.py:237`
- `backend/app/api/v1/routes/audit.py:72`
- `backend/app/api/v1/routes/notifications.py:61`
- `backend/app/api/v1/routes/reports.py:142`
- `backend/app/services/security_service.py:59`
- `backend/app/services/security_service.py:140`
- `backend/app/services/security_service.py:172`
- `backend/app/services/prediction_history_service.py:130`
- `backend/app/services/exports/export_service.py:171`
- `backend/app/services/admin/users_service.py:29`

No shared pagination utility or base class exists. Each route/service re-implements the same formula.

#### 5c. IP address extraction (3 patterns)

- `audit_service.py:21-33`: `_extract_request_meta` — parses `x-forwarded-for` header or falls back to `request.client.host`
- `auth/router.py:128-129`: `_get_ip` — returns `request.client.host` only (no `x-forwarded-for` parsing)
- `dependencies.py:94-96`: inside `_in_memory_rate_limit` — parses `x-forwarded-for` similar to audit_service but inline

The `auth/router.py` version lacks `x-forwarded-for` support, which may produce incorrect client IPs behind a proxy.

#### 5d. `DEFAULT_RETENTION_DAYS` constant

Defined in `audit_service.py:16` (unused) and `audit_retention_service.py:13` (actively used). The copy in `audit_service.py` is dead code.

---

## Summary

| # | Area | Verdict | Key issue |
|---|---|---|---|
| 1 | Audit module boundaries | **Verified** (1 minor) | `DEFAULT_RETENTION_DAYS` duplicated; route bypasses service layer |
| 2 | Service single responsibility | **Verified** | All services have clear single purposes |
| 3 | Circular dependencies | **Verified** (with notes) | 1 soft circular pattern (`webhook_service` ↔ `webhook_security_service`) |
| 4 | Dependency injection consistency | **Configuration Reviewed** | Tenant ID resolution has 3 implementations; only `api_keys.py` uses the shared `get_current_tenant` |
| 5 | Duplicate logic | **Not Verified** | Pagination (11×), tenant resolution (3×), IP extraction (3×), dead constant |
