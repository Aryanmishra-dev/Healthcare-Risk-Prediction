# Phase 1 Recommendations & Post-Deployment Validation

## 1. Local Runtime Validation Checklist
Before any Phase 2 code is written, a senior engineer must execute the following commands on a local machine to ensure runtime harmony:

1. **Boot PostgreSQL:**
   ```bash
   docker compose -f deployment/docker/docker-compose.yml up -d db redis
   ```
2. **Apply Migrations:**
   ```bash
   cd backend && alembic upgrade head
   ```
3. **Validate Application Boot:**
   ```bash
   python -m uvicorn backend.app.main:app --reload
   ```
4. **Execute Core API Flows:**
   - Call `POST /api/v1/auth/register`
   - Call `POST /api/v1/auth/login` (Verify 200 OK and JWT receipt)
   - Call `GET /api/v1/auth/me` with Bearer token
   - Call `POST /api/v1/predict/diabetes` (Verify predictions execute and log to Postgres successfully).
5. **Run Test Suite:**
   ```bash
   pytest tests/
   ```

## 2. Hardening Recommendations for Phase 2
- **Test Database Dependency Injection:** Implement `app.dependency_overrides[get_db] = override_get_db` in `tests/conftest.py` so that the test suite targets a disposable `_test` database.
- **Implement Rate Limiting:** Apply `fastapi-limiter` or `slowapi` on `/auth/login` (e.g., max 5 attempts per minute per IP) leveraging the existing Redis container.
- **JWT Storage:** Modify `/login` to return standard JSON for API consumers *but additionally* set an `HttpOnly` Secure cookie containing the refresh token to shield it from XSS.
- **RBAC Enforcement:** Write a `get_current_admin_user` dependency that wraps `get_current_user` and asserts `user.role == 'admin'`, and apply it to sensitive endpoints.
