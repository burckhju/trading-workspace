# D01-A MarketDataInstrument Identity Foundation

## Scope

D01-A introduces a provider-neutral persistence identity for market-data and analysis addressing. It does not migrate ProviderInstrumentMapping, DailyPrice, MarketAnalysis, readiness, provider imports, or public APIs.

The supported owner contract is intentionally narrow:

- one `MarketDataInstrument` is owned by exactly one FT-001 `Listing`, or
- one `MarketDataInstrument` is owned by exactly one `MarketReference`.

`MarketDataInstrument` is not a tradable product, provider symbol, trading venue, FT-001 Underlying, or provider mapping.

## Persistence invariants

`market_data_instruments` contains `id`, `workspace_id`, `kind`, the two nullable owner foreign keys, and `created_at`.

There is deliberately no independent `active` flag. Listing lifecycle and MarketReference activity remain the existing sources of lifecycle truth; D01-A is an identity foundation only.

A check constraint couples `kind` to the exclusive owner foreign key. Unique constraints guarantee at most one identity per owner. Owner deletes are `RESTRICT` so the new identity foundation cannot silently erase future market-data provenance.

Workspace consistency is enforced twice:

1. the identity resolution service verifies that the requested owner belongs to the requested workspace;
2. PostgreSQL rejects inserts or owner/workspace updates whose owner belongs to another workspace.

## Migration and backfill

Revision `20260826_0025` follows `20260825_0024` and creates the identity table without changing existing Listing, MarketReference, provider mapping, price, or analysis rows.

Every existing Listing and MarketReference receives exactly one identity during upgrade. Backfilled `created_at` is copied from the owner because the identity represents that already-existing internal object rather than a new business lifecycle event. IDs are generated once with repository-compatible UUID values and are independent of names, symbols, providers, and provider mappings.

Downgrade drops only the D01-A trigger/function, index, and identity table. Existing owners and consumers remain untouched.

## D01-B handoff contract

`MarketDataInstrumentIdentityService` provides the internal contract required by the next slice:

- Listing + workspace -> exactly one MarketDataInstrument;
- MarketReference + workspace -> exactly one MarketDataInstrument;
- MarketDataInstrument ID + workspace -> its persisted owner type and owner ID.

The service can create a missing identity for a newly created owner after validating workspace ownership. Existing identities are returned unchanged, so provider or owner metadata changes do not replace the internal identity.

## Explicit non-goals

D01-A does not make MarketDataInstrument the source of truth for ProviderInstrumentMapping, DailyPrice, MarketAnalysis, FT-006 model provenance, or readiness. Those consumer changes require later explicit D01 slices.
