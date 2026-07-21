# Checkpoint 2 — Database & Migrations

## Environment
- **DB**: SQLite (local disposable copy for audit)
- **Migration tool**: Alembic 1.x with async support
- **ORM**: SQLAlchemy 2.0 async

---

## Alembic Integrity

| Check | Result |
|---|---|
| `alembic history` | 17 revisions, clean linear chain |
| `alembic heads` | Single head: `0017` |
| `alembic current` | At head (fresh upgrade) |
| `alembic upgrade head` (from scratch) | **PASS** — 26 tables created, no errors |
| `alembic check` | **PASS** — "No new upgrade operations detected" |
| Branch points | **None** — linear chain base → `f496bd7cc74d` → `0002` → ... → `0017` |
| Merge/revision conflicts | **None** |

---

## Schema vs Models

| Metric | Result |
|---|---|
| Models registered in `Base.metadata` | **26** |
| Tables in actual DB | **26** |
| Tables only in DB (not in models) | **None** |
| Tables only in models (not in DB) | **None** |
| Column mismatches | **None** — all 26 tables match model definitions |
| Tables without primary keys | **None** |

---

## Foreign Keys (30 total)

All FKs have explicit `ON DELETE` behavior:

| Behavior | Count | Examples |
|---|---|---|
| `ON DELETE CASCADE` | 17 | `memberships.tenant_id → tenants.id`, `user_sessions.user_id → users.id`, `api_keys.tenant_id → tenants.id` |
| `ON DELETE SET NULL` | 10 | `admin_actions.admin_id → users.id`, `prediction_audit_logs.user_id → users.id`, `audit_events.tenant_id → tenants.id` |

**No FKs use `NO ACTION` or `RESTRICT`** — explicit cascade/nullify is always set.

---

## Indexes & Constraints

| Table | Indexes | Unique Constraints | Notes |
|---|---|---|---|
| `api_keys` | 3 | 1 | `key_hash` unique — good |
| `audit_events` | 8 | 0 | Heavily indexed (expected for audit) |
| `users` | 1 | 0 | Email unique — enforced in Python, not DB |
| `tenants` | 1 | 0 | Slug unique — enforced in Python |
| `memberships` | 0 | 0 | **No composite unique on (tenant_id, user_id)** — potential duplicate memberships |
| `prediction_audit_logs` | 0 | 0 | **No indexes** — querying by user_id/tenant_id will be slow at scale |
| `login_history` | 0 | 0 | **No indexes** |
| `user_sessions` | 1 | 0 | OK |
| `user_reports` | 2 | 0 | OK |

**Notable gaps:**
- `memberships` lacks a unique constraint on `(tenant_id, user_id)` — a user could be added as OWNER twice.
- `prediction_audit_logs` has **zero indexes** — no index on `user_id`, `tenant_id`, or `created_at`. This table is queried by `/auth/history` and `/auth/stats`.
- `login_history` has **zero indexes** — no index on `user_id` or `created_at`.

---

## env.py Configuration

| Setting | Value |
|---|---|
| `render_as_batch` | `True` (when SQLite) — required for ALTER TABLE |
| `compare_type` | `True` — detects column type changes |
| `compare_server_default` | `True` — detects default changes |
| SQLite fallback | Creates all tables via `Base.metadata.create_all()` + stamps to head |

---

## Findings

| Severity | Count | Details |
|---|---|---|
| **Critical** | 0 | — |
| **High** | 0 | — |
| **Medium** | 0 | ~~All 3 index/constraint findings fixed~~ |
| **Low** | 0 | ~~Typo fixed~~ |

## Fixes Applied

| # | Finding | File(s) | Fix |
|---|---|---|---|
| M1 | Missing index on `prediction_audit_logs` | `models/prediction.py` | Added `__table_args__` with indexes on `user_id`, `tenant_id`, `created_at` |
| M2 | Missing index on `login_history` | `models/user.py` | Added `__table_args__` with indexes on `user_id`, `created_at` |
| M3 | Missing unique constraint on `memberships` | `models/tenant.py` | Added `UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user")` |
| L1 | Typo "suppored" → "supported" | `migrations/env.py:87` | Fixed typo |
