"""Opt-in HTTP CRUD acceptance against a dedicated MySQL test database."""

import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_
from sqlalchemy.engine import make_url

from app.config import Settings
from app.db import DatabaseResources
from app.main import create_app
from app.models import Issue


RUN_MYSQL_CRUD_TESTS = (
    os.environ.get("DEVFIX_RUN_MYSQL_CRUD_TESTS") == "1"
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.mysql,
    pytest.mark.skipif(
        not RUN_MYSQL_CRUD_TESTS,
        reason=(
            "set DEVFIX_RUN_MYSQL_CRUD_TESTS=1 "
            "to enable real MySQL CRUD checks"
        ),
    ),
]


async def test_mysql_api_crud_round_trip() -> None:
    """Exercise all Issue endpoints through real request-scoped Sessions."""
    raw_database_url = os.environ.get("DEVFIX_TEST_DATABASE_URL")
    assert raw_database_url, "DEVFIX_TEST_DATABASE_URL is required"

    settings = Settings(_env_file=None, database_url=raw_database_url)
    assert settings.database_url is not None

    parsed_url = make_url(settings.database_url.get_secret_value())
    assert parsed_url.database is not None
    assert parsed_url.database.endswith("_test"), (
        "CRUD checks require a dedicated *_test database"
    )

    marker = f"crud-test-{uuid4().hex}"
    unique_title = f"MySQL CRUD 验收 {uuid4().hex}"
    application = create_app(settings=settings)

    async with application.router.lifespan_context(application):
        resources = application.state.database_resources
        assert isinstance(resources, DatabaseResources)
        transport = ASGITransport(
            app=application,
            raise_app_exceptions=True,
        )

        try:
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                create_response = await client.post(
                    "/api/v1/issues",
                    json={
                        "title": unique_title,
                        "description": "验证真实 FastAPI 与 MySQL CRUD 调用链",
                        "error_message": "RuntimeError: acceptance marker",
                        "ai_tool": "Codex",
                        "ai_prompt": marker,
                    },
                )
                assert create_response.status_code == 201
                created_issue = create_response.json()
                issue_id = created_issue["id"]
                assert isinstance(issue_id, int)
                assert created_issue["title"] == unique_title
                assert created_issue["status"] == "OPEN"

                list_response = await client.get("/api/v1/issues")
                assert list_response.status_code == 200
                assert any(
                    item["id"] == issue_id
                    for item in list_response.json()
                )

                detail_response = await client.get(
                    f"/api/v1/issues/{issue_id}"
                )
                assert detail_response.status_code == 200
                assert detail_response.json()["ai_prompt"] == marker

                update_response = await client.patch(
                    f"/api/v1/issues/{issue_id}",
                    json={
                        "error_message": None,
                        "solution": "真实 MySQL 更新已提交",
                        "verification_notes": "HTTP CRUD round-trip",
                        "status": "RESOLVED",
                    },
                )
                assert update_response.status_code == 200
                updated_issue = update_response.json()
                assert updated_issue["title"] == unique_title
                assert updated_issue["error_message"] is None
                assert updated_issue["status"] == "RESOLVED"

                persisted_response = await client.get(
                    f"/api/v1/issues/{issue_id}"
                )
                assert persisted_response.status_code == 200
                persisted_issue = persisted_response.json()
                assert persisted_issue["title"] == unique_title
                assert persisted_issue["description"] == (
                    "验证真实 FastAPI 与 MySQL CRUD 调用链"
                )
                assert persisted_issue["error_message"] is None
                assert persisted_issue["solution"] == (
                    "真实 MySQL 更新已提交"
                )
                assert persisted_issue["ai_prompt"] == marker
                assert persisted_issue["status"] == "RESOLVED"

                delete_response = await client.delete(
                    f"/api/v1/issues/{issue_id}"
                )
                assert delete_response.status_code == 204
                assert delete_response.content == b""

                missing_response = await client.get(
                    f"/api/v1/issues/{issue_id}"
                )
                assert missing_response.status_code == 404
                assert missing_response.json() == {
                    "detail": "Issue 不存在。"
                }
        finally:
            async with resources.session_factory.begin() as cleanup_session:
                await cleanup_session.execute(
                    delete(Issue).where(
                        or_(
                            Issue.ai_prompt == marker,
                            Issue.title == unique_title,
                        )
                    )
                )
