"""Environment-based application settings."""

import re
from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config.frankfurt import FrankfurtQuoteSettings


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class StuttgartDelayedSourceMode(StrEnum):
    """Supported transport sources for verified XSTU delayed payloads."""

    INDEX = "index"
    LOCAL_DIRECTORY = "local_directory"
    DIRECT_URL = "direct_url"


class VontobelMarketsSettings(BaseModel):
    """Transport settings for the official Vontobel Markets product payload."""

    enabled: bool = False
    base_url: str = "https://markets.vontobel.com"
    culture: str = "de-de"
    timeout_seconds: Annotated[float, Field(gt=0, le=60)] = 15.0

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.hostname != "markets.vontobel.com":
            raise ValueError("Vontobel Markets base_url must use the official HTTPS host")
        return normalized

    @field_validator("culture")
    @classmethod
    def validate_culture(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z]{2}-[a-z]{2}", normalized):
            raise ValueError("Vontobel Markets culture must use ll-cc format")
        return normalized


class EodhdSettings(BaseModel):
    """Validated transport settings for the optional EODHD provider."""

    enabled: bool = False
    base_url: str = "https://eodhd.com/api"
    api_key: SecretStr | None = None
    connect_timeout_seconds: Annotated[float, Field(gt=0, le=30)] = 5.0
    read_timeout_seconds: Annotated[float, Field(gt=0, le=60)] = 15.0
    write_timeout_seconds: Annotated[float, Field(gt=0, le=30)] = 5.0
    pool_timeout_seconds: Annotated[float, Field(gt=0, le=30)] = 5.0
    daily_call_limit: Annotated[int, Field(ge=1)] = 100_000
    daily_call_safety_reserve: Annotated[int, Field(ge=0)] = 1_000
    requests_per_minute: Annotated[int, Field(ge=1)] = 1_000
    historical_eod_call_cost: Annotated[int, Field(ge=1)] = 1
    historical_cache_ttl_seconds: Annotated[int, Field(ge=1)] = 86_400
    latest_cache_ttl_seconds: Annotated[int, Field(ge=1)] = 900
    retry_max_attempts: Annotated[int, Field(ge=1, le=10)] = 3
    retry_base_delay_seconds: Annotated[float, Field(ge=0, le=30)] = 0.5
    retry_max_retry_after_seconds: Annotated[float, Field(ge=0, le=300)] = 30.0
    retry_total_timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 45.0
    rate_limit_burst_capacity: Annotated[int, Field(ge=1)] = 10

    @field_validator("daily_call_safety_reserve")
    @classmethod
    def validate_daily_call_safety_reserve(cls, value: int, info: object) -> int:
        data = getattr(info, "data", {})
        limit = data.get("daily_call_limit", 100_000)
        if value >= limit:
            raise ValueError("daily_call_safety_reserve must be below daily_call_limit")
        return value

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("EODHD base_url must be an absolute HTTPS URL")
        return normalized

    @field_validator("api_key")
    @classmethod
    def normalize_api_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        secret = value.get_secret_value().strip()
        return SecretStr(secret) if secret else None


