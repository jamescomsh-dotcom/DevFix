"""Stage 4.4 tests for partially updating one issue without MySQL."""

from collections.abc import AsyncIterator
from datetime import datetime
from types import SimpleNamespace
from typing import Any, cast
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
async def issue_update_session() -> AsyncIterator[SimpleNamespace]:
    created_at = datetime(2026, 8, 28, 15, 10, 20, 123456)
    updated_at = datetime(2026, 8, 29, 9, 30, 40, 654321)
    issue = Issue(
        title="更新前的标题",
        description="未提供的字段必须保持原值",
        error_message="ValueError: old error",
        ai_tool="旧工具",
        ai_prompt="旧提示词",
        solution="旧解决方案",
        verification_notes="旧验证记录",
        status=IssueStatus.OPEN,
    )
    issue.id = 7
    issue.created_at = created_at
    issue.updated_at = created_at
    events: list[str] = []

    async def find_issue(model: type[Issue], issue_id: int) -> Issue:
        events.append("get")
        return issue

    async def apply_database_values() -> None:
        events.append("flush")
        issue.updated_at = updated_at

    async def record_commit() -> None:
        events.append("commit")

    session = SimpleNamespace(
        get=AsyncMock(side_effect=find_issue),
        add=Mock(),
        flush=AsyncMock(side_effect=apply_database_values),
        commit=AsyncMock(side_effect=record_commit),
        refresh=AsyncMock(),
        delete=AsyncMock(),
        issue=issue,
        events=events,
    )

    async def override_database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_database] = override_database
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_database, None)


@pytest.mark.asyncio
async def test_patch_issue_updates_only_explicit_fields(
    client: AsyncClient,
    issue_update_session: SimpleNamespace,
) -> None:
    response = await client.patch(
        "/api/v1/issues/7",
        json={
            "title": "  更新后的标题  ",
            "ai_tool": "  Codex CLI  ",
            "solution": None,
            "status": "IN_PROGRESS",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 7,
        "title": "更新后的标题",
        "description": "未提供的字段必须保持原值",
        "error_message": "ValueError: old error",
        "ai_tool": "Codex CLI",
        "ai_prompt": "旧提示词",
        "solution": None,
        "verification_notes": "旧验证记录",
        "status": "IN_PROGRESS",
        "created_at": "2026-08-28T15:10:20.123456",
        "updated_at": "2026-08-29T09:30:40.654321",
    }
    assert issue_update_session.issue.description == (
        "未提供的字段必须保持原值"
    )
    assert issue_update_session.issue.solution is None
    assert issue_update_session.issue.status is IssueStatus.IN_PROGRESS
    issue_update_session.get.assert_awaited_once_with(Issue, 7)
    issue_update_session.flush.assert_awaited_once_with()
    issue_update_session.commit.assert_awaited_once_with()
    assert issue_update_session.events == ["get", "flush", "commit"]
    issue_update_session.add.assert_not_called()
    issue_update_session.refresh.assert_not_awaited()
    issue_update_session.delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "   "},
        {"description": None},
        {"status": None},
        {"status": "CLOSED"},
        {"id": 99},
        {"ai_tool": "x" * 51},
    ],
)
async def test_patch_issue_rejects_invalid_payloads_before_query(
    client: AsyncClient,
    issue_update_session: SimpleNamespace,
    payload: dict[str, Any],
) -> None:
    response = await client.patch("/api/v1/issues/7", json=payload)

    assert response.status_code == 422
    issue_update_session.get.assert_not_awaited()
    issue_update_session.flush.assert_not_awaited()
    issue_update_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_issue_returns_404_without_writing_when_missing(
    client: AsyncClient,
    issue_update_session: SimpleNamespace,
) -> None:
    issue_update_session.get.side_effect = None
    issue_update_session.get.return_value = None

    response = await client.patch(
        "/api/v1/issues/999",
        json={"title": "找不到的记录"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Issue 不存在。"}
    issue_update_session.get.assert_awaited_once_with(Issue, 999)
    issue_update_session.flush.assert_not_awaited()
    issue_update_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_issue_does_not_commit_when_flush_fails(
    client: AsyncClient,
    issue_update_session: SimpleNamespace,
) -> None:
    issue_update_session.flush.side_effect = RuntimeError("update failed")

    with pytest.raises(RuntimeError, match="update failed"):
        await client.patch(
            "/api/v1/issues/7",
            json={"title": "无法保存的标题"},
        )

    issue_update_session.get.assert_awaited_once_with(Issue, 7)
    issue_update_session.flush.assert_awaited_once_with()
    issue_update_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_openapi_exposes_patch_contract_for_issue_detail(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    detail_path = response.json()["paths"]["/api/v1/issues/{issue_id}"]
    assert "patch" in detail_path

    patch_operation = detail_path["patch"]
    assert {"200", "404", "422"}.issubset(patch_operation["responses"])
    request_schema = patch_operation["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert request_schema["$ref"].endswith("/IssueUpdate")
    response_schema = patch_operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert response_schema["$ref"].endswith("/IssueRead")
