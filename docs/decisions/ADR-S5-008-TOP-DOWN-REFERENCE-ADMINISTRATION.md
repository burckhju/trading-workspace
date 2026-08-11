# ADR-S5-008 – Top-down reference administration

## Status
Accepted – Sprint 5

## Context
Semantic source resolution requires explicit, historized configuration for market references, sector references and their relationship to analyzable listings. Provider symbols must remain outside the domain model and must not be guessed by Candidate or Market Analysis.

## Decision
The application exposes a dedicated administrative API under `/api/v1/top-down-reference-data`.

`POST /bootstrap-v1` idempotently creates only the approved semantic benchmark references:

- `DAX` – Germany broad market
- `SP500` – USA broad market
- `NASDAQ100` – USA growth/technology context

The bootstrap does **not** create provider symbols, provider mappings or sector taxonomies.

Administrators explicitly configure:

1. `MarketReference -> Listing` assignments.
2. Existing `Listing -> ProviderInstrumentMapping` through the FT-003 market-data administration API.
3. `Underlying -> BROAD_MARKET MarketReference` assignments.
4. `Underlying -> Sector` assignments.
5. `Sector -> SECTOR_INDEX MarketReference` assignments.

Assignments are valid-time based and overlapping assignments for the same semantic role are rejected.

## Operational configuration sequence

For a broad-market reference such as S&P 500:

1. Bootstrap/create the semantic `MarketReference`.
2. Create an `INDEX` underlying and listing using the normal FT-001 API.
3. Assign the semantic reference to that listing.
4. Configure and validate the provider mapping using `/api/v1/market-data/provider-mappings`.
5. Import EOD prices through the existing market-data import endpoint.
6. Run the existing FT-006 analysis for that listing.

For a sector:

1. Create the canonical `Sector`.
2. Create a `SECTOR_INDEX` market reference.
3. Create the analyzable underlying/listing for the chosen sector reference.
4. Assign reference -> listing and provider mapping.
5. Assign sector -> sector reference.
6. Assign stock underlyings -> sector.

No provider-specific ticker or exchange code is stored in `MarketReference`, `Sector` or Candidate.

## Consequences

- Semantic meaning and provider transport remain separated.
- DAX/S&P 500/Nasdaq-100 can use the existing listing, provider mapping, daily-price and FT-006 analysis pipeline.
- Historical Candidate evaluations remain reproducible through valid-time mappings.
- A real environment still requires an administrator to choose and validate the actual provider symbols and sector-reference instruments. These values are deliberately not hard-coded by Sprint 5.
