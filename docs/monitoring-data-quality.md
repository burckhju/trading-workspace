# Scheduler diagnostics and data-quality boundaries

## Verified baseline (2026-10-30)

This change starts from main
[`d1108ae4f7fba976f4771885e84b5b8662248edb`](https://github.com/burckhju/trading-workspace/commit/d1108ae4f7fba976f4771885e84b5b8662248edb).
`VERSION`, the backend project and the frontend package all report **1.5.31**.
The actual `v1.5.31` tag points to
`5f1b675e09bd993da8e0576067e3e466c5b5bbdb`; main additionally contains the
documentation-only merge of #301. This was verified from the repository, not
inferred from the historical version in the request. GitHub's latest formal
Release object remains `v1.0.0-product-selection`; Release objects, version tags
and the main commit are distinct evidence.

The inspected remote pull requests contain:

| PR | Inspected head | Actual published changes |
| --- | --- | --- |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Only `.github/workflows/hebeltrader-baseline.yml`, a development export helper. The described local monitoring-rule implementation is not published in this PR. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Position-history design documentation and two development helpers. The parallel agent's new implementation is not present in this inspected head. |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Three source-research documents, no provider implementation. |

No Actions runs, check runs or commit statuses were recorded on the exact main
baseline when inspected. Successful Backend, Frontend and End-to-End runs on
`5f1b675e...` are earlier evidence and do not qualify this change. The integration
PR records its own final head and actual CI results.

During validation, the parallel position-history implementation was merged as
[#302](https://github.com/burckhju/trading-workspace/pull/302), moving main to
`e8703a65ce8c1ba48ed1c9be3a8b7b8ff4dac37f`. This monitoring branch incorporates
that main commit without conflicts. The exact 24 changed paths in #302 and the
eight monitoring paths have **no intersection**. Version 1.5.31 and migration
head `20261028_0048` remain unchanged. The final integration CI must use the
updated monitoring head; earlier runs against `d1108ae4...` are not sufficient.

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
| `kind`, `source`, `listing_id` | `JOB` or `SOURCE`; source checks are keyed by the existing provider name and exact warrant listing. |
| `status`, `category`, `reason` | The latest observed result and bounded diagnostic code. Categories distinguish job errors, provider errors, missing quotes, configuration/mapping and data quality. |
| `consecutive_failures` | Number of unsuccessful completed checks for this identity since its last successful check. Waiting or a check of another identity does not increment or reset it. |
| `first_failure_at`, `last_failure_at` | Beginning of the current failure sequence and last unsuccessful observation. The beginning becomes null after recovery; the last failure remains inspectable. |
| `last_failure_reason`, `last_failure_category` | Last actual failure cause, retained across deferral and recovery so a throttle result does not erase the preceding outage. |
| `recovered_at` | Timestamp of a later successful check of this exact identity. A new failure clears it. Successful later checks retain the same recovery timestamp. |
| `last_checked_at` | Completion time of this check's last observed attempt. |
| `observed_in_latest_run` | False for a source not checked in the latest job result. Its old evidence is retained without asserting a current outage or recovery. |

The conditions use existing outcomes rather than new time or alarm thresholds:

1. `ERROR`, `MISSING`, `INSUFFICIENT`, `UNAVAILABLE`, `BLOCKED` and
   `NEEDS_MASTER_DATA` remain distinct causes of an unsuccessful check. A missing
   quote is not classified as provider unreachability. Known error classes/codes
   refine the category.
2. A source attempt with `refresh_error` is unsuccessful even if its retained
   quote makes its raw status `AVAILABLE`. A successful other source or listing
   cannot clear that failure sequence.
3. A completed `AVAILABLE` check without `refresh_error` ends the sequence for
   that identity. This proves recovery of the observed request/result, not a
   fresh quote, complete historical coverage or permission to trade. Job-level
   success and source-level failure can coexist.
4. `PENDING` and `DEFERRED` neither increment failures nor assert recovery. The
   existing cooldown determines the next attempt. The previous failure cause
   remains available separately from the current waiting reason.
5. Duplicate source/listing observations in a single job are counted once. A
   failed duplicate takes precedence over a successful one, independent of
   iteration order. Status GETs never change counters, deadlines or provider state.

There is no event queue, new trading alert or notification per failure or poll.
Repeated failures update the same record. Evidence resets on backend restart and
is discarded when its catalog job is removed. It is not durable monitoring
history or a cluster-wide provider-health claim. Source checks not revisited
remain explicitly historical within the process.

The existing **Automatischer Kursabruf** panel displays this evidence in its
diagnostic details, current execution separately, all five lanes and each lane's
error. Its existing **QuoteCoveragePanel** remains responsible for showing quote
age and missing/stale observations. Earlier API responses without the new fields
remain renderable.

## Integration boundary

Production changes are limited to:

- `backend/app/features/market_data/service/refresh.py`: execution metadata and
  one diagnostic fold after an existing job completes; this is the only shared
  runtime file a parallel scheduler change may need to reconcile.
- New `backend/app/features/market_data/service/refresh_diagnostics.py`.
- `frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx`:
  existing administration view only.

The implemented #205 scope, now merged through #302, does not touch `refresh.py`
or any other file changed here. A future shared scheduler edit must preserve the
additive status fields. There is no dependency on the chart or history API.
Quote models, retained-provider logic, history readers, position details, chart
components and provider discovery behavior are unchanged. #207's unpublished
rule code is neither imported nor assumed to exist; #220 adds no runtime
dependency. This document is new, avoiding a shared rewrite of
`docs/automatic-market-data.md` or #205's design document.

**No migration is added.** The inspected main migration head is
`20261028_0048`. No version, tag, release, deployment, provider activation or
production-data change is included.

## Verification

New tests cover state transitions, exact source/listing identity, provider
unreachability, mixed source results, retained errors, missing/old quotes,
deferral, deduplication, safe error codes, running attempts, cancellation,
catalog rescans, recovery and read-only API serialization. Frontend tests cover
the same operational presentation and responses predating the extension.

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
