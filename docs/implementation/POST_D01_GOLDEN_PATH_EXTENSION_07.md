# Post-D01 Golden Path Extension 07

## Purpose

Qualify the released FT-012 consumer seam after Extension 06: finalized FT-011 evidence can be represented as immutable FT-012 `LearningEvidence` and consumed as supporting evidence by a current LessonVersion without rewriting historical post-trade provenance.

## Qualified path

`FT-011 finalized ExitReviewVersion -> LearningEvidence(type=FT011) -> FT011Evidence provenance -> Lesson V1/CURRENT -> SUPPORTS evidence link`

## Invariants

- FT-012 evidence keeps the exact `trade_id`, `post_trade_observation_id`, `exit_review_id`, and `exit_review_version_id` from the finalized FT-011 source.
- Lesson creation requires evidence and at least one `SUPPORTS` relation.
- The LessonVersion binds the immutable `learning_evidence_id`; later FT-011 activity cannot retarget the historical link.
- Learning evidence remains queryable by workspace and evidence id.

## Important architecture boundary

The current released FT-012 application surface exposes query and consumption contracts for `LearningEvidenceType.FT011`, but no automatic FT-011-to-FT-012 materialization command/service is introduced by this slice. This extension therefore qualifies the existing consumer handoff and records automated materialization as a separate capability gap rather than inventing orchestration.

## Non-scope

- automatic FT-011 evidence materialization
- lesson suggestion automation
- FT-013 model governance
- runtime model activation
- production logic or schema changes

## Implementation

Added `tests/integration/backend/test_ft012_learning_handoff.py`.

No production code or migration is changed by this slice.
