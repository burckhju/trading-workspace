# Automatic market-data refresh

The active workspace catalog drives discovery and retrieval. An open position is
not required. There are no per-product UUID commands and no hardcoded user
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

- New active catalog records are detected on the next scan, normally within
  30 seconds after the previous batch. Inactive instruments, inactive listings
  and disabled mappings are not reactivated.
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
  be created only if search returns an unambiguous exact ISIN, stock type, currency
  and exchange association. Exchange/MIC evidence comes from existing validated
  workspace mappings through the venue-reconciliation service. Missing ISINs,
  missing active listings, unknown venue associations and contradictory mappings
  remain blocked with a reason. Symbol similarity alone is never sufficient.
- Daily imports use the existing idempotent persistence path. Initial history is
  up to 400 calendar days; later imports overlap seven days to capture corrections.
  No EOD price is converted into a warrant bid/ask or an execution permission.
- Successful issuer responses and Frankfurt observations are cached per identity;
  Stuttgart's large payload is shared. Quote eligibility is checked before cache
  access. Original quote and retrieval timestamps remain unchanged, while age is
  reassessed at read time. A browser visit is not needed to initiate background
  retrieval.
- Workspace cards display available indicative reference valuations as well as
  normal bid valuations, with warnings and source/time information. The existing
  execution restrictions remain in effect.

Intervals are minimum pauses after a job finishes. Provider pacing, retries and
large catalogs can delay a subsequent run. The global Frankfurt request budget
still applies; changing the instrument does not reset it. Individual failures do
not stop other jobs. Missing discoveries retry at the discovery interval.
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
