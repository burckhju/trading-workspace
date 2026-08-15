# Sprint 7B / FT-003 – Architecture Review and Gap Closure

## S7B-00 repository baseline

Verified repository baseline before FT-003 implementation:

- branch at start: `main`;
- `HEAD`: `a3a60cb` – S7A governance closeout merge;
- `origin/main`: `a3a60cb` in the supplied repository metadata;
- release tag `v0.7.0-trading-venues` exists;
- FT-002 documentation reports Released;
- four pre-existing untracked local files were present and are excluded from S7B work;
- working branch created: `feature/s7b-ft003-issuers`.

A live remote pull cannot be treated as verified unless network/remote authentication is available.
The supplied Git metadata is therefore the verifiable repository baseline in this workspace.

## Existing-domain review

Repository search found no reusable `Company`, `Organization`, `LegalEntity`, `Issuer`,
`Institution` or `Counterparty` aggregate in application source. Existing boundaries relevant to
FT-003 are:

- `Underlying`: workspace-scoped market identity;
- `Listing`: workspace-scoped listing identity referencing `TradingVenue`;
- `TradingVenue`: global provider-neutral reference data;
- provider instrument mappings: provider-specific symbol/exchange data kept outside core identity;
- `TradePlan`: released product-neutral boundary that must not gain Issuer/Product attributes.

Therefore no existing domain entity can safely be renamed or reused as Issuer.

## S7B-00 decisions

The accepted design is recorded in
`ADR-S7-002-ISSUER-IDENTITY-SOURCE-OF-TRUTH-AND-LIFECYCLE.md`.

Key decisions:

- Issuer V1 represents the issuing legal entity, not brand/group.
- Issuer identity is a global internal UUID.
- legal/display names are mutable master data, not identity.
- LEI is optional external evidence and duplicate protection, not primary identity.
- provider discovery cannot silently create or overwrite Issuer master data.
- no name-based automatic merge.
- provider reconciliation remains out of V1 until a reliable provider issuer-data contract exists.
- lifecycle is deactivate/reactivate without hard delete.
- FT-004 consumes stable `issuer_id` independently from Venue, Underlying and provider IDs.
- TradePlan remains unchanged.

## Minimal implementation slice

The next implementation slice should be backend-first and intentionally small:

1. add Issuer persistence model and Alembic migration;
2. add domain/service contract for list/get/create/update/deactivate/reactivate;
3. add global audit support for Issuer administration using the existing audit infrastructure;
4. add read/admin REST contracts under the existing reference-data routing boundary;
5. add validation for non-blank names, optional ISO country code, optional canonical LEI,
   optimistic concurrency and duplicate LEI;
6. add focused persistence/service/API tests;
7. prove TradePlan has no diff;
8. only then decide whether any frontend administration is actually needed for FT-003 acceptance.

## Explicit non-goals for the implementation slice

- no Warrant model/API/UI;
- no Product Selection;
- no issuer field in TradePlan/TradePlanVersion;
- no Underlying → Issuer relation;
- no corporate group hierarchy;
- no automatic provider-created issuer;
- no fuzzy-name automatic merge;
- no synthetic LEI;
- no provider reconciliation without a real structured issuer-data source.

## Auswirkung für den Nutzer

The normal trading workflow remains unchanged. No trader input is added. Issuer administration is
an exceptional reference-data concern; later products should resolve an issuer automatically when
there is sufficient evidence. Manual intervention is reserved for unresolved or conflicting
reference-data cases.
