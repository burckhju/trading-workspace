# Sprint 8 / FT-008 – Technical Closeout

## Feature

FT-008 Product Selection / Produktauswahl

## Released implementation baseline

- Implementation PR: #15
- Implementation commit: `ca7480c`
- Merge commit: `e3d6887`
- Baseline before Sprint 8: `ec799a7` / `v0.9.0-warrants`
- Alembic head: `20260816_0013`

## Implemented scope

FT-008 implements Product Selection as a transparent decision-support workflow after an approved TradePlanVersion.

The implemented workflow separates:

- Product Universe Construction
- Eligibility
- ProductEvaluation
- ProductSelection

ProductEvaluation remains a reproducible system result. ProductSelection remains an explicit user decision.

Historical evaluation context retains the exact:

- TradePlanVersion
- Warrant
- WarrantTermsVersion
- WarrantListing
- evaluation model/version
- criteria
- inputs
- metrics
- reasons
- data availability and provenance

## Selection policy

V1 permits a normal ProductSelection only for an `ELIGIBLE` ProductEvaluation.

There is no normal override for:

- `INELIGIBLE`
- `NOT_EVALUABLE`

No autonomous product recommendation or automatic selection is implemented.

## Market-data boundary

WarrantListing provider identity is separated from the released FT-001 ProviderInstrumentMapping contract.

Warrant market-data capability remains fail-closed.

No live Bid/Ask support is claimed unless provider capability is explicitly verified for the actual FT-004 warrant universe.

The implementation does not introduce:

- Black-Scholes
- IV solver
- internal Greeks engine
- automatic pricing
- automatic position sizing
- order execution

## User impact

Users can:

- start Product Selection from an approved TradePlanVersion;
- inspect considered products;
- see explicit universe omissions;
- distinguish ELIGIBLE, INELIGIBLE and NOT_EVALUABLE;
- inspect criteria, reasons, missing data, data quality and provenance;
- compare evaluations;
- explicitly confirm one eligible product;
- retain the historical decision context.

The system does not convert an evaluation into a trading decision automatically.

## Quality evidence

### Backend

- Ruff: PASS
- Black: PASS
- mypy: PASS
- Unit + integration tests: 388 / 388 PASS
- Coverage: >= 85% gate PASS

### Frontend

- TypeScript: PASS
- ESLint: PASS
- Prettier: PASS
- Unit tests: 24 / 24 files, 81 / 81 tests PASS
- Coverage thresholds: PASS
- Production build: PASS

### End-to-End

- Playwright: 12 / 12 PASS
- FT-008 NOT_EVALUABLE fail-closed scenario: PASS
- FT-008 ELIGIBLE -> explicit ProductSelection scenario: PASS

### PostgreSQL / Alembic

- PostgreSQL stack: healthy
- Alembic current: `20260816_0013 (head)`
- Alembic check: no new upgrade operations detected
- `alembic_version`: `20260816_0013`

### Protected CI

PR #15:

- Backend / quality: PASS
- Frontend / quality: PASS
- End-to-End / smoke: PASS

## Architecture decisions

- ADR-S8-001 ProductSelectionRun and decision boundary
- ADR-S8-002 Historical product reference
- ADR-S8-003 Universe and eligibility
- ADR-S8-004 TradePlan handoff
- ADR-S8-005 Warrant market-data boundary
- ADR-S8-006 Evaluation and comparison
- ADR-S8-007 Provider capability and selection policy

## Remaining operational dependency

A live production workflow requiring WarrantListing Bid/Ask depends on a provider capability explicitly verified for the actual warrant universe.

Until then, quote-dependent evaluation remains intentionally fail-closed.

## Release decision

FT-008 satisfies the implemented V1 scope and repository quality gates.

Release candidate:

`v1.0.0-product-selection`
