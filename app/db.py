"""Build reusable asynchronous SQLAlchemy engine and session resources."""
"""异步SQLAlchemy的engine and session factory的创建,之后可以复用"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@dataclass(slots=True)
class DatabaseResources:
    """Process-level database resources shared by request sessions."""

    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    async def dispose(self) -> None:
        """Release pooled database connections during application shutdown."""
        await self.engine.dispose()

#下面的函数需要在main里调用，database_url需要传参
def build_database_resources(database_url: str) -> DatabaseResources:
    """Build lazy async resources without connecting or creating tables."""
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return DatabaseResources(
        engine=engine,
        session_factory=session_factory,
    )