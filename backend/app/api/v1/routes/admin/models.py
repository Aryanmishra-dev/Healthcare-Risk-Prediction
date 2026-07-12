import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequireRole
from backend.app.core.database import get_db
from backend.app.core.enums import UserRole
from backend.app.schemas.model_version import ModelVersionResponse
from backend.app.services.admin.model_admin_service import AdminModelsService

router = APIRouter(prefix="/models", tags=["Admin Models"])


@router.get("", response_model=List[ModelVersionResponse])
async def list_models(
    disease_type: str = Query(None, description="Filter by disease type"),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """List all model versions, optionally filtered by disease type."""
    return await AdminModelsService.get_model_versions(db, disease_type)


@router.post("/{model_id}/promote", response_model=ModelVersionResponse)
async def promote_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Promote a model version to production."""
    return await AdminModelsService.promote_model(db, model_id)


@router.post("/{model_id}/archive", response_model=ModelVersionResponse)
async def archive_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Archive a model version."""
    return await AdminModelsService.archive_model(db, model_id)


@router.post("/rollback/{disease_type}", response_model=ModelVersionResponse)
async def rollback_model(
    disease_type: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(RequireRole([UserRole.ADMIN, UserRole.SUPER_ADMIN])),
):
    """Rollback to the previous production model."""
    return await AdminModelsService.rollback_model(db, disease_type)
