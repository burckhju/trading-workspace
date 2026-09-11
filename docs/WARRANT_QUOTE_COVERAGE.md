# Warrant quote coverage

Held-product valuation resolves quotes through the existing provider-neutral `WarrantListingQuoteProvider` boundary.

## Listing fallback

The listing recorded by the product evaluation remains the provenance anchor and is attempted first. If it has no usable BID, valuation may try other **active** `WarrantListing` rows that belong to the same `Warrant` in the same workspace. A quote from an unrelated warrant is never eligible for fallback.

Every quote-source attempt records the concrete `warrant_listing_id` that was queried. If an alternate listing supplies the BID, the returned valuation exposes that listing and uses reason `WARRANT_BID_AVAILABLE_ON_ALTERNATE_LISTING`.

## Delayed venues

Börse Stuttgart XSTU delayed data remains an optional delayed source. gettex publishes official delayed pre-trade files for MUND and MUNC with a maximum delay of 15 minutes and UTC timestamps. The runtime keeps gettex fail-closed until the CSV schema and listing identity mapping have been verified against a real downloaded file on the deployment host.

Do not estimate a warrant market value when no exact, valid BID is available.
