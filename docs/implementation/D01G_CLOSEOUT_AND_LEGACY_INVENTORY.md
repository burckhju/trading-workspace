# D01-G — Closeout, workflow qualification, and legacy inventory

## Purpose

D01-G closes the D01 MarketReference/MarketDataInstrument migration without adding a new product capability. It verifies the released A–F chain as one user-facing workflow, records the remaining Listing references, and separates intentional compatibility from future cleanup candidates.

## Qualified target chain

The MarketReference live path is now:

`MarketReference -> MarketDataInstrument -> EODHD ProviderInstrumentMapping -> DailyPrice -> FT-006 MarketAnalysis -> Readiness`

A MarketReference does not require an FT-001 Underlying or Listing to complete this chain.

The D01-G HTTP contract test exercises, in order:

1. initial readiness (not ready, no Listing),
2. EODHD mapping upsert,
3. explicit mapping validation,
4. historical daily-price import,
5. MarketReference-owned FT-006 analysis creation,
6. FT-006 analysis run,
7. final readiness (`ready=true`) with `listing_id=null`.

Provider transport is deterministic in this qualification test; CI does not call the live EODHD network. Provider-specific search/currency/price behavior remains covered by the D01-E service boundary and the regular backend suite.

## Readiness contract after D01-F

Readiness is owned by the MarketDataInstrument chain. The relevant blockers are:

- `INACTIVE_MARKET_REFERENCE`
- `NO_MARKET_DATA_INSTRUMENT`
- `NO_ACTIVE_PROVIDER_MAPPING`
- `INSUFFICIENT_DAILY_PRICE_HISTORY`
- `NO_COMPLETED_ANALYSIS`

`NO_ACTIVE_LISTING_ASSIGNMENT` is no longer a MarketReference readiness blocker.

## Legacy inventory

### Keep: intentional domain behavior

- Listing-owned market-data mappings, prices, and FT-006 analyses remain valid for tradable instruments.
- Existing Listing-based APIs remain supported; D01 did not replace FT-001 Listing ownership for securities.
- `DirectMarketReferenceListing` remains a valid optional business association where a reference intentionally points to a tradable proxy/listing.

These are not cleanup defects.

### Keep for compatibility, but do not use as a readiness dependency

- The readiness response still exposes nullable `listing_id` as informational compatibility data.
- Top-down administration still exposes MarketReference listing-assignment operations.

Neither may be required for MarketReference mapping, price import, analysis, or readiness.

### Future cleanup candidates

A later contract-cleanup slice may evaluate whether consumers still need the informational `listing_id` in the readiness response and whether legacy UI/client wording implies that a listing assignment is mandatory. Removal should be evidence-driven and separately versioned because clients may depend on these fields/routes.

### Explicitly out of scope for cleanup

- Do not make `DailyPrice.listing_id` or `MarketAnalysis.listing_id` globally disappear merely because MarketReference-owned records can be instrument-only. Listing ownership remains correct for tradable securities.
- Do not collapse MarketReference lifecycle into `MarketDataInstrument`; lifecycle remains on the owning semantic object.
- Do not create synthetic Underlyings/Listings for indices or other semantic references.

## D01 closeout result

D01-A through D01-F established the neutral MarketDataInstrument boundary and migrated MarketReference mapping, prices, analysis, and readiness onto it. D01-G adds the cross-route qualification and aligns stale test expectations with the final blocker vocabulary.

After D01-G passes the standard backend, frontend, and E2E gates, D01 can be treated as closed. The next architectural work should be a separately scoped contract/UI cleanup only if concrete consumers still expose legacy Listing assumptions; otherwise development can proceed to the next product feature on the stable MDI boundary.
