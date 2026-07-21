# Bandit Review

## Summary

3 Bandit B608 (hardcoded_sql_expressions) findings — all in Alembic migration file `0012_phase6_1_multi_tenancy.py`. All classified as **False Positive**. Suppressed with inline `# nosec B608` comments.

---

## Finding 1 — Insert Default Tenant

| Field | Value |
|-------|-------|
| **File** | `backend/migrations/versions/0012_phase6_1_multi_tenancy.py:79` |
| **Code** | `f"INSERT INTO tenants (id, name, slug, is_active, ...)"` |
| **Severity** | Medium |
| **Classification** | **False Positive** |
| **Exploitable** | No |
| **Suppression** | `# nosec B608` on line 79 |

**Why it is NOT exploitable:**
- Executed only during Alembic migration (one-time, not at runtime)
- `default_tenant_id` is `uuid.uuid4()` — generated server-side, no user input
- All values are hardcoded literals (`'Default Organization'`, `'default-org'`, `true`)
- `now` is `datetime.now(timezone.utc)` — generated server-side

---

## Finding 2 — Update Existing Tables with Tenant ID

| Field | Value |
|-------|-------|
| **File** | `backend/migrations/versions/0012_phase6_1_multi_tenancy.py:108` |
| **Code** | `f"UPDATE {table} SET tenant_id = '{default_tenant_id}'"` |
| **Severity** | Medium |
| **Classification** | **False Positive** |
| **Exploitable** | No |
| **Suppression** | `# nosec B608` on line 108 |

**Why it is NOT exploitable:**
- Executed only during Alembic migration (one-time, not at runtime)
- `table` iterates over a hardcoded list of table names (lines 89-98), not user input
- `default_tenant_id` is `uuid.uuid4()` — generated server-side
- No runtime request context exists during migrations

---

## Finding 3 — Create Memberships for Existing Users

| Field | Value |
|-------|-------|
| **File** | `backend/migrations/versions/0012_phase6_1_multi_tenancy.py:113` |
| **Code** | `f"INSERT INTO memberships (id, tenant_id, user_id, ...)"` |
| **Severity** | Medium |
| **Classification** | **False Positive** |
| **Exploitable** | No |
| **Suppression** | `# nosec B608` on line 113 |

**Why it is NOT exploitable:**
- Executed only during Alembic migration (one-time, not at runtime)
- User IDs come from `SELECT ... FROM users` (trusted database data)
- `default_tenant_id` is `uuid.uuid4()` — generated server-side
- `'MEMBER'` is a hardcoded literal
- All values are trusted at migration time

---

## Verification

| Check | Result |
|-------|--------|
| `bandit -r backend/ -ll` | ✅ Exit 0 — No issues identified |
| `flake8 backend/` | ✅ 0 errors |
| `black --check backend/` | ✅ 148 files unchanged |
| `mypy backend/` | ✅ 0 errors |
| `python -c "from backend.app.main import app"` | ✅ App imports successfully |

**Bandit metrics after fix:**
- Total issues skipped via `# nosec B608`: **3**
- Remaining Medium severity findings: **0**
- High severity findings: **0**
