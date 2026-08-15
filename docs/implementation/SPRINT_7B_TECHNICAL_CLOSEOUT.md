# Sprint 7B – FT-003 Technical Closeout

## Status

**IMPLEMENTATION COMPLETE – RELEASE/PROTECTED-BRANCH CI PENDING**

FT-003 implementation and local architecture gap closure are complete on `feature/s7b-ft003-issuers`. This document does not claim merge, release or protected-branch CI success before those events actually occur.

## Delivered capability

- global provider-neutral Issuer identity with stable internal UUID;
- legal-entity V1 semantics separated from brand/group and Underlying identity;
- optional country and LEI master data;
- LEI duplicate protection without making LEI primary identity;
- optimistic-concurrency administration;
- deactivate/reactivate lifecycle preserving stable identity;
- global audit events;
- active-only consumer API plus separate administration API;
- exceptional low-input administration UI;
- FT-004 consumer compatibility contract;
- architecture guards proving TradePlan remains product-neutral;
- explicit provider-reconciliation gap review.

## Provider / reconciliation review

The current EODHD search boundary exposes `Code`, `Exchange`, `Name`, `Type`, `Currency` and `ISIN`. It does not expose a structured Issuer identity or LEI in the repository contract.

Consequences:

- no artificial Issuer reconciliation is implemented;
- provider/display names are not treated as durable identity;
- no automatic name matching or merge is performed;
- no synthetic LEI/provider issuer identifier is generated;
- a later provider integration may add evidence/mapping only after its own explicit contract review.

This is an intentional FT-003 scope decision, not a missing implementation required for completion of stable internal Issuer reference data.

## FT-004 consumer compatibility

FT-004 can later model a Warrant using stable `issuer_id` independently from:

- underlying/listing identity;
- `trading_venue_id`;
- provider product identifier/mapping.

FT-003 introduces no Warrant table, service, API or UI.

## TradePlan boundary verification

Automated architecture tests verify that FT-007 domain and persistence models do not contain Issuer/Warrant/Product-specific fields introduced by FT-003.

## Auswirkung für den Nutzer

### Eingaben, die entfallen

Normal traders do not enter `issuer_id`, LEI, provider issuer ID, technical version or provenance/mapping data.

### Automatisch verwendete Informationen

Active Issuer reference data is available through the consumer API. Future product flows can retain/use stable `issuer_id` automatically after unambiguous resolution.

### Wann ist eine Benutzerentscheidung nötig?

Not in the normal FT-003 trading workflow. Ambiguous/conflicting issuer evidence is intentionally not guessed and belongs to exceptional administration/reconciliation.

### Ändert sich der normale Trading-Workflow?

No. FT-003 adds reference-data capability and exceptional administration, not a recurring trading step.

### Neuer administrativer Aufwand

Only when reference data must be created, corrected, deactivated/reactivated or later reconciled. The admin UI intentionally limits editable master data to the minimum V1 fields.

## Local verification policy

Local verification is evidence for implementation readiness only. Protected-branch Backend, Frontend and End-to-End CI remain authoritative for release closeout.

A merge commit, pull-request number, CI PASS or release tag must be added only after actually observed.

## Decision

FT-003 is ready for final repository quality gates and release-candidate preparation. Any failing gate should be fixed narrowly; it is not justification to expand FT-003 into Warrant/Product Selection or speculative provider reconciliation.

## Verified evidence in the available environment

### Backend

- Market feature unit suite: 111/111 passed.
- Full repository pytest run with the CI-style `PYTHONPATH=backend`: 319/319 passed.
- Ruff, Black and mypy are not installed in the available system Python, so no local PASS is claimed
  for those protected-CI gates; protected-branch Backend CI remains authoritative for them.

### Frontend

Because archived `.bin` wrappers are not reliable in this workspace, installed package entrypoints
were invoked directly.

- 67/67 frontend tests passed.
- TypeScript typecheck passed.
- ESLint passed with zero warnings.
- Vite production build passed.

### Boundary verification

- `git diff main --` shows no FT-003 modification under the TradePlan feature boundary.
- No Warrant/Product implementation is introduced.
- Current EODHD provider source has no issuer/LEI identity contract; provider reconciliation stays
  explicitly deferred.
