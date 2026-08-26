# D01-B Provider Mapping → MarketDataInstrument Boundary

## Scope

D01-B is the expand-phase consumer migration immediately after D01-A. It moves only `ProviderInstrumentMapping` toward the provider-neutral `MarketDataInstrument` identity.

It does **not** migrate `DailyPrice`, `MarketAnalysis`, readiness, provider imports, or FT-006 behavior. Those remain later D01 slices.

## Persistence contract

`provider_instrument_mappings` gains nullable `market_data_instrument_id` referencing `market_data_instruments`.

The legacy `listing_id` remains supported and becomes nullable only so a later MarketReference mapping can be represented without inventing an FT-001 stock Listing. During the expand phase a stock mapping may carry both fields:

- `listing_id` keeps released stock paths compatible;
- `market_data_instrument_id` establishes the new neutral ownership boundary.

At least one internal owner is required. The existing provider+listing uniqueness remains, and provider+MarketDataInstrument uniqueness is added.

## Backfill and dual-write

Revision `20260826_0026` follows D01-A revision `20260826_0025`.

Before mapping rows are backfilled, the migration creates missing LISTING-owned `MarketDataInstrument` identities for Listings that may have been created after the D01-A migration. Existing identities are reused. Existing provider mappings are then linked to the matching LISTING instrument in the same workspace.

After migration, the production listing-mapping administration service uses the D01-A identity service in the same database session. New listing mappings therefore write both `listing_id` and `market_data_instrument_id`; updating an older listing mapping also fills a missing neutral identity. This prevents drift between migration time and later consumer cutover.

Identity is never derived from provider symbols, exchange codes, names, or ticker text.

## Workspace and owner consistency

PostgreSQL rejects a mapping whose `market_data_instrument_id` belongs to another workspace. If a row contains both `listing_id` and `market_data_instrument_id`, the instrument must be a LISTING identity owned by that exact Listing.

The new MarketDataInstrument foreign key uses restrictive delete semantics so mapping provenance is not silently removed when an identity is deleted.

## Application compatibility

The immutable provider-mapping domain model and persistence conversion can carry either a Listing owner or a MarketDataInstrument owner. The existing listing administration, venue reconciliation, and DailyPrice paths remain explicitly listing-scoped and refuse instrument-only rows instead of treating a MarketReference as a stock Listing.

The public mapping response can expose `market_data_instrument_id` and makes `listing_id` nullable for expand compatibility, while the existing mapping upsert remains listing-only. The repository adds `find_for_instrument(...)` as the handoff contract for the next D01 slice.

## Downgrade

Listing-owned mappings are preserved when downgrading to `20260826_0025`, and D01-A MarketDataInstrument identities are not removed. If instrument-only provider mappings exist, downgrade refuses to proceed because the legacy schema cannot represent them. This avoids silent data loss.

## Explicit non-goals

D01-B does not yet create or validate MarketReference provider mappings through public routes, does not import reference prices, and does not change readiness or analysis semantics.
