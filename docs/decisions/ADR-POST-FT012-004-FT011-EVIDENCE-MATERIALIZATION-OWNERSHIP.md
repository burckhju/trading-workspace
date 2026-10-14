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

## Proposed additive confirmation refinement — 2026-10-14

This section describes the bounded patch based on repository commit
`f918194150636f03faab466a6e41a4b67b2841dc`. It does not change the historical
Accepted decision into a new approval. Full technical review, PostgreSQL/browser
qualification and business acceptance of this extension remain outstanding.
See [scope, evidence and limitations](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md).
The [central materialization entry](../planning/PRODUCT_BACKLOG.md#pb-019-materialization)
remains the status authority.

First-party UI confirmation includes `expected_exit_review_version_id` for the
version actually shown. FT-012 compares this precondition with the qualified
FT-011 handoff before new evidence writes. A mismatch returns
`409 SOURCE_VERSION_MISMATCH`; it does not retarget the user's action to latest.
FT-011 still owns readiness and currentness. This check is not an atomic lock
against a concurrent upstream correction after the handoff read.

The new field is part of the idempotency fingerprint when supplied. Historical
bodyless requests keep their original fingerprints and semantics. An explicit
request body must contain a valid UUID; malformed or empty objects do not silently
fall back to the legacy path. First-party callers use the separate
`ft011-to-ft012:v2:<trade-id>:<review-version-id>` key namespace, so old successful
keys are not reinterpreted as pinned requests. Bodyless legacy clients still do
not confirm a previously displayed source version.

A successful replay returns the original evidence, including after that source
becomes stale. It is a historical receipt, not a new readiness/currentness
assessment. The UI reads owner status again after success, failure or replay and
does not synthesize READY/CURRENT from a command response. Current handoff status
is not an inventory of previously materialized historical evidence.

No migration, backfill, automatic Lesson, journal finalization, performance
calculation or model activation is introduced. The separate journal contract and
write path remain open; this amendment does not declare FT-012 complete.
