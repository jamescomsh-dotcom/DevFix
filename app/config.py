"""Load and validate DevFix configuration from environment variables."""
"""获取连接数据库的URL配置文件"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    """DevFix settings without an unsafe default database connection."""

    database_url: SecretStr | None = Field(
        default=None,
        validation_alias="DATABASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(
        cls,
        database_url: SecretStr | None,
    ) -> SecretStr | None:
        """Require the asynchronous MySQL driver and an explicit database."""
        if database_url is None:
            return None

        try:
            parsed_url = make_url(database_url.get_secret_value())
        except ArgumentError as exc:
            raise ValueError("DATABASE_URL 不是有效的 SQLAlchemy URL。") from exc

        if parsed_url.drivername != "mysql+asyncmy":
            raise ValueError("DATABASE_URL 必须使用 mysql+asyncmy 驱动。")
        if not parsed_url.username or not parsed_url.host:
            raise ValueError("DATABASE_URL 必须包含数据库用户名和主机。")
        if not parsed_url.database:
            raise ValueError("DATABASE_URL 必须指定数据库名称。")
        return database_url


@lru_cache
def get_settings() -> Settings:
    """Load settings once for the running application process."""
    return Settings()
