"""Alembic environment for the asynchronous DevFix MySQL database."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

#下面的是修改后的导入
from sqlalchemy.engine import Connection, URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> URL:
    """Return the validated secret URL only while an Alembic command runs."""
    database_url = get_settings().database_url
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is required for Alembic commands."
        )
    return make_url(database_url.get_secret_value())


def run_migrations_offline() -> None:
    """Render SQL without creating an Engine or opening a connection."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run configured revisions on an existing synchronous connection view."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create a short-lived async Engine for online Alembic commands."""
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations through SQLAlchemy's asynchronous Engine."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
