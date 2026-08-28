"""Stage 4.2 tests for listing issues without a real database."""

from collections.abc import AsyncIterator
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database
from app.enums import IssueStatus
from app.main import app
from app.models import Issue


def build_issue(
    *,
    issue_id: int,
    title: str,
    created_at: datetime,
) -> Issue:
    """Build a complete ORM object as if it had been loaded from MySQL."""
    issue = Issue(
        title=title,
        description=f"{title}的描述",
        error_message=None,
        ai_tool="Codex",
        ai_prompt="分析问题",
        solution="记录解决方案",
        verification_notes="自动化测试通过",
        status=IssueStatus.OPEN,
    )
    issue.id = issue_id
    issue.created_at = created_at
    issue.updated_at = created_at
    return issue


@pytest_asyncio.fixture
async def issue_list_session() -> AsyncIterator[SimpleNamespace]:
    newer_issue = build_issue(
        issue_id=2,
        title="较新的问题",
        created_at=datetime(2026, 8, 28, 14, 0, 0),
    )
    older_issue = build_issue(
        issue_id=1,
        title="较早的问题",
        created_at=datetime(2026, 8, 28, 13, 0, 0),
    )
    scalar_result = Mock()
    scalar_result.all.return_value = [newer_issue, older_issue]
    session = SimpleNamespace(
        scalars=AsyncMock(return_value=scalar_result),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        refresh=AsyncMock(),
        delete=AsyncMock(),
    )

    async def override_database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_database] = override_database
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_database, None)


@pytest.mark.asyncio
async def test_list_issues_returns_200_in_stable_newest_first_order(
    client: AsyncClient,
    issue_list_session: SimpleNamespace,
) -> None:
    response = await client.get("/api/v1/issues")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [2, 1]
    assert [item["title"] for item in response.json()] == [
        "较新的问题",
        "较早的问题",
    ]

    issue_list_session.scalars.assert_awaited_once()
    statement = issue_list_session.scalars.await_args.args[0]
    compiled_sql = " ".join(
        str(statement.compile(dialect=mysql.dialect())).split()
    )
    order_by_sql = compiled_sql.partition(" ORDER BY ")[2]
    assert order_by_sql == "issues.created_at DESC, issues.id DESC"
    assert " WHERE " not in compiled_sql
    assert " LIMIT " not in compiled_sql
    assert " OFFSET " not in compiled_sql

    issue_list_session.add.assert_not_called()
    issue_list_session.flush.assert_not_awaited()
    issue_list_session.commit.assert_not_awaited()
    issue_list_session.refresh.assert_not_awaited()
    issue_list_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_issues_returns_empty_array(
    client: AsyncClient,
    issue_list_session: SimpleNamespace,
) -> None:
    empty_result = Mock()
    empty_result.all.return_value = []
    issue_list_session.scalars.return_value = empty_result

    response = await client.get("/api/v1/issues")

    assert response.status_code == 200
    assert response.json() == []
    issue_list_session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_openapi_exposes_get_and_post_for_issue_collection(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    issue_path = paths["/api/v1/issues"]
    assert set(issue_path) == {"get", "post"}
    assert issue_path["get"].get("parameters") is None
    get_schema = issue_path["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert get_schema["type"] == "array"
    assert get_schema["items"]["$ref"].endswith("/IssueRead")
    assert "/api/v1/issues/{issue_id}" not in paths
