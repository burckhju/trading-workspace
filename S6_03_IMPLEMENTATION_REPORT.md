# S6-03 Implementation Report – FT-007 Persistence + Migration

## Status

Completed – 2026-08-11.

## Scope

Implemented FT-007 SQLAlchemy persistence and Alembic schema only. No repository/application service, REST API, frontend, or product-selection behavior is part of this unit.

## Delivered

- `trade_plans` as durable identity with workspace, underlying and MANUAL vs CANDIDATE_EVALUATION provenance.
- Database-level origin consistency constraint for candidate/candidate-evaluation references.
- `trade_plan_versions` with unique `(trade_plan_id, version)`, LONG-only check, immutable content fields, predecessor reference and amendment reason.
- Product-neutral flattened Entry, Invalidation and Risk-Assumption persistence.
- `trade_plan_targets` as ordered version-owned target rows.
- Append-only `trade_plan_events` for lifecycle/audit history including actor, timestamp and correlation identity.
- Append-only `trade_plan_approvals` with one explicit approval proof per concrete TradePlanVersion.
- Alembic revision `20260811_0008` based on `20260810_0007`.
- Alembic metadata registration for TradePlan while preserving existing feature-model registrations.
- Persistence and migration tests, including product-neutrality guardrails.

## Architecture Notes

- Candidate-originated plans reference the concrete immutable `candidate_evaluations.id`; no `latest evaluation` lookup is encoded in persistence.
- Warrant/product attributes, position size, order quantity and execution fields are absent by design.
- Approval proof is not reduced to a status flag: the dedicated approval row persists version, actor, timestamp and correlation id.
- Lifecycle status is stored on the version for current-state queries; append-only events preserve transition history. Snapshot content fields are not redesigned as mutable workflow state.

## Quality Gates

- Ruff check for TradePlan persistence, migration, migration environment and TradePlan tests – passed.
- `PYTHONPATH=backend python -m pytest -q tests/unit/backend/features/trade_plan` – 9 passed.
- Existing migration-model imports were preserved in `migrations/env.py` to avoid metadata-regression during autogeneration.

## Next Unit

S6-04 – Repository / Unit-of-Work persistence access and domain↔persistence mapping, including version allocation and provenance-safe queries.
