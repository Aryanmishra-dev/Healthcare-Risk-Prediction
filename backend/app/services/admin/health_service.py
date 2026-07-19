import time
from typing import Any, Dict

import mlflow
import psutil  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.cache_service import cache_service, cached


class AdminHealthService:

    @staticmethod
    @cached(expire=30)
    async def get_system_health(db: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive system health including DB, Redis, MLflow, and
        System Resources."""

        health_status: Dict[str, Any] = {
            "status": "ok",
            "timestamp": time.time(),
            "services": {
                "database": "unknown",
                "redis": "unknown",
                "mlflow": "unknown",
            },
            "system_resources": {},
        }

        # 1. Check Database
        try:
            await db.execute(text("SELECT 1"))
            health_status["services"]["database"] = "up"
        except Exception:
            health_status["services"]["database"] = "down"
            health_status["status"] = "degraded"

        # 2. Check Redis (if active)
        if cache_service._enabled and cache_service._redis:
            try:
                await cache_service._redis.ping()
                health_status["services"]["redis"] = "up"
            except Exception:
                health_status["services"]["redis"] = "down"
        else:
            health_status["services"]["redis"] = "disabled"

        # 3. Check MLflow
        try:
            mlflow.get_tracking_uri()
            # Simple check if uri is set, could do a request if needed.
            health_status["services"]["mlflow"] = "up"
        except Exception:
            health_status["services"]["mlflow"] = "down"

        # 4. System Resources (via psutil)
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            health_status["system_resources"] = {
                "cpu_percent": cpu_percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_total_mb": memory.total / (1024 * 1024),
                "memory_percent": memory.percent,
                "disk_used_gb": disk.used / (1024 * 1024 * 1024),
                "disk_total_gb": disk.total / (1024 * 1024 * 1024),
                "disk_percent": disk.percent,
            }
        except Exception as e:
            health_status["system_resources"] = {"error": str(e)}

        return health_status
