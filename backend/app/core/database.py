from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings

# SQLite directory creation is now handled lazily when getting a connection

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env != "production",
    future=True,
    pool_pre_ping=True,
    # RC2: production-grade pool sizing
    # Default of 5 connections is insufficient under concurrent load.
    # pool_size=10 + max_overflow=20 allows up to 30 concurrent DB connections.
    # These values are tuned for a 2-worker gunicorn deployment.
    # Increase proportionally when adding workers.
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # Ensure SQLite directory exists before SQLAlchemy attempts to connect
    if settings.database_url.startswith("sqlite"):
        parsed = urlparse(settings.database_url)
        db_path = Path(parsed.path.lstrip("/"))
        if db_path.name != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        yield session
