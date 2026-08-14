# FT-002 – Trading Venues

## Status

Released – Sprint 7A.

Merged via PR #8 into `main`.

Release merge commit: `7f39bc0`.

## User outcome

Trading Workspace centrally maintains provider-neutral trading-venue identities while keeping venue handling nearly invisible in normal trading workflows.

A trader should not repeatedly enter exchange metadata. When one valid venue is known, the system uses it automatically. A user choice is requested only for genuine ambiguity, especially later when a product can actually be purchased on more than one valid venue.

## Implemented scope

- reuse of existing global `TradingVenue` identity;
- MIC canonicalization and uniqueness;
- technical optimistic-concurrency version;
- activation/deactivation lifecycle without hard delete;
- global audit events using the existing audit infrastructure;
- administration service and REST mutations;
- admin read contract including inactive venues;
- provider-exchange reconciliation and mapping validation;
- read-only reconciliation visibility for administration;
- low-input Listing/Underlying UI behavior;
- dedicated, non-primary-navigation admin UI;
- persistence, service, REST, frontend and reconciliation tests;
- FT-002 E2E contract for automatic versus explicit venue selection.

## Explicit boundaries

- Provider exchange code is not TradingVenue identity.
- Provider discovery does not silently create or overwrite TradingVenue master data.
- Currency is not modeled as a TradingVenue default in FT-002; Listing already owns `currency_code`.
- TradingVenue is global; no workspace duplicate master data is introduced.
- TradePlan receives no Venue or Issuer fields.
- Issuer remains FT-003.
- Warrant remains FT-004.
- Product Selection remains FT-008.

## Lifecycle

Deactivation prevents a venue from being offered for new normal selections but does not delete the identity or invalidate historical Listing references. Reactivation restores availability using the same identity.

## FT-004 consumer contract

A later Warrant may reference:

- stable `issuer_id` from FT-003;
- stable `trading_venue_id` from FT-002;
- underlying/listing reference;
- provider mappings in the provider boundary.

MIC and provider exchange codes must not replace `trading_venue_id`.

This is an architecture compatibility contract only and does not implement Warrant.

## Low-input rule

- one valid venue: automatic use/preselection;
- multiple valid venues: user chooses when the distinction matters;
- unresolved provider evidence: no free-form MIC/exchange-code input is pushed to the trader;
- administration handles exceptional reference-data conflicts.

## Release status

Released after successful protected-branch CI on PR #8.

- Backend: PASS
- Frontend: PASS
- End-to-End: PASS
- Pull Request: #8
- Merge commit: `7f39bc0`
