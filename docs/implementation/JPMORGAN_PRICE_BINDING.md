# JPMorgan route identity without a DOM quote clock

Date: 2026-10-04. Baseline: v1.4.4 / `8fba3730e4e65f0649df14b99e4c08f5b927d22e`.
Category: provider integration defect; no trading/model/time policy change.

## Evidence and reproduction

An operator-returned setup trace passed the reviewed terms/form submission and
product metadata checks, then failed with `ISSUER_STREAM_BINDING_UNVERIFIED`.
A bounded structural diagnostic showed the same exact product-item bindings in
the live and sanitized DOM: bid, bidsize, ask, asksize and calculated display
fields, but no quotetime. The sanitizer did not remove a clock node. No consent
state was saved. Raw operator output, consent, cookies and portfolio identifiers
are not repository fixtures.

A synthetic product table and exact same-item bid/ask bindings, without a DOM
clock, reproduce the old failure in
`test_jpmorgan_price_bindings_verify_route_without_dom_clock`. This test failed
against the unchanged parser before the correction. It does not fetch a provider.

## Contract and acceptance criteria

1. JPMorgan bid and ask must both bind the same exact ISIN-specific DOM item in
   staticgrid from lightstreamer. Never construct a stream identifier from a prefix.
2. A DOM quotetime is optional for JPMorgan route identity. If such a binding
   participates in the expected grid/source, its item must not conflict with prices.
3. Both price cells must still establish EUR, with consistent product-table
   metadata, ISIN/WKN, supported type and nonexpired valuation date on the allowed
   official product URL. Missing sides or conflicting stream items still fail.
4. Morgan Stanley retains its existing required lastquotetimestamp binding.
5. PageEvidence format and existing mapping identity remain compatible. Quote
   acquisition still uses the existing stream schema. Unknown quote time remains
   unknown; receipt/underlying/expiry dates are never promoted to quote timestamps.
   Indicative and non-executable status, retention and selection policies are unchanged.
6. Consent still requires the explicitly reviewed hash and personal declarations.
   Saving still requires product verification in a fresh context. A failed reuse
   check must not save state. Neither setup nor this patch creates a trade or listing.
7. Updating an already canonical four-service deployment uses a new clean release
   checkout and private preparation directory. All existing settings, data, consent,
   sandbox and image checks remain mandatory; old sealed state is never edited.

## Implementation and verification

The single provider-page parser changes its required field set for JPMorgan only.
Backend HTTP/rendered discovery, renderer validation and consent setup already
share this parser; no duplicate extraction logic or frontend calculation is added.
The historical discovery package document points explicitly to this correction.
No migration, new model rule, provider priority or source-selection policy is added.

Synthetic regressions cover absent clocks, missing price sides, wrong grids/sources,
conflicting price and present-clock items, and the unchanged Morgan Stanley gate.
Renderer and consent tests exercise the actual parser; consent tests retain both
successful and failing fresh-context reuse. SQL discovery/selection/adapter tests
cover JPMorgan without a DOM clock through HTTP and rendered acquisition, preserving
unknown quote time and original retention provenance. PostgreSQL concurrency and
the existing full regression suites remain required in CI.

The disposable Docker deployment check additionally performs a second deployment
from an already canonical stack to a distinct synthetic revision. It checks the
existing database container, database marker, consent marker, effective settings,
new images and Chromium sandbox through the unchanged deployment helper. This is
CI-only infrastructure; it is not an operator deployment or provider acceptance.

Final commit, complete CI outcomes and immutable tag are recorded in the delivery
PR. A passing regression does not prove the next server consent attempt succeeds:
the full live product access and stored-state reuse remain separate acceptance.
