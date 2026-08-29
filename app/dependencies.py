"""FastAPI dependencies shared by database-backed routes."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import DatabaseResources


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database-backed route has no configured resources."""


def get_database_resources(request: Request) -> DatabaseResources:
    """Read process-level database resources from the FastAPI application."""
    resources: DatabaseResources | None = getattr(
        request.app.state,
        "database_resources",
        None,
    )
    if resources is None:
        raise DatabaseNotConfiguredError(
            "数据库尚未配置，请先设置 DATABASE_URL。"
        )
    return resources


async def get_database(
    resources: Annotated[DatabaseResources, Depends(get_database_resources)],
) -> AsyncIterator[AsyncSession]:
    """Yield one AsyncSession and always close it after the request."""
    session = resources.session_factory()
    #因为resources是DatabaseResources类里的对象，本来应该是resources.session_factory，是在DatabaseResources类里取出
    #session_factory()这个，然后用session()=resources.session_factory,session=session()才行，但是这里直接用了resources.session_factory()
    #相当于两步合成一步了
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

#routers里直接导入DatabaseSession，就可以直接使用ORM的增删改查方法
DatabaseSession = Annotated[AsyncSession, Depends(get_database)]