class StuttgartDelayedSettings(BaseModel):
    """Fail-closed configuration for the verified official XSTU delayed feed."""

    enabled: bool = False
    source_mode: StuttgartDelayedSourceMode = StuttgartDelayedSourceMode.INDEX
    index_url: str = (
        "https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/"
        "mifir-ii-delayed-data/xstu-pre-trade/"
    )
    local_directory: str | None = None
    local_file_pattern: str = "XSTU-pretrade-*.json.gz"
    direct_url: str | None = None
    schema_version: str | None = "xstu-pretrade-flat-2026-09-04"
    records_path: str | None = "$"
    isin_field: str | None = "Isin"
    mic_field: str | None = "VenueOfPublication"
    bid_field: str | None = "Bid"
    ask_field: str | None = "Ask"
    currency_field: str | None = "PriceCurrency"
    observed_at_field: str | None = "TransactionTime"
    timeout_seconds: Annotated[float, Field(gt=0, le=60)] = 15.0

    @field_validator("index_url")
    @classmethod
    def validate_index_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or parsed.hostname not in {
            "www.boerse-stuttgart.de",
            "boerse-stuttgart.de",
        }:
            raise ValueError("Stuttgart delayed index_url must use the official HTTPS host")
        return normalized

    @field_validator("direct_url")
    @classmethod
    def validate_direct_url(cls, value: str | None) -> str | None:
        from urllib.parse import urlparse

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Stuttgart delayed direct_url must be an absolute HTTPS URL")
        return normalized

    @field_validator("local_directory")
    @classmethod
    def normalize_local_directory(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @property
    def has_verified_schema(self) -> bool:
        """Only the complete verified flat XSTU mapping is activation-ready."""
        required = (
            self.schema_version,
            self.records_path,
            self.isin_field,
            self.mic_field,
            self.bid_field,
            self.ask_field,
            self.currency_field,
            self.observed_at_field,
        )
        return all(value is not None and value.strip() for value in required)

    @property
    def has_source_configuration(self) -> bool:
        """Return whether the selected transport mode has the required source configured."""
        if self.source_mode == StuttgartDelayedSourceMode.INDEX:
            return True
        if self.source_mode == StuttgartDelayedSourceMode.LOCAL_DIRECTORY:
            return self.local_directory is not None
        if self.source_mode == StuttgartDelayedSourceMode.DIRECT_URL:
            return self.direct_url is not None
        return False


class MarketDataSettings(BaseModel):
    """Settings for market-data infrastructure and providers."""

    eodhd: EodhdSettings = Field(default_factory=EodhdSettings)
    vontobel_markets: VontobelMarketsSettings = Field(default_factory=VontobelMarketsSettings)
    stuttgart_delayed: StuttgartDelayedSettings = Field(default_factory=StuttgartDelayedSettings)
    frankfurt: FrankfurtQuoteSettings = Field(default_factory=FrankfurtQuoteSettings)


class PositionMonitoringSettings(BaseModel):
    """Background scheduling and completed-price freshness settings."""

    enabled: bool = False
    interval_seconds: Annotated[float, Field(ge=30, le=86_400)] = 900.0
    max_completed_price_age_days: Annotated[int, Field(ge=0, le=30)] = 4
    delivery_recovery_timeout_seconds: Annotated[int, Field(ge=30, le=3600)] = 300


class TelegramSettings(BaseModel):
    """Outbound-only Telegram delivery configuration."""

    enabled: bool = False
    base_url: str = "https://api.telegram.org"
    bot_token: SecretStr | None = None
    chat_id: str | None = None
    timeout_seconds: Annotated[float, Field(gt=0, le=60)] = 10.0
    max_attempts: Annotated[int, Field(ge=1, le=10)] = 3

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        from urllib.parse import urlparse

        normalized = value.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Telegram base_url must be an absolute HTTPS URL")
        return normalized

    @field_validator("bot_token")
    @classmethod
    def normalize_bot_token(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        secret = value.get_secret_value().strip()
        return SecretStr(secret) if secret else None

    @field_validator("chat_id")
    @classmethod
    def normalize_chat_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class NotificationSettings(BaseModel):
    """Provider-neutral notification configuration."""

    telegram: TelegramSettings = Field(default_factory=TelegramSettings)


class Settings(BaseSettings):
    """Validated settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TRADING_WORKSPACE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    application_name: str = "Trading Workspace API"
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: Annotated[str, Field(pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")] = "INFO"
    documentation_enabled: bool = False
    database_url: str = "postgresql+asyncpg://localhost/trading_workspace"
    database_echo: bool = False
    database_pool_size: Annotated[int, Field(ge=1, le=50)] = 5
    database_max_overflow: Annotated[int, Field(ge=0, le=100)] = 10
    database_pool_recycle_seconds: Annotated[int, Field(ge=30)] = 1800
    market_data: MarketDataSettings = Field(default_factory=MarketDataSettings)
    position_monitoring: PositionMonitoringSettings = Field(
        default_factory=PositionMonitoringSettings
    )
    notification: NotificationSettings = Field(default_factory=NotificationSettings)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
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
