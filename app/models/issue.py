"""Single-table SQLAlchemy model for development issues."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Enum, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.enums import IssueStatus
from app.models.base import Base, utc_now


class Issue(Base):
    """A development problem, its solution, and AI collaboration notes."""

    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "CAST(status AS BINARY) "
            "IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_issues_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_tool: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(
            IssueStatus,
            native_enum=False,
            create_constraint=False,
            validate_strings=True,
            length=20,
        ),
        default=IssueStatus.OPEN,
        server_default=IssueStatus.OPEN.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6),    #秒后面的单位保留小数6位
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
