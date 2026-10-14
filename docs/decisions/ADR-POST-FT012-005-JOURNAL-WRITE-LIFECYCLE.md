# ADR-POST-FT012-005 — Explicit journal snapshots and source provenance

Date: 2026-10-14. Implementation decision for the authorized V1 slice; technical
qualification is reported separately, no human domain approval asserted.
Status remains in [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal).

## Context

The existing FT-012 TradeJournal/TradeJournalVersion model and evidence type have
no end-to-end writer in the verified PR #259 source tree. Empty final versions
are valid in that model. FT-011 already owns the review gate; FT-012 owns personal
reflection. The existing TradePlan hard-delete traverses both histories.

## Decision

Use the existing FT-012 persistence and UOW. Commands are CREATE_DRAFT, SAVE_DRAFT,
FINALIZE, REBIND_SOURCE and MATERIALIZE, never automatic. Creating a first or
successor draft and finalizing retain the existing FT-011 suitable-review gate;
editing an existing draft does not gain a new Performance/completion dependency.
All three existing text fields remain optional. An empty final is visibly empty,
not a Lesson, assessment or inferred interpretation. No scores or financial
calculations are added.

A journal has one draft at most. `edit_revision` is a mandatory optimistic
precondition on draft mutations. Every command uses FT-012 idempotency records,
including actor and exact input in its fingerprint. Its receipt identifies the
result; it is not an immutable copy of a draft's then-current content. Clients
read the saved state separately, preserve local text on failure and do not retry
mutations automatically.

Finalization freezes exactly the saved text, audit, predecessor and concrete
`source_exit_review_version_id`. It does not materialize evidence or create a
Lesson. A correction starts an explicit increasing successor draft from the last
final. Rebinding a draft's review source is explicit and revision-checked. Legacy
source remains NULL/UNKNOWN; a migration never substitutes latest review data.

FT-011's new non-writing exact-version inspection checks its own fingerprint
against present inputs. This is separate from its existing stored CURRENT/STALE
and explicit revalidation contracts. Journal readback exposes the check time and
source result; it never rewrites a review, journal or Lesson. A successor draft
and an outdated source are distinct from immutable historical contents.

A finalized journal can be explicitly materialized with the existing
TRADE_JOURNAL_VERSION source, even when historic/stale: it proves what the user
wrote, not that the old review is currently valid or that its opinion is true.
Source ID/type/relation must stay visible. Lesson creation still requires explicit
interpretation and existing supporting evidence rules; no hypothesis, approval or
runtime model action follows automatically.

## Consistency and retention

Application commands use the existing actual-trade lock, shared with execution
writers; journal revision comparison and existing semantic unique constraints
remain authoritative. PostgreSQL additionally rejects any change/deletion of a
final version, journal identity reassignment, wrong-trade review binding and
mutation of a materialized journal source. The TradePlan hard-delete rejects
finalized journal histories with JOURNAL_HISTORY_PROTECTED before dependent
writes. Draft deletion through that already existing consumer is retained and
ordered before the new review reference. No new journal DELETE endpoint.

This is not global serializability against every concurrent market-data or
review write. Present source inspection is as-of-read and may later turn stale;
historical sources are never silently rebound. The broader FT-011 materialization
race after source read remains a separate requirement.

## Migration / acceptance boundary

Revision 20261014_0046 extends 20261012_0045 additively with revision=1 and nullable
source for legacy rows. No retroactive timestamp/source fabrication, no activation.
Downgrade refuses new provenance/revisions and otherwise removes protections;
it is not a lossless rollback. Use a verified backup for operational rollback.

The [DoR and acceptance criteria](../implementation/FT012_JOURNAL_WRITE_DOR.md)
and separately recorded PostgreSQL/browser/full-gate results define the technical
scope. External-observation journals, a general Lesson review editor and model
optimization are not substitutes for or additions to this slice.


## Qualification refinement: explicit review correction UI

The journal correction journey exposed an existing FT-011 consumer gap: the
backend permits an explicit successor draft, but the finalized-review UI did not
offer it. The existing `createReviewDraft` command is now reachable as
"Neue Review-Version vorbereiten". An explicit currentness check is available
for finalized CURRENT sources as well as the existing STALE check. No UI flag
creates a review automatically or decides that correction is required. Owner
validation, immutable previous reviews and separate finalization are retained.
The real browser acceptance additionally exercises review correction followed by
a saved/finalized JournalVersion 2, while Version 1 and its Lesson stay unchanged.
