import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings  # noqa: E402
from backend.app.models import Base  # noqa: E402

target_metadata = Base.metadata


def _include_symbol(tablename: str, schema: str | None) -> bool:
    """Include all tables in autogenerate migrations."""
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.database_url
    config.set_main_option("sqlalchemy.url", url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_symbol=_include_symbol,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    is_sqlite = "sqlite" in settings.database_url
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=is_sqlite,
        compare_type=True,
        compare_server_default=True,
        include_symbol=_include_symbol,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        if "sqlite" in settings.database_url:

            def _setup_sqlite(conn):
                from alembic.migration import MigrationContext
                from alembic.script import ScriptDirectory

                # Create all tables for SQLite (incr ALTER not supported).
                Base.metadata.create_all(conn)

                # Stamp to head so alembic state is consistent.
                script = ScriptDirectory.from_config(config)
                head_revision = script.get_heads()[0]
                mc = MigrationContext.configure(
                    conn,
                    opts={"target_metadata": Base.metadata},
                )
                mc.stamp(script, head_revision)

            await connection.run_sync(_setup_sqlite)
        else:
            await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
