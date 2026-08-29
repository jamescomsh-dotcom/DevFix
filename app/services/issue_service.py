"""Business operations for the single Issue resource."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Issue
from app.schemas.issue import IssueCreate, IssueUpdate


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


async def get_issue(
    session: AsyncSession,
    issue_id: int,
) -> Issue | None:
    """Return one Issue by primary key, or None when it does not exist."""
    #get(ORM类.ORM类里的id)
    return await session.get(Issue, issue_id)


async def update_issue(
    session: AsyncSession,
    issue_id: int,
    issue_data: IssueUpdate,
) -> Issue | None:
    """Apply explicitly provided fields and commit one Issue update."""
    issue = await get_issue(session, issue_id)
    if issue is None:
        return None

    changes = issue_data.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(issue, field_name, value)

    await session.flush()
    await session.commit()
    return issue


async def delete_issue(
    session: AsyncSession,
    issue_id: int,
) -> bool:
    """Delete one Issue and report whether it existed."""
    issue = await get_issue(session, issue_id)
    if issue is None:
        return False

    await session.delete(issue)
    await session.flush()
    await session.commit()
    return True
