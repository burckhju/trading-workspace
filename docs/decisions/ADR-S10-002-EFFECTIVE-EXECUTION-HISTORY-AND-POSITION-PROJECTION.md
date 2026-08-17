# ADR-S10-002 – Effective Execution History and Position Projection

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
FT-009 specified that Position is reproducible from effective execution history, but its released V1 implementation can incrementally apply additional purchases and does not yet expose full effectiveness/supersession querying. SELL and corrections make a single central projection contract necessary.

## Decision
Execution history is the authoritative economic history. Position is a deterministic projection from the effective BUY/SELL execution stream.

The persistence boundary must support loading the effective executions required for reconstruction. Projection ordering and tie handling must be explicit and deterministic.

A materialized Position may remain persisted for read efficiency, but after any command that changes effective execution history its values must equal a fresh projection from that history.

Correction handling rebuilds derived state from effective history rather than trying to reverse opaque prior mutations.

## Consequences
The implementation requires an execution-history query contract and a centralized Position projector. Existing FT-009 incremental purchase behavior must remain regression-equivalent.

Projection tests become a critical invariant test suite, including rebuild equivalence after BUY, SELL and correction sequences.

## User impact
Displayed quantity, cost basis and realized result remain trustworthy even after multiple purchases, partial sales or corrections.
