"""Static Alembic tests that never connect to a database."""

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.models import Issue


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"
EXPECTED_REVISION = "20260828_01"
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


def get_alembic_scripts() -> ScriptDirectory:
    config = Config(str(ALEMBIC_CONFIG_PATH))
    return ScriptDirectory.from_config(config)


def render_revision_operation(operation_name: str) -> str:
    revision = get_alembic_scripts().get_revision(EXPECTED_REVISION)
    output = StringIO()
    context = MigrationContext.configure(
        dialect=mysql.dialect(),
        opts={"as_sql": True, "output_buffer": output},
    )
    operations = Operations(context)

    with patch.object(revision.module, "op", operations):
        getattr(revision.module, operation_name)()

    return output.getvalue()


def normalize_sql(statement: str) -> str:
    return " ".join(statement.strip().removesuffix(";").split())


def test_alembic_has_one_initial_revision() -> None:
    assert ALEMBIC_CONFIG_PATH.is_file()
    scripts = get_alembic_scripts()

    assert scripts.get_heads() == [EXPECTED_REVISION]
    revision = scripts.get_revision(EXPECTED_REVISION)
    assert revision.down_revision is None
    assert revision.is_base is True
    assert revision.is_head is True
    assert [item.revision for item in scripts.walk_revisions()] == [
        EXPECTED_REVISION
    ]


def test_alembic_configuration_uses_model_metadata_without_saved_url() -> None:
    ini_source = ALEMBIC_CONFIG_PATH.read_text(encoding="utf-8")
    env_source = (PROJECT_ROOT / "alembic" / "env.py").read_text(
        encoding="utf-8"
    )

    assert "mysql+asyncmy://" not in ini_source
    assert "sqlalchemy.url" not in ini_source
    assert "target_metadata = Base.metadata" in env_source
    assert "get_settings()" in env_source
    assert "get_secret_value()" in env_source
    assert "make_url(" in env_source
    assert "create_async_engine(" in env_source
    assert "config.set_main_option" not in env_source
    assert "async_engine_from_config" not in env_source


def test_initial_revision_compiles_expected_mysql_sql() -> None:
    upgrade_sql = render_revision_operation("upgrade")

    assert upgrade_sql.count("CREATE TABLE issues") == 1
    assert "CREATE TABLE projects" not in upgrade_sql
    assert "CREATE TABLE solution_attempts" not in upgrade_sql
    assert "CREATE TABLE alembic_version" not in upgrade_sql
    for column_name in EXPECTED_COLUMNS:
        assert column_name in upgrade_sql
    assert "status VARCHAR(20) NOT NULL DEFAULT 'OPEN'" in upgrade_sql
    assert "created_at DATETIME(6) NOT NULL" in upgrade_sql
    assert "updated_at DATETIME(6) NOT NULL" in upgrade_sql
    assert (
        "CONSTRAINT ck_issues_status "
        "CHECK (CAST(status AS BINARY) IN ('OPEN', 'IN_PROGRESS', 'RESOLVED'))"
        in upgrade_sql
    )
    model_sql = str(
        CreateTable(Issue.__table__).compile(dialect=mysql.dialect())
    )
    assert normalize_sql(upgrade_sql) == normalize_sql(model_sql)

    downgrade_sql = render_revision_operation("downgrade")
    assert downgrade_sql.strip() == "DROP TABLE issues;"
