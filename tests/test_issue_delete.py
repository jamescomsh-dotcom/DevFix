"""Stage 4.5 tests for deleting one issue without MySQL."""

from collections.abc import AsyncIterator
from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock, call

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_database
from app.enums import IssueStatus
from app.main import app
from app.models import Issue


@pytest_asyncio.fixture
async def issue_delete_session() -> AsyncIterator[SimpleNamespace]:
    persisted_at = datetime(2026, 8, 29, 10, 20, 30, 123456)
    issue = Issue(
        title="准备删除的问题",
        description="删除后应无法再次查询",
        error_message=None,
        ai_tool="Codex",
        ai_prompt=None,
        solution=None,
        verification_notes=None,
        status=IssueStatus.OPEN,
    )
    issue.id = 7
    issue.created_at = persisted_at
    issue.updated_at = persisted_at
    events: list[str] = []
    state = {"deleted": False}

    async def find_issue(model: type[Issue], issue_id: int) -> Issue | None:
        events.append("get")
        return None if state["deleted"] else issue

    async def mark_for_deletion(issue_to_delete: Issue) -> None:
        events.append("delete")

    async def flush_deletion() -> None:
        events.append("flush")

    async def commit_deletion() -> None:
        events.append("commit")
        state["deleted"] = True

    session = SimpleNamespace(
        get=AsyncMock(side_effect=find_issue),
        delete=AsyncMock(side_effect=mark_for_deletion),
        flush=AsyncMock(side_effect=flush_deletion),
        commit=AsyncMock(side_effect=commit_deletion),
        add=Mock(),
        refresh=AsyncMock(),
        issue=issue,
        events=events,
        state=state,
    )

    async def override_database() -> AsyncIterator[AsyncSession]:
        yield cast(AsyncSession, session)

    app.dependency_overrides[get_database] = override_database
    try:
        yield session
    finally:
        app.dependency_overrides.pop(get_database, None)


@pytest.mark.asyncio
async def test_delete_issue_returns_empty_204_then_get_returns_404(
    client: AsyncClient,
    issue_delete_session: SimpleNamespace,
) -> None:
    delete_response = await client.delete("/api/v1/issues/7")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert delete_response.text == ""
    assert "content-type" not in delete_response.headers
    issue_delete_session.delete.assert_awaited_once_with(
        issue_delete_session.issue
    )
    issue_delete_session.flush.assert_awaited_once_with()
    issue_delete_session.commit.assert_awaited_once_with()
    issue_delete_session.add.assert_not_called()
    issue_delete_session.refresh.assert_not_awaited()

    get_response = await client.get("/api/v1/issues/7")

    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Issue 不存在。"}
    assert issue_delete_session.get.await_args_list == [
        call(Issue, 7),
        call(Issue, 7),
    ]
    assert issue_delete_session.events == [
        "get",
        "delete",
        "flush",
        "commit",
        "get",
    ]


@pytest.mark.asyncio
async def test_delete_issue_returns_404_without_writing_when_missing(
    client: AsyncClient,
    issue_delete_session: SimpleNamespace,
) -> None:
    issue_delete_session.state["deleted"] = True

    response = await client.delete("/api/v1/issues/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Issue 不存在。"}
    issue_delete_session.get.assert_awaited_once_with(Issue, 999)
    issue_delete_session.delete.assert_not_awaited()
    issue_delete_session.flush.assert_not_awaited()
    issue_delete_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_issue_rejects_non_integer_path_id(
    client: AsyncClient,
    issue_delete_session: SimpleNamespace,
) -> None:
    response = await client.delete("/api/v1/issues/not-an-int")

    assert response.status_code == 422
    issue_delete_session.get.assert_not_awaited()
    issue_delete_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_issue_stops_when_delete_fails(
    client: AsyncClient,
    issue_delete_session: SimpleNamespace,
) -> None:
    async def fail_delete(issue_to_delete: Issue) -> None:
        issue_delete_session.events.append("delete")
        raise RuntimeError("delete failed")

    issue_delete_session.delete.side_effect = fail_delete

    with pytest.raises(RuntimeError, match="delete failed"):
        await client.delete("/api/v1/issues/7")

    assert issue_delete_session.events == ["get", "delete"]
    issue_delete_session.flush.assert_not_awaited()
    issue_delete_session.commit.assert_not_awaited()
    assert issue_delete_session.state["deleted"] is False


@pytest.mark.asyncio
async def test_delete_issue_does_not_commit_when_flush_fails(
    client: AsyncClient,
    issue_delete_session: SimpleNamespace,
) -> None:
    async def fail_flush() -> None:
        issue_delete_session.events.append("flush")
        raise RuntimeError("delete flush failed")

    issue_delete_session.flush.side_effect = fail_flush

    with pytest.raises(RuntimeError, match="delete flush failed"):
        await client.delete("/api/v1/issues/7")

    assert issue_delete_session.events == ["get", "delete", "flush"]
    issue_delete_session.commit.assert_not_awaited()
    assert issue_delete_session.state["deleted"] is False


@pytest.mark.asyncio
async def test_openapi_exposes_complete_issue_crud_methods(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert set(paths["/api/v1/issues"]) == {"get", "post"}
    detail_path = paths["/api/v1/issues/{issue_id}"]
    assert set(detail_path) == {"get", "patch", "delete"}

    delete_operation = detail_path["delete"]
    assert {"204", "404", "422"}.issubset(delete_operation["responses"])
    assert "200" not in delete_operation["responses"]
    assert "content" not in delete_operation["responses"]["204"]
    assert "requestBody" not in delete_operation
