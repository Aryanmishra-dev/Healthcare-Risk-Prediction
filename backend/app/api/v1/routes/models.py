"""
Phase 3 — Model Registry & MLOps API Routes.

Provides endpoints for managing model versions, monitoring, drift detection, and health checks.
Admin-only routes are protected by RBAC.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.model_version import ModelVersion
from backend.app.models.user import User
from backend.app.schemas.model_version import (
    ModelComparisonResponse,
    ModelVersionCreate,
    ModelVersionResponse,
)
from backend.app.services.model_drift_service import model_drift_service
from backend.app.services.model_manager import model_manager
from backend.app.services.model_monitoring_service import (
    model_monitoring_service,
)
from backend.app.services.model_registry_service import model_registry_service

router = APIRouter(prefix="/models", tags=["Model Registry"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency: only Admin users may access this endpoint."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


# ─────────────────────────────────────────────────────────────────────────────
#  Phase 3.10 — Public Model Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[ModelVersionResponse])
async def list_models(
    disease: Optional[str] = Query(None, description="Filter by disease type"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status"
    ),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered model versions (any authenticated user)."""
    query = (
        select(ModelVersion)
        .order_by(desc(ModelVersion.created_at))
        .limit(limit)
    )
    if disease:
        query = query.where(ModelVersion.disease == disease)
    if status_filter:
        query = query.where(ModelVersion.status == status_filter)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/current", response_model=List[ModelVersionResponse])
async def get_current_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the active Production model version for each disease."""
    diseases = ["diabetes", "heart_disease", "lung_cancer"]
    current_models = []
    for disease in diseases:
        active = await model_registry_service.get_active_model(db, disease)
        if active:
            current_models.append(active)
    return current_models


@router.get("/history", response_model=List[ModelVersionResponse])
async def get_model_history(
    model_name: str = Query(..., description="Model name to get history for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full version history for a specific model name."""
    return await model_registry_service.get_models_by_name(db, model_name)


@router.get("/health")
async def get_model_health(
    current_user: User = Depends(get_current_user),
):
    """
    Get health, readiness, and status of all loaded models.
    Includes version, stage, latency, and startup diagnostics.
    """
    health = model_manager.get_health_status()
    return {
        "status": (
            "healthy"
            if any(v["status"] == "ready" for v in health["models"].values())
            else "degraded"
        ),
        "models": health["models"],
        "diagnostics": health["diagnostics"],
    }


@router.get("/metrics")
async def get_model_metrics(
    admin: User = Depends(require_admin),
):
    """Admin only: Return per-model inference metrics (count, latency, error rate)."""
    return model_monitoring_service.get_metrics()


@router.get("/drift")
async def get_model_drift(
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
):
    """Admin only: Return recent drift detection records."""
    records = model_drift_service.get_recent_drift()
    return {"drift_records": records[-limit:], "total": len(records)}


@router.get("/{model_id}", response_model=ModelVersionResponse)
async def get_model_version(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific model version by ID."""
    model = await model_registry_service.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model version not found")
    return model


# ─────────────────────────────────────────────────────────────────────────────
#  Phase 3.10 — Admin-only Model Management
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_model(
    schema: ModelVersionCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: Register a new model version in the registry."""
    return await model_registry_service.register_model(db, schema)


@router.post("/promote/{model_id}", response_model=ModelVersionResponse)
async def promote_model(
    model_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: Promote a model version to Production, archiving the previous one."""
    return await model_registry_service.promote_model(db, model_id)


@router.post("/rollback/{model_id}", response_model=ModelVersionResponse)
async def rollback_model(
    model_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: Rollback to a specific model version (promotes it, deprecates current)."""
    return await model_registry_service.rollback_model(db, model_id)


@router.post("/archive/{model_id}", response_model=ModelVersionResponse)
async def archive_model(
    model_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: Archive a non-Production model version."""
    return await model_registry_service.archive_model(db, model_id)


@router.get("/compare/{model_id_1}/{model_id_2}")
async def compare_models(
    model_id_1: uuid.UUID,
    model_id_2: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin only: Compare metrics between two model versions."""
    return await model_registry_service.compare_models(
        db, model_id_1, model_id_2
    )
