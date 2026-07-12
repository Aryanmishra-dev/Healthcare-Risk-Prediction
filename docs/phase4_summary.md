# Phase 4: Admin Portal & Platform Analytics

## Overview
Phase 4 focuses on building a production-grade Admin Portal that serves as the operational control center of the entire platform. This phase moves beyond simple CRUD panels to provide deep insights into user behavior, system health, security events, and model performance.

## Key Accomplishments
- **RBAC Overhaul**: Replaced string-based roles with a robust `UserRole` Enum (`USER`, `ADMIN`, `SUPER_ADMIN`).
- **Dashboard & Analytics**: Implemented cached aggregation queries (via SQLAlchemy) to display system metrics, active users, prediction latencies, and disease distribution without Python-level loops.
- **System Health**: Added real-time health checks using `psutil` to monitor CPU, memory, and disk usage, alongside Database, Redis, and MLflow connectivity checks.
- **Security & Audit**: Segmented high-privilege operations into an `AdminAction` table and exposed administrative views for failed logins and security anomalies.
- **Models & Reports**: Exposed endpoints for admins to promote/archive ML models and delete errant reports directly.

## Architecture
The Admin Portal follows a strict layered design:
1. **Models / Schemas**: Clear definitions for `AdminAction`, `PaginatedUserResponse`, `SecurityEventResponse`, etc.
2. **Repositories**: Complex ORM aggregations (`AdminAnalyticsRepository`, `AdminUsersRepository`, etc.).
3. **Services**: Business logic and caching (`CacheService` with a 30s TTL).
4. **Routers**: Thin controllers organized under `/api/v1/admin/`.
