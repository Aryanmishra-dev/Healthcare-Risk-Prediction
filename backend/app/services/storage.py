import os
from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

import aiofiles


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def save_file(
        self, user_id: UUID, report_uuid: str, filename: str, content: bytes
    ) -> str:
        """Save a file and return its storage path."""
        pass

    @abstractmethod
    async def get_file(self, storage_path: str) -> bytes:
        """Retrieve a file by its storage path."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file by its storage path."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider."""

    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = Path(base_dir)

    async def save_file(
        self, user_id: UUID, report_uuid: str, filename: str, content: bytes
    ) -> str:
        # Prevent path traversal
        safe_filename = os.path.basename(filename)

        dir_path = self.base_dir / str(user_id) / report_uuid
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / safe_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return str(file_path)

    async def get_file(self, storage_path: str) -> bytes:
        path = Path(storage_path)
        # Security: Prevent traversing out of base_dir
        if not path.is_absolute():
            path = path.resolve()

        if not path.is_relative_to(self.base_dir.resolve()):
            raise ValueError("Invalid storage path")

        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, storage_path: str) -> bool:
        path = Path(storage_path)
        if not path.is_absolute():
            path = path.resolve()

        if not path.is_relative_to(self.base_dir.resolve()):
            raise ValueError("Invalid storage path")

        if path.exists() and path.is_file():
            os.remove(path)
            return True
        return False


# Global instance for injection
storage_provider = LocalStorageProvider()
