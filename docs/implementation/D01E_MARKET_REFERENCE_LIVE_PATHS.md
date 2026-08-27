# D01-E MarketReference Live Paths

Date: 2026-08-27

## Scope

D01-E exposes the first public MarketReference market-data runtime paths on top of the neutral `MarketDataInstrument` foundation delivered by D01-A through D01-D.

Included:

- EODHD provider-mapping upsert for a `MarketReference`.
- Explicit EODHD mapping validation using an exact symbol/exchange match.
- Currency resolution from the exact EODHD Search result; no region/code inference.
- Historical EOD price import directly to the MARKET_REFERENCE `MarketDataInstrument` with `listing_id = NULL`.
- Reuse of the process-wide EODHD call budget, retry policy and rate limiter.
- Active `MarketReference` lifecycle checks before mapping, validation and import.

Not included:

- Public MarketReference FT-006 analysis routes.
- Top-down readiness cutover.
- Any removal or semantic change of the existing listing-based market-data API.
- Synthetic FT-001 Underlying/Listing creation for indexes or references.

## Public routes

- `PUT /api/v1/top-down-reference-data/market-references/{reference_id}/provider-mapping/eodhd`
- `POST /api/v1/top-down-reference-data/market-references/{reference_id}/provider-mapping/eodhd/validate`
- `POST /api/v1/top-down-reference-data/market-references/{reference_id}/daily-prices/import`

## Safety and compatibility

The existing Listing mapping/import contracts remain unchanged. Reference-owned mappings and prices use `market_data_instrument_id` and keep `listing_id` null. The database owner/workspace guards introduced in earlier D01 slices remain the final persistence boundary.

A mapping update returns it to `DISABLED` and clears prior validation. Import requires an ACTIVE mapping and re-resolves the exact provider search match so that the persisted currency is provider-backed rather than inferred.

D01-E requires no new Alembic revision because D01-B and D01-C already expanded the mapping and DailyPrice schemas for instrument-owned rows.
