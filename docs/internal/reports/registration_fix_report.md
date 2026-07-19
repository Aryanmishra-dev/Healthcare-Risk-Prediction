# Registration Fix Report

## Root Cause

**PostgreSQL database server was not running.**

The backend uses `asyncpg` to connect to PostgreSQL at `postgresql+asyncpg://admin:healthpredict_db_password@localhost:5432/healthcare_audit`. When the server started, no PostgreSQL instance was available, so every database operation (including `POST /auth/register`) failed with a connection refused error.

## Stack Trace

```
OSError: Multiple exceptions: [Errno 61] Connect call failed ('127.0.0.1', 5432), [Errno 61] Connect call failed ('::1', 5432, 0, 0)

  File "backend/app/auth/router.py", line 149, in register
    user = await create_user(...)
  File "backend/app/services/auth_service.py", line 37, in create_user
    existing_user = await get_user_by_email(db, user_in.email)
  File "backend/app/services/auth_service.py", line 27, in get_user_by_email
    result = await db.execute(select(User).where(User.email == email))
  File "sqlalchemy/ext/asyncio/session.py", line 449, in execute
    result = await greenlet_spawn(...)
  ...
  File "asyncpg/connection.py", line 2421, in connect
    return await connect_utils._connect(...)
  File "asyncpg/connect_utils.py", line 802, in _create_ssl_connection
    tr, pr = await loop.create_connection(...)
OSError: [Errno 61] Connection refused
```

## Files Modified

| File | Change |
|------|--------|
| None | No source code changes needed — infrastructure issue only |

## Why the Bug Occurred

The `.env` file specifies a PostgreSQL connection URL:
```
DATABASE_URL=postgresql+asyncpg://admin:healthpredict_db_password@localhost:5432/healthcare_audit
```

- PostgreSQL was installed via Homebrew (`postgresql@15`) but **not started** (`brew services list` showed status `none`)
- No database, user, or migrations had been created/applied
- The app starts fine (FastAPI doesn't connect at import time), but fails on the first database query

## Fix Implemented

1. **Started PostgreSQL**:
   ```bash
   brew services start postgresql@15
   ```

2. **Configured database user and password**:
   ```bash
   createuser -s admin
   createdb -O admin healthcare_audit
   psql -d postgres -c "ALTER USER admin WITH PASSWORD 'healthpredict_db_password';"
   ```

3. **Applied all 16 Alembic migrations**:
   ```bash
   alembic upgrade head
   ```
   Migrations applied: `f496bd7cc74d` (initial) → `0002` → `0003` → `0004` → `0005` → `0006` → `0007` → `0008` → `0009` → `0010` → `0011` → `0012` → `0013` → `0014` → `0015` → `0016` (head)

4. **Restarted the uvicorn server**

## Validation Performed

### Successful Registration
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -d '{"email":"test@example.com","password":"TestPass123","full_name":"Test User"}'
```
→ **HTTP 201** with user object returned

### Successful Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0" \
  -d '{"email":"test@example.com","password":"TestPass123"}'
```
→ **HTTP 200** with `access_token` and `refresh_token` returned

### Alembic Current
```
0016 (head)
```
All migrations applied.

### Test Suite
```
pytest tests/test_auth.py -x -v
```
→ **34 passed, 0 failed**

### Edge Cases Verified
- **Duplicate email**: Registration with the same email returns appropriate error
- **Missing fields**: Validation errors returned for incomplete payloads
- **Invalid password**: Validation enforces password requirements
- **Bot detection**: `verify_user_agent` blocks `curl`/`python-requests`/`wget` (returns 403), but allows browser user agents
- **Tenant/membership**: Created automatically during registration flow

## Post-Fix Notes

- The database now persists at `/opt/homebrew/var/postgresql@15/`
- On system restart, run `brew services start postgresql@15` before starting the app
- Consider adding a startup health check that verifies database connectivity before accepting requests
- For CI/CD, use Docker with the provided `docker-compose.yml` which includes PostgreSQL, Redis, and MLflow
