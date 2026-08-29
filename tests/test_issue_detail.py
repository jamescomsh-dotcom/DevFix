"""Stage 4.3 tests for reading one issue without a real database."""

from collections.abc import AsyncIterator
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database
from app.enums import IssueStatus
from app.main import app
from app.models import Issue


@pytest_asyncio.fixture
async def issue_detail_session() -> AsyncIterator[SimpleNamespace]:
    persisted_at = datetime(2026, 8, 28, 15, 10, 20, 123456)
    issue = Issue(
        title="定位异步查询错误",
        description="记录并解释详情查询的调用链",
        error_message="ValueError: invalid result",
        ai_tool="Codex",
        ai_prompt=None,
        solution="使用 AsyncSession.get 按主键查询",
        verification_notes="详情接口测试通过",
        status=IssueStatus.RESOLVED,
    )
    issue.id = 7
    issue.created_at = persisted_at
    issue.updated_at = persisted_at

    session = SimpleNamespace(
        get=AsyncMock(return_value=issue),
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
async def test_get_issue_returns_200_and_complete_record(
    client: AsyncClient,
    issue_detail_session: SimpleNamespace,
) -> None:
    response = await client.get("/api/v1/issues/7")

    assert response.status_code == 200
    assert response.json() == {
        "id": 7,
        "title": "定位异步查询错误",
        "description": "记录并解释详情查询的调用链",
        "error_message": "ValueError: invalid result",
        "ai_tool": "Codex",
        "ai_prompt": None,
        "solution": "使用 AsyncSession.get 按主键查询",
        "verification_notes": "详情接口测试通过",
        "status": "RESOLVED",
        "created_at": "2026-08-28T15:10:20.123456",
        "updated_at": "2026-08-28T15:10:20.123456",
    }
    issue_detail_session.get.assert_awaited_once_with(Issue, 7)
    issue_detail_session.add.assert_not_called()
    issue_detail_session.flush.assert_not_awaited()
    issue_detail_session.commit.assert_not_awaited()
    issue_detail_session.refresh.assert_not_awaited()
    issue_detail_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_issue_returns_404_when_record_does_not_exist(
    client: AsyncClient,
    issue_detail_session: SimpleNamespace,
) -> None:
    issue_detail_session.get.return_value = None

    response = await client.get("/api/v1/issues/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Issue 不存在。"}
    issue_detail_session.get.assert_awaited_once_with(Issue, 999)


@pytest.mark.asyncio
async def test_get_issue_rejects_non_integer_path_id(
    client: AsyncClient,
    issue_detail_session: SimpleNamespace,
) -> None:
    response = await client.get("/api/v1/issues/not-an-int")

    assert response.status_code == 422
    issue_detail_session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_openapi_exposes_get_contract_for_issue_detail(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths["/api/v1/issues"]) == {"get", "post"}

    detail_path = paths["/api/v1/issues/{issue_id}"]
    assert "get" in detail_path
    detail_operation = detail_path["get"]
    assert {"200", "404", "422"}.issubset(detail_operation["responses"])
    response_schema = detail_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema["$ref"].endswith("/IssueRead")
    assert detail_operation["responses"]["404"]["description"] == (
        "Issue 不存在"
    )
    assert detail_operation["parameters"] == [
        {
            "name": "issue_id",
            "in": "path",
            "required": True,
            "schema": {"type": "integer", "title": "Issue Id"},
        }
    ]
