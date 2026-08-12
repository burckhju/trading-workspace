# S6-04 Implementation Report – FT-007 Repository / Unit-of-Work

## Status

Completed – 2026-08-11.

## Scope

Implemented FT-007 domain↔persistence mapping, repository contracts/adapters and SQLAlchemy Unit-of-Work integration. No REST API, frontend, product selection, position sizing, order quantity or execution behavior is part of this unit.

## Delivered

- Bidirectional mapping for durable `TradePlan` identities and immutable `TradePlanVersion` snapshots.
- Mapping of product-neutral Entry, Invalidation, RiskAssumptions and ordered Targets.
- `TradePlanRepository` with workspace-scoped lookup/listing and row locking of the durable plan identity.
- `TradePlanVersionRepository` with version-specific lookup, latest/list queries and target hydration.
- Serialized `next_version_number()` allocation using `SELECT ... FOR UPDATE` on the durable TradePlan identity before deriving `MAX(version)+1`.
- Append-only event repository access for version lifecycle/audit history.
- Version-specific approval repository access.
- `TradePlanUnitOfWork` / `SqlAlchemyTradePlanUnitOfWork` with flush, commit and rollback transaction boundaries.
- Unit tests for mapping round-trips, version allocation, repository helpers and transaction rollback behavior.

## Architecture Notes

- Candidate provenance remains on the durable TradePlan identity and is mapped without resolving a later/latest CandidateEvaluation.
- TradePlanVersion hydration always reconstructs ordered Target value objects before domain validation.
- Amendment version allocation is serialized by locking the durable TradePlan row. Writers must perform allocation and insert within the same Unit-of-Work transaction; the existing database unique constraint remains the final integrity guard.
- Approval and event history stay separate from immutable content snapshots.
- The repository layer introduces no product/Warrant fields and no market/candidate recalculation.

## Quality Gates

- `python -m pytest ../tests/unit/backend/features/trade_plan ../tests/unit/backend/features/candidate/test_candidate_repository.py -q` – 17 passed.
- `python -m compileall -q backend/app/features/trade_plan` – passed.
- Ruff could not be executed in the current runtime because the Ruff module/binary is not installed in the available Python environment. No Ruff result is claimed for this unit.

## Next Unit

S6-05 – TradePlan Application Service: creation, candidate/manual origin validation, version creation/amendment orchestration, lifecycle commands and explicit approval using the S6-04 Unit-of-Work boundary.
