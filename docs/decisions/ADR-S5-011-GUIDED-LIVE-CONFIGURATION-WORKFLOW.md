# ADR-S5-011 – Guided live configuration workflow

## Status
Accepted for Sprint 5 V1.

## Context
The top-down source resolver is intentionally strict. A live evaluation can fail because benchmark, sector, reference-listing, provider mapping, price history or FT-006 analysis prerequisites are missing. Returning only a low-level resolver error forces operators to discover the configuration sequence manually.

## Decision
Expose a read-only candidate-specific live workflow at `GET /api/v1/candidates/{candidate_id}/live-workflow`.

The workflow evaluates prerequisites in the approved semantic order and returns explicit `COMPLETE` or `BLOCKED` steps plus one machine-readable `next_action`. It does not create mappings, validate provider symbols, import market data, run analyses or change candidate state automatically.

When all steps are complete, `ready=true` and the existing automatic candidate evaluation endpoint remains the single write path.

A CLI helper, `scripts/top_down_guided_live.py`, presents the workflow and may invoke the existing auto-evaluation only when readiness is complete.

## Consequences
- Operator actions remain explicit and auditable.
- No provider or trading decision is inferred by the workflow.
- The same readiness semantics can later drive an administrative UI.
- Real EODHD credentials are still required for provider validation and live imports.
