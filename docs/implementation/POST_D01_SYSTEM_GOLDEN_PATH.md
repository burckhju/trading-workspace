# Post-D01 System Golden Path and Architecture Stabilization

## Purpose

This stabilization slice follows the completed D01 MarketReference/MarketDataInstrument migration. It does not add a new product capability, continue D01 with another lettered slice, remove Listing-based security contracts, or introduce runtime model activation.

The goal is to qualify the first downstream system seam after the released D01 boundary and make the remaining cross-feature gaps explicit before new product expansion.

## Released D01 boundary

D01-G already qualifies the public MarketReference chain:

`MarketReference -> MarketDataInstrument -> EODHD ProviderInstrumentMapping -> DailyPrice -> FT-006 MarketAnalysis -> Readiness`

A MarketReference reaches this boundary without an FT-001 Underlying or Listing. `listing_id = null` is therefore an intentional released state for semantic market references.

## Added post-D01 qualification

The integration test `tests/integration/backend/test_post_d01_system_golden_path.py` exercises the real released analysis and candidate domain calculators across the next seam:

`FT-006 analysis output -> Market Context -> Relative Strength -> TOP_DOWN_CANDIDATE qualification`

The market leg is represented explicitly by a MarketReference-owned MarketDataInstrument with no Listing. The test keeps sector and underlying calculations separate and verifies that the downstream top-down decision path consumes analysis outputs rather than requiring a market Listing identity.

The deterministic fixture proves:

- the market reference remains listing-free at the downstream seam;
- FT-006 trend classifications can drive Market Context;
- sector and underlying Relative Strength can be computed against that market analysis series;
- Candidate Qualification can reach `QUALIFIED`;
- the persisted/runtime candidate identity remains `TOP_DOWN_CANDIDATE / 1.0.0` at this boundary.

This test intentionally reuses released domain behavior and does not fake a new listing for the market reference.

## Composition of the current golden path

The repository now has two adjacent deterministic qualification segments:

1. D01-G public HTTP contract:
   `MarketReference -> MDI -> Mapping -> DailyPrice -> FT-006 -> Readiness`
2. Post-D01 downstream integration contract:
   `FT-006 output -> Market Context -> Relative Strength -> Candidate Qualification`

Together they close the highest-risk seam introduced by D01: a listing-free MarketReference can supply the market leg of the released top-down candidate workflow.

This is deliberately not described as one monolithic end-to-end public API test. The current repository exposes these capabilities through different service/domain boundaries, and this slice avoids inventing orchestration that does not yet exist.

## Remaining system gaps

The following capabilities are released independently but are not yet qualified as one continuous public workflow starting from the post-D01 MarketReference path:

- Candidate Qualification -> TradePlan
- TradePlan -> Product Selection
- Product Selection -> Trade / Position
- Trade -> Exit / Post Trade
- Post Trade -> Learning
- Learning -> Controlled Model Governance

These are integration-confidence gaps, not evidence that the individual features are defective.

A later slice should extend the golden path only when released consumer contracts provide a natural seam. It must not create synthetic domain objects merely to make a diagram continuous.

## Model governance boundary

This slice does not change FT-013 or FT-006 governed provenance.

`APPROVED` remains distinct from runtime assignment and activation. No dynamic rule loading, current-version pointer, automatic switching, automatic approval, or automatic trading decision is introduced here.

The candidate path continues to expose its released runtime identity. Extending governed ModelVersion provenance to `TOP_DOWN_CANDIDATE` or other consumers requires a separate consumer/provenance review that proves the governed definition represents the rule set actually executed.

## D01 legacy boundary

No D01 cleanup is included.

In particular:

- Listing-owned mappings, prices, and analyses remain valid for tradable securities;
- `DailyPrice.listing_id` and `MarketAnalysis.listing_id` are not removed globally;
- informational compatibility fields are not removed without consumer evidence;
- MarketReference lifecycle is not moved onto MarketDataInstrument.

## Provider and CI boundary

The new downstream test is deterministic and performs no live EODHD network calls. D01-G remains the public contract qualification for the provider-facing reference workflow with provider behavior faked at the service boundary.

A live-provider smoke test, if added later, must remain optional and separate from mandatory CI.

## Definition of Done

This stabilization slice is complete when:

- the post-D01 downstream integration test is part of the regular backend suite;
- Ruff and Black accept the new test;
- the full backend suite remains above the 85% coverage gate;
- frontend and Playwright gates remain unchanged unless affected by discovered regressions;
- all relevant final gates qualify the same final commit;
- no unrelated cleanup, model activation, or new product feature is mixed into the slice.

## Next decision after this slice

After same-head qualification, the next architectural review should compare:

1. governed ModelVersion provenance for additional real runtime consumers;
2. runtime assignment / controlled activation as a separately specified architecture slice;
3. evidence-driven D01 contract/UI cleanup;
4. the next product capability selected from the actual repository backlog and user value.

The golden path should be extended again only where it closes a concrete released integration seam.
