from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from backend.app.core.config import settings

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
    async with AsyncSessionLocal() as session:
        yield session
