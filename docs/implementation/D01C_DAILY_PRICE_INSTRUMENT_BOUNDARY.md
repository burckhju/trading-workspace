# D01-C DailyPrice → MarketDataInstrument boundary

## Scope

D01-C expands completed daily-price persistence from an FT-001 Listing-only key to the provider-neutral `MarketDataInstrument` identity introduced by D01-A and populated on provider mappings by D01-B.

This slice is deliberately additive. Existing listing-based import, API, provider-adapter, FT-006 analysis, and readiness contracts remain unchanged.

## Persistence contract

`daily_prices` gains nullable `market_data_instrument_id` with a RESTRICT foreign key to `market_data_instruments`. Existing `listing_id` remains available for compatibility and becomes nullable in storage so future MARKET_REFERENCE-owned daily prices can be represented without inventing an FT-001 Listing.

The expand-phase invariants are:

- at least one internal owner (`listing_id` or `market_data_instrument_id`) is required;
- existing `(listing_id, trading_date, price_type)` uniqueness remains;
- new `(market_data_instrument_id, trading_date, price_type)` uniqueness prevents duplicate prices for the neutral identity;
- PostgreSQL enforces workspace consistency between a daily price and its MarketDataInstrument;
- when both identifiers are present, the MarketDataInstrument must be a LISTING identity for exactly that listing;
- MarketDataInstrument deletion is RESTRICT while a price references it.

## Migration and backfill

Revision `20260826_0027` follows `20260826_0026`.

Before backfilling prices, the migration defensively creates a LISTING MarketDataInstrument for any listing that does not already have one. Existing listing-owned daily prices are then linked to the corresponding identity. This covers listings or prices created after the earlier migration by paths that did not yet dual-write the identity.

Downgrade preserves all listing-owned prices and D01-A identities. If instrument-only daily prices exist, downgrade refuses to proceed rather than silently deleting or fabricating a listing owner that revision `0026` cannot represent.

## Runtime compatibility

The immutable `DailyPrice` domain contract and the existing daily-price import remain listing-scoped in D01-C. Storage is prepared for instrument-only rows, but those rows are deliberately not exposed through the listing-scoped domain conversion until a later consumer slice defines the corresponding runtime contract.

When the selected D01-B provider mapping carries `market_data_instrument_id`, newly inserted DailyPrice rows dual-write both identifiers. Existing rows missing the neutral identity are repaired during a subsequent import update.

The repository adds instrument-aware `get`, range, and latest lookup contracts for later consumers while retaining all listing-based methods.

## Explicitly deferred

D01-C does not add MarketReference price-import endpoints, change provider request DTOs, migrate FT-006 MarketAnalysis, change readiness semantics, or remove listing-based DailyPrice access. Those consumer transitions belong to later D01 slices.
