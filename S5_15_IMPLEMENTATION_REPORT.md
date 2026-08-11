# S5.15 Implementation Report – Guided Live Configuration Workflow

## Implemented
- Candidate-specific read-only live workflow endpoint: `GET /api/v1/candidates/{candidate_id}/live-workflow`.
- Ordered prerequisite inspection for broad-market benchmark, sector, sector reference, listing mappings, EODHD mappings, 61-day price history and completed FT-006 analyses.
- Machine-readable `next_action` plus per-step `COMPLETE` / `BLOCKED` state.
- Candidate auto-evaluation remains the only evaluation write path and is enabled only after readiness is complete.
- Operator CLI `scripts/top_down_guided_live.py` with optional `--evaluate` after readiness.
- Candidate frontend displays readiness steps and disables auto evaluation while blocked.
- ADR-S5-011 documents the workflow boundary.

## Domain / architecture decisions
- Workflow is read-only: it never guesses symbols, creates mappings, imports prices, runs analyses, or changes candidate state.
- Provider validation remains in the existing market-data administration boundary.
- A minimum of 61 daily prices is required for the approved 60-trading-day relative-strength model.
- Explicit operator actions remain auditable.

## Tests
- Full backend suite: 230 passed.
- Python compile/import check: passed.
- Frontend tests/typecheck/build: not rerun because this slim archive does not contain `frontend/node_modules`.

## Next step
S5.16 should connect the machine-readable `next_action` values to guided administrative UI actions (deep links/forms) and, in an environment with EODHD credentials, execute the first real S&P 500 → sector reference → US underlying live path.
