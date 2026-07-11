"""Shared test fixtures and configuration."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DEV_API_KEY", "test-dev-api-key")

from backend.app.main import app

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.app.core.database import get_db
from backend.app.models.base import Base

from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared&uri=true"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db
import backend.app.core.database as core_db
import backend.app.services.audit_log as audit_log
core_db.AsyncSessionLocal = TestingSessionLocal
audit_log.AsyncSessionLocal = TestingSessionLocal

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
