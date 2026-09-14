# Automatic market-data refresh

The active workspace catalog drives discovery and retrieval. An open position is
not required. Products held in open positions and their underlyings are processed
first within their respective queues; the remaining active catalog follows in
that queue's batch. Position priority is derived from positive open quantity and no closing timestamp in the
configured workspace, not from a manually maintained product list.
There are no per-product UUID commands and no hardcoded user
instruments. Existing provider adapters, provider mappings, quote resolution and
daily-price import services remain the governing paths.

## Enable locally

Add or update these values in `docker/.env` (backend-only installations use
`backend/.env`). Values below are conservative defaults, in seconds:

```dotenv
TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED=true
TRADING_WORKSPACE_MARKET_DATA__REFRESH__WARRANTS_INTERVAL_SECONDS=300
TRADING_WORKSPACE_MARKET_DATA__REFRESH__UNDERLYINGS_INTERVAL_SECONDS=3600
TRADING_WORKSPACE_MARKET_DATA__REFRESH__DISCOVERY_INTERVAL_SECONDS=3600
TRADING_WORKSPACE_MARKET_DATA__REFRESH__REQUEST_SPACING_SECONDS=15
TRADING_WORKSPACE_MARKET_DATA__REFRESH__AUTO_CONFIGURE=true
```

Existing Vontobel/Frankfurt/EODHD activation, usage approvals and credentials still
apply. The scheduler enables no provider or subscription. Frankfurt uses the
already configured `docker/frankfurt.env`; see [Frankfurt setup](frankfurt-quotes.md).
No additional secret is introduced. EODHD requests consume the configured API
budget. The existing rate limits, safety reserve and retries remain in force;
public website access does not grant a contractual feed or executable quotes.

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

The startup helper rebuilds the application and applies all current migrations.
This change itself adds no migration. The existing application workspace is the
default scope. Other backend deployments can set
`TRADING_WORKSPACE_MARKET_DATA__REFRESH__WORKSPACE_ID` explicitly.

## Behavior

- New active catalog records are detected on the next scan, normally every
  30 seconds while the leader is running. Catalog scans and the leader connection
  check continue even while a provider queue is busy. New jobs are visible as
  pending and start when their queue can accept its next batch. Inactive
  instruments/listings and disabled mappings are not reactivated.
- Frankfurt discovery reuses the existing verifier: the public structured response
  must match the exact ISIN, provider exchange code and an active reference
  currency. Only then may an XFRA listing and XSC provider mapping be created.
  This works for issuers such as BNP and Vontobel when the source actually covers
  their product. Empty/invalid responses do not create mappings.
- Vontobel issuer names only select a candidate probe. An exact ISIN/WKN/currency
  match and a valid timestamped bid in the official payload are required before
  writing an issuer mapping. An existing active listing with unambiguous quote
  currency is required; Frankfurt can supply that verified listing first.
  No venue is invented for an issuer indication.
- Basiswerte/stock listings use EODHD completed daily prices. Missing mappings may
  be created only if the official exchange and symbol catalogs verify one exact
  ISIN, stock type, listing currency and venue. This also works for the first
  mapping at a venue; the composite US code requires instrument-specific NYSE or
  NASDAQ evidence. Existing mappings, including disabled mappings, are preserved.
  Catalogs share the configured EODHD quota, limiter and retries and are cached
  for 24 hours. Unresolved identity or venue differences remain blocked with a
  specific reason. See [Underlying mapping discovery](underlying-mapping-discovery.md)
  for evidence, limits and deployment verification.
- Daily imports use the existing idempotent persistence path. Initial history is
  up to 400 calendar days; later imports overlap seven days to capture corrections.
  No EOD price is converted into a warrant bid/ask or an execution permission.
- Successful issuer responses and Frankfurt observations are cached per identity;
  Stuttgart's large payload is shared. Quote eligibility is checked before cache
  access. Original quote and retrieval timestamps remain unchanged, while age is
  reassessed at read time. A malformed/empty public Frankfurt response invalidates
  only that requested ISIN, retaining independently verified observations for
  other instruments. HTTP 401/403 invalidate all cached source data. The shared
  provider cooldown remains in effect; expired transport caches may be reused
  only through the existing disclosed historical-analysis fallback. A browser visit
  is not needed to initiate background retrieval.
- Workspace cards display available indicative reference valuations as well as
  normal bid valuations, with warnings and source/time information. The existing
  execution restrictions remain in effect.

