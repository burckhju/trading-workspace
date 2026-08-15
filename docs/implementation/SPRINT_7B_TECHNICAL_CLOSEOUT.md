# Sprint 7B – FT-003 Technical Closeout

## Status

**MERGED – RELEASE TAG / FINAL GOVERNANCE CLOSEOUT PENDING**

FT-003 implementation is merged to `main` through PR #10. Protected pull-request Backend, Frontend and End-to-End CI have all passed. The observed merge commit is `346f246`. This document does not yet claim final release tagging or completed Sprint 7B governance closeout.

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

## Verification and merge evidence

- PR #10: `FT-003: Add issuer reference data`.
- PR state: merged into `main`.
- Observed merge commit: `346f246`.
- Backend protected PR CI: PASS.
- Frontend protected PR CI: PASS.
- End-to-End protected PR CI: PASS.
- Final release tag / Sprint 7B governance closeout: still pending.

No release tag is claimed until it is actually created and verified.

## Decision

FT-003 has passed implementation, review, protected PR quality gates and merge to `main`. The remaining work is governance closeout and release tagging only. No remaining FT-003 work justifies expansion into Warrant/Product Selection or speculative provider reconciliation.

## Verified evidence

### Backend

- Full backend unit/integration suite: 318/318 passed locally with CI-style `PYTHONPATH`.
- Ruff: PASS.
- Black: PASS.
- mypy: PASS across 167 source files.
- Protected PR Backend quality CI: PASS.

### Frontend

- 70/70 frontend tests passed.
- Global coverage: 90.29% statements, 82.15% functions, 90.29% lines.
- TypeScript typecheck: PASS.
- ESLint: PASS with zero warnings.
- Prettier: PASS.
- Vite production build: PASS.
- Protected PR Frontend quality CI: PASS.

### End-to-End

- Protected PR End-to-End smoke CI: PASS.

### Boundary verification

- No FT-003 modification to the TradePlan product-neutral boundary.
- No Warrant/Product implementation introduced.
- Current EODHD provider boundary has no structured issuer/LEI identity contract;
  provider reconciliation remains explicitly deferred.
