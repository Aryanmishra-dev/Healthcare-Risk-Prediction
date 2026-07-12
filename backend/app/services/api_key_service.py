import hashlib
import secrets
import string
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.api_key import ApiKey
from backend.app.models.base import utc_now


class ApiKeyService:
    @staticmethod
    def generate_raw_key() -> str:
        """Generate a cryptographically secure API key."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(40))

    @staticmethod
    def get_prefix(raw_key: str) -> str:
        """Extract the prefix from a raw key."""
        return raw_key[:8]

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Hash a raw key for secure storage using SHA-256."""
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_key(raw_key: str, hashed_key: str) -> bool:
        """Verify a raw key against its hash."""
        return ApiKeyService.hash_key(raw_key) == hashed_key

    @staticmethod
    async def create_api_key(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        created_by: uuid.UUID,
        name: str,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Tuple[ApiKey, str]:
        """Create a new API key. Returns the ApiKey object and the raw (plaintext) key."""
        if scopes is None:
            scopes = ["read-only"]

        raw_key = ApiKeyService.generate_raw_key()
        prefix = ApiKeyService.get_prefix(raw_key)
        hashed_key = ApiKeyService.hash_key(raw_key)

        api_key = ApiKey(
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            key_prefix=prefix,
            hashed_key=hashed_key,
            scopes=scopes,
            expires_at=expires_at,
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return api_key, raw_key

    @staticmethod
    async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[ApiKey]:
        """Validate an API key and update its last_used_at timestamp.
        Returns the ApiKey object if valid, else None."""
        prefix = ApiKeyService.get_prefix(raw_key)

        # Retrieve all active keys with this prefix
        stmt = select(ApiKey).where(
            ApiKey.key_prefix == prefix, ApiKey.is_active.is_(True)
        )
        result = await db.execute(stmt)
        candidate_keys = result.scalars().all()

        for key in candidate_keys:
            # Check expiry (handle naive datetimes from SQLite)
            if key.expires_at:
                expires = key.expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires < utc_now():
                    continue

            # Verify hash
            if ApiKeyService.verify_key(raw_key, key.hashed_key):
                # Update last_used_at
                key.last_used_at = utc_now()
                db.add(key)
                await db.commit()
                return key

        return None

    @staticmethod
    async def revoke_api_key(
        db: AsyncSession, tenant_id: uuid.UUID, key_id: uuid.UUID
    ) -> bool:
        """Revoke an API key by setting is_active to False."""
        stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == tenant_id)
        result = await db.execute(stmt)
        api_key = result.scalar_one_or_none()

        if api_key:
            api_key.is_active = False
            db.add(api_key)
            await db.commit()
            return True
        return False

    @staticmethod
    async def get_api_keys_for_tenant(
        db: AsyncSession, tenant_id: uuid.UUID
    ) -> List[ApiKey]:
        """Get all API keys for a tenant."""
        stmt = select(ApiKey).where(ApiKey.tenant_id == tenant_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def has_scope(api_key: ApiKey, required_scope: str) -> bool:
        """Check if an API key has a specific scope."""
        from backend.app.core.enums import ApiKeyScope

        return ApiKeyScope.has_scope(api_key.scopes, required_scope)

    @staticmethod
    async def get_api_key_by_id(
        db: AsyncSession,
        key_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[ApiKey]:
        """Get a single API key by ID within a tenant."""
        stmt = select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def rotate_api_key(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        key_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Tuple[ApiKey, str]:
        """Revoke the existing key and create a new one with identical metadata.
        Returns the new (ApiKey, raw_key) pair."""
        existing = await ApiKeyService.get_api_key_by_id(db, key_id, tenant_id)
        if not existing:
            raise ValueError("API Key not found")

        existing.is_active = False
        db.add(existing)

        new_key, raw_key = await ApiKeyService.create_api_key(
            db=db,
            tenant_id=tenant_id,
            created_by=created_by,
            name=existing.name,
            scopes=existing.scopes,
            expires_at=existing.expires_at,
        )

        return new_key, raw_key
