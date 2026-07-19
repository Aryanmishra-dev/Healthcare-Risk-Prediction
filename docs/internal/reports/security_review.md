# Phase 1 Security Review

## 1. Authentication & JWT Vulnerabilities
- **Signing Algorithm:** `HS256` is securely enforced. No `"none"` algorithm attack vector is exposed because `PyJWT` explicit algorithm pinning is used (`algorithms=[settings.algorithm]`).
- **Secret Leakage:** Secrets are loaded from `.env` via `Pydantic Settings`. No hardcoded keys exist.
- **Revocation Delay:** As noted, standard JWTs are stateless. Revoked sessions will not terminate an access token until the 30-minute expiration window expires. This is acceptable for most applications but represents a minor security compromise for performance.

## 2. Password Handling & Vulnerabilities
- **Insecure Storage:** Avoided. Raw passwords are never stored. `passlib.context.CryptContext` with `bcrypt` handles all hashing securely.
- **Timing Attacks:** Mitigated by `pwd_context.verify()` standard time-constant comparators.
- **Password Reset:** Tokens are randomly generated UUIDs, hashed with SHA-256 before storage. This prevents database dumps from leaking useable reset tokens (though the impact is minimal since tokens are short-lived, it adds defense-in-depth). 
- **Session Revocation:** Resetting a password correctly loops through and revokes *all* active `UserSession` records for the target user, forcing them to log in again.

## 3. Rate Limiting & Bruteforce Risks
- **Missing Rate Limiting:** The `/auth/login` and `/auth/register` endpoints lack dedicated Redis rate-limiting dependencies. This makes the system susceptible to credential stuffing and brute force attacks. *High Priority Technical Debt.*

## 4. Injection & Cross-Site Scripting (XSS/CSRF)
- **SQL Injection:** Entirely mitigated by SQLAlchemy 2.0 ORM parameterized queries (`select().where()`).
- **XSS & CSRF:** The authentication endpoints currently respond with JSON tokens (intended for API consumers). If the frontend intends to store these tokens in `localStorage`, XSS is a risk. Storing them in `HttpOnly` cookies would mitigate this, but currently, the endpoints only yield JSON responses.

## 5. Authorization & IDOR
- **Missing Authorization Checks:** RBAC role checking is entirely unimplemented on protected endpoints. 
- **IDOR Risks:** `revoke_session` is guarded. `history` is guarded by `user.id`. The endpoints currently written correctly isolate user data (e.g., `where(PredictionAuditLog.user_id == user.id)`).
