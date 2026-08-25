# D-01 Generic Market-Data Instrument — Implementation Status

Date: 2026-08-25
Branch: `feat/d01-generic-market-data-instrument`
Base: `main@0e2bec6153be7c1d3ac2d18ec371beef973719b3`

## Implemented

- ADR-S9-001 defines `MarketDataInstrument` as the neutral pricing/analysis identity.
- Migration `20260825_0022` creates and backfills LISTING and MARKET_REFERENCE identities.
- Migration `20260825_0023` expands provider mappings, daily prices and market analyses with `market_data_instrument_id` while retaining released stock ownership during cutover.
- Existing listing-based repositories resolve/backfill neutral identities for stock operations.
- Top-down readiness resolves MARKET_REFERENCE instruments directly and no longer requires `MarketReferenceListingAssignment`.
- Reference-specific EODHD mapping administration writes `ProviderInstrumentMappingModel` with `listing_id=NULL` and `market_data_instrument_id=<reference instrument>`.
- EODHD validation requires an exact provider symbol/exchange match and an explicit provider currency.
- Reference DailyPrice import persists EOD history with `listing_id=NULL` and the reference instrument identity.
- FT-006 reference analysis creates analyses with `underlying_id=NULL`, `listing_id=NULL`, and a MARKET_REFERENCE instrument, then runs the released calculator/lifecycle from instrument-owned DailyPrice rows.
- HTTP routes expose mapping upsert/validation, price import, analysis create/run and instrument-aware readiness.
- Stock and reference EODHD paths share the same process-wide `DailyCallBudget`, `RetryPolicy`, and `TokenBucketRateLimiter`; retry and throttling behavior is therefore no longer split by semantic owner.
- Regression tests assert FT-001 remains STOCK-only and reference-owned consumer schemas/routes are present.

## Safety boundaries retained

- No synthetic stock Underlying or Listing is created for an index.
- Existing historical migrations are unchanged.
- FT-001 STOCK semantics remain unchanged.
- FT-012 Underlying references remain unchanged.
- Existing listing-based stock writes remain valid during the expand phase.

## Validation still required

Executable validation is not yet available in this session. The user's local shell did not expose the `alembic` executable, and the isolated execution container cannot resolve github.com to clone the branch. Before the PR leaves draft, run at minimum:

```bash
cd backend
python -m alembic heads
python -m alembic upgrade head
pytest ../tests/unit/backend/features/market_data/test_instrument_identity_model.py \
       ../tests/unit/backend/features/market_data/test_reference_market_data_service.py \
       ../tests/unit/backend/features/market/test_top_down_reference_market_data_routes.py
ruff check app ../tests/unit/backend/features/market_data ../tests/unit/backend/features/market
mypy app
```

Then execute a database-backed DAX/SP500/NASDAQ100 smoke path:

1. bootstrap top-down references;
2. create and validate the EODHD reference mapping;
3. import at least the FT-006 minimum price history;
4. create and run a reference analysis;
5. confirm `/api/v1/top-down-reference-data/readiness` reports no blockers;
6. verify no Underlying/Listing was created for the reference.

## Remaining transition note

Provider resilience is now shared with the released EODHD path. The remaining merge gate is executable qualification: migrations, tests, static checks and database/live smoke evidence. A later contract migration may tighten or remove legacy listing ownership only after all writers/readers have been validated on the neutral identity.
