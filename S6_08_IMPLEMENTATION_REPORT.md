# S6-08 Implementation Report — Amendment / Versioning Hardening

## Scope

Hardening of FT-007 TradePlan amendment lineage and version invariants. No REST or frontend changes.

## Implemented

- Initial `TradePlanVersion` (`version == 1`) must not reference a previous version and must not carry an amendment reason.
- Every later `TradePlanVersion` requires an explicit `previous_version_id`.
- Every later version requires a non-blank `change_reason`.
- A version cannot reference itself as its predecessor.
- Amendment orchestration verifies that the newly allocated monotonically increasing version number is strictly greater than the approved base version number.
- Existing durable TradePlan identity locking remains the serialization boundary for version allocation and amendments.

## Invariants preserved

- Approved snapshots are never edited in place.
- Amendments create new immutable `DRAFT` snapshots.
- CandidateEvaluation provenance remains attached to the durable TradePlan origin and is not recalculated or replaced.
- Product neutrality and LONG-only V1 remain unchanged.
- No Position Sizing, Order Quantity, Execution, Warrant, Issuer or Product Selection behavior introduced.

## Tests

Focused TradePlan domain/application/repository/mapping/query/UoW suite: 31 passed.
Full backend unit regression suite: 266 passed.
`compileall`: passed.

## Next unit

S6-09 — REST API: expose TradePlan create/read/version/lifecycle/approval/amendment commands using the existing REST error, DTO, dependency-injection and actor/correlation patterns.
