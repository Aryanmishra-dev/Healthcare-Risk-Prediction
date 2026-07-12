import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.core.enums import ApiKeyScope
from backend.app.models.api_key import ApiKey


class TestApiKeyHasScope:
    def test_admin_scope_grants_everything(self):
        key = ApiKey(scopes=["admin"])
        assert ApiKeyScope.has_scope(key.scopes, "predictions") is True
        assert ApiKeyScope.has_scope(key.scopes, "reports") is True
        assert ApiKeyScope.has_scope(key.scopes, "models") is True
        assert ApiKeyScope.has_scope(key.scopes, "admin") is True
        assert ApiKeyScope.has_scope(key.scopes, "read-only") is True

    def test_specific_scope_grants_only_that(self):
        key = ApiKey(scopes=["predictions"])
        assert ApiKeyScope.has_scope(key.scopes, "predictions") is True
        assert ApiKeyScope.has_scope(key.scopes, "reports") is False
        assert ApiKeyScope.has_scope(key.scopes, "models") is False

    def test_multiple_scopes(self):
        key = ApiKey(scopes=["predictions", "reports"])
        assert ApiKeyScope.has_scope(key.scopes, "predictions") is True
        assert ApiKeyScope.has_scope(key.scopes, "reports") is True
        assert ApiKeyScope.has_scope(key.scopes, "models") is False

    def test_read_only_scope(self):
        key = ApiKey(scopes=["read-only"])
        assert ApiKeyScope.has_scope(key.scopes, "read-only") is True
        assert ApiKeyScope.has_scope(key.scopes, "predictions") is False

    def test_empty_scopes(self):
        key = ApiKey(scopes=[])
        assert ApiKeyScope.has_scope(key.scopes, "anything") is False


class TestApiKeyService:
    def test_generate_raw_key_length(self):
        from backend.app.services.api_key_service import ApiKeyService

        key = ApiKeyService.generate_raw_key()
        assert len(key) == 40
        assert isinstance(key, str)

    def test_generate_raw_key_entropy(self):
        from backend.app.services.api_key_service import ApiKeyService

        keys = {ApiKeyService.generate_raw_key() for _ in range(100)}
        assert len(keys) == 100

    def test_get_prefix(self):
        from backend.app.services.api_key_service import ApiKeyService

        key = "ABCDefgh1234567890"
        assert ApiKeyService.get_prefix(key) == "ABCDefgh"

    def test_hash_and_verify(self):
        from backend.app.services.api_key_service import ApiKeyService

        raw = "test-api-key-12345"
        hashed = ApiKeyService.hash_key(raw)
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex
        assert ApiKeyService.verify_key(raw, hashed) is True
        assert ApiKeyService.verify_key("wrong-key", hashed) is False

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        from backend.app.services.api_key_service import ApiKeyService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        tenant_id = uuid.uuid4()
        created_by = uuid.uuid4()

        api_key, raw_key = await ApiKeyService.create_api_key(
            db=mock_db,
            tenant_id=tenant_id,
            created_by=created_by,
            name="Test Key",
            scopes=["predictions"],
            expires_at=None,
        )

        assert api_key.tenant_id == tenant_id
        assert api_key.created_by == created_by
        assert api_key.name == "Test Key"
        assert api_key.key_prefix == raw_key[:8]
        assert len(raw_key) == 40
        assert api_key.scopes == ["predictions"]
        assert mock_db.add.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_create_api_key_default_scope(self):
        from backend.app.services.api_key_service import ApiKeyService

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        api_key, raw_key = await ApiKeyService.create_api_key(
            db=mock_db,
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            name="Default Scope",
        )

        assert api_key.scopes == ["read-only"]

    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self):
        from backend.app.services.api_key_service import ApiKeyService

        raw_key = ApiKeyService.generate_raw_key()
        hashed = ApiKeyService.hash_key(raw_key)
        prefix = ApiKeyService.get_prefix(raw_key)
        test_key = ApiKey(
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            name="Test",
            key_prefix=prefix,
            hashed_key=hashed,
            scopes=["read-only"],
            is_active=True,
            expires_at=None,
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [test_key]
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await ApiKeyService.validate_api_key(mock_db, raw_key)
        assert result is not None
        assert result.name == "Test"
        assert result.last_used_at is not None

    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self):
        from backend.app.services.api_key_service import ApiKeyService

        raw_key = ApiKeyService.generate_raw_key()
        hashed = ApiKeyService.hash_key(raw_key)
        prefix = ApiKeyService.get_prefix(raw_key)
        test_key = ApiKey(
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            name="Expired",
            key_prefix=prefix,
            hashed_key=hashed,
            scopes=["read-only"],
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [test_key]
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await ApiKeyService.validate_api_key(mock_db, raw_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_inactive(self):
        from backend.app.services.api_key_service import ApiKeyService

        raw_key = ApiKeyService.generate_raw_key()

        # Mock an empty result set (SQL filters out inactive keys)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await ApiKeyService.validate_api_key(mock_db, raw_key)
        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_api_key(self):
        from backend.app.services.api_key_service import ApiKeyService

        test_key = ApiKey(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="To Revoke",
            is_active=True,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = test_key
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await ApiKeyService.revoke_api_key(
            mock_db, test_key.tenant_id, test_key.id
        )
        assert result is True
        assert test_key.is_active is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self):
        from backend.app.services.api_key_service import ApiKeyService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        result = await ApiKeyService.revoke_api_key(mock_db, uuid.uuid4(), uuid.uuid4())
        assert result is False

    @pytest.mark.asyncio
    async def test_rotate_api_key(self):
        from backend.app.services.api_key_service import ApiKeyService

        tenant_id = uuid.uuid4()
        created_by = uuid.uuid4()
        key_id = uuid.uuid4()

        original_key = ApiKey(
            id=key_id,
            tenant_id=tenant_id,
            created_by=created_by,
            name="Original",
            scopes=["predictions"],
            is_active=True,
        )

        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = original_key

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_get_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        new_key, raw_key = await ApiKeyService.rotate_api_key(
            db=mock_db,
            tenant_id=tenant_id,
            key_id=key_id,
            created_by=created_by,
        )

        assert original_key.is_active is False
        assert new_key.name == "Original"
        assert new_key.scopes == ["predictions"]
        assert len(raw_key) == 40

    @pytest.mark.asyncio
    async def test_rotate_nonexistent_key(self):
        from backend.app.services.api_key_service import ApiKeyService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="API Key not found"):
            await ApiKeyService.rotate_api_key(
                db=mock_db,
                tenant_id=uuid.uuid4(),
                key_id=uuid.uuid4(),
                created_by=uuid.uuid4(),
            )
