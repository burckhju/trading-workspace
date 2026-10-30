# Scheduler diagnostics and data-quality boundaries

## Verified baseline (2026-10-30)

This qualification began against main
[`e8703a65ce8c1ba48ed1c9be3a8b7b8ff4dac37f`](https://github.com/burckhju/trading-workspace/commit/e8703a65ce8c1ba48ed1c9be3a8b7b8ff4dac37f),
the merge of the position-history implementation in
[#302](https://github.com/burckhju/trading-workspace/pull/302).
The original #303 implementation started from
[`d1108ae4f7fba976f4771885e84b5b8662248edb`](https://github.com/burckhju/trading-workspace/commit/d1108ae4f7fba976f4771885e84b5b8662248edb)
and incorporated the newer main in its inspected head
`b95409ada22a731cd59785b7904cdfd72cea79e4`.

While the remaining defects were being qualified, `burckhju` merged that original
#303 head at **2026-10-30 17:42:38 UTC (18:42:38 Europe/Berlin)**. The current main
is therefore
[`4f70760c0dcf0448e470eef85e79253d897189e5`](https://github.com/burckhju/trading-workspace/commit/4f70760c0dcf0448e470eef85e79253d897189e5),
whose tree `88941a4499ed028f1447d8697c90f70e6fce155f` is exactly the original
inspected #303 tree. The agent did not perform that merge. These later changes
are a separate follow-up containing only proven qualification/correctness gaps;
they do not recreate the already integrated initial implementation. The same
feature branch incorporates the current main before its follow-up review.

`VERSION`, the backend project and the frontend package report **1.5.31**.
A fresh tag-ref inspection confirms that **v1.5.31** is still the newest version
tag; its ref is a lightweight tag pointing directly to commit
`5f1b675e09bd993da8e0576067e3e466c5b5bbdb`, with no annotated tag object to peel.
Main additionally contains #301, #302 and the original #303. GitHub's latest formal
[Release object](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection)
is still **v1.0.0-product-selection**, whose tag resolves to commit
`773201bcc0605f89e0817a297ada45b41020ec3e`. Release objects, version tags and the
main commit are separate evidence; none establishes a user-PC installation or
functional acceptance of #303.

The inspected remote pull requests contain:

| PR | Inspected head | Remote state | Actual published changes |
| --- | --- | --- | --- |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Open, draft | Only `.github/workflows/hebeltrader-baseline.yml`, a 40-line development export helper. The described local monitoring-rule implementation is not published in this PR. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Open, draft | Position-history design documentation and two development helpers. The implementation is in main through #302, not in this old PR's diff. |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Open | Three source-research documents, no provider implementation. |
| [#197](https://github.com/burckhju/trading-workspace/pull/197) | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Open, draft | Seven research/workflow files: public historical-data acquisition, targeted session repair, public symbols, documentation and collector tests. No production scheduler or strategy change. |

The full published file lists and patches were read, not inferred from PR
descriptions. All four remote PRs report `mergeable=true` at inspection; that is
textual mergeability, not a qualification of their intended implementations.
Their changes have **no file intersection** with the eight original #303 paths
or the 17 paths in the qualified follow-up. The 24 changed paths in merged #302
also have no intersection with those paths. Version 1.5.31 and migration head
`20261028_0048` are unchanged. Final integration evidence must distinguish the
merged #303 head from the follow-up head, current main and GitHub test merge;
earlier green runs cannot qualify later corrections.

## Existing functionality reused

- Five independent scheduler lanes: `WARRANTS`, `ISSUER_QUOTES`,
  `WARRANT_DISCOVERY`, `ISSUER_DISCOVERY`, `UNDERLYINGS`. Existing leader locking,
  per-source pacing, due/overdue backlog, deferred retry and discovery retry
  ownership remain intact. In particular, #210, #216, #237, #271 and #295 are
  already integrated. A scheduled due time is not a guaranteed job start time.
- `QuoteSourceAttempt` already distinguishes source availability, missing quotes,
  insufficient data, configuration failures and provider errors per listing.
  Stored last-success quotes preserve their original timestamps and carry a
  `refresh_error` when a later refresh fails.
- `QuoteCoverageService` and `PositionQuoteCoverageService` already assess
  identity, mapping, source, currency, original observation time and age. Their
  existing snapshot age budgets and session-freshness policy remain authoritative.
  A recent HTTP request does not make an old quote fresh.
- The position-monitoring runner already reports cycle times, the previous
  completed result and separate missing/stale/error counters. Existing alert
  deduplication and notification behavior are unchanged.
- Main already has `WarrantQuoteSampleModel`, `QuoteHistoryReader` and
  `WarrantQuoteHistory.tsx`. The existing
  `FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1` policy preserves observed samples and
  failure evidence. It deliberately reports no invented time-coverage percentage.
  The older statement in #205 that warrant quotes are only process-local no
  longer describes main.

## Disposition of the older #207 objectives

#207 describes a confirmed position-notification rule set B01-B58 excluding B08.
That business-rule package and the provider/scheduler diagnostics in #303 have
different responsibilities. **#303 is not a complete replacement for #207.**
The actual #207 diff contains only the export helper identified above. Reports
of separately saved local patches, tests or upload attempts do not prove that
the rule implementation is present in the remote branch or current main.

| Classification | Verified scope and disposition |
| --- | --- |
| Already integrated | Main contains the position-monitoring runner, cycle timestamps, separate missing/stale/error counters, price-bound STOP/TARGET evaluation, invalidation of alerts with unconfirmed price axes, notification delivery and persisted quote evidence. Reuse these existing foundations. |
| Operational objectives addressed by #303 | Current-attempt visibility, source-specific failure sequences, retained-quote failure evidence and recovery belong to this operational diagnostics PR. Qualify its final implementation on its own head; this does not establish any of the separate B01-B58 business rules. |
| Not implemented in the published #207 code | The described confirmed-baseline rule/evidence/persistence/API/UI package is absent from that PR. Current main also has no `baseline_records.py`, `baseline_ports.py`, `baseline_repository.py`, confirmed-baseline migration or `BASELINE_NOTICE` alert type. Its completion cannot be inferred from the old PR's narrative. |
| Superseded technical preparation | The development export helper is not a production monitoring feature and should not be imported into #303. September integration trees and proposed migration numbers are obsolete starting points: main already has another revision 0039 and a migration chain through `20261028_0048`. Never apply an old file overlay over current price-binding, alert or notification contracts. |
| Continue separately | Any still-required confirmed business-rule package needs its actual complete source, an additive integration against then-current main and its own tests. Retention of operational incidents across restarts is likewise a separate persistence requirement, not established by process-local counters. Leave #207 open; this audit does not close or rewrite it. |

Code checks supporting this classification include
[`MonitoringRuleType`](../backend/app/features/position_monitoring/domain/models.py)
(`STOP_REACHED`, `TARGET_REACHED`),
[`AlertType`](../backend/app/features/alert/domain/models.py)
(STOP/TARGET and the existing trend/volatility risk types),
the [monitoring runner](../backend/app/features/position_monitoring/service/runner.py)
and [legacy-alert invalidation](../backend/app/features/position_monitoring/service/legacy_alerts.py).
The already implemented trend/volatility risk assessment is not evidence that
the separate confirmed-baseline catalogue has been implemented.

## Added operational evidence

The existing read-only `GET /api/v1/market-data/refresh/status` gains two objects
on each job. Existing job fields, statuses, quote results and retry intervals
remain available with their previous meanings. Known exception reasons in the
new diagnostics use the existing `MarketDataError.code` values. Free-form
exception messages, transport URLs and credentials are not included.

### Current execution

`execution.running`, `execution.started_at` and `execution.elapsed_seconds`
describe the currently executing attempt. The elapsed duration uses the existing
monotonic scheduler clock and is sampled when status is read. When idle, start
and duration are null. The existing `started_at`, `checked_at` and
`duration_seconds` continue to describe the last completed attempt; they are not
silently overwritten while another attempt is running. Cancellation does not
create a completed result, failure or recovery.

There is no invented `HUNG` threshold. A job can legitimately wait for pacing and
process several listings/providers. The refresh interval is not a contractual
maximum execution time. A future hang alarm requires an explicit overall deadline
or progress contract; the new running duration makes long execution observable.

### Per-check failure and recovery

`diagnostics.scope` is `PROCESS_LOCAL`. `diagnostics.checks` contains one current
record for the job and one per observed source/listing identity:

| Field | Meaning |
| --- | --- |
| `kind`, `source`, `listing_id`, `identity_key` | `JOB` or `SOURCE`; source checks use provider, exact listing and the existing canonical `QuoteIdentity.key`. Its product/listing/mapping versions prevent a replacement route from recovering the previous route. |
| `status`, `category`, `reason` | The latest observed result and bounded diagnostic code. Categories distinguish job errors, provider errors, missing quotes, configuration/mapping and data quality. |
| `provider_reachable`, `response_valid` | Separate tri-state evidence. Explicit transport errors indicate a failed reachability attempt; explicit HTTP error responses prove reachability but not a valid quote response. Ordinary adapters, caches and local files do not prove network reachability, so unknown remains null. |
| `quote_status`, `quote_usable` | Validated quote outcome: `FRESH`, `LAST_AVAILABLE`, `STALE`, `REFERENCE_ONLY`, `MISSING`, `INVALID`, `TIMESTAMP_UNKNOWN` or `UNASSESSED`. Reference prices remain usable for their existing analysis purpose, but do not satisfy a monitoring bid requirement. |
| `retained_quote`, `quote_observed_at`, `quote_retrieved_at` | Stored fallback is identified independently of its age; original observation and retrieval times are retained. |
| `qualified_success`, `waiting` | A source success requires a valid, usable bid within the existing session freshness contract. Waiting/local throttling is not a new failed provider attempt. |
| `consecutive_failures` | Number of unsuccessful completed checks for this identity since its last successful check. Waiting or a check of another identity does not increment or reset it. |
| `first_failure_at`, `last_failure_at` | Beginning of the current failure sequence and last unsuccessful observation. The beginning becomes null after recovery; the last failure remains inspectable. |
| `last_failure_reason`, `last_failure_category` | Last actual failure cause, retained across deferral and recovery so a throttle result does not erase the preceding outage. |
| `last_success_at` | For SOURCE, original retrieval time of the last observed qualified success; a cache hit cannot advance it. For JOB, completion time of the successful scheduler operation. The legacy top-level job `last_success_at` retains its scheduler meaning. |
| `recovered_at` | Timestamp of a later successful check of this exact identity. A new failure clears it. Successful later checks retain the same recovery timestamp. |
| `last_checked_at` | Completion time of this check's last observed attempt. |
| `attempt_started_at` | SOURCE attempt start, independently of other providers in the job. Source failure/recovery and freshness use its own completion time, not a later job finish; legacy results without attempt clocks fall back to job completion. |
| `observed_in_latest_run` | False for a source not checked in the latest job result. Its old evidence is retained without asserting a current outage or recovery. |

The conditions use existing outcomes rather than new time or alarm thresholds:

1. `ERROR`, `MISSING`, `INSUFFICIENT`, `UNAVAILABLE`, `BLOCKED` and
   `NEEDS_MASTER_DATA` remain distinct causes of an unsuccessful check. A missing
   quote is not classified as provider unreachability. Known error classes/codes
   refine the category.
2. A source attempt with `refresh_error` is unsuccessful even if its retained
   quote makes its raw status `AVAILABLE`. A successful other source or listing
   cannot clear that failure sequence.
3. Raw `AVAILABLE` alone never qualifies source success. The existing
   `WarrantQuoteSnapshot` validation rejects invalid/crossed/nonfinite prices,
   inconsistent timestamps and malformed observations. Missing, reference-only,
   timestamp-unknown and stale quotes do not recover a monitoring source.
   `TradingSessionFreshnessPolicy` uses the original quote timestamp and the
   existing age budget, including an explicit zero budget. Its `LAST_AVAILABLE`
   result can qualify a newly retrieved closing-session quote while remaining
   visibly distinct from `FRESH`. There is no new age policy or trading permission.
   Job completion and source failure can coexist.
4. `PENDING` and `DEFERRED` neither increment failures nor assert recovery. The
   existing cooldown determines the next attempt. The same applies to a source
   returning `FRANKFURT_REQUEST_THROTTLED`, even with raw `ERROR` or a retained
   `AVAILABLE` quote: the client did not make another network request. The
   previous failure cause remains available separately from the waiting reason.
5. A cache result retrieved before the last failure cannot prove recovery. Its
   current quality remains visible, but the failure sequence waits for newer
   successful retrieval evidence. A healthy cache hit retains the original
   last-success time. A stored quote, even without a `refresh_error`, never
   proves a current provider success.
6. Identity is read using the existing read-only identity function before and
   after resolution. A mapping/product change during I/O is an invalid current
   observation; the old fingerprint remains open. A later healthy new identity
   starts its own evidence and does not recover the old one.
7. Duplicate source/listing/fingerprint observations in a single job are counted once. A
   failed duplicate takes precedence over a successful one, independent of
   iteration order. Status GETs never change counters, deadlines or provider state.

There is no event queue, new trading alert or notification per failure or poll.
Repeated failures update the same record. Evidence resets on backend restart and
is discarded when its catalog job is removed. It is not durable monitoring
history or a cluster-wide provider-health claim. Source checks not revisited
remain explicitly historical within the process. Existing persisted last-success
quotes and quote-history evidence survive restart and are re-read with their
original timestamps; an empty process-local counter is not a claim that there
were no earlier incidents.

The existing **Automatischer Kursabruf** panel displays this evidence in its
diagnostic details, current execution separately, all five lanes and each lane's
error. `AVAILABLE` is displayed as a completed scheduler run, with open source
findings visible before expanding diagnostics. Its existing **QuoteCoveragePanel**
continues to show current age and missing/stale observations; `refresh_error`
also keeps a stored fallback visible in the inspection filter and prevents a
misleading successful-fetch label. Earlier API responses without the new fields
remain renderable.

## Integration boundary

Production changes are limited to:

- `backend/app/features/market_data/service/refresh.py`: execution metadata,
  read-only identity evidence and one diagnostic fold after an existing job
  completes; this is the shared runtime file a parallel scheduler change may
  need to reconcile.
- New `backend/app/features/market_data/service/refresh_diagnostics.py` and
  `refresh_quality.py`, reusing existing quote validation and session freshness.
- `frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx`:
  existing administration view only.
- The adjacent existing `QuoteCoveragePanel.tsx`: fallback labeling and inspection
  filtering only; the quote-coverage API and provider interfaces are unchanged.

The implemented #205 scope, now merged through #302, does not touch `refresh.py`
or any other file in the inspected #303 delta. The old #205 branch adds only
`docs/ui/position-price-history.md` and its two development workflows. #220
changes `docs/GETTEX_SCHEMA_PROBE.md`, `docs/issuer-quote-coverage.md` and
`docs/issuer-quote-research-expanded.md`. #197 changes only its research workflow,
`docs/research/HEBELTRADER_EXECUTION.md` and files under `scripts/research/`.
These are verified current file boundaries, not a promise that future edits
cannot overlap. #207's unpublished rule code is neither imported nor assumed
to exist.

| Shared contract or potential future overlap | Integration requirement |
| --- | --- |
| `MarketDataRefreshRuntime.status()` / `GET /api/v1/market-data/refresh/status` | Keep operational fields additive and old responses renderable. A future scheduler edit in `refresh.py` must preserve the diagnostics without changing lane, pacing or retry ownership. |
| `QuoteSourceAttempt` in `position_monitoring/service/quote_sources.py` | Reuse source, listing, reason, original observation time, bid/ask/reference availability, currency and `refresh_error`. `AVAILABLE` can describe an older bid or an analysis reference; it is not by itself proof of freshness. |
| `WarrantListingQuoteProvider` and `MarketDataResult[WarrantQuoteSnapshot \| None]` | Keep existing adapter contracts compatible for later #220 integrations. No new provider adapter or activation belongs to #303. |
| `QuoteCoverageService` / `PositionQuoteCoverageService` | Reuse identity, age, missing-data and retained-quote assessments. Do not reinterpret fetch time as original quote time. |
| Persisted quote samples, `QuoteHistoryReader` and the #302 position-history API | Keep their existing persistence and read semantics. #303 adds no chart, duplicate history store or chart-triggered provider request. |
| #197 historical-research collector | Keep its research-only acquisition and retry logic separate from production scheduler state; no strategy or research-data modification is required here. |

This document avoids rewriting shared `docs/automatic-market-data.md` or #205's
design document. Any future runtime overlap must be reconciled additively against
the actual peer head; do not replace peer files with an older snapshot.

**No migration is added.** The inspected main migration head is
`20261028_0048`. No version, tag, release, deployment, provider activation or
production-data change is included.

## Verification

New tests cover state transitions, canonical source/listing/product/mapping
identity, provider unreachability, mixed results, retained errors, absent/old/
invalid quotes, missing timestamps, reference-only quotes, session-close policy,
zero age budgets, cache retrieval times, source-local deferral, deduplication,
safe error codes, overlapping attempts, cancellation, catalog rescans, recovery
and read-only API serialization. Real retained-provider and SQL tests exercise
mapping changes during I/O and restart/re-display of persisted observations.
Frontend and browser tests cover the operational presentation, replacement
quotes, subsequent recovery and responses predating the extension. Earlier tests
that allowed recovery from a bare `AVAILABLE` or stale quote now require real
qualified quote evidence; no quality assertion or gate is weakened.

The unchanged lane, pacing, discovery, coverage and quote-history suites remain
regressions. Relevant local commands from the repository root:

```bash
PYTHONPATH=backend:. .venv/bin/python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/features/market_data \
  tests/integration/backend/test_refresh_diagnostics_api.py \
  tests/integration/backend/test_monitoring_diagnostics.py
cd frontend
npm run typecheck
npm run lint
npm run format
npm run test:coverage
npm run build
```

The final PR evidence must identify the exact tested commit. Standard Backend CI
adds PostgreSQL 17 migrations/integration and the existing 85% coverage gate;
standard Frontend and End-to-End workflows retain their existing gates. A local
test run without PostgreSQL or Docker is not a replacement for those jobs.

Remaining broader gaps are explicit: a contractual whole-job hang deadline;
proof of complete historical coverage; durable operational incident history;
and the separate coverage projection omissions for issuer discovery and some
generic exception class names. This narrow change does not silently expand into
those concerns or into #207's unavailable rule implementation.
