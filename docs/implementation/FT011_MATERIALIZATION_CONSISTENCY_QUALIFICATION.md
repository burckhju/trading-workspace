# FT-011 → FT-012: source-stable materialization and historical evidence

2026-10-16. Authoritative task status: [PB-019 Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization).
This report records the bounded technical qualification, not human domain acceptance,
release, model activation or observation of the new code on JMBbot.

## Exact scope and proof identity

Baseline main/v1.5.7: `3faf0f768b23c719cb16239280a2c9875d9ae451`, tree
`8e30df4fcfe48f2b9579da86202d27802643b6de`. Development branch:
`dev/ft011-materialization-consistency-20261016`, [PR #263](https://github.com/burckhju/trading-workspace/pull/263).
The [DoR](FT011_MATERIALIZATION_CONSISTENCY_DOR.md) was recorded before implementation;
[ADR-007](../decisions/ADR-POST-FT012-007-MATERIALIZATION-CONSISTENCY.md) extends existing ownership.
No tracked AGENTS.md was present. The full credential-free baseline tree was checked
against GitHub; the local reconstruction's commit ancestry is not the remote ancestry.
No foreign working files or production configuration were overwritten.

**Common executed code/test commit:** `0863248b0c44e7c36d41b29acbef56b451d2592f`,
complete tree **`691ad6091952e3e606cec0d3e7b9a0227122085c`**.
[Qualification run 38957166870](https://github.com/burckhju/trading-workspace/actions/runs/38957166870)
checks this commit explicitly. Its workflow trigger `2ad5deeef7e28ef9c46a1a8fb9f655d6d9048700`
is NOT the test checkout. Identity files and Playwright git metadata identify the
actual source. Temporary transport/workflow files were removed before checkout.
Later documentation-only commits must retain identical application/test/migration
blobs. Their current required PR checks and any actual merge receipt are recorded
in PR #263, not inferred from an earlier successful source checkout.

## Implemented contract

FT-012 still owns the existing command, evidence, idempotency receipt and commit or
rollback. FT-011 owns the observation, Exit Review and exact source inspection.
The production command injects a guarded FT-011 handoff using the **same AsyncSession**
as its FT-012 transaction. Native PostgreSQL `FOR UPDATE NOWAIT` locks cover the trade,
execution/position/management children, observation/review/version aggregate, exact
plan version/targets and pinned listing/all its daily prices. Existing parent FKs
also exclude new children, including a previously missing early observation date.
After acquisition, the existing FT-011 gate and actual version fingerprint are checked.
No review is revalidated or mutated as a side effect. Locks survive until commit/rollback.

A preceding source writer produces 409 `SOURCE_BUSY` and rollback; a committed stale
source produces the existing not-ready error. A writer starting later waits until
materialization ends and may then perform a subsequent correction. That does not
rewrite the historical evidence. Idempotency and source-version mismatch checks
remain intact. An already successful receipt is resolved before source locking;
its replay is not a new statement that the source is CURRENT. No automatic retry.

Public FT-011 Handoff and FT-012 materialization-status GETs use the same inspected
FT-011 reader, **without** a write guard. Thus a stored CURRENT flag cannot alone
explain a ready handoff after a known input correction. The stored review flag stays
separate and can change through the existing explicit owner action. Journal commands
retain their previous gate/composition; no Performance dependency or timing rule is added.

A separate read-only inventory is registered in the existing FT-012 router:

```text
GET /api/v1/learning/trades/{trade_id}/ft011-evidence/history
```

It does not depend on today's handoff readiness. Entries retain evidence type/ID,
exact trade/observation/review/version identity, review ordinal/status, stored
currentness, separate current input inspection and checked_at, and superseding
review identity. Every saved LessonEvidenceLink retains its link ID, exact
LessonVersion and SUPPORTS/CONTRADICTS/CONTEXTUAL relation, including older versions.
The legacy status response shape is unchanged. Missing provenance remains UNKNOWN.

## User-visible path

In the existing Post-Trade page, **Bisherige Review-Evidence** is available separately
from a new handoff action, including at NOT_READY or after a status-fetch error.
Loading, empty, failed and stale responses across navigation are distinguished.
An explicit reload reads history; it does not create evidence or resolve a review.
The link opens `/lessons/{id}?lesson_version_id={exact-id}#lesson-history` and selects
that stored version, also after reload. Invalid version IDs do not fall back to latest.
The current Lesson summary is labelled separately from its selected historical content.

A single full-width wrapper also prevents the existing combined page's sections
being squeezed next to each other. This is not a second dashboard or global owner.
Desktop evidence screenshots were visually inspected: consistent not-ready handoff,
retained historical evidence, exact V1 interpretation/relations while V2 exists.
No comprehensive mobile/accessibility acceptance is claimed.

## Executed acceptance matrix

| Criterion / capability | Technical evidence | Remaining limit |
|---|---|---|
| C1 — observation / Exit Review / suitable source | Existing owner gate and exact fingerprint; actual full exit, open-trade rejection and current/stale/version mismatch tests. | Existing 20 real post-exit EOD semantics unchanged; no repair of a user's missing prices. |
| C2 — atomic evidence handoff | Coordinated PostgreSQL execution correction, review successor, stored STALE, daily-price update/delete and earlier-date insert. `pg_blocking_pids` asserts the actual materialization backend PID blocks the writer. Correction-first busy/not-ready paths and complete rollback covered. | Supported source graph under current constraints, not administrator DDL or disabled constraints; full high-volume load benchmark separate. |
| C3 — retries / concurrency | Same and different keys, semantic uniqueness, historical replay after correction, commit failure with no orphan evidence/receipt. | No retry automatically issues a new decision or manufactures a currentness certification. |
| C4 — history / lineage | Native PostgreSQL history at NOT_READY and after V2; old V1 SUPPORTS and later V2 CONTRADICTS remain different stored links. Workspace/trade/provenance and UNKNOWN cases tested. | Display title is the current Lesson-root title, not a fabricated frozen title. |
| C5 — UI / exact detail | React tests cover unavailable current status, empty/error/read retry, obsolete responses, exact historical selection and missing version. | No new global navigation or Lesson index. |
| C6 — real browser / PostgreSQL | Synthetic actual REST capture → browser review/materialization/Lesson V1 → execution correction → retained history → new source/Evidence V2 → exact old Lesson V1 through link and reload. Run twice with retries disabled. | Only Underlying prices are fixtures; capture/correction and the additional Lesson V2 command use actual APIs, not every step a click. Existing journal/Lesson-dialog journey runs in the full suite. No live provider or user data. |
| C7 — regression / operations | All three unchanged full gate scripts, migration head, exact tree and diff validation; results below. | Technical proof is not human acceptance, release or PC installation. |
| Journal lifecycle | Reuses qualified FT-012 writer and full journal correction browser case. | First-draft gate and external journals unchanged. |
| Lesson creation / review / history | Existing explicit commands, no automatic interpretation or relation remapping; exact version detail reused. | No automatic model/hypothesis/approval/activation. |

## Completed gate results on the common code commit

| Entry point | Result |
|---|---|
| `bash scripts/check-backend.sh` | 2736 tests passed; 87.08% coverage, unchanged 85% threshold. Ruff, Black and mypy passed. |
| `bash scripts/check-frontend.sh` | 500 tests / 106 files passed; TypeScript, ESLint, Prettier and build passed. Coverage lines/statements 92.56%, branches 84.04%, functions 84.59%. |
| `bash scripts/run-e2e.sh` | 53 passed, zero failed/flaky/skipped cases, both protected write paths explicitly enabled only in the verified disposable stack. |
| Focused source/owner/native database tests | 92 passed, including 11 real PostgreSQL cases. These are a subset, not additional full-suite tests. |
| New real browser case | Two successful repetitions, `--repeat-each=2 --retries=0`, with traces. It is one case in the 53, not two new acceptance criteria. |
| Existing-schema migration | Upgrade succeeded; before/after head `20261014_0046`. No migration added or modified in this PR. |
| Local source checks | 81 focused backend tests, Ruff, Black, mypy (535 sources); identical frontend full gate previously 500 tests. Local Python 3.13 is not the manifest-Python-3.12 or database proof. |

These test writes ran only on fresh GitHub-hosted runners, PostgreSQL 17, Python
3.12.15 and Node/npm 22.16.0/10.9.2. The browser project `trading-workspace-e2e`,
ports 25432/8000/8080, empty project volumes/mounts and the specific test database
were verified before writes. Private .env files were absent; providers, refresh,
scheduler and Telegram were disabled. Cleanup applied exclusively to that new stack.
No user stack, paid data, message, new consent, economic holding or model was touched.

## Red attempts and additional defects — not hidden by green gates

First source `5119782c...` passed 84 focused tests including 10 native PG cases and
500 frontend tests, but the genuine browser could not reach the Lesson form after
materialization: existing `learning-evidence/{id}/lessons` returned HTTP 500.
The pre-existing DISTINCT query ordered by Lesson.updated_at without selecting it.
The corrected reader adds that field to the SQL projection only, not the public
response. Actual PostgreSQL reproduced `InvalidColumnReferenceError` on the original
reader, then the exact corrected source was restored. Empty, populated and deduplicated
V2 root-reference results now pass. The initial browser failures remain failed runs.

Second source `8117d5ba...` passed the new browser twice, but visual inspection found
an old Handoff card saying READY alongside current not-ready inspection. The public
FT-011 GET now shares the inspected owner service. Additional native PG and browser
assertions require both handoff surfaces to reject stale inputs without changing
stored historical review content. The common final commit above contains that repair.

A local intermediate frontend run failed because a new test was outside its fixture
scope; scope was corrected, assertions preserved. Intermediate incorrect formatter
invocations were not full-gate successes. Existing test/code warnings remain visible.
No assertion, coverage threshold, standard workflow or protected write-skip condition
was weakened. Bot-triggered standard PR runs marked action_required are not successes;
only completed current-head required checks permit a normal merge.

## Performance / Governance read boundaries

Financially realized outcomes remain read from the Execution/Position owner.
Underlying EOD observations do not establish hypothetical Warrant sale prices.
Evidence inventory `materialized_at` projects persisted LearningEvidence.created_at:
it is the command's recorded evidence-creation time, **not** an exact database commit
time, source market timestamp, or proof of what was known at the original trade.
`checked_at` belongs to that item's present source inspection; the history GET is
as-of-read, not a global transaction snapshot or a future CURRENT guarantee.

Stored review CURRENT/STALE, present input inspection and supersession are distinct.
Lesson CURRENT means current interpretation, not universal freshness of its evidence.
Read exact old LessonVersion/link/relation IDs; do not silently use latest. Journal
versions keep their existing finalization/source contracts. Historical receipt IDs
are not new currentness checks. Reads neither repair source data nor open/resolve a
review. Explicit user commands still own interpretation and later versions.

## Integration / operational follow-through

Source locking adds no new schema or update-helper change. All stored price rows
for the selected listing are protected to cover inserts and date changes; different
trades using that listing may briefly receive SOURCE_BUSY. The user reloads and
retries deliberately. Large histories require separate latency/lock-footprint testing.
Supported foreign-key and native lock semantics do not promise safety against arbitrary
administrator SQL with constraints disabled, or future unknown source dependencies.

The original two race/inventory gaps are closed for this defined V1 contract by the
common qualification above. Older reports listing them as open describe their own
baselines and are not retroactively rewritten. M0–M11, other PB-019 abilities, the
journal timing discussion, navigation, real missing-data diagnosis and broader
mobile/accessibility work remain separate. Main integration requires current green
PR checks under existing branch protection. The user's installed v1.5.7 is unchanged
by this development task. A later release and pinned PC update need their own checks;
no target-installation evidence or human domain acceptance is inferred.
