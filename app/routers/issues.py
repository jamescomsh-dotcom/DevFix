"""HTTP routes for the single Issue resource."""

from fastapi import APIRouter, status

from app.dependencies import DatabaseSession
from app.models import Issue
from app.schemas.issue import IssueCreate, IssueRead
from app.services.issue_service import create_issue as create_issue_record


router = APIRouter(
    prefix="/api/v1/issues",
    tags=["issues"],
)


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
