"""Pluggable secret provider abstraction.

Replace direct os.environ / settings reads with a ``SecretProvider``
interface so that secrets can be sourced from environment variables,
HashiCorp Vault, AWS Secrets Manager, or Kubernetes secrets without
changing application code.

Usage::

    from backend.app.core.secret_provider import env_secret_provider

    db_password = env_secret_provider.get("DB_PASSWORD")
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional


class SecretProvider(ABC):
    """Abstract interface for secret retrieval."""

    @abstractmethod
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret by key.

        Returns ``None`` (or *default*) when the secret does not exist.
        Implementations **must not** raise for missing keys.
        """
        ...

    @abstractmethod
    def list_keys(self) -> list[str]:
        """Return all available secret keys (for auditing / validation)."""
        ...


class EnvSecretProvider(SecretProvider):
    """Reads secrets from the process environment variables."""

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)  # type: ignore[arg-type]

    def list_keys(self) -> list[str]:
        return [k for k in os.environ.keys() if not k.startswith("_")]


env_secret_provider: SecretProvider = EnvSecretProvider()
