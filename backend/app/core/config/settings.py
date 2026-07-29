"""Environment-based application settings."""

from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRADING_WORKSPACE_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    application_name: str = "Trading Workspace API"
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: Annotated[
        str,
        Field(pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    ] = "INFO"
    documentation_enabled: bool = False
    database_url: str = "postgresql+asyncpg://localhost/trading_workspace"
    database_echo: bool = False
    database_pool_size: Annotated[int, Field(ge=1, le=50)] = 5
    database_max_overflow: Annotated[int, Field(ge=0, le=100)] = 10
    database_pool_recycle_seconds: Annotated[int, Field(ge=30)] = 1800

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Require the documented asynchronous PostgreSQL driver."""

        from sqlalchemy.engine import make_url

        url = make_url(value)
        if url.drivername != "postgresql+asyncpg":
            raise ValueError("database_url must use postgresql+asyncpg")
        if not url.database:
            raise ValueError("database_url must include a database name")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""

    return Settings()
