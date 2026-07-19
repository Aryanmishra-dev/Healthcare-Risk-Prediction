# Phase 1 Technical Debt

1. **Test Suite Mocking:** The current test suite fails utterly without a live PostgreSQL instance. The `get_db` dependency is not overridden during `pytest` runs, causing 500 errors. We must implement standard `app.dependency_overrides` using `testcontainers` or an isolated testing database.
2. **Stateless JWT Revocation:** We rely strictly on token expiration. If an access token is compromised immediately after issue, the attacker has a 30-minute window of access regardless of session revocation.
3. **Missing SMTP Integration:** The `/password-reset-request` endpoint executes perfectly up to the point of dispatch. It generates the token and stores it but does not email the user.
4. **Missing Rate Limiting:** The auth routes are dangerously exposed to credential stuffing attacks due to the absence of `slowapi` or Redis-based rate limiting on `/login`.
5. **No HttpOnly Cookies:** Currently, JWTs are returned as JSON, implying frontend storage in `localStorage`. Transitioning to `HttpOnly` Secure cookies is highly advised for security, especially for HTMX interactions.
