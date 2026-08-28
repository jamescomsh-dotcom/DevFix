"""Business operations for the single Issue resource."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Issue
from app.schemas.issue import IssueCreate


async def create_issue(
    session: AsyncSession,
    issue_data: IssueCreate,
) -> Issue:
    """Insert and commit one Issue using the request-scoped Session."""
    issue = Issue(**issue_data.model_dump())
    session.add(issue)
    await session.flush()
    await session.commit()
    return issue


async def list_issues(session: AsyncSession) -> list[Issue]:
    """Return all issues in a stable newest-first order."""
    statement = select(Issue).order_by(
        Issue.created_at.desc(),
        Issue.id.desc(),
    )
    result = await session.scalars(statement)
    return list(result.all())
