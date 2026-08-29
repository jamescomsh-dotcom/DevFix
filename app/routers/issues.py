"""HTTP routes for the single Issue resource."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DatabaseSession
from app.models import Issue
from app.schemas.issue import IssueCreate, IssueRead
from app.services.issue_service import create_issue as create_issue_record
from app.services.issue_service import get_issue as get_issue_record
from app.services.issue_service import list_issues as list_issue_records


router = APIRouter(
    prefix="/api/v1/issues",
    tags=["issues"],
)


@router.get(
    "",
    response_model=list[IssueRead],
    summary="查询全部开发问题记录",
)
async def list_issues(session: DatabaseSession) -> list[Issue]:
    """Return all development issues in a stable newest-first order."""
    return await list_issue_records(session)


@router.get(
    "/{issue_id}",
    response_model=IssueRead,
    responses={404: {"description": "Issue 不存在"}},
    summary="查询一条开发问题记录",
)
async def get_issue(
    issue_id: int,
    session: DatabaseSession,
) -> Issue:
    """Return one development issue or translate a missing row to 404."""
    issue = await get_issue_record(session, issue_id)
    if issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue 不存在。",
        )
    return issue


@router.post(
    "",
    response_model=IssueRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建开发问题记录",
)
async def create_issue(
    issue_data: IssueCreate,
    session: DatabaseSession,
) -> Issue:
    """Validate, persist, and return one development issue."""
    return await create_issue_record(session, issue_data)