Intervals are minimum pauses after a job finishes. Provider pacing, retries and
large catalogs can delay a subsequent run. The global Frankfurt request budget
still applies; changing the instrument does not reset it. Individual failures do
not stop other jobs. Missing discoveries retry at the discovery interval.
Public Frankfurt 404 responses now wait per ISIN (default one hour) while other
identities retain the ordinary 15-second provider pacing. Cached failures perform
no network request. Other source errors keep their global backoff, including
longer `Retry-After` instructions on HTTP 429/503. See the retry diagnostics in
[Frankfurt quotes](frankfurt-quotes.md#per-instrument-retry-isolation-2026-09-14).
Set `AUTO_CONFIGURE=false` to refresh only existing configured routes.

The supported deployment remains a single backend process, as for the existing
provider budget/cache. A PostgreSQL session advisory lock prevents another
scheduler process from concurrently doing catalog discovery. Quote caches and
job diagnostics are process-local and rebuilt after restart; mappings and EOD
prices are durable. A replicated deployment requires shared caches, distributed
provider budgets and durable job scheduling before activation.

## Diagnose and verify

Open **Arbeitsbereich → Automatischer Kursabruf → Abrufstatus laden** to see
intervals, per-instrument coverage, diagnostic reasons and the earliest next run.
All catalog jobs are published before provider work begins. `PENDING` means the
first check has not completed; it is not a negative coverage result. `current_job`
is a compatibility field showing one running operation. `current_jobs` and
`lanes` show both independent queues (`WARRANTS` and `UNDERLYINGS`), their running
jobs, errors and remaining first checks. Each job includes its `lane`.
`pending_jobs` counts jobs without a first completed check across both queues.
It does **not** measure the repeat-refresh backlog. Top-level and per-lane
`due_jobs` count eligible waiting jobs, including first checks; `overdue_jobs`
count jobs whose scheduled repeat deadline has passed. `max_overdue_seconds`
reports the longest such delay. Running jobs are excluded from these waiting
counters. Status reads do not issue provider requests or reschedule work.

`DEFERRED` / `FRANKFURT_REQUEST_THROTTLED` means the local shared request budget
prevented a discovery request. It is neither an external HTTP failure nor a
negative coverage result. `retry_after_seconds` and `next_run_at` use the greater
of the scheduler spacing and the remaining shared provider cooldown, instead of
the full discovery interval. The next eligible lane pass performs the retry;
the deadline is not a guaranteed start time. `deferred_jobs` counts these waiting
jobs, including those whose retry deadline has not arrived yet. Successful
retries restore the normal discovery interval. Instrument 404s, invalid ISINs,
access failures and upstream rate limits retain their existing error/backoff
policy. No additional request budget or cache is created.

The workspace panel displays due/overdue counts and the longest delay for each
lane even when `pending_jobs` is zero. A five-minute configured refresh interval
is not a coverage or latency guarantee: at 15 seconds per slot, 52 single-slot
jobs already require 13 minutes, before discovery, additional listings or other
catalog work. Missing identity or coverage cannot be fixed by shorter intervals.

`held: true` identifies a product or underlying belonging to an open position. Failed discovery exposes the safe provider reason, for example
`FRANKFURT_ISIN_INVALID` or `FRANKFURT_PUBLIC_EMPTY_RESPONSE`, instead of only an
exception class. Missing quote observations alone cannot identify the discovery
failure; inspect both the mapping and quote jobs.

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '{running, current_jobs, lanes, pending_jobs, due_jobs, overdue_jobs,
         max_overdue_seconds, deferred_jobs, last_error,
         jobs: [.jobs[] | select(.held == true)
                | {name, isin, job, status, reason, quotes, source_attempts}]}'
```

An invalid catalog ISIN must be corrected against verified instrument evidence;
it is never guessed or automatically padded. A product outside the active catalog
(for example an inactive issuer) remains excluded and needs master-data review.

`AVAILABLE` in this view describes successful retrieval or mapping verification;
it does not assert a fresh or executable price.

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status | jq

curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '.jobs[] | {name, isin, job, status, reason, checked_at, next_run_at, quotes}'

curl -fsS \
  http://localhost:8000/api/v1/position-monitoring/trades/dd8338bd-a092-42c0-94c0-c068a9094f77/product-valuation \
  | jq '{selected_source, provider_identity, reference_price, quote_observed_at, analysis_usable, analysis_warning, source_attempts}'
```

The first batch may take several minutes because requests are deliberately paced.
For the other positions, no warrant IDs need to be entered: their active catalog
ISINs are processed in the same batch. Coverage is established by their actual
results, not assumed from their names or this document.

