"""Opt-in configuration for a licensed, normalized Frankfurt quote snapshot."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class FrankfurtSourceMode(StrEnum):
    HTTPS_JSON = "https_json"
    LOCAL_FILE = "local_file"


class FrankfurtQuoteSettings(BaseModel):
    """No undocumented exchange endpoint or presumed market-data entitlement."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = False
    usage_approved: bool = False
    contract_verified: bool = False
    source_name: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,80}$")] | None = None
    source_mode: FrankfurtSourceMode = FrankfurtSourceMode.HTTPS_JSON
    snapshot_url: str | None = None
    allowed_host: str | None = None
    bearer_token: SecretStr | None = None
    local_file: str | None = None
    feed_delay_seconds: Annotated[int, Field(ge=0, le=900)] = 0
    max_quote_age_seconds: Annotated[int, Field(ge=1, le=900)] = 900
    timeout_seconds: Annotated[float, Field(gt=0, le=30)] = 10.0
    refresh_interval_seconds: Annotated[int, Field(ge=1, le=60)] = 15
    max_response_bytes: Annotated[int, Field(ge=1024, le=32_000_000)] = 8_000_000

    @field_validator("snapshot_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Frankfurt snapshot requires HTTPS without credentials/query/fragment")
        return value

    @field_validator("allowed_host")
    @classmethod
    def normalize_host(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None

    @field_validator("local_file")
    @classmethod
    def validate_file(cls, value: str | None) -> str | None:
        if value is not None and (not Path(value).is_absolute() or Path(value).suffix != ".json"):
            raise ValueError("Frankfurt local_file must be an absolute .json file path")
        return value

    @property
    def readiness_reason(self) -> str:
        if not self.enabled:
            return "FRANKFURT_DISABLED"
        if not self.usage_approved:
            return "FRANKFURT_USAGE_NOT_APPROVED"
        if not self.contract_verified:
            return "FRANKFURT_CONTRACT_NOT_VERIFIED"
        if not self.source_name:
            return "FRANKFURT_SOURCE_NAME_MISSING"
        if self.source_mode is FrankfurtSourceMode.LOCAL_FILE:
            return "CONFIGURED_NOT_PROBED" if self.local_file else "FRANKFURT_LOCAL_FILE_MISSING"
        if not self.snapshot_url:
            return "FRANKFURT_ENDPOINT_MISSING"
        if urlsplit(self.snapshot_url).hostname != self.allowed_host:
            return "FRANKFURT_HOST_NOT_APPROVED"
        return "CONFIGURED_NOT_PROBED"
