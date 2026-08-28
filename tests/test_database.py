"""Stage 1 async database resource and lifecycle tests."""

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db import DatabaseResources, build_database_resources
from app.dependencies import (
    DatabaseNotConfiguredError,
    get_database,
    get_database_resources,
)
from app.main import create_app

pytestmark = pytest.mark.asyncio


async def test_build_database_resources_uses_async_session() -> None:
    resources = build_database_resources(
        "mysql+asyncmy://devfix:password@127.0.0.1:3306/devfix"
    )

    try:
        assert resources.engine.dialect.name == "mysql"
        assert resources.engine.dialect.driver == "asyncmy"
        assert resources.engine.dialect.is_async is True
        assert resources.session_factory.class_ is AsyncSession
        assert resources.session_factory.kw["expire_on_commit"] is False

        session = resources.session_factory()
        assert isinstance(session, AsyncSession)
        await session.close()
    finally:
        await resources.dispose()


async def test_database_dependency_closes_session_after_success() -> None:
    session = SimpleNamespace(
        rollback=AsyncMock(),
        close=AsyncMock(),
    )
    session_factory = Mock(return_value=session)
    resources = cast(
        DatabaseResources,
        SimpleNamespace(session_factory=session_factory),
    )
    dependency = get_database(resources)

    provided_session = await anext(dependency)
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert provided_session is session
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once_with()


async def test_database_dependency_rolls_back_and_closes_after_error() -> None:
    session = SimpleNamespace(
        rollback=AsyncMock(),
        close=AsyncMock(),
    )
    resources = cast(
        DatabaseResources,
        SimpleNamespace(session_factory=Mock(return_value=session)),
    )
    dependency = get_database(resources)

    await anext(dependency)
    error = RuntimeError("request failed")
    with pytest.raises(RuntimeError, match="request failed"):
        await dependency.athrow(error)

    session.rollback.assert_awaited_once_with()
    session.close.assert_awaited_once_with()


async def test_missing_database_resources_raise_clear_error() -> None:
    request = cast(
        Request,
        SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(database_resources=None),
            )
        ),
    )

    with pytest.raises(DatabaseNotConfiguredError, match="DATABASE_URL"):
        get_database_resources(request)


async def test_lifespan_skips_database_when_url_is_missing() -> None:
    settings = Settings(_env_file=None, database_url=None)

    with patch("app.main.build_database_resources") as build_resources:
        application = create_app(settings=settings)
        async with application.router.lifespan_context(application):
            assert application.state.database_resources is None

    build_resources.assert_not_called()


async def test_lifespan_disposes_engine_without_connecting() -> None:
    settings = Settings(
        _env_file=None,
        database_url="mysql+asyncmy://devfix:password@127.0.0.1:1/devfix",
    )
    resources = SimpleNamespace(dispose=AsyncMock())

    with patch(
        "app.main.build_database_resources",
        return_value=resources,
    ) as build_resources:
        application = create_app(settings=settings)
        async with application.router.lifespan_context(application):
            assert application.state.database_resources is resources

    build_resources.assert_called_once_with(
        settings.database_url.get_secret_value()  # type: ignore[union-attr]
    )
    resources.dispose.assert_awaited_once_with()
    assert application.state.database_resources is None


async def test_application_source_never_calls_create_all() -> None:
    forbidden_call = "create" + "_all"
    application_directory = Path(__file__).resolve().parents[1] / "app"
    source_files = application_directory.rglob("*.py")

    matches = [
        str(source_file)
        for source_file in source_files
        if forbidden_call in source_file.read_text(encoding="utf-8")
    ]

    assert matches == []
