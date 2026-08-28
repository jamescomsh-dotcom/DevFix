"""Stage 4.1 tests for creating one issue without a real database."""

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
from app.schemas.issue import IssueCreate
from app.services.issue_service import create_issue


@pytest_asyncio.fixture
async def issue_session() -> AsyncIterator[SimpleNamespace]:
    persisted_at = datetime(2026, 8, 28, 12, 30, 45, 123456)
    events: list[str] = []
    session = SimpleNamespace(
        add=Mock(side_effect=lambda issue: events.append("add")),
        flush=AsyncMock(),
        refresh=AsyncMock(),
        commit=AsyncMock(),
        events=events,
    )

    async def apply_database_values() -> None:
        events.append("flush")
        issue = session.add.call_args.args[0]
        issue.id = 1
        issue.status = IssueStatus.OPEN
        issue.created_at = persisted_at
        issue.updated_at = persisted_at

    async def record_commit() -> None:
        events.append("commit")

    session.flush.side_effect = apply_database_values
    session.commit.side_effect = record_commit

    async def override_database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_database] = override_database
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_database, None)


@pytest.mark.asyncio
async def test_create_issue_returns_201_and_persisted_record(
    client: AsyncClient,
    issue_session: SimpleNamespace,
) -> None:
    response = await client.post(
        "/api/v1/issues",
        json={
            "title": "  AsyncSession 提交失败  ",
            "description": "  调查事务为什么没有保存  ",
            "error_message": "RuntimeError: commit failed",
            "ai_tool": "  Codex  ",
            "ai_prompt": "检查事务边界",
            "solution": "显式提交事务",
            "verification_notes": "重新查询记录成功",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "title": "AsyncSession 提交失败",
        "description": "调查事务为什么没有保存",
        "error_message": "RuntimeError: commit failed",
        "ai_tool": "Codex",
        "ai_prompt": "检查事务边界",
        "solution": "显式提交事务",
        "verification_notes": "重新查询记录成功",
        "status": "OPEN",
        "created_at": "2026-08-28T12:30:45.123456",
        "updated_at": "2026-08-28T12:30:45.123456",
    }

    issue_session.add.assert_called_once()
    created_issue = issue_session.add.call_args.args[0]
    assert isinstance(created_issue, Issue)
    assert created_issue.title == "AsyncSession 提交失败"
    assert created_issue.description == "调查事务为什么没有保存"
    assert created_issue.ai_tool == "Codex"
    issue_session.flush.assert_awaited_once_with()
    issue_session.commit.assert_awaited_once_with()
    issue_session.refresh.assert_not_awaited()
    assert issue_session.events == ["add", "flush", "commit"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("title", "   "),
        ("description", "   "),
        ("ai_tool", "x" * 51),
    ],
)
async def test_create_issue_rejects_invalid_text_fields(
    client: AsyncClient,
    issue_session: SimpleNamespace,
    field_name: str,
    invalid_value: str,
) -> None:
    payload = {
        "title": "无法连接数据库",
        "description": "连接被拒绝",
    }
    payload[field_name] = invalid_value

    response = await client.post("/api/v1/issues", json=payload)

    assert response.status_code == 422
    issue_session.add.assert_not_called()
    issue_session.flush.assert_not_awaited()
    issue_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_issue_rejects_server_managed_fields(
    client: AsyncClient,
    issue_session: SimpleNamespace,
) -> None:
    response = await client.post(
        "/api/v1/issues",
        json={
            "title": "错误地覆盖状态",
            "description": "创建接口不允许指定服务端字段",
            "status": "RESOLVED",
            "id": 99,
            "unexpected": True,
        },
    )

    assert response.status_code == 422
    issue_session.add.assert_not_called()
    issue_session.flush.assert_not_awaited()
    issue_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_issue_propagates_flush_error_without_committing() -> None:
    session = SimpleNamespace(
        add=Mock(),
        flush=AsyncMock(side_effect=RuntimeError("insert failed")),
        commit=AsyncMock(),
    )
    issue_data = IssueCreate(
        title="插入失败",
        description="验证异常继续交给数据库依赖处理",
    )

    with pytest.raises(RuntimeError, match="insert failed"):
        await create_issue(cast(AsyncSession, session), issue_data)

    session.add.assert_called_once()
    session.flush.assert_awaited_once_with()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_openapi_exposes_only_post_for_issue_collection(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    issue_path = paths["/api/v1/issues"]
    assert set(issue_path) == {"post"}
    assert issue_path["post"]["responses"].get("201") is not None
    assert "/api/v1/issues/{issue_id}" not in paths
