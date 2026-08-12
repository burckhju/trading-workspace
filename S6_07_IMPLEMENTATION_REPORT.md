# S6-07 Implementation Report — Lifecycle + Approval Hardening

## Scope

Hardening of FT-007 TradePlan lifecycle and approval behavior. No REST or frontend changes.

## Implemented

- Approval is idempotent for an already `APPROVED` version when its immutable approval record exists; retries do not create duplicate status writes, approval rows, audit events, or commits.
- Approval fails closed when persistence state is inconsistent:
  - `APPROVED` status without approval record.
  - approval record present while version is not `APPROVED`.
- Only the latest TradePlan version may be approved.
- Approval fails closed if more than one previously active `APPROVED` version is detected instead of silently choosing one.
- Amendment locks the durable TradePlan identity before loading/validating its approved base version, strengthening serialization against concurrent lifecycle/approval operations.
- Existing plan-identity lock remains the serialization boundary for lifecycle transitions and approvals.

## Invariants preserved

- Historical approved versions remain immutable.
- Supersede is performed only as part of successful approval of a newer version.
- Approval remains an explicit user action tied to an exact version, actor, timestamp and correlation id.
- Product neutrality and LONG-only V1 remain unchanged.
- No Position Sizing, Order Quantity, Execution, Warrant, Issuer or Product Selection behavior introduced.

## Tests

Focused lifecycle/application/domain/repository/query suite: 24 passed.
Full backend unit regression suite: passed.
`compileall`: passed.

## Next unit

S6-08 — Amendment / Versioning hardening and integration semantics, including lineage consistency and version-chain validation before exposing mutation commands through REST.
