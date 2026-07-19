from fastapi import APIRouter, Depends

from backend.app.api.dependencies import (
    RATE_LIMIT,
    OptionalRateLimiter,
    audit_admin_action,
)
from backend.app.api.v1.routes.admin import (
    analytics,
    dashboard,
    health,
    models,
    reports,
    security,
    users,
)

admin_router = APIRouter(
    prefix="/admin",
    dependencies=[
        Depends(audit_admin_action),
        Depends(OptionalRateLimiter(times=RATE_LIMIT, seconds=60)),
    ],
)
admin_router.include_router(dashboard.router)
admin_router.include_router(users.router)
admin_router.include_router(analytics.router)
admin_router.include_router(health.router)
admin_router.include_router(security.router)
admin_router.include_router(reports.router)
admin_router.include_router(models.router)
