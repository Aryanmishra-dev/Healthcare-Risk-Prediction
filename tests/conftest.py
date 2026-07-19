import os

import pytest
from fastapi.testclient import TestClient

# Tell HardenedRateLimiter to skip in-memory throttle during tests.
# Redis is not available in CI, so without this flag tests would be
# rate-limited by the fallback bucket after just a few requests.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DEV_API_KEY", "test-dev-api-key")

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.base import Base

TEST_DATABASE_URL = (
    "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"
)

engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool)
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
import backend.app.core.database as core_db
import backend.app.services.audit_log as audit_log

core_db.AsyncSessionLocal = TestingSessionLocal
audit_log.AsyncSessionLocal = TestingSessionLocal

import backend.app.models.api_key  # noqa: F401, E402
import backend.app.models.audit_event  # noqa: F401, E402

# Import all models so FK references are resolved in metadata
import backend.app.models.tenant  # noqa: F401, E402
import backend.app.models.usage  # noqa: F401, E402
import backend.app.models.webhook  # noqa: F401, E402


@pytest.fixture(autouse=True)
def setup_db():
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest.fixture(scope="session")
def client():
    """Session-scoped TestClient"""
    with TestClient(app) as c:
        yield c
