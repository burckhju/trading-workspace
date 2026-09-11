# S6.14 Implementation Report — Warrant Quote Coverage

## Scope

Implemented the first P0 coverage slice for held warrant valuation:

- preserve the existing provider-neutral quote boundary;
- trace every quote-source attempt with the concrete `warrant_listing_id`;
- try the product-evaluation listing first;
- if no usable BID is found, try other active listings for the same warrant and workspace;
- expose alternate-listing provenance in the returned valuation;
- never synthesize a value when no exact valid BID exists.

## Identity safety

Cross-listing fallback is constrained by `workspace_id`, `warrant_id`, and active listing lifecycle. A provider result must still match the concrete listing request before it can be selected.

## Tests

Added a regression test where the primary listing has no quote and an alternate listing for the same warrant supplies a valid BID. The test asserts alternate-listing provenance, market value, P&L, and attempt tracing.

## Remaining operational validation

The deployment-host validation for ISIN `DE000VH2LU21` is still required. The gettex official MUND/MUNC delayed feed is documented, but runtime activation remains fail-closed until its real CSV schema and exact listing identity mapping are verified on the Linux host.
