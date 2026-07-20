import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncGenerator

import aiofiles  # type: ignore[import-untyped]


class ExportProvider(ABC):
    """Abstract base class for export storage providers."""

    @abstractmethod
    async def save_export(
        self, user_id: str, export_id: str, filename: str, content: bytes
    ) -> str:
        """Saves the export data and returns the storage path/URI."""
        pass

    @abstractmethod
    async def get_export_stream(
        self, storage_path: str
    ) -> AsyncGenerator[bytes, None]:
        """Returns an async generator to stream the export data."""
        pass

    @abstractmethod
    async def delete_export(self, storage_path: str) -> None:
        """Deletes the export data from storage."""
        pass


import logging

logger = logging.getLogger(__name__)


class LocalExportProvider(ExportProvider):
    """Local filesystem implementation of ExportProvider."""

    def __init__(self, base_dir: str = "exports_data"):
        self.base_dir = Path(base_dir).resolve()
        logger.info(
            f"LocalExportProvider initialized with base_dir: {self.base_dir}"
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_export(
        self, user_id: str, export_id: str, filename: str, content: bytes
    ) -> str:
        # Prevent path traversal
        safe_user_id = os.path.basename(user_id)
        safe_export_id = os.path.basename(export_id)
        safe_filename = os.path.basename(filename)

        user_dir = self.base_dir / safe_user_id / safe_export_id
        user_dir.mkdir(parents=True, exist_ok=True)

        file_path = user_dir / safe_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return str(file_path.absolute())

    async def get_export_stream(
        self, storage_path: str
    ) -> AsyncGenerator[bytes, None]:
        path = Path(storage_path)
        # Security: verify it's within our base_dir
        try:
            path.resolve().relative_to(self.base_dir.resolve())
        except ValueError:
            raise ValueError("Invalid storage path")

        if not path.exists() or not path.is_file():
            raise FileNotFoundError("Export file not found")

        async def iterfile():
            async with aiofiles.open(path, "rb") as f:
                while chunk := await f.read(1024 * 1024):  # 1MB chunks
                    yield chunk

        return iterfile()

    async def delete_export(self, storage_path: str) -> None:
        path = Path(storage_path)
        try:
            path.resolve().relative_to(self.base_dir.resolve())
        except ValueError:
            raise ValueError("Invalid storage path")

        if path.exists() and path.is_file():
            path.unlink()
            # Optionally remove the empty parent directory (export_id dir)
            parent = path.parent
            try:
                parent.rmdir()
            except OSError:
                pass
