"""Shared test fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_API_KEY", "test-dev-api-key")

from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient — models loaded once via lifespan."""
    with TestClient(app) as c:
        yield c
