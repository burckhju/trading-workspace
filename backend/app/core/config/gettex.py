"""Fail-closed configuration for the official gettex delayed pre-trade feed."""

from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class GettexDelayedSettings(BaseModel):
    """Configuration for the official MUND/MUNC delayed pre-trade files."""

    enabled: bool = False
    private_use_confirmed: bool = False
    base_url: str = "https://erdk.bayerische-boerse.de:8000/delayed-data/MUNC-MUND/pretrade"
    timeout_seconds: Annotated[float, Field(gt=0, le=600)] = 180.0
    max_download_bytes: Annotated[int, Field(ge=1, le=2_147_483_648)] = 1_073_741_824
    fallback_windows: Annotated[int, Field(ge=1, le=16)] = 8
    unavailable_retry_seconds: Annotated[int, Field(ge=1, le=900)] = 60
    feed_delay_seconds: Annotated[int, Field(ge=0, le=3600)] = 900

    @model_validator(mode="after")
    def validate_activation(self) -> "GettexDelayedSettings":
        """Require an explicit operator confirmation before enabling the private-use feed."""
        parsed = urlparse(self.base_url.rstrip("/"))
        if (
            parsed.scheme != "https"
            or parsed.hostname != "erdk.bayerische-boerse.de"
            or parsed.port != 8000
            or parsed.path.rstrip("/") != "/delayed-data/MUNC-MUND/pretrade"
        ):
            raise ValueError("gettex base_url must use the verified official HTTPS endpoint")
        if self.enabled and not self.private_use_confirmed:
            raise ValueError(
                "gettex delayed data may only be enabled after confirming eligible private use"
            )
        return self
