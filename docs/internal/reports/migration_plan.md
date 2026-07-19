# Migration Plan: Phase 1 (Auth & User Management)

## 1. Current Schema (SQLite)

Currently, the application relies on an ad-hoc SQLite database (`data/interim/audit_log.db`) initialized via `init_auth_db()` in `backend/app/auth/router.py`.

**Tables:**
1. `users`
   - `id` (TEXT, PRIMARY KEY)
   - `email` (TEXT, UNIQUE)
   - `full_name` (TEXT)
   - `password_hash` (TEXT)
   - `created_at` (TEXT)

2. `auth_sessions`
   - `id` (TEXT, PRIMARY KEY)
   - `user_id` (TEXT, FOREIGN KEY)
   - `refresh_token_hash` (TEXT, UNIQUE)
   - `user_agent` (TEXT)
   - `created_at` (TEXT)
   - `expires_at` (TEXT)
   - `revoked` (INTEGER)

3. `prediction_audit_logs`
   - `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
   - `request_id` (TEXT)
   - `user_id` (TEXT)
   - `disease_model` (TEXT)
   - `source` (TEXT)
   - `risk_percentage` (REAL)
   - `risk_level` (TEXT)
   - `input_json` (TEXT)
   - `created_at` (TEXT)

## 2. Target Schema (PostgreSQL via SQLAlchemy 2.0)

We will introduce PostgreSQL as the sole database. Alembic will manage migrations.

**New & Modified Tables:**

1. `users`
   - `id` (UUID, PRIMARY KEY)
   - `email` (VARCHAR, UNIQUE, INDEXED)
   - `full_name` (VARCHAR, NULLABLE)
   - `password_hash` (VARCHAR)
   - `role` (VARCHAR, DEFAULT 'user')  *// ENUM or VARCHAR: 'user', 'admin', 'super_admin'*
   - `is_active` (BOOLEAN, DEFAULT TRUE)
   - `is_verified` (BOOLEAN, DEFAULT FALSE)
   - `created_at` (TIMESTAMP WITH TIME ZONE)
   - `updated_at` (TIMESTAMP WITH TIME ZONE)

2. `user_sessions`
   - `id` (UUID, PRIMARY KEY)
   - `user_id` (UUID, FOREIGN KEY -> users.id)
   - `refresh_token_hash` (VARCHAR, UNIQUE)
   - `ip_address` (VARCHAR, NULLABLE)
   - `user_agent` (VARCHAR, NULLABLE)
   - `is_revoked` (BOOLEAN, DEFAULT FALSE)
   - `expires_at` (TIMESTAMP WITH TIME ZONE)
   - `created_at` (TIMESTAMP WITH TIME ZONE)

3. `password_reset_tokens`
   - `id` (UUID, PRIMARY KEY)
   - `user_id` (UUID, FOREIGN KEY -> users.id)
   - `token_hash` (VARCHAR, UNIQUE)
   - `is_used` (BOOLEAN, DEFAULT FALSE)
   - `expires_at` (TIMESTAMP WITH TIME ZONE)
   - `created_at` (TIMESTAMP WITH TIME ZONE)

4. `email_verification_tokens`
   - `id` (UUID, PRIMARY KEY)
   - `user_id` (UUID, FOREIGN KEY -> users.id)
   - `token_hash` (VARCHAR, UNIQUE)
   - `is_used` (BOOLEAN, DEFAULT FALSE)
   - `expires_at` (TIMESTAMP WITH TIME ZONE)
   - `created_at` (TIMESTAMP WITH TIME ZONE)

5. `audit_logs` *(Auth & Security Logging)*
   - `id` (UUID, PRIMARY KEY)
   - `user_id` (UUID, FOREIGN KEY -> users.id, NULLABLE)
   - `action` (VARCHAR) *(e.g., 'login', 'logout', 'failed_login', 'password_change', 'role_change')*
   - `ip_address` (VARCHAR, NULLABLE)
   - `details` (JSONB, NULLABLE)
   - `timestamp` (TIMESTAMP WITH TIME ZONE)

6. `predictions` *(Migrated from prediction_audit_logs to maintain APIs)*
   - We will preserve the schema structure of `prediction_audit_logs` in PostgreSQL to ensure legacy APIs and endpoints do not break.
   - `id` (INTEGER / UUID, PRIMARY KEY)
   - `request_id` (UUID, NULLABLE)
   - `user_id` (UUID, FOREIGN KEY -> users.id, NULLABLE)
   - `disease_model` (VARCHAR)
   - `source` (VARCHAR)
   - `risk_percentage` (FLOAT)
   - `risk_level` (VARCHAR)
   - `input_json` (JSONB)
   - `created_at` (TIMESTAMP WITH TIME ZONE)

## 3. Migration Steps

1. **Scaffold Alembic & SQLAlchemy:**
   - Install `asyncpg`, `sqlalchemy`, `alembic`, `bcrypt`, `passlib`, `pyjwt`.
   - Initialize Alembic (`alembic init -t async migrations`).
   - Create the SQLAlchemy Base and models in `backend/app/models/`.

2. **Generate Initial Migration:**
   - Run `alembic revision --autogenerate -m "Initial schema"` to create the tables.

3. **Data Migration (SQLite -> PostgreSQL):**
   - Write a one-off Python script (`scripts/migrate_sqlite_to_pg.py`) that:
     1. Connects to the legacy SQLite database.
     2. Connects to the new PostgreSQL database.
     3. Copies over `users`, `auth_sessions`, and `prediction_audit_logs` directly, transforming string timestamps to `TIMESTAMP WITH TIME ZONE` and `id`s to UUID where applicable. Default new fields (`role`, `is_active`) will be injected during insertion.

4. **Service Layer Updates:**
   - Deprecate `init_auth_db()` entirely.
   - Update `backend/app/auth/router.py` (and potentially `legacy_main.py`/`main.py`) to use `AsyncSession` dependencies instead of direct `sqlite3` connections.
   - Update `get_current_user` to rely on the new DB schema.
   - Add bcrypt hashing (`passlib`) to replace whatever custom hashing might exist.
   - Integrate `AuditLog` into auth actions transactionally.

## 4. Rollback Strategy

If Phase 1 fails or causes critical errors during testing/deployment:
1. **Database Reversion**: Ensure the `DATABASE_URL` environment variable is pointed back to a known-good SQLite state, or restore PostgreSQL from a snapshot taken before the migration script ran.
2. **Code Reversion**: Since this is developed on a separate Git branch (`phase-1-auth`), rolling back is as simple as checking out the `main` branch.
3. **Alembic Downgrade**: If testing against the same Postgres instance, run `alembic downgrade base` to wipe the schema before reverting branch code.

## 5. Validation Plan

1. **Docker / Postgres Check**: Ensure Docker Compose boots correctly with the new Postgres database image.
2. **Migrations Check**: Run `alembic upgrade head` and `alembic downgrade base` to ensure both directions succeed cleanly.
3. **API Contracts Check**: Run existing tests (`pytest`). Legacy prediction endpoints and legacy login must still respond correctly (or deprecated alternatives must respond exactly as HTMX expects).
4. **Auth Flow Check**: 
   - Register a user.
   - Login and receive a JWT + Refresh Token.
   - Test refresh token reuse (must revoke all active sessions).
   - Test password reset flow (generates token, consumes token once).
   - Check `AuditLog` table manually to ensure actions (login, failed login) wrote securely.
5. **UI Check**: Start the server and navigate the HTMX UI. Verify that logging in and performing predictions works visually.
