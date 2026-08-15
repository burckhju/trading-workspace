# Sprint 7B – FT-003 Release Candidate Readiness

## Status

**RELEASE CANDIDATE READY FOR COMMIT / PR – PROTECTED CI AND MERGE PENDING**

This review is based on the actual `feature/s7b-ft003-issuers` worktree against `main` at `a3a60cb` / tag `v0.7.0-trading-venues`.
It does not claim a commit, pull request, protected-branch CI result, merge or release tag that has not actually occurred.

## Final diff review

The staged FT-003 change set contains the intended architecture, persistence, service, API, administration UI, tests and documentation.

Boundary review confirms:

- no FT-003 changes under the TradePlan feature boundary;
- no Warrant/Product persistence, service, API or UI;
- no workspace duplication of Issuer master data;
- no provider identifier used as internal Issuer identity;
- no automatic name-based merge;
- no speculative EODHD Issuer reconciliation;
- lifecycle is deactivate/reactivate, not destructive deletion.

Four pre-existing untracked files remain outside the staged FT-003 change set and must not be included accidentally.

## Local release-candidate evidence

### Repository integrity

- `git diff --cached --check`: PASS.
- Python compile check for Market/FT-003 test scope: PASS.
- working branch: `feature/s7b-ft003-issuers`.
- baseline commit: `a3a60cb`.

### Backend

- focused Market feature suite: 111/111 PASS;
- full repository pytest run with CI-style `PYTHONPATH=backend`: 319/319 PASS;
- Ruff / Black / mypy: not locally executable because those modules are absent from the available system Python; no PASS is claimed for these gates.

Protected Backend CI remains authoritative and must run its repository-defined `requirements-dev.txt` toolchain, quality checks and coverage threshold.

### Frontend

- Vitest: 67/67 PASS;
- TypeScript: PASS;
- ESLint: PASS;
- Vite production build: PASS.

The archived workspace's `.bin` wrappers are unreliable, so package entrypoints were invoked directly. Protected Frontend CI must still run the canonical `npm ci` scripts, including Prettier and coverage thresholds.

### End-to-End

No local protected-CI E2E PASS is claimed in this review. The repository workflow builds the Docker stack and runs Playwright; that protected-branch gate remains mandatory before release closeout.

## Commit / PR readiness

The staged change set is ready to commit, but this environment has no configured `user.name` or `user.email`. No author identity is invented.

Before creating the commit:

1. configure the intended Git author identity;
2. re-run `git status --short` and confirm only FT-003 files are staged;
3. do not stage the four pre-existing untracked files;
4. create the FT-003 implementation commit;
5. push `feature/s7b-ft003-issuers` and open the implementation PR to `main`;
6. require Backend, Frontend and End-to-End workflows to pass;
7. resolve only evidenced failures without expanding FT-003 scope;
8. merge only after required reviews/gates pass;
9. perform a separate governance/release closeout based on actually observed merge/CI evidence.

## Suggested commit subject

`feat(market): add issuer reference data`

The subject is a recommendation only; no commit is claimed until Git records it with the configured project author.

## Suggested PR scope statement

FT-003 introduces global provider-neutral Issuer reference data with stable internal identity, minimal administration, lifecycle/audit support and an FT-004 consumer contract. It preserves TradePlan product neutrality and intentionally defers provider reconciliation because the current EODHD boundary exposes no structured Issuer/LEI identity contract.

## Auswirkung für den Nutzer

### Welche Eingaben entfallen?

The normal trader does not enter Issuer UUIDs, LEIs, provider Issuer IDs, versions, provenance or mapping data.

### Welche Informationen werden automatisch verwendet?

Active Issuer reference data is available centrally. A future Warrant/Product flow can persist the stable `issuer_id` automatically after unambiguous resolution.

### Wann ist eine Benutzerentscheidung nötig?

Not in the normal trading workflow. Only exceptional master-data correction or genuinely ambiguous/conflicting evidence requires administration; the system does not guess.

### Ändert sich der normale Trading-Workflow?

No. The release candidate adds background reference-data capability plus a separate administration surface, not a new recurring trading step.

### Entsteht neuer administrativer Aufwand?

Only exceptional reference-data maintenance. The V1 form is intentionally limited to legal name, display name and optional country/LEI; technical identity and concurrency fields are handled by the system.

## Release gate

FT-003 may be called **Released** only after actual commit/PR evidence, protected Backend + Frontend + End-to-End CI PASS, merge to `main`, and the repository's governance/release closeout. Until then the truthful state is **Release Candidate**.
