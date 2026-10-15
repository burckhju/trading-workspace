# ADR-POST-FT012-006 — Explicit source review and immutable Lesson successors

2026-10-15. Implementation decision for the authorized FT-012 slice, not a human
business approval. [DoR](../implementation/FT012_LESSON_REVIEW_DOR.md) and
[PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons) own scope/status.

## Decision

Reuse Lesson, LessonVersion, LessonEvidenceLink, LessonStateTransition,
LessonReviewSignal and the existing FT-012 UOW/receipts. No new Review object or
parallel status truth. The new application command composes the existing service
operations and owns its whole transaction. Legacy version/state/review API entry
points get named transaction-owning wrappers; lower-level composition still only
flushes. Lock and compare the precise Lesson projection before a new write.

A user-requested source review records CURRENT → REVIEW_RECOMMENDED with the exact
LessonVersion and a nonblank user reason. This is not a LessonReviewSignal: that
existing object requires current CONTRADICTS links. Source staleness is not evidence
of contradiction. Source review pins and verifies the complete current evidence snapshot,
not an implicit subset. The transition pins that exact LessonVersion; its reason
contains the user note (maximum 200 characters to fit the existing audit field). Contradiction review keeps its
exact trigger links and signal lifecycle. General endpoints cannot strand/bypass an
open signal. RETIRED Lessons cannot open a new review in this slice.

Explicit unchanged confirmation and retirement record the user's reason. An explicit
successor contains the complete user-selected snapshot of unique evidence IDs and
relations plus nonblank interpretation/category. At least one SUPPORTS link remains
required. Old versions/links are not mutated or rebound. A version can intentionally
retain historical evidence, but source age/currentness remains visible and is not
made CURRENT by an interpretation decision. Evidence types and versions are not
interchangeable; no latest-source substitution occurs.

A receipt is the original command result identity, not a present-currentness promise.
Idempotency fingerprint includes workspace, lesson, actor, expected version/state/
signal, reason, interpretation and exact chosen evidence/trigger IDs. A retry does
not auto-rebase or generate a new version. Source checks are read-time observations,
not an execution decision or a guarantee against all concurrent upstream changes.

## Persistence and compatibility

No new schema required: existing state-transition reasons carry user review reasons,
related_lesson_version_id pins the interpretation, and existing idempotency records
carry command fingerprints/results. Existing contradiction-resolution enums remain.
Read APIs expose history, state-transition audit and exact source inspection. Missing
legacy source is UNKNOWN, not CURRENT or zero. Journal currentness distinguishes
later finalized journal versions from review-input staleness and in-progress drafts.

Historical content immutability here is enforced by using append-only version/link
writers and tested no-mutation snapshots. This slice does not claim a new database
trigger protecting every pre-existing FT-012 table from arbitrary administrative SQL.
No change to runtime model/hypothesis/approval/activation or financial facts.

## Additive API / consumer contract

- GET `/api/v1/learning/lessons/{lesson_id}/review-context`: exact Lesson projection,
  immutable history ordered by descending version, contradiction signals/triggers,
  state-transition audit and read time. No review is opened by reading.
- GET `/api/v1/learning/learning-evidence/{evidence_id}/currentness`: exact typed
  source-version ID, source lineage currentness, separately inspected FT-011 review
  currentness for journals, optional known successor ID and inspection time. CURRENT
  never proves data completeness, market validity or knowledge at trade time.
- POST `/api/v1/learning/lessons/{lesson_id}/review-commands`: required
  Idempotency-Key, `confirmed=true`, exact expected version/state/open-signal ID
  (including explicit null), reason and the operation-specific fields. A successful
  response returns the immutable receipt identity; a subsequent context GET is a
  separate read. Incompatible fields/identity injection are 422, changed pins/key
  content are 409, missing workspace-owned sources are 404. No blind retry.

Existing public version/state/contradiction endpoints preserve payloads and result
shapes but now finish a transaction. Existing composable lower-level methods still
only flush. Generic version/state endpoints reject an open contradiction signal;
only its proper resolution may advance the projection. Retired reactivation and
mutable title/tag commands remain outside this UI slice.

## 2026-10-16 qualification clarification

Explicit label/control associations identify relation selects independently of
option text. A stable request-generation counter is captured by the effect
cleanup; StrictMode and late-read regression coverage preserve this contract.
FT-011 readback of the same draft does not discard unsaved text/assessments.
Successful writes or a genuinely different/finalized owner version rehydrate the
form. This local draft flag makes no readiness/currentness decision and writes no
review itself. The normal PR merge is user-authorized only after green checks;
release, target installation and human domain acceptance remain separate.
