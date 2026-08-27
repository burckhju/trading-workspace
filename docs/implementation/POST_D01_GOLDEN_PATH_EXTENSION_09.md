# Post-D01 Golden Path Extension 09

## Purpose

Close the remaining controlled handoff gap between a qualified FT-011 ExitReviewVersion and FT-012-owned immutable LearningEvidence without introducing a new Golden Path orchestrator.

## Qualified path

`FT-011 ExitReviewVersion FINALIZED/CURRENT -> Ft012Handoff READY -> explicit FT-012 materialization command -> LearningEvidence(FT011) -> FT011Evidence provenance`

The slice ends at LearningEvidence. Existing Lesson and FT-013 governance seams remain separate and explicit.

## Ownership and trigger

FT-012 owns materialization because it owns the aggregate being created. Materialization is an explicit idempotent application command. It is not executed inside FT-011 ExitReview finalization, avoiding upstream/downstream transaction coupling. No REST endpoint or frontend control is required for this capability slice.

The command accepts only `workspace_id`, `trade_id`, and an `idempotency_key`. FT-011 technical provenance is resolved from the released `Ft012HandoffService`; callers do not reconstruct observation/review/version IDs.

## Invariants

- FT-011 remains source of truth for READY eligibility; FT-012 does not duplicate finalized/current/staleness rules.
- FT-012 does not read or mutate FT-011 persistence directly.
- Evidence is pinned to the exact `exit_review_version_id` returned by the qualified handoff.
- Historical evidence is not retargeted if another ExitReviewVersion later becomes current.
- Materialization is evidence transport, not interpretation; no Lesson or FT-013 artifact is created automatically.
- Same request key and fingerprint replays the original evidence result.
- Same source with a different idempotency key resolves to the existing semantic evidence.
- Semantic uniqueness is protected by the existing `uq_ft011_evidence_exit_review_version` database constraint.
- Parent LearningEvidence is flushed before FT011 provenance; provenance is flushed before idempotency SUCCESS is recorded.
- A database uniqueness race is translated to `MATERIALIZATION_CONFLICT` after rollback rather than leaking a raw `IntegrityError`.
- Workspace scope is enforced both by the FT-011 handoff and FT-012 evidence lookup.

## Persistence and migrations

No migration is required. The existing `learning_evidence`, `ft011_evidence`, and Learning idempotency schema already provides the necessary aggregate, source provenance, request idempotency and concrete-version uniqueness.

No historical backfill is performed.

## Implementation

Added:

- `MaterializeFt011LearningEvidenceService` as the FT-012 application command;
- `Ft011MaterializationRepository` / `SqlAlchemyFt011MaterializationRepository` as the FT-012 persistence port/adapter;
- focused unit coverage for deterministic fingerprints, happy-path provenance, same-key replay, same-source/different-key semantic deduplication, not-ready fail-closed behavior, and idempotency-key reuse.

The released FT-011 `Ft012HandoffService` remains unchanged.

## Non-scope

- automatic materialization during ExitReview finalization
- REST/API surface
- frontend controls or Learning dashboard
- automatic Lesson creation
- FT-013 hypothesis/proposal/model governance execution
- schema changes
- historical backfill
- broad revalidation workflow for superseded historical evidence
