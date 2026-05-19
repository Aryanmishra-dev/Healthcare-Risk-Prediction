"""Shared test fixtures and configuration."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient — models loaded once via lifespan."""
    with TestClient(app) as c:
        yield c
