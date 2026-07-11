# Changelog

## [Unreleased]
### Added
- **Phase 1: Authentication & User Management**
  - PostgreSQL as the only supported database.
  - SQLAlchemy 2.0 (async) and Alembic for robust database operations and migrations.
  - New DB schemas: `users`, `user_sessions`, `password_reset_tokens`, `email_verification_tokens`, `audit_logs`, and migrated `prediction_audit_logs`.
  - Robust JWT authentication with strict refresh token rotation.
  - BCrypt password hashing via passlib.
  - RBAC (Role-Based Access Control) foundation (`user`, `admin`, `super_admin`).
  - Comprehensive Audit Logging for security events (login, logout, failed login, password reset).
  - Password Reset Request & Confirm endpoints.
  - Email Verification endpoints.
  - Clean Architecture refactoring: extraction of business logic to `backend/app/services/auth_service.py` and `backend/app/schemas/user.py`.

### Changed
- Refactored `backend/app/auth/router.py` to use dependency-injected `AsyncSession` rather than raw SQLite connections.
- Migrated legacy `log_prediction_to_db` logic to use asynchronous SQLAlchemy sessions.
- Deprecated SQLite databases (`audit_log.db`).

### Security
- Revoked all user sessions upon password reset.
- Detailed IP Address and User Agent tracking bound to `UserSession`.
- Full separation of access and refresh tokens.
