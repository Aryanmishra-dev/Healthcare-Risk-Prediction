# Admin Security Review

## RBAC Enforcement
The Admin Portal strictly enforces RBAC across all its routers (`/api/v1/admin/*`).
- Role Enum: Defined in `UserRole` class (`USER`, `ADMIN`, `SUPER_ADMIN`).
- Enforcement: Accomplished via `RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])` dependency injected at the router level.
- Unauthenticated access returns HTTP 401. Unauthorized access returns HTTP 403.

## Admin Audit Logging
- **Mechanism**: The `AuditAdminAction` dependency is now attached globally to the `admin_router`. 
- **Trigger**: Every POST, PUT, PATCH, and DELETE request made by an admin is intercepted. 
- **Storage**: The action is asynchronously logged to the `AdminAction` table using a FastAPI `BackgroundTasks` queue to prevent response blocking.

## Security Headers
The Admin API serves over HTTPS and leverages `SecurityHeadersMiddleware`:
- `Content-Security-Policy`: Restricts inline execution.
- `Strict-Transport-Security`: HSTS strictly enforces HTTPS for a year.
- `X-Frame-Options: DENY`: Defends against clickjacking.
- `X-Content-Type-Options: nosniff`: Mitigates MIME-sniffing.
- The headers apply seamlessly to both the primary API and the Admin sub-routers.

## Rate Limiting
Administrative endpoints are now protected by the `OptionalRateLimiter`.
- Limits are typically set to 60 req/min for mutating actions.
- The system gracefully degrades to in-memory limits if the Redis server goes offline, ensuring protections are never dropped.

## IDOR and Escalation Mitigations
- Route handlers strictly rely on `db: AsyncSession = Depends(get_db)` to ensure data isolation.
- Role elevation attempts by non-Super Admins are blocked effectively at the schema and route levels.
