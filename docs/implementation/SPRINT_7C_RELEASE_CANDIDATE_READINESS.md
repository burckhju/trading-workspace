# Sprint 7C – FT-004 Release Candidate Readiness

## Status

**LOCAL RELEASE CANDIDATE – PROTECTED CI, MERGE AND RELEASE PENDING**

This review is based on the actual `feature/s7c-ft004-warrants` worktree against the verified Sprint-7B baseline `4ad4e0440502336af4be8cd5c85fd7c3c2d5e7b1` / `v0.8.0-issuers`.

It does not claim a commit, pull request, protected CI result, merge or release tag that has not actually occurred.

## Delivered capability

- workspace-scoped stable Warrant UUID identity;
- classic bank-issued CALL/PUT Warrant V1 scope;
- released FT-003 Issuer and FT-001 Underlying references;
- separate WarrantListing with released FT-002 TradingVenue reference;
- immutable/effective-dated product terms history;
- explicit ratio semantics: underlying units per warrant;
- maturity separated from administrative active/inactive lifecycle;
- duplicate ISIN/WKN and venue/symbol conflict handling;
- optimistic concurrency for lifecycle and terms changes;
- administration UI separating product, terms history and listings;
- explicit provider and market-data boundary;
- no FT-008 selection, ranking, scoring, execution or TradePlan product coupling.

## User impact

A new `Produkte · Optionsscheine` administration entry is visible. Users select existing Issuer, Underlying and TradingVenue reference data instead of entering technical IDs or duplicating master data.

Terms corrections create a new version rather than rewriting history. Multiple venues are represented as listings of one product. Stale edits and duplicates are rejected with stable conflict semantics.

FT-004 does not add automatic product selection or a trading decision. No automatic EODHD Warrant ingestion is claimed because the repository does not prove a complete authoritative Warrant reference-data contract.

## Local verification evidence

### Backend

- full Backend unit/integration suite: **333/333 PASS**;
- Backend coverage: **85.04%** (required >= 85%): PASS;
- Ruff over app + unit/integration tests: PASS;
- `git diff --check`: PASS;
- Black and mypy still require canonical protected CI because the archived Python-3.12 environment is not portable in this runner.

### Frontend

- full Vitest suite: **22 files / 77 tests PASS**;
- Frontend coverage: **90.87% statements/lines, 83.65% functions, 77.62% branches**: PASS against protected thresholds;
- TypeScript project build: PASS;
- ESLint: PASS;
- Prettier: PASS;
- Vite production build: PASS;
- protected Frontend CI remains authoritative for the clean `npm ci` rerun.

### Migration

Revision `20260815_0011` is based on `20260815_0010` and defines symmetric creation/removal of `warrants`, `warrant_terms_versions` and `warrant_listings` plus indexes/constraints.

A real database upgrade/downgrade execution is **not claimed in this archived environment**. It remains a release gate.

### End-to-End

No protected-CI E2E PASS is claimed for S7C yet. The repository-defined protected E2E workflow remains mandatory.

## FT-008 readiness assessment

FT-004 provides stable Warrant, WarrantListing, Issuer, Underlying and effective-dated product-term identities. FT-008 must still decide which exact terms version and listing a ProductSelection references and how market-data snapshots/provenance and the user's selection decision are recorded.

FT-008 must not reinterpret ratio semantics or use current mutable reference data to rewrite historical selections.

## Remaining release gates

1. Keep the four known legacy untracked files out of S7C.
2. Run canonical Backend Black and mypy under Python 3.12; Ruff/tests/coverage already pass locally.
3. Execute Alembic upgrade to `20260815_0011`, downgrade to `20260815_0010`, and re-upgrade on a supported PostgreSQL database.
4. Re-run canonical Frontend CI from a clean `npm ci`; all equivalent local frontend gates currently pass.
5. Run protected End-to-End CI.
6. Configure the intended project Git identity, commit/push the staged S7C changes and open the FT-004 implementation PR.
7. Merge only after required protected gates pass.
8. Perform governance/status synchronization and release tagging only from observed merged evidence.

## Decision

FT-004 is **locally implementation-complete and release-candidate ready**, but it is not yet truthfully `Released`. Remaining work is release evidence and governance, not expansion into FT-008, execution or speculative provider integration.
