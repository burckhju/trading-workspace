"""Provider-specific hints for approved top-down market references.

This module deliberately lives below the provider boundary.  Domain and candidate
logic only know semantic market-reference codes; provider symbols are merely
administrative suggestions and still require the existing mapping validation flow.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EodhdReferenceSuggestion:
    reference_code: str
    provider_symbol: str | None
    provider_exchange_code: str | None
    verification_status: str
    verification_source: str
    note: str


TOP_DOWN_V1_EODHD_SUGGESTIONS: tuple[EodhdReferenceSuggestion, ...] = (
    EodhdReferenceSuggestion(
        reference_code="DAX",
        provider_symbol="GDAXI",
        provider_exchange_code="INDX",
        verification_status="DOCUMENTED",
        verification_source="EODHD available-index list",
        note="DAX index is publicly listed by EODHD as GDAXI.INDX; validate mapping before activation.",
    ),
    EodhdReferenceSuggestion(
        reference_code="SP500",
        provider_symbol="GSPC",
        provider_exchange_code="INDX",
        verification_status="DOCUMENTED",
        verification_source="EODHD Fundamentals / index documentation",
        note="S&P 500 is publicly documented by EODHD as GSPC.INDX; validate mapping before activation.",
    ),
    EodhdReferenceSuggestion(
        reference_code="NASDAQ100",
        provider_symbol=None,
        provider_exchange_code=None,
        verification_status="REQUIRES_PROVIDER_VALIDATION",
        verification_source="No unambiguous EODHD index ticker established by project verification",
        note=(
            "Do not substitute a Nasdaq-100 ETF or guess an INDX ticker. Resolve through the EODHD "
            "Search API and activate only after the existing mapping validation succeeds."
        ),
    ),
)
