"""Create the single issues business table.

Revision ID: 20260828_01
Revises:
Create Date: 2026-08-28

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260828_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the only DevFix business table."""
    op.create_table(
        "issues",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("ai_tool", sa.String(length=50), nullable=True),
        sa.Column("ai_prompt", sa.Text(), nullable=True),
        sa.Column("solution", sa.Text(), nullable=True),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "IN_PROGRESS",
                "RESOLVED",
                native_enum=False,
                create_constraint=False,
                length=20,
            ),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            nullable=False,
        ),
        sa.CheckConstraint(
            "CAST(status AS BINARY) "
            "IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_issues_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove only the issues business table."""
    op.drop_table("issues")
