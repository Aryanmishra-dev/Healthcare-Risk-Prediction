import uuid
from typing import List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.model_version import ModelVersion
from backend.app.services.model_registry_service import model_registry_service


class AdminModelsService:

    @staticmethod
    async def promote_model(
        db: AsyncSession, model_id: uuid.UUID
    ) -> ModelVersion:
        """Promote a model to production."""
        return await model_registry_service.promote_model(db, model_id)

    @staticmethod
    async def archive_model(
        db: AsyncSession, model_id: uuid.UUID
    ) -> ModelVersion:
        """Archive a model."""
        return await model_registry_service.archive_model(db, model_id)

    @staticmethod
    async def rollback_model(
        db: AsyncSession, disease_type: str
    ) -> ModelVersion:
        """Rollback to the previous production model."""
        model = await model_registry_service.get_active_model(db, disease_type)
        if not model:
            raise HTTPException(
                status_code=404,
                detail="No active model found for disease",
            )
        return await model_registry_service.rollback_model(db, model.id)

    @staticmethod
    async def get_model_versions(
        db: AsyncSession, disease_type: str | None = None
    ) -> List[ModelVersion]:
        """List all model versions, optionally filtered by
        disease."""
        return await model_registry_service.list_models(
            db, disease_type=disease_type
        )
