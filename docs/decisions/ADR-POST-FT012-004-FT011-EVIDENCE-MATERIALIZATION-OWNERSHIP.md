# ADR POST-FT012-004 – FT-011 Evidence Materialization Ownership

## Status
Accepted

## Context
FT-011 already owns the post-trade lifecycle and exposes a released FT-012 handoff gate. FT-012 already owns immutable `LearningEvidence` and the source-specific `FT011Evidence` provenance. The missing capability is the controlled materialization of a qualified FT-011 source into that FT-012 aggregate.

Automatically writing FT-012 data while finalizing an FT-011 ExitReview would couple the upstream finalization transaction to downstream Learning availability and failure modes.

## Decision
- FT-012 owns FT-011 LearningEvidence materialization because it owns the aggregate being created.
- Materialization is an explicit idempotent FT-012 application command, not an implicit side effect of ExitReview finalization.
- The command reads FT-011 exclusively through the released `Ft012HandoffService` application contract; FT-012 does not use FT-011 repositories, ORM models or tables as a domain contract.
- Command input is the low-input identity `workspace_id + trade_id + idempotency_key`; technical provenance IDs are resolved from the qualified handoff.
- Request idempotency is separate from semantic source identity. Semantic uniqueness remains the concrete `exit_review_version_id`, already protected by `uq_ft011_evidence_exit_review_version`.
- Successful evidence remains pinned to the exact materialized ExitReviewVersion even if a later version supersedes it.
- Materialization creates no Lesson, Hypothesis, proposal, validation or ModelVersion.
- No REST endpoint or frontend action is introduced by this slice. The application command may later be invoked by a user-facing or automated workflow without changing ownership.
- No migration or backfill is introduced because the existing FT-012 schema already represents the required immutable provenance and uniqueness invariant.

## Consequences
FT-011 finalization remains independent of FT-012 persistence failures. READY means materializable, not already materialized. Retries are safe, different idempotency keys cannot create semantic duplicates, and downstream interpretation remains explicitly user/governance controlled.
