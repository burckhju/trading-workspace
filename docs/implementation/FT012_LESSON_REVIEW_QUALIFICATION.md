# FT-012 Lesson review — qualification and integration boundary

2026-10-16 (Europe/Berlin). Status owner: [PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).
Basis: Journal PR #260, `37b6ed0ab45a30ea5a6b8f8111c9a5f3b76aacaa`.
The user explicitly authorized normal merges after green checks on 2026-10-16 Berlin time.
This is technical qualification, not human domain acceptance, a release or a deployment.

## Exact proof boundary

Initial Lesson PR #261 head `8dbff08e56c507e9ca1726aef24ade80f3dd5563` was not qualified:
run 38704759931 stopped at Ruff/ESLint and failed the extended browser journey.
Corrected code/test head: `4081563509cb4ad4e765de499765a1759b59cdd3`;
complete tree: `59aed8a58ad2990459f172ac77554341db3cbaac`.
[Qualification run 38824269518](https://github.com/burckhju/trading-workspace/actions/runs/38824269518)
checks this exact head, not its workflow trigger `0fa187e...`. Artifact identity files
and browser traces identify the checkout. Temporary workflows and transport files
were removed before the test checkout. Later documentation/ancestry-only commits
must retain the same application/test/migration blobs. Final required current-main
checks and merge receipt are recorded in [PR #261](https://github.com/burckhju/trading-workspace/pull/261).

## Corrected failures

The relation selector nested in its label had an ambiguous accessible name. A
unique React useId-based control id and explicit label association now give each
selector the exact visible name, without weakening the existing browser assertions.
A separate deterministic regression reproduces a real race: a passive owner read
of the same ExitReview draft could overwrite unsaved rationale and assessments.
Only that same-draft hydration is now suppressed while user edits exist. An explicit
save receipt or a different/finalized version still hydrates the form; currentness
and review eligibility remain entirely backend-owned. In-flight mutation fields
are disabled. Navigation stays keyed by trade and lesson identity.

LessonReviewPanel cleanup captures the stable read-sequence object and invalidates
reads from the finished effect lifetime. StrictMode and late-response tests verify
that obsolete context cannot replace a newer context. Test-only import/line/unused
variable fixes and correctly awaited mock microtasks resolve lint failures. No
coverage threshold, assertion, test timeout, financial contract or migration changed.
The new regressions first failed on the original behavior, then passed after repair.

## Executed tests

| Check | Result on corrected code head |
|---|---|
| `bash scripts/check-backend.sh` | 2705 tests passed, 86.99% coverage (unchanged 85% threshold); Ruff, Black (930 files) and mypy (532 source files) passed. |
| `bash scripts/check-frontend.sh` | 493 tests / 105 files passed; TypeScript, ESLint, Prettier and build passed. Coverage lines/statements 92.49%, branches 84.00%, functions 84.65%. |
| `bash scripts/run-e2e.sh` | 52 passed; zero failed, flaky or skipped cases. The genuine journal/Lesson successor is included, not counted again. |
| Targeted real journal → explicit Lesson V2 journey | Twice passed with `--repeat-each=2 --retries=0`, success traces retained. These are repetitions of a case in the full suite, not two additional unique acceptance cases. |
| Targeted frontend | 35 passed, including exact labels, StrictMode, delayed owner reads and unchanged historical relations; same 35 passed locally. |
| Targeted review/backend/PostgreSQL | 40 passed in the selected command/source/PostgreSQL run, including two real PostgreSQL journeys; other API/domain regressions are in the full 2705. |
| Alembic | Existing single head `20261014_0046`; migration succeeded. No new schema in this Lesson slice. |
| Integrity | Patch hash and complete tree checked before commit; `git diff --check`; downloaded artifact SHA-256 checks; no transport file retained. |

All PostgreSQL/browser writes ran only on fresh GitHub-hosted runners with synthetic
data. The named `trading-workspace-e2e` project, ports 25432/8000/8080, empty volumes,
private configuration absence and the test database were checked before writes.
Providers, scheduler and Telegram were disabled. Browser API uses the existing
canonical localhost origin. No user stack, provider consent, paid data, message,
model activation or real holding was touched. Local Python 3.13 and missing pytest,
Docker/PostgreSQL are not represented as manifest-Python-3.12 or database proof.
Local full-gate failures during intermediate type/lint corrections remain failures;
the completed CI gates are separate evidence.

## Acceptance and ownership matrix

| Capability | Evidence / result | Remaining boundary |
|---|---|---|
| Observation / Exit Review | Existing FT-011 owner; actual REST capture, full exit and review exercised in the genuine browser journey. Same-draft edits survive delayed reads. | FT-011 materialization race against upstream correction is separate. |
| Journal lifecycle | Qualified #260 writer reused. Explicit V2 preserves original journal texts/identity. | External observation journals and full mobile/accessibility acceptance are separate. |
| Evidence transfer | Explicit journal V2 evidence used; full selected source identities and relations sent to Lesson commands. | Historical FT011 evidence inventory at NOT_READY remains separate. |
| Lesson interpretation | Explicit content/category/reason and complete unique evidence snapshot; at least one SUPPORTS under the existing contract. | No automatic suggestion acceptance or model/hypothesis creation. |
| Source review | Explicit version/state/no-signal pin, full reviewed evidence set and audited reason. STALE SUPPORTS never fabricated as CONTRADICTS. | Inspection is as-of-read, not global upstream serializability. |
| Contradiction resolution | Actual current CONTRADICTS link IDs; generic APIs cannot bypass an open signal. Unchanged/new-version/retire paths, conflict and rollback tested. | General RETIRED reactivation is outside V1. |
| Version history | Genuine browser records capture → review → journal → Lesson V1 → execution correction → journal V2 → explicit Lesson review → chosen V2 links → reload and read-only V1. PostgreSQL checks exact historical snapshots. | No new trigger claim for every legacy table against arbitrary administrator SQL. |
| Runtime / performance | No activation, approval or performance prerequisite introduced. | No human acceptance, release or target-installation observation. |

## Reading sources for performance and governance

The existing Execution/Position owner remains the source of financially realized
results; an Underlying observation is not an executable Warrant exit quote. A
LessonVersion stores personal interpretation and exact source links, not realized
profit. Relation values SUPPORTS, CONTRADICTS and CONTEXTUAL remain version-specific.
Journal text/version/finalization and FT-011 source version can be read separately.
Journal lineage SUPERSEDED and its source review STALE are distinct. Lesson CURRENT
means current interpretation, not that all linked data are current, complete or
tradable. UNKNOWN is not CURRENT, zero or low risk.

Use `GET /api/v1/learning/lessons/{id}/review-context` for concrete history, signals
and audit; use `GET /api/v1/learning/learning-evidence/{id}/currentness` for a separate
inspection with its own checked_at. Historic receipt result IDs are not new
currentness certifications. No GET opens/resolves a review. Do not replace an old
link by a latest source. Successor selection and interpretation are explicit commands.
The existing Journal API and immutable journal evidence retain their own sources.
No new read model or financial calculation owner is introduced.

## Delivery and residual scope

#259 was merged normally as `c78122ffd2a7e44b422bcdb6e500f4da7831dcb8` after its exact
checks were verified. #260 was retargeted to main, updated without file changes and
merged as `708d4bf6cfb18c12aa39c5cf9ee4ad0f9f320153` after all new required checks on
`9da6a8097732bfc96aedb6465df9dd9348d8bd06` passed. No force-push or rule bypass.
This report does not itself certify a future #261 merge; the exact receipt is in
that PR. Existing v1.5.6 and VERSION files are unchanged; merge is not release.

Remaining original work: FT011 atomic materialization/currentness under upstream
correction and historical NOT_READY evidence readback; independent external-source
and mobile/accessibility qualification, explicit title/tag editing and retired
reactivation. Human domain acceptance and target installation remain unverified.
The next technical slice is the FT011 materialization consistency/inventory contract,
not a new Journal/Lesson owner. Journal migration 0046 is additive but rollback can
refuse protected provenance data and is not lossless. No production migration run.
