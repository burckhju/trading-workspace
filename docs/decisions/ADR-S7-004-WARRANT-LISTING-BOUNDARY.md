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

## Implementation note: optional venue symbol
The existing nullable-symbol contract (migration `20260912_0032`) also applies to the administration UI. When a venue publishes no symbol, leave the Symbol field empty; the API client sends `null`, not an empty string or a substituted ISIN/WKN/underlying ticker. A verified venue and quotation currency remain required. The existing service validates active references and rejects duplicate symbol-less listings for the same product and venue.

A saved product without a listing is still not a ProductSelection candidate. Complete the existing listing form deliberately, then start a new evaluation through the existing product-selection page. Historical runs are not rewritten. Missing quotes remain incomplete data requiring the existing explicit selection confirmation; adding a listing never records a purchase.

Read-only local check after update: open the existing Optionsscheine administration, select a product, and check that Symbol is optional while Handelsplatz and Handelswährung remain required. Do not submit merely for diagnosis. The automated disposable-stack regression is `tests/e2e/warrant-listing-without-symbol.spec.ts` and follows actual listing persistence through the existing confirmation and BUY flow. Never enable its write-test flag on a user depot.
