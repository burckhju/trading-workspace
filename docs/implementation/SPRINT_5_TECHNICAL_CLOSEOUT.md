# Sprint 5 Technical Closeout

Date: 2026-08-10

## Scope

Technical closeout for FT-005 Candidate Qualification V1 after the cross-sprint compatibility review.
No feature scope was added. The closeout validates the established repository quality gates and closes test-coverage gaps introduced by Sprint 5.

## Backend quality gates

### pytest / coverage

Executed with the same scope and threshold as `.github/workflows/backend.yml`:

```bash
PYTHONPATH=. python -m pytest ../tests/unit/backend ../tests/integration/backend \
  --cov=app --cov-report=term --cov-fail-under=85 -q
```

Result:

- 238 tests passed
- total coverage: 85.06%
- required threshold: 85%
- status: PASS

Additional tests were added for:

- top-down reference administration service,
- candidate application lifecycle paths,
- semantic source-resolution validation,
- candidate persistence repository.

No threshold was reduced and no production logic was weakened to satisfy coverage.

### Ruff / Black / mypy

Status: BLOCKED BY EXECUTION ENVIRONMENT.

The tools are declared in `backend/requirements-dev.txt`, but are not installed in this slim artifact. Installation from the available internal package mirror failed because the required packages/versions were not available (including `ruff==0.15.1`; installing the complete requirements additionally fails on `asyncpg==0.31.0`).

These checks therefore remain required CI/release gates and are not reported as passing locally.

### Python compile/import check

```bash
python -m compileall -q app ../tests/unit/backend ../tests/integration/backend
```

Status: PASS.

## Alembic

Alembic metadata validation:

- single head: `20260810_0007`
- revision chain is linear from `20260803_0001` through `20260810_0007`
- `alembic heads`: PASS
- `alembic history`: PASS

A real PostgreSQL `upgrade head` / downgrade verification was not executed in this environment because no PostgreSQL test instance / connection was provided. It remains a release gate.

## Frontend quality gates

Status: BLOCKED BY EXECUTION ENVIRONMENT.

`frontend/node_modules` is absent. `npm ci` was attempted with Node 22.16.0 / npm 10.9.2 and failed against the available internal registry mirror because `yocto-queue@0.1.0` could not be retrieved.

The following repository-defined gates therefore remain pending in CI or a complete developer environment:

- TypeScript
- ESLint
- Prettier
- Vitest coverage thresholds (80% lines/functions/statements, 70% branches)
- production build
- Playwright/E2E

No frontend threshold was reduced.

## Release assessment

Candidate Qualification V1 is technically consistent with Sprint 0-4 and the forward constraints documented in the cross-sprint review.

The backend test/coverage release blocker found during this closeout is closed.

Sprint 5 must still not be declared fully released until the following external/environmental gates are green:

1. Ruff / Black / mypy in the repository CI environment.
2. PostgreSQL migration `upgrade head` (and the repository's expected migration smoke path).
3. Full frontend quality workflow.
4. Live EODHD top-down smoke path with validated reference mappings.
5. Git clean-working-tree / PR / branch-protection release checks.

The generic Watchlist aggregate remains deferred FT-005 scope and is not a blocker for Candidate Qualification V1 or FT-007 TradePlan, as documented in the cross-sprint review.
