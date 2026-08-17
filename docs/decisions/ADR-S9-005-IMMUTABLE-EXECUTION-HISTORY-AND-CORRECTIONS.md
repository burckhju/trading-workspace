# ADR-S9-005 – Immutable Execution History and Corrections

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
Confirmed ExecutionRecords are immutable. A factual correction must preserve the original record and establish a traceable replacement/correction relation. The current Position is derived from effective, non-superseded execution history.

Potential duplicates are warnings rather than hard business-key uniqueness constraints.

## Consequences
Historical recording mistakes remain auditable and genuine repeated purchases remain representable. The exact persistence form of the correction relation may be selected during implementation without weakening this invariant.

## User impact
The user can correct a mistaken entry without silently rewriting history and can still deliberately record two genuinely identical purchases.