`POST /api/v1/market-data/refresh/run` wakes the scheduler for a catalog scan.
Existing job due times and provider budgets still apply. It returns 409 while
refresh is disabled. Provider errors and disabled mappings can be inspected in
status without exposing credentials.

Validation includes two different issuers without positions in a PostgreSQL
transaction, exact-identity rejection, disabled-mapping preservation, independent
intervals, new/deactivated catalog members, cache timestamp/freshness behavior,
leader shutdown and an indicative workspace browser flow. Live quotes for the
user's other products still require the user's local catalog and provider access.

For underlying catalog ISIN misses, refresh now corroborates exact ISIN Search
results against symbol and exchange catalogs before activating an existing listing
mapping. Verified alternative venues/currencies appear in `alternative_candidates`;
they require explicit listing/rule-basis review and are never substituted silently.
See [underlying mapping discovery](underlying-mapping-discovery.md#sparse-isin-catalogs-and-alternative-venues-2026-09-14)
for limits, account requirements, provenance and local verification.

## Independent warrant and underlying queues (2026-09-14)

The deployment diagnostics showed first-check pending jobs falling from 238 to
188 while all 52 held underlying mapping jobs still awaited their first result.
The worker was progressing through warrant jobs. A single serial queue placed
held warrants before held underlyings; Frankfurt's pacing/cooldown also governed
EODHD work. Completing a fast group could not start its next due run until the
entire mixed batch finished.

The scheduler now dispatches two independent, sequential workers under the same
PostgreSQL leader lock:

- `WARRANTS`: Frankfurt/Vontobel discovery and warrant quote resolution, preserving
  their ordering, existing provider cooldowns and shared website limits.
- `UNDERLYINGS`: EODHD mapping discovery and completed daily-price import, preserving
  mapping-before-import order and all existing identity/currency checks.

At most one worker per queue runs. Catalog scans dispatch only idle queues;
repeated scans or manual wake requests cannot duplicate a running queue. The
completed queue can execute newly due work on the next scan without waiting for
the other queue. No per-instrument task explosion or parallel HTTP burst is added
within a queue. Work already queued in the same group can still delay its next
run: intervals remain minimum completion-based pauses, not a portfolio-wide SLA.

`REQUEST_SPACING_SECONDS` now supplies a separate pacing clock for each queue.
It remains 15 seconds by default. EODHD continues to enforce its own shared API
budget, limiter and retries for all internal requests; Frankfurt's provider-wide
cooldown still governs the warrant queue. Requests to the independent providers
may therefore occur concurrently, while neither provider's limit is increased.
No new provider, subscription, secret or migration is required. The configured
API quota may be consumed earlier because unrelated website delays no longer
hold up EODHD work.

Shutdown, disablement or a failed catalog scan cancels and joins outstanding
workers. The leader probes its dedicated database connection before each scan;
a detected connection failure stops both workers before attempting unlock.
Normal shutdown joins workers before releasing the lock. Connection failure is
detected at these probes, not instantaneously. Newly inactive queued jobs are
removed on catalog rescan; a finishing removed job cannot recreate a stale job
entry. Already issued operations still rely on their existing provider/service
validation and transaction boundaries. The single-backend-process deployment
requirement remains in effect.

After deploying with `bash scripts/start-linux.sh --frankfurt`, verify progress:

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '{enabled, running, leader, scheduling_mode, last_error, current_jobs, lanes,
         basiswert_mapping_status: (
           [.jobs[] | select(.held == true and (.job | startswith("EODHD_MAPPING:")))]
           | group_by(.status)
           | map({status: .[0].status, anzahl: length})
         )}'
```

Expect `scheduling_mode: INDEPENDENT_WARRANT_UNDERLYING_LANES`. Underlying jobs can
now finish while the warrant queue is still busy. Two non-null current jobs are
allowed; a completed queue reports `running: false` until its next scan/run.
`PENDING` remains a first-result state, and a running first check is counted in
pending until it completes. The workspace refresh panel displays both queues
and marks both currently running jobs. A successful schedule is not evidence of
provider coverage: inspect mapping/import results and the position's monitoring
health separately.

Regression tests reproduce 52 underlying discoveries/imports completing and
running again while the first warrant request remains blocked, and the inverse
case with a stalled EOD import. They cover per-provider pacing, duplicate dispatch,
queued removal, cancellation, catalog failures, heartbeat failure and joining
both workers before leader unlock. The browser regression displays two concurrent
jobs while preserving indicative-valuation and no-order-permission warnings.
