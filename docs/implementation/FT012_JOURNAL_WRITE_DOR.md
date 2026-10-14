# FT-012 Journal write slice — V1 contract / Definition of Ready

Status: implementation contract for the user-authorized continuation of 2026-10-14;
not human business approval, release or deployment. Task status remains exclusively
[PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal).
Base: PR #259 head `818d1d800f02bfe7478cefa89073643d655b7413`, tree
`3ee2a3fbdd94f9421942fd2e1733954b007ba469`; main remains v1.5.6.

## Evidence and decisions before implementation

TradeJournal/TradeJournalVersion, their mapping, constraints and the
TRADE_JOURNAL_VERSION evidence type exist in `learning`. No journal repository,
application writer, registered write API or editor exists in this complete tree.
FT-011 readiness stays owned by `post_trade`. ADR-S11-007 supplies the regular
COMPLETED / FINALIZED / CURRENT handoff. No Performance dependency is introduced.
The older Golden Path closeout's materialization gap is superseded by Extension 09
and PR #259. Empty `journal` directories are not implementation owners.

All three existing reflection texts remain optional, including on finalization.
An empty final is explicitly labelled empty; it is not an inferred assessment or
Lesson. Requiring a non-empty reflection would be a separate business decision.
No scores, financial metrics, new instruments or external imports are introduced.

## Lifecycle and API acceptance criteria

1. GET history is non-writing and returns original immutable versions even when
   the current handoff is not ready. Missing journal and failed read are distinct.
2. Explicit first draft requires an eligible actual fully closed trade and the
   existing FT-011 gate, plus the exact displayed review version. No journal or
   evidence is created by GET or by review completion. One journal per trade,
   at most one open draft; competing first/successor creation has one winner.
3. Save replaces only the three optional texts on the specified draft. Expected
   edit revision is mandatory; save/finalize/source-rebind are optimistic commands.
   A stale tab cannot silently overwrite. Saving an existing draft is allowed
   while its review becomes stale; finalization requires a suitable source again.
4. Finalization confirms the *saved* content and source version, not unsaved form
   state, not performance completeness, and not the truth of the interpretation.
   It makes no Lesson or Evidence automatically. ID, version number, source, texts,
   audit and predecessor become immutable. DB rejects update/delete of finals.
5. A later correction explicitly creates a new draft from the last final, with
   a new ID and increasing version, original text as a visible starting copy and
   `supersedes_version_id`. Existing draft is edited instead of replaced. Source
   rebind is explicit and changes only a draft; no implicit `latest` substitution.
6. All commands use FT-012 idempotency records. Retry returns an original receipt,
   then UI reads current state; it never pretends a mutable draft receipt is a
   historic content snapshot. Different request or actor with reused key: 409.
7. Explicit materialization refers to one *finalized* journal version using the
   existing evidence table/type and unique source constraint. Historical/stale
   journal statements remain materializable as historical personal reflection,
   not as current review approval. Replay/different keys never duplicate source.
   Relation and personal Lesson interpretation remain separate user inputs/actions.
8. GET detail exposes journal supersession separately from owner-assessed review
   source currentness. UNKNOWN legacy source is not filled with latest. Owner
   inspection reads current input fingerprint without silently refreshing stored
   review status. Check time is not observation time or historic knowledge.
9. No journal DELETE command is invented. Existing TradePlan hard-delete must
   reject finalized journal history *before* deleting dependencies, return 409,
   and roll back failures. Draft dependencies keep their previous delete behavior.
10. Positive, empty, validation, cross-workspace, lost-response, concurrency,
    rollback and provenance tests; actual disposable PostgreSQL migration and
    browser journey. Full existing gates remain unchanged.

## Implementation/transaction boundaries

FT-012 extends its existing domain/persistence/UOW/API. Additive migration adds a
review-version reference and integer edit revision (legacy defaults 1/null), no
invented historical source or timestamps. Final-content guard and same-journal /
same-trade-source validation live in PostgreSQL as well as commands. Commands
lock the actual trade before the journal; existing execution writers use the same
trade lock. Review currentness inspection is implemented by FT-011, not the UI.
No promise of serializability against every concurrent TC-001 price update is made;
inspection is an as-of-read assessment, and later reads can become stale.

Downgrade refuses while new source-bound/revisioned journal data exists; otherwise
it removes newly added protections. It is not lossless / safe runtime rollback.
No stamp, destructive user-volume operation, scheduler or notification run.

## Rest beyond this slice

ExternalObservationJournal editor, deletion-policy redesign beyond the necessary
final-journal blocker, general Lesson review workflow, all-source materialization
race closure and Performance remain separate. Preserve M0–M11 and current owners.
