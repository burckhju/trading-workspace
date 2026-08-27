# D01-F — MarketReference analysis and readiness cutover

## Goal

Complete the direct MarketReference live chain without requiring a synthetic FT-001 Underlying or Listing.

## Public analysis path

D01-F exposes FT-006 for semantic MarketReferences:

- `POST /api/v1/top-down-reference-data/market-references/{reference_id}/analyses`
- `POST /api/v1/top-down-reference-data/market-reference-analyses/{analysis_id}/runs`

The existing `MarketReferenceAnalysisService` remains the calculation boundary. It resolves the MarketReference-owned `MarketDataInstrument` and reads only instrument-owned DailyPrice rows.

## Readiness cutover

Top-down reference readiness now evaluates:

`MarketReference -> MarketDataInstrument -> EODHD ProviderInstrumentMapping -> DailyPrice -> completed MarketAnalysis`

An active MarketReference no longer needs an active `MarketReferenceListingAssignment` to become ready. The legacy `listing_id` field remains in the readiness response when an assignment exists, but it is informational and does not contribute a blocker.

Readiness blockers are now based on the direct chain, including:

- `MARKET_REFERENCE_INACTIVE`
- `NO_MARKET_DATA_INSTRUMENT`
- `NO_EODHD_PROVIDER_MAPPING`
- `EODHD_PROVIDER_MAPPING_NOT_ACTIVE`
- `INSUFFICIENT_DAILY_PRICE_HISTORY`
- `NO_COMPLETED_MARKET_ANALYSIS`

## Compatibility

- Existing listing-based market-data and FT-006 paths are unchanged.
- Existing top-down administration endpoints are unchanged.
- Existing readiness response fields are retained.
- No schema change or Alembic revision is required.
- No synthetic Underlying or Listing is created for a MarketReference.
