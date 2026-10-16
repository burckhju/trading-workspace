# ADR-POST-FT012-007 — Source-stable FT011 materialization and historical inventory

Date: 2026-10-16. Implementation decision for technical review; no human domain
acceptance asserted. Status owner: [PB-019 Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization).
DoR fixed before changes: [FT011 consistency DoR](../implementation/FT011_MATERIALIZATION_CONSISTENCY_DOR.md).
Extends [ADR-POST-FT012-004](ADR-POST-FT012-004-FT011-EVIDENCE-MATERIALIZATION-OWNERSHIP.md),
not a new ownership system. M0–M11 and the released observation/session rules remain unchanged.

## Context and decision

A pinned review ID plus an idempotency record prevents duplicate or misconfirmed
materialization, but does not freeze inputs between the readiness read and commit.
The current-status endpoint intentionally describes today's handoff, not the
inventory of past handoffs. Returning false there must not hide historical evidence.

FT-012 retains its existing command, unit of work, receipt and Evidence writes.
FT-011 supplies `InspectedFt012HandoffService` with a transaction-scoped source
guard. The production dependency uses **the same AsyncSession** for guard, FT-011
read-only inspection and FT-012 commit. The guard commits nothing. Existing
successful historical receipts are resolved before the guard and are never
re-certified as current. Legacy bodyless commands retain their old fingerprints.

The guard takes native PostgreSQL `FOR UPDATE NOWAIT` row locks on the selected
workspace/trade; existing execution, position and management children; observation,
review and review versions; the exact historical plan version and targets; and the
pinned underlying listing plus all stored daily prices for that listing. Parent
locks cooperate with existing child foreign-key checks: a missing early daily
price inserted after validation must also wait. Existing-child locks protect
non-key updates and deletes. Locking only the 20 returned rows would not protect
an earlier-date insert or movement of a previously out-of-range trading date.

All acquisitions are NOWAIT: an existing source writer produces 409 `SOURCE_BUSY`
and full rollback. No retry is automatic. SQLSTATE 55P03, 40P01 and 40001 map to
this recoverable conflict; other database errors are not silently relabelled.
Native PostgreSQL row-lock semantics are the technical basis, not a new business
threshold: [PostgreSQL 17 explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html).
No table-wide lock, new trigger, provider call or migration is added.

After acquiring the guard, FT-011 first applies the existing completed/finalized/
stored-current gate, then compares the selected version's existing fingerprint
against its actual current inputs through the released owner inspector. A prior
committed correction is rejected even if nobody has explicitly persisted STALE.
Inspection does not revalidate or mutate a final review. The guard remains held
until the FT-012 commit/rollback. A waiting writer may then commit a **later**
correction; the original receipt and source links remain historical facts.

The consistency guarantee is limited to the evidenced input graph under existing
foreign keys and supported owners. Disabling constraints/triggers, arbitrary
administrator SQL or schema DDL is not a supported business correction. Short
materializations of different trades on the **same listing** may conflict. All
listing price rows are locked because range gaps are relevant; large histories
can increase lock footprint/latency and need separate load qualification. No
future/global CURRENT guarantee is made.

## Read contract

`GET /api/v1/learning/trades/{trade_id}/ft011-evidence/history` returns FT-012's
historical inventory independently of current readiness. No observation, receipt,
review, lesson or model is written by the read. The existing status endpoint retains
its response shape; its injected FT-011 reader also inspects the actual inputs.

Each inventory entry contains Evidence ID/type/materialized_at; exact trade,
observation, review and review-version IDs; review ordinal/status and **stored**
currentness; a separate FT-011 source inspection/checked_at; and explicit later
review-version identity when superseded. Missing/unqualified source provenance
is UNKNOWN, never CURRENT. `checked_at` is the completion time of that source
inspection, not historical data availability or a whole-list snapshot timestamp.
The inventory is as-of-read, not the atomic command's source-stability certificate.

Every saved LessonEvidenceLink is read with its exact LessonVersion, link ID and
SUPPORTS/CONTRADICTS/CONTEXTUAL relation, including noncurrent versions. The display
title is the current Lesson root title, not a fabricated frozen historical title.
A later relation never replaces an older relation. Links include
`lesson_version_id` and open the existing read-only history selection; unknown
version IDs yield an explicit not-found state, not silent latest fallback. The
current Lesson summary is labelled separately. Reads never open a review.

## Consumer and verification boundary

The existing PostTradeLearningPage renders the independent inventory even when
status is NOT_READY or status loading fails. Loading, empty, failed and outdated
responses stay distinct. A single width-constrained page wrapper makes the existing
sections readable in the application's flex container; no second dashboard/router
or global lesson owner is introduced. The journal writing gate is unchanged.

Coordinated PostgreSQL tests assert actual blocked backend PIDs for execution,
new review, stale metadata, daily UPDATE/DELETE and phantom INSERT, together with
correction-first rejection, same/different-key replay, rollback and exact historical
relations. A real synthetic capture/browser journey keeps old evidence accessible
after correction and selects its original LessonVersion after a successor exists.
Fakes do not establish native lock behavior. Test source presence is not a successful
run; completed results and exact checkouts are recorded in the qualification report
and PR. No PC deployment or human acceptance follows from this decision.
