"""Database configuration validation tests."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_database_url_is_optional_for_process_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+asyncmy://other:password@127.0.0.1:3306/other",
    )

    settings = Settings(_env_file=None, database_url=None)

    assert settings.database_url is None


def test_database_url_accepts_asyncmy_and_hides_password() -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "mysql+asyncmy://devfix:super-secret@127.0.0.1:3306/devfix"
        ),
    )

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value().startswith("mysql+asyncmy://")
    assert "super-secret" not in repr(settings)


@pytest.mark.parametrize(
    "database_url",
    [
        "mysql+pymysql://devfix:password@127.0.0.1:3306/devfix",
        "mysql+asyncmy://devfix:password@127.0.0.1:3306",
        "not-a-database-url",
    ],
)
def test_database_url_rejects_unsafe_or_incomplete_values(
    database_url: str,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=database_url)


def test_database_url_validation_error_hides_original_value() -> None:
    database_url = (
        "mysql+pymysql://devfix:should-never-leak@127.0.0.1:3306/devfix"
    )

    with pytest.raises(ValidationError) as captured_error:
        Settings(_env_file=None, database_url=database_url)

    error_text = str(captured_error.value)
    assert "should-never-leak" not in error_text
    assert "input_value" not in error_text
