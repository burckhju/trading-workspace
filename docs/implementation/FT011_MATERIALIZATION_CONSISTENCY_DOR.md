# FT-011 → FT-012: atomic handoff and historical evidence inventory

2026-10-16. Status authority: [PB-019 materialization](../planning/PRODUCT_BACKLOG.md#pb-019-materialization).
Baseline: `3faf0f768b23c719cb16239280a2c9875d9ae451` / v1.5.7,
complete source tree `8e30df4fcfe48f2b9579da86202d27802643b6de`.
This is a bounded continuation, not a new FT, journal, lesson or financial owner.

## Evidence before changes

| Capability | Existing owner / consumer / tests | Verified gap / decision |
|---|---|---|
| Observation | FT-011 ObservationService, PostTradeReviewPage; observation and journal PostgreSQL tests | Retain actual economic full exit, pinned listing and 20 real post-exit EOD observations. No missing-price repair in this slice. |
| Exit Review | FT-011 ExitReviewService and Ft012HandoffService; finalized version/fingerprint/currentness tests | Reuse exact-version read-only input inspection. A stored CURRENT flag alone is insufficient after an un-revalidated correction. |
| Journal | FT-012 JournalService / TradeJournalPanel; qualified #260 | Existing lifecycle unchanged, no new Performance gate. |
| Evidence command | FT-012 MaterializeFt011LearningEvidenceService; pin/idempotency/schema/independent-transaction tests | Existing source check precedes commit without a source stability boundary. Close that interval, not just duplicate POSTs. |
| Evidence inventory | FT-012 status service returns false/no ID when FT-011 is NOT_READY | Retain legacy current-status semantics; add independent historical inventory, never infer nonexistence from readiness. |
| Lesson creation/review | FT-012 explicit commands/versions/relations; qualified #261 | Read exact historical links, no automatic link changes or review actions. |
| Traceability | FT011Evidence pins Trade/Observation/Review/Version; LessonEvidenceLink pins LessonVersion/relation | Keep all identities and source check time, stored status and supersession distinct. |
| Operation | User supplied v1.5.7 installation/0046/healthy-container output | No write tests, provider requests, deployment or migration on JMBbot. New slice requires separate qualification. |

The older Golden Path closeout's missing materialization was superseded by
Extension 09/ADR-POST-FT012-004 and #259. The outstanding race/inventory statements
in the later Journal/Lesson qualification reports remain correct at this baseline.

## Contract and smallest connected implementation

FT-012 still owns the explicit command and its commit/rollback/idempotency record.
FT-011 supplies a transaction-scoped guarded handoff: acquire existing PostgreSQL
row locks, then run the released handoff gate and exact fingerprint inspection in
that same request session. Hold locks until the FT-012 transaction ends. No owner
writes are moved into FT-012 and no review is revalidated as a side effect.

Lock scope is the selected trade and its execution/position/management rows,
observation/review/version aggregate, exact historical plan version/targets (when
present), and the observation's pinned listing and all its stored daily prices.
Exclusive parent locks also block child INSERTs through existing foreign keys;
locking existing children alone would miss an earlier-date backfill. Every lock
attempt is NOWAIT, with a retryable SOURCE_BUSY conflict and full rollback rather
than deadlock-prone waiting. Unrelated listings/trades are not table-locked.
Native row/FK locks must be proved on real PostgreSQL, not inferred from fakes.

A correction already committed before acquisition is inspected and prevents new
materialization from the outdated version. A writer starting after acquisition
may proceed after materialization commits; that is a later correction, not a
retroactive invalidation of the historical receipt. Successful old retries return
the old receipt without requiring a currently eligible source. No global/future
CURRENT guarantee, no autonomous retry. Bodyless legacy requests remain supported.

Historical inventory is independent of current readiness. Each entry retains
FT011 type, materialization time, exact source IDs, review version number/status,
stored CURRENT/STALE, separate current fingerprint inspection with checked_at,
and explicit superseding version ID. Missing/unqualified provenance is UNKNOWN.
Historical LessonVersion links retain link ID, exact version and relation, even
when the current LessonVersion no longer uses that evidence. Read-only detail
navigation must not silently substitute current/latest for an old link.

## Acceptance fixed before implementation

- C1: Suitable finalized current source creates one Evidence with exact provenance;
  mismatched version, incomplete horizon, stale/unqualified source fail closed.
- C2: Coordinated real PostgreSQL races cover execution correction, review
  supersession/currentness update, price UPDATE/DELETE and earlier-date INSERT.
  Existing correction blocks acquisition or is observed; later correction waits
  until commit. No orphan Evidence/receipt on conflict or commit failure.
- C3: Same/different key retries preserve semantic uniqueness; successful historical
  replay stays stable after correction/supersession. No new Lesson/model is created.
- C4: Inventory returns all and only the trade/workspace's historical evidence at
  NOT_READY and after a newer review; every version/relationship remains unchanged.
- C5: UI independently shows history when status is not ready or fails, and separates
  loading/empty/error/stale responses across trade navigation. Explicit retry only.
- C6: Real browser/PG capture→observation→review→FT011 Evidence→Lesson→correction
  keeps the old evidence discoverable and its exact old LessonVersion accessible;
  a new review/evidence never retargets the old source or old lesson links.
- C7: Existing backend/frontend/E2E gates unchanged; PostgreSQL migration head and
  source trees rechecked; no release/PC update claimed by a development merge.

## Boundaries and delivery

No new migration is planned; existing foreign keys are part of the lock contract.
No table-wide price lock, new provider, data import, calendar synthesis, score,
performance calculation, journal timing change, automatic Lesson/revalidation or
model activation. Deleting data/constraints with an administrator bypass is not a
supported concurrent business command. Original M0–M11 scope is not relabelled done.
The global journal/lesson dashboard and the known navigation/data-feed issues are
independent. Only the combined page's wrapper may change as needed to make the
inventory readable without introducing another navigation system.

## Qualification finding, 2026-10-16 (before readback correction)

The first real browser run 38954345066 reached materialized FT011 Evidence but
received HTTP 500 from the existing `learning-evidence/{id}/lessons` GET. The
original DISTINCT query ordered by Lesson.updated_at without selecting it, which
PostgreSQL rejects even for an empty result. Fix only this query projection, not
the response contract, relation semantics or the new browser assertions. Add real
PostgreSQL coverage for empty and populated references and deduplication after
multiple LessonVersions reference the same Evidence. The original browser
failure stays a failed run. Requalify the exact corrected code/tree.

## Visual qualification finding, 2026-10-16 (before reader unification)

The corrected real browser journey passed twice in run 38955904535. Visual
inspection nevertheless found the legacy FT-011 Handoff card still saying READY
after correction, while the materialization status and independent inventory
correctly said NOT_READY/STALE. Its public GET must use the same FT-011 inspected
reader as the materialization status, without mutating the stored review. Keep
the journal command's existing gate/composition unchanged. Add explicit real PG
and browser assertions that both public read surfaces reject the outdated source,
while old Evidence remains discoverable. No frontend currentness calculation.

## Executed qualification reference

The [separate result report](FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md)
records the common executed source commit, native PostgreSQL lock/rollback proof,
real browser history navigation, complete gates and exact operational limits.
These results do not change the pre-implementation criteria above or turn failed
intermediate runs into successes. PB-019 is the only task-status authority.
