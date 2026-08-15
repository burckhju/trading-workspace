# ADR-S7-004 – Warrant and WarrantListing Boundary

## Status
Accepted for Sprint 7C after S7C-00 review.

## Decision
Warrant product identity and tradable quotation are separate concepts.

`Warrant 1 -> n WarrantListing`. A WarrantListing references the released FT-002 `trading_venue_id` and owns venue-specific symbols and quotation currency. `trading_venue_id` is not stored directly on Warrant.

ProviderInstrument and MarketDataSeries remain separate from both Warrant and WarrantListing. Existing FT-001 ProviderInstrumentMapping is not silently widened because its current contract is Listing-specific.

## Consequences
The same product can be represented at more than one venue without cloning the product. Execution can later reference a concrete WarrantListing while FT-008 can reason about product identity and tradability separately.

## User impact
The UI must distinguish product data from tradable listings. Users do not need to create a duplicate warrant merely because it is available at another venue.
