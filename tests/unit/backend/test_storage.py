"""Tests for storage providers (47% coverage -> target 80%)."""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLocalStorageProvider:
    @pytest.mark.asyncio
    async def test_save_file_returns_path(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            uid = uuid.uuid4()
            report_uuid = str(uuid.uuid4())
            content = b"test file content"
            result = await provider.save_file(
                uid, report_uuid, "report.pdf", content
            )
            assert result is not None
            assert os.path.exists(result)
            with open(result, "rb") as f:
                assert f.read() == content

    @pytest.mark.asyncio
    async def test_save_file_sanitizes_path_traversal(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            uid = uuid.uuid4()
            report_uuid = str(uuid.uuid4())
            content = b"safe"
            result = await provider.save_file(
                uid, report_uuid, "../../etc/passwd", content
            )
            assert result is not None
            assert "../" not in result
            assert "etc" not in result
            assert os.path.exists(result)

    @pytest.mark.asyncio
    async def test_get_file_returns_content(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            file_path = Path(tmpdir) / "testfile.txt"
            file_path.write_bytes(b"hello")
            result = await provider.get_file(str(file_path))
            assert result == b"hello"

    @pytest.mark.asyncio
    async def test_get_file_rejects_path_outside_base(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            with pytest.raises(ValueError, match="Invalid storage path"):
                await provider.get_file("/etc/passwd")

    @pytest.mark.asyncio
    async def test_delete_file_existing(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            file_path = Path(tmpdir) / "delete_me.txt"
            file_path.write_bytes(b"bye")
            result = await provider.delete_file(str(file_path))
            assert result is True
            assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_nonexistent(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            result = await provider.delete_file(str(Path(tmpdir) / "nope.txt"))
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_rejects_path_outside_base(self):
        from backend.app.services.storage import LocalStorageProvider

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = LocalStorageProvider(base_dir=tmpdir)
            with pytest.raises(ValueError, match="Invalid storage path"):
                await provider.delete_file("/etc/shadow")

    def test_global_instance_created(self):
        from backend.app.services.storage import (
            LocalStorageProvider,
            storage_provider,
        )

        assert isinstance(storage_provider, LocalStorageProvider)
