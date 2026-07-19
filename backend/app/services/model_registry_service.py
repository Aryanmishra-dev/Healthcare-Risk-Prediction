import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import utc_now
from backend.app.models.model_version import ModelVersion
from backend.app.schemas.model_version import (
    ModelVersionCreate,
    ModelVersionUpdate,
)


class ModelRegistryService:
    async def register_model(
        self, db: AsyncSession, schema: ModelVersionCreate
    ) -> ModelVersion:
        """Register a new model version in the 'Training' status."""
        new_version = ModelVersion(
            **schema.model_dump(), status="Training", training_date=utc_now()
        )
        db.add(new_version)
        await db.commit()
        await db.refresh(new_version)
        return new_version

    async def get_model(
        self, db: AsyncSession, model_id: uuid.UUID
    ) -> Optional[ModelVersion]:
        """Fetch a specific model version by ID."""
        return await db.get(ModelVersion, model_id)

    async def get_models_by_name(
        self, db: AsyncSession, model_name: str
    ) -> List[ModelVersion]:
        """Fetch all versions of a specific model name."""
        result = await db.execute(
            select(ModelVersion)
            .where(ModelVersion.model_name == model_name)
            .order_by(desc(ModelVersion.created_at))
        )
        return list(result.scalars().all())

    async def get_active_model(
        self, db: AsyncSession, disease: str
    ) -> Optional[ModelVersion]:
        """Fetch the active production model for a given disease."""
        result = await db.execute(
            select(ModelVersion)
            .where(ModelVersion.disease == disease)
            .where(ModelVersion.status == "Production")
            .order_by(desc(ModelVersion.deployed_at))
            .limit(1)
        )
        return result.scalars().first()

    async def promote_model(
        self, db: AsyncSession, model_id: uuid.UUID
    ) -> ModelVersion:
        """Promote a model to Production, archiving the previous active one."""
        target_model = await db.get(ModelVersion, model_id)
        if not target_model:
            raise HTTPException(
                status_code=404, detail="Model version not found"
            )

        if target_model.status == "Production":
            raise HTTPException(
                status_code=400, detail="Model is already in Production"
            )

        # Find current active model for this disease
        active_model = await self.get_active_model(db, target_model.disease)
        if active_model and active_model.id != target_model.id:
            active_model.status = "Archived"
            active_model.retired_at = utc_now()

        target_model.status = "Production"
        target_model.deployed_at = utc_now()

        await db.commit()
        await db.refresh(target_model)
        return target_model

    async def rollback_model(
        self, db: AsyncSession, model_id: uuid.UUID
    ) -> ModelVersion:
        """Rollback to a previous model (promotes the old model, deprecates current)."""
        target_model = await db.get(ModelVersion, model_id)
        if not target_model:
            raise HTTPException(
                status_code=404, detail="Model version not found"
            )

        active_model = await self.get_active_model(db, target_model.disease)
        if active_model and active_model.id != target_model.id:
            active_model.status = "Deprecated"
            active_model.retired_at = utc_now()

        target_model.status = "Production"
        target_model.deployed_at = utc_now()
        target_model.retired_at = None

        await db.commit()
        await db.refresh(target_model)
        return target_model

    async def archive_model(
        self, db: AsyncSession, model_id: uuid.UUID
    ) -> ModelVersion:
        """Archive a model (e.g. if it's no longer useful)."""
        target_model = await db.get(ModelVersion, model_id)
        if not target_model:
            raise HTTPException(
                status_code=404, detail="Model version not found"
            )

        if target_model.status == "Production":
            raise HTTPException(
                status_code=400,
                detail="Cannot archive active Production model. Promote another first.",
            )

        target_model.status = "Archived"
        target_model.retired_at = utc_now()

        await db.commit()
        await db.refresh(target_model)
        return target_model

    async def list_models(
        self, db: AsyncSession, disease_type: str = None
    ) -> List[ModelVersion]:
        """List all model versions, optionally filtered by disease."""
        query = select(ModelVersion).order_by(desc(ModelVersion.created_at))
        if disease_type:
            query = query.where(ModelVersion.disease == disease_type)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def compare_models(
        self, db: AsyncSession, model_id_1: uuid.UUID, model_id_2: uuid.UUID
    ) -> Dict[str, Any]:
        """Compare two models' metrics."""
        m1 = await db.get(ModelVersion, model_id_1)
        m2 = await db.get(ModelVersion, model_id_2)

        if not m1 or not m2:
            raise HTTPException(
                status_code=404, detail="One or both models not found"
            )

        m1_metrics = m1.metrics or {}
        m2_metrics = m2.metrics or {}

        diff = {}
        all_keys = set(m1_metrics.keys()).union(set(m2_metrics.keys()))
        for k in all_keys:
            val1 = m1_metrics.get(k, 0)
            val2 = m2_metrics.get(k, 0)
            if isinstance(val1, (int, float)) and isinstance(
                val2, (int, float)
            ):
                diff[k] = val1 - val2
            else:
                diff[k] = f"{val1} -> {val2}"

        return {
            "model_name": m1.model_name,
            "versions": [m1, m2],
            "metrics_diff": diff,
        }


model_registry_service = ModelRegistryService()
