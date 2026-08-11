# ADR-S5-007 – Semantic Top-down Source Resolution

## Status
Accepted for Sprint 5 V1.

## Context
Candidate evaluations must not trust client-supplied market, sector or underlying classifications or arbitrary analysis identifiers. The approved top-down process is Market → Sector → Underlying → Candidate and every evaluation must be reproducible from persisted, versioned analyses.

Sprint 4 MarketAnalysis is listing based. Sprint 5 therefore needs a provider-neutral bridge from semantic references (for example a broad-market benchmark or sector reference) to analyzable listings without moving provider symbols into domain logic.

## Decision
1. Underlyings receive historized `UnderlyingBenchmarkAssignment` records. V1 resolves exactly one active `BROAD_MARKET` assignment at the evaluation date.
2. Underlyings receive the existing historized sector assignment. The sector resolves through the existing `SectorReferenceAssignment`.
3. Every `MarketReference` used for analysis is bridged to exactly one valid listing through `MarketReferenceListingAssignment`.
4. Benchmark/sector reference listings use the existing Market Data and MarketAnalysis pipeline, including existing provider instrument mappings and immutable analysis runs.
5. Automatic candidate evaluation resolves the latest completed analysis at or before the requested `as_of` timestamp for the broad-market listing, sector-reference listing and candidate underlying.
6. Overlapping or missing semantic assignments fail explicitly. `INSUFFICIENT` reference-assignment quality also fails resolution.
7. The previous explicit analysis-source endpoint remains available for compatibility; the new automatic endpoint is the preferred workflow.
8. The internal underlying type catalogue is extended with `INDEX` and `SECTOR_INDEX` so benchmark and sector-reference listings can be represented without pretending to be stocks.

## Consequences
- Clients no longer need to know analysis IDs for normal candidate evaluation.
- Provenance is selected by the backend from controlled reference data and immutable analysis history.
- Existing provider mapping, market-data persistence and FT-006 calculation logic are reused.
- Reference assignments must be administered before automatic evaluation can succeed.
- Provider-specific index/sector symbols remain configuration in the market-data mapping layer, not Candidate domain logic.
