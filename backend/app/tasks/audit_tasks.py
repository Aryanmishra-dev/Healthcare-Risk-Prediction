import asyncio
import logging

from backend.app.celery_app import celery_app
from backend.app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(acks_late=True)
def apply_audit_retention():
    from backend.app.services.audit_retention_service import (
        audit_retention_service,
    )

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await audit_retention_service.apply_retention(db)
            if result["total_purged"]:
                logger.info(
                    "audit_retention_applied total=%d",
                    result["total_purged"],
                )

    asyncio.run(_run())
