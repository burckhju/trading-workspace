# D01-D MarketAnalysis → MarketDataInstrument boundary

## Scope

D01-D expands FT-006 MarketAnalysis persistence from an FT-001 Listing-only owner to the provider-neutral `MarketDataInstrument` identity established by D01-A and carried through mappings/prices by D01-B/C.

The released listing-based FT-006 API and overview remain unchanged in this slice. D01-D adds the persistence/runtime foundation required for semantic MarketReference analyses without inventing an FT-001 Underlying or Listing.

## Persistence contract

`market_analyses` gains nullable `market_data_instrument_id` with a RESTRICT foreign key to `market_data_instruments`. Existing `listing_id` and `underlying_id` become nullable in storage only so a future MarketReference-owned analysis can be represented as `market_data_instrument_id != NULL`, `listing_id = NULL`, `underlying_id = NULL`.

The expand-phase invariants are:

- listing-owned analyses retain both `underlying_id` and `listing_id`;
- instrument-only analyses must have neither legacy owner field;
- PostgreSQL enforces MarketDataInstrument workspace consistency;
- when a listing and instrument are both present, the instrument must be the LISTING identity for exactly that listing;
- instrument-only analyses require a MARKET_REFERENCE identity;
- MarketDataInstrument deletion is RESTRICT while an analysis references it.

## Migration and backfill

Revision `20260827_0028` follows `20260826_0027`.

Before backfilling analyses, the migration defensively creates a LISTING MarketDataInstrument for any listing that does not already have one. Existing listing-owned analyses are then linked to that neutral identity.

Downgrade preserves listing-owned analyses and D01-A identities. If instrument-only analyses exist, downgrade refuses to proceed rather than deleting data or fabricating an FT-001 owner that revision `0027` cannot represent.

## Runtime compatibility

The existing `MarketAnalysisService` stays listing-scoped. A model-level insert hook dual-writes the LISTING MarketDataInstrument for new legacy analyses, including the defensive missing-identity case, while leaving the released service/API contract untouched.

`MarketReferenceAnalysisService` is an internal D01-D service. It resolves an active MarketReference to its MARKET_REFERENCE MarketDataInstrument, creates an analysis without synthetic FT-001 owners, reads instrument-owned DailyPrice rows, and reuses the released FT-006 calculator, lifecycle, snapshot and governed-model provenance behavior.

## Explicitly deferred

D01-D does not add public MarketReference analysis routes, reference provider-mapping administration, reference price-import endpoints, top-down readiness changes, or remove listing-based FT-006 access. Those application-surface transitions belong to the next D01 slice.
