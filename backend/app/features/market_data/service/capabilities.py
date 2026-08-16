"""Explicit provider capability resolution for cross-feature consumers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider


class ProviderCapabilityStatus(StrEnum):
    VERIFIED_SUPPORTED = "VERIFIED_SUPPORTED"
    VERIFIED_UNSUPPORTED = "VERIFIED_UNSUPPORTED"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class ProviderCapabilityResolution:
    provider: MarketDataProvider
    capability: MarketDataCapability
    status: ProviderCapabilityStatus
    reason: str

    @property
    def usable(self) -> bool:
        return self.status is ProviderCapabilityStatus.VERIFIED_SUPPORTED


def resolve_provider_capability(
    provider: MarketDataProvider,
    capability: MarketDataCapability,
) -> ProviderCapabilityResolution:
    """Return the repository-approved capability state, never an inferred provider promise."""
    if (
        provider is MarketDataProvider.EODHD
        and capability is MarketDataCapability.WARRANT_LISTING_QUOTE
    ):
        return ProviderCapabilityResolution(
            provider=provider,
            capability=capability,
            status=ProviderCapabilityStatus.UNVERIFIED,
            reason=(
                "EODHD bid/ask coverage for the FT-004 WarrantListing universe is not "
                "verified; documented real-time quote paths must not be assumed to cover warrants"
            ),
        )
    return ProviderCapabilityResolution(
        provider=provider,
        capability=capability,
        status=ProviderCapabilityStatus.UNVERIFIED,
        reason="provider capability has no explicit repository verification",
    )
