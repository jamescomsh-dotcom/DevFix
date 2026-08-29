"""Pure metadata tests for the single-table Issue model."""

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum as SqlAlchemyEnum,
    String,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.enums import IssueStatus
from app.models import Base, Issue
from app.models.base import utc_now


EXPECTED_COLUMNS = {
    "id",
    "title",
    "description",
    "error_message",
    "ai_tool",
    "ai_prompt",
    "solution",
    "verification_notes",
    "status",
    "created_at",
    "updated_at",
}


def test_issue_status_has_only_confirmed_values() -> None:
    assert [status.value for status in IssueStatus] == [
        "OPEN",
        "IN_PROGRESS",
        "RESOLVED",
    ]


def test_issue_is_the_only_business_table() -> None:
    assert set(Base.metadata.tables) == {"issues"}
    assert Issue.__table__ is Base.metadata.tables["issues"]
    assert set(Issue.__table__.columns.keys()) == EXPECTED_COLUMNS


def test_issue_column_types_and_nullability_match_design() -> None:
    table = Issue.__table__

    assert isinstance(table.c.id.type, BigInteger)
    assert table.c.id.primary_key is True
    assert table.c.id.autoincrement is True
    assert table.c.id.nullable is False

    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 200
    assert table.c.title.nullable is False
    assert table.c.title.unique is not True

    assert isinstance(table.c.description.type, Text)
    assert table.c.description.nullable is False

    for field_name in (
        "error_message",
        "ai_prompt",
        "solution",
        "verification_notes",
    ):
        column = table.c[field_name]
        assert isinstance(column.type, Text)
        assert column.nullable is True

    assert isinstance(table.c.ai_tool.type, String)
    assert table.c.ai_tool.type.length == 50
    assert table.c.ai_tool.nullable is True


def test_issue_status_uses_validated_non_native_enum() -> None:
    column = Issue.__table__.c.status

    assert isinstance(column.type, SqlAlchemyEnum)
    assert column.type.enum_class is IssueStatus
    assert column.type.enums == ["OPEN", "IN_PROGRESS", "RESOLVED"]
    assert column.type.native_enum is False
    assert column.type.validate_strings is True
    assert column.type.create_constraint is False
    assert column.type.length == 20
    assert column.nullable is False
    assert column.default is not None
    assert column.default.arg is IssueStatus.OPEN
    assert column.server_default is not None
    assert str(column.server_default.arg) == "OPEN"


def test_issue_mysql_ddl_has_strict_status_constraint() -> None:
    table = Issue.__table__
    status_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]

    assert len(status_constraints) == 1
    assert status_constraints[0].name == "ck_issues_status"

    ddl = str(CreateTable(table).compile(dialect=mysql.dialect()))
    assert "status VARCHAR(20) NOT NULL DEFAULT 'OPEN'" in ddl
    assert (
        "CONSTRAINT ck_issues_status "
        "CHECK (CAST(status AS BINARY) IN ('OPEN', 'IN_PROGRESS', 'RESOLVED'))"
        in ddl
    )
    assert ddl.count("DATETIME(6)") == 2


def test_issue_timestamps_store_utc_with_microsecond_precision() -> None:
    table = Issue.__table__
    created_at = table.c.created_at
    updated_at = table.c.updated_at

    for column in (created_at, updated_at):
        assert isinstance(column.type, mysql.DATETIME)
        assert column.type.fsp == 6
        assert column.nullable is False
        assert column.default is not None
        assert callable(column.default.arg)
        generated_time = column.default.arg(None)
        assert generated_time.tzinfo is None
        assert abs((datetime.now(UTC).replace(tzinfo=None) - generated_time).total_seconds()) < 1

    assert updated_at.onupdate is not None
    assert callable(updated_at.onupdate.arg)
    updated_time = updated_at.onupdate.arg(None)
    assert updated_time.tzinfo is None
    assert abs((datetime.now(UTC).replace(tzinfo=None) - updated_time).total_seconds()) < 1

    current_time = utc_now()
    expected_utc = datetime.now(UTC).replace(tzinfo=None)
    assert current_time.tzinfo is None
    assert abs((expected_utc - current_time).total_seconds()) < 1


def test_issue_has_no_relationships_foreign_keys_or_unique_constraints() -> None:
    table = Issue.__table__

    assert list(inspect(Issue).relationships) == []
    assert set(table.foreign_keys) == set()
    assert not any(
        isinstance(constraint, UniqueConstraint)
        for constraint in table.constraints
    )
