"""Reviewed setup suggestions, never a source for chart/assignment resolution.

Evidence snapshot 2026-10-04. Import remains an explicit administration action;
no prices, provider coverage, investor eligibility or licensed datasets are implied.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorProposal:
    code: str
    sector: str
    benchmark: str
    ticker: str
    isin: str
    source_url: str
    mic: str = "ARCX"
    currency: str = "USD"
    classification_system: str = "GICS"
    classification_version: str = "sectors-reviewed-2026-10-04"
    reviewed_on: str = "2026-10-04"
    taxonomy_source: str = "https://www.spglobal.com/spdji/en/landing/topic/gics/"
    venue_source: str = "https://www.iso20022.org/market-identifier-codes"
    provider_coverage: str = "NOT_VERIFIED"


def _proposal(code: str, sector: str, benchmark: str, ticker: str, isin: str) -> SectorProposal:
    slug = benchmark.lower().replace(" ", "-")
    url = f"https://www.ssga.com/us/en/intermediary/etfs/state-street-{slug}-select-sector-spdr-etf-{ticker.lower()}"
    return SectorProposal(code, sector, f"{benchmark} Select Sector Index", ticker, isin, url)


SECTOR_PROPOSALS = (
    _proposal("10", "Energy", "Energy", "XLE", "US81369Y5069"),
    _proposal("15", "Materials", "Materials", "XLB", "US81369Y1001"),
    _proposal("20", "Industrials", "Industrial", "XLI", "US81369Y7040"),
    _proposal("25", "Consumer Discretionary", "Consumer Discretionary", "XLY", "US81369Y4070"),
    _proposal("30", "Consumer Staples", "Consumer Staples", "XLP", "US81369Y3080"),
    _proposal("35", "Health Care", "Health Care", "XLV", "US81369Y2090"),
    _proposal("40", "Financials", "Financial", "XLF", "US81369Y6059"),
    _proposal("45", "Information Technology", "Technology", "XLK", "US81369Y8030"),
    _proposal("50", "Communication Services", "Communication Services", "XLC", "US81369Y8527"),
    _proposal("55", "Utilities", "Utilities", "XLU", "US81369Y8865"),
    _proposal("60", "Real Estate", "Real Estate", "XLRE", "US81369Y8600"),
)
