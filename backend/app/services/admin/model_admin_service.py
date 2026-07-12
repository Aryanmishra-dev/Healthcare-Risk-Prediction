import uuid
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.model_version import ModelVersion
from backend.app.services.model_registry_service import ModelRegistryService


class AdminModelsService:

    @staticmethod
    async def promote_model(db: AsyncSession, model_id: uuid.UUID) -> ModelVersion:
        """Promote a model to production."""
        return await ModelRegistryService.promote_model_to_production(db, model_id)

    @staticmethod
    async def archive_model(db: AsyncSession, model_id: uuid.UUID) -> ModelVersion:
        """Archive a model."""
        return await ModelRegistryService.archive_model(db, model_id)

    @staticmethod
    async def rollback_model(db: AsyncSession, disease_type: str) -> ModelVersion:
        """Rollback to the previous production model."""
        return await ModelRegistryService.rollback_model(db, disease_type)

    @staticmethod
    async def get_model_versions(
        db: AsyncSession, disease_type: str = None
    ) -> List[ModelVersion]:
        """List all model versions, optionally filtered by disease."""
        return await ModelRegistryService.list_models(db, disease_type=disease_type)
