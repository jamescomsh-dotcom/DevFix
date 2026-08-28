"""Opt-in, read-only MySQL integration acceptance test."""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.db import build_database_resources

RUN_MYSQL_TESTS = os.environ.get("DEVFIX_RUN_MYSQL_TESTS") == "1"

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.mysql,
    pytest.mark.skipif(
        not RUN_MYSQL_TESTS,
        reason="set DEVFIX_RUN_MYSQL_TESTS=1 to enable real MySQL checks",
    ),
]


async def test_mysql_async_session_selects_one() -> None:
    raw_database_url = os.environ.get("DEVFIX_TEST_DATABASE_URL")
    assert raw_database_url, "DEVFIX_TEST_DATABASE_URL is required"

    settings = Settings(_env_file=None, database_url=raw_database_url)
    assert settings.database_url is not None

    parsed_url = make_url(settings.database_url.get_secret_value())
    assert parsed_url.database is not None
    assert parsed_url.database.endswith("_test"), (
        "integration checks require a dedicated *_test database"
    )

    resources = build_database_resources(
        settings.database_url.get_secret_value()
    )
    try:
        async with resources.session_factory() as session:
            value = await session.scalar(text("SELECT 1"))
        assert value == 1
    finally:
        await resources.dispose()

