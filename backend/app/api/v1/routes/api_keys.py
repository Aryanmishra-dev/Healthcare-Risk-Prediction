import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import RequirePermission, get_current_tenant
from backend.app.auth.router import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from backend.app.services.api_key_service import ApiKeyService
from backend.app.services.authorization_service import Permission

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    schema: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequirePermission(Permission.MANAGE_API_KEYS)),
):
    """
    Create a new API key. The plaintext key is only returned once in the response.
    """
    api_key, raw_key = await ApiKeyService.create_api_key(
        db=db,
        tenant_id=tenant_id,
        created_by=current_user.id,
        name=schema.name,
        scopes=schema.scopes,
        expires_at=schema.expires_at,
    )

    response_data = ApiKeyResponse.model_validate(api_key).model_dump()
    response_data["raw_key"] = raw_key

    return response_data


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequirePermission(Permission.MANAGE_API_KEYS)),
):
    """
    List all API keys for the current tenant.
    """
    return await ApiKeyService.get_api_keys_for_tenant(db, tenant_id)


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequirePermission(Permission.MANAGE_API_KEYS)),
):
    """
    Get a single API key by ID.
    """
    api_key = await ApiKeyService.get_api_key_by_id(db, key_id, tenant_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key not found")
    return api_key


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rotate_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequirePermission(Permission.MANAGE_API_KEYS)),
):
    """
    Rotate an API key: revoke the existing key and create a new one with identical metadata.
    """
    try:
        new_key, raw_key = await ApiKeyService.rotate_api_key(
            db=db,
            tenant_id=tenant_id,
            key_id=key_id,
            created_by=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="API Key not found")

    response_data = ApiKeyResponse.model_validate(new_key).model_dump()
    response_data["raw_key"] = raw_key
    return response_data


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _=Depends(RequirePermission(Permission.MANAGE_API_KEYS)),
):
    """
    Revoke an API key.
    """
    success = await ApiKeyService.revoke_api_key(db, tenant_id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")
