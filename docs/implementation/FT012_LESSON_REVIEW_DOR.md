# FT-012 Lesson review / successor — Definition of Ready

2026-10-15. Base: PR #260 `37b6ed0ab45a30ea5a6b8f8111c9a5f3b76aacaa`.
Status owner: [PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).
This is an implementation slice, not human business acceptance or a release.

## Evidence / decision matrix before implementation

| Capability | Existing executable owner / consumer | Verified gap / slice decision |
|---|---|---|
| Observation / Exit Review | `post_trade/application/{observation,exit_review,handoff}_service.py`; PostTradeReviewPage | Retain ownership, gates and exact-version inspection; no new FT-011 writer. |
| Journal / journal evidence | `learning/application/journal_service.py`; TradeJournalPanel | PR #260 qualified; consume, do not rebuild. |
| Lesson creation | `LessonService.create_with_tags`; LessonDraftFromEvidence | Preserve explicit interpretation and complete transaction. |
| Lesson history / new version | `LessonService.create_new_version`; existing versions/history API | Version endpoint only flushes; no general editor/history selection. Provide explicit command boundary and consumer. |
| Contradiction review | `LessonReviewService`; review-signals API | Lower-level operations only flush. Keep CONTRADICTS triggers; stale SUPPORTS is not a contradiction. |
| Source-related review | existing state transitions and immutable evidence snapshots | Use explicit CURRENT → REVIEW_RECOMMENDED and explicit resolution, with user reason and exact version. No fabricated contradiction signal. |
| Source currentness | FT-011 exact-version inspector; journal source read | Read exact source and current inspection separately; no GET writes, no implicit Lesson state change. |
| Retry / concurrency | lesson row lock, version/state preconditions, FT-012 receipts | One owning application command, exact expected projection and signal ID, idempotent historical receipt, no blind retry. |

## V1 contract and testable acceptance criteria

1. User opens a source-related review of the displayed LessonVersion with a
   nonblank reason (at most 200 characters, matching the existing 255-character
   audit field plus action prefix), or selects concrete current CONTRADICTS links for the existing
   contradiction signal. Reading/refreshing never opens or resolves a review.
2. Review resolution explicitly confirms unchanged interpretation, retires the
   Lesson or creates a new version. User reason is audited in the existing state
   transition. NEW_VERSION requires explicit nonblank content/category and a full
   chosen evidence snapshot containing SUPPORTS; duplicate evidence IDs (including
   conflicting relations) are invalid. No old snapshot/link mutation.
3. Lesson state CURRENT means current interpretation, not current/tradable source
   data. Unchanged confirmation cannot repair a stale source. A source-related
   review never turns SUPPORTS into CONTRADICTS; existing open contradiction
   signals cannot be bypassed by the general version/state endpoints.
4. Every new UI command pins current LessonVersion/state and exact open signal
   (including no signal). Changed projection is 409. Retry of an identical successful
   command returns its original receipt without a new version/event. Same key with
   changed actor/input is 409. PostgreSQL concurrent transactions and commit failure
   must prove uniqueness/rollback/durable readback, not merely fake repositories.
5. Existing composable service operations stay uncommitted for composition; public
   version/state/review API commands obtain explicit application-owned commit
   boundaries. No success before commit, no global session auto-commit change.
6. UI has explicit preparation/confirmation/cancel, preserves text after failure,
   isolates navigation and late responses, synchronously locks double submit and
   distinguishes mutation success from readback failure. Old version views are
   read-only; replacement evidence is selected, never silently substituted.
7. Browser + PostgreSQL path extends actual synthetic capture → journal → Lesson
   through source correction → explicit Lesson review → selected Journal V2 evidence
   → Lesson V2, while old LessonVersion, evidence relations and audit remain unchanged.
   Unchanged confirmation and contradiction/retirement also receive tests.
8. Existing full backend/frontend/E2E gates and coverage thresholds stay unchanged.
   Tests only in identified disposable CI; no user .env, volumes, provider, scheduler,
   notification, activation, merge/tag/deployment or external import actions.

## Scope boundaries

No new model/hypothesis/suggestion generation. No journal lifecycle changes. No new
financial rules or performance prerequisites. No full-history knowledge assertion.
Currentness is as-of-read, not global source-write serializability. External journal
source currentness without an existing qualified reader remains explicitly UNKNOWN.
General RETIRED reactivation, title/tag editors, journal mobile acceptance and the
FT-011 materialization race remain separate. Existing M0–M11 references remain.
