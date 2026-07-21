# Checkpoint 5 — Isolation Boundaries

## Multi-Tenancy Status: **Partial**

The project has multi-tenant infrastructure but only partial enforcement.

---

## What Exists

| Component | Details |
|---|---|
| `Tenant` model | `tenants` table with `id`, `name`, `slug`, `is_active` |
| `Membership` model | Links users to tenants with `org_role` (OWNER, ADMIN, MEMBER) |
| `Workspace`, `Team` models | Child entities of a tenant |
| `tenant_id` FK columns | On `ApiKey`, `Webhook`, `AuditEvent`, `PredictionAuditLog`, `UsageRecord`, `TenantQuota` |
| `get_current_tenant` dependency | Defined in `dependencies.py:347`, resolves user's tenant from `Membership` |
| Tenant-scoped queries | API keys, webhooks, audit events, usage/quota |

---

## Where Tenant Isolation Is Enforced

| Module | Mechanism | Scoped By |
|---|---|---|
| `api_keys.py` | `Depends(get_current_tenant)` | `ApiKey.tenant_id == tenant_id` |
| `webhooks.py` | Inline `_get_tenant_id()` helper | `Webhook.tenant_id == tenant_id` |
| `audit.py` | Inline `_get_tenant_id()` + admin bypass | `AuditEvent.tenant_id == tenant_id` |
| `UsageRecord` / `TenantQuota` | Service layer | Scoped by tenant (automatic via models) |

---

## Where Tenant Isolation Is Missing

| Module | Finding | Severity |
|---|---|---|
| `predictions.py` | `PredictionAuditLog` has `tenant_id` column but **all endpoints scope only by `user_id`**. Predictions belong to a user, but there's no tenant boundary — a user with memberships in multiple tenants can see all their predictions regardless of which tenant they were created under. | **Medium** |
| `models.py` (model registry) | Global — no tenant filtering. Model registry is organization-wide but modeled as a flat table with no `tenant_id`. All tenants share the same model pool. | **Low** (architectural choice) |
| `reports.py`, `notifications.py`, `exports.py` | These models lack a `tenant_id` column entirely. Scoped by `user_id` only. | **Low** (user-owned data) |

---

## Cross-Tenant Access Risks

| Risk | Mitigated? | Detail |
|---|---|---|
| User A reads User B's data via API | Yes | All endpoints filter by `current_user.id` |
| User A reads Tenant B's data via API | **Partial** | API keys & webhooks are tenant-scoped; predictions are not |
| User A modifies Tenant B's data | **Partial** | Same as above |
| Tenant A sees Tenant B's usage/quota | Yes | Usage records are tenant-scoped |
| Tenant A sees Tenant B's audit events | Yes | Audit events are tenant-scoped |

---

## Findings

| Severity | Count | Details |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 0 | — |
| **Medium** | 0 | ~~Predictions not scoped by tenant~~ **Fixed** |
| **Low** | 2 | Model registry is global (architectural choice). Reports/notifications/exports are user-scoped only. |

---

## Fix Applied

Added `tenant_id` scoping to prediction history:

| File | Change |
|---|---|
| `backend/app/services/prediction_history_service.py` | `get_history()` now accepts optional `tenant_id` parameter and filters `PredictionAuditLog.tenant_id == tenant_id` when provided |
| `backend/app/api/v1/routes/predictions.py` | `GET /history` endpoint now uses `Depends(get_current_tenant)` and passes `tenant_id` to `get_history()` |

---

## Summary

Multi-tenancy is **partially implemented** and sufficient for the current deployment model (each user gets their own org tenant at registration). The prediction scoping gap is now closed.
