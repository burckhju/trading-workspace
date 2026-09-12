# Frankfurt quotes: implementation and activation boundary

## Implemented scope

`FRANKFURT_QUOTES` is an opt-in provider behind the existing
`WarrantListingQuoteProvider` and `MultiSourceWarrantQuoteResolver`. It reads a
bounded JSON snapshot over HTTPS or an atomically replaced local JSON file.
The normalized bid/ask import is tried before existing sources **for each eligible active listing**.
The existing cross-listing order remains unchanged; this is not a global
best-price aggregator. Historical evaluation/purchase listings are not rewritten.

There are now two explicit capabilities behind this provider:

| Mode | Actual input | Capability | Position valuation |
| --- | --- | --- | --- |
| `public_website` | Official website REST endpoint, direct ISIN/XSC query | Last trade with exchange timestamp; no bid/ask | Diagnostic API/CSV only; never selected as a warrant quote |
| `https_json` / `local_file` | Application-owned normalized snapshot | Validated bid/ask and side timestamps | Monitoring only, always `execution_usable=false` |

The normalized import still requires an approved upstream vendor/exporter.
The public website mode needs no API key for the tested request, but is an
undocumented website interface without a verified production SLA or rate limit.
Both modes remain disabled by default and require usage approval. No master data,
portfolio tables, active mappings, subscription or paid access are created.

## Git and live findings (2026-09-12)

Base `main`: `e138125f16ec3d5a591fce694739fcad9aeaea89`. That revision already
implemented the normalized Frankfurt importer, but had no actual upstream
retrieval. It also labelled Frankfurt monitoring quotes non-executable only in
diagnostics: product valuation could still set `execution_usable=true` for an
OPEN Frankfurt quote. The provider-level exclusion now applies in valuation too,
including if the upstream source-mode label is missing.
Before the PR, the branch was updated to `43cc9899c9b3a90ec1af0cb2e7ef6460f5759e9b`,
including PR #183 (strike currency) and #184 (Docker checkout permissions).

The [official product page](https://live.deutsche-boerse.com/derivative/de000vh2lu21-call-auf-unitedhealth-group)
identifies ISIN `DE000VH2LU21`, WKN `VH2LU2`, issuer Vontobel and website venue
code `XSC`. Its structured application data identifies the instrument type as
`derivative`. No underlying symbol search is needed. The page was inspected for
discovery; the implementation reads JSON directly and does not scrape HTML.

A direct anonymous GET to the actual website endpoint succeeded:

```text
https://api.live.deutsche-boerse.com/v1/data/price_information/single?isin=DE000VH2LU21&mic=XSC
```

Observed response fields (historical test evidence, not a current quote):

```json
{
  "isin": "DE000VH2LU21",
  "mic": "XSC",
  "currency": {"originalValue": "EUR"},
  "lastPrice": 0.231,
  "timestampLastPrice": "2026-09-11T19:43:41+02:00"
}
```

This is a **last trade**, not bid, ask or issuer indication. The source does not
return a WKN in this endpoint; `record.wkn` therefore stays null. The input CSV's
WKN is operator-supplied identity information, not independently verified here.
No feed-generation timestamp, bounded delay, quoted sizes or current trading
status is supplied. These remain null/UNKNOWN rather than being inferred from
download time, turnover, minimum tradable unit or published trading hours.

The website JavaScript calls `/data/quote_history_derivatives` with ISIN, mic,
UTC from/to, offset and limit. Requests for the target's Friday session returned
HTTP 200 with `{}`. The website's real-time quote component uses a separate MDS
WebSocket/token service; an anonymous token request also returned `{}`. Neither
result establishes missing product coverage, market closure or usable feed access.
No website request-signature emulation or access-control workaround is implemented.

`XSC` is a **provider code**, not an ISO MIC. The [official market contact page](https://www.cashmarket.deutsche-boerse.com/cash-en/your-contacts)
identifies Frankfurt as `XFRA`. The [ISO register](https://www.iso20022.org/10383/iso-10383-market-identifier-codes)
also contains separate technical identifiers `XSCO`, `XSC1/2/3` and `XXSC`;
we do not guess a product-level segment from these names. A verified internal
Frankfurt listing uses `XFRA`, while this public mode requires mapping exchange
code **`XSC`** and preserves that code in every diagnostic result. The normalized
import continues to require its existing verified `XFRA` mapping.

## Public retrieval configuration and verification

`docker/frankfurt-public.env.example` configures the fixed official host and source
mode without accepting usage terms or activating access. Review the website's
[disclaimer and data-download terms](https://live.deutsche-boerse.com/en/disclaimer-en)
for your intended use. A free browser page or non-commercial historical download
does not by itself verify rights for a commercial service or automated non-display
use. The configuration gate is retained until the operator confirms the intended
usage; no paid action is required merely to review this implementation.

After that review, copy the example to `docker/frankfurt.env` **only if that file
does not already exist**, configure it, and set ENABLED/USAGE_APPROVED/
CONTRACT_VERIFIED true. The last flag confirms only the observed Last-Trade JSON
contract; it does not assert access to a bid/ask feed. Do not set a snapshot URL,
allowed host, local file or bearer token in public mode: conflicting vendor
configuration is rejected before network I/O.

For the existing listing diagnostic, first create or identify a verified ACTIVE
Frankfurt listing through the product administration and an
ACTIVE `FRANKFURT_QUOTES` mapping: provider symbol = exact ISIN, exchange code =
`XSC`, validated timestamp set, matching workspace. Do not change the existing
XSTU listing into a Frankfurt listing or rewrite the trade's historical listing.
Warrant mappings currently use `warrant_provider_mappings` and its existing
repository/admin procedure; the `/market-data/provider-mappings` API administers
underlying listings and must not be used for these warrant mappings. This change
does not introduce an automatic mapping writer.
No database mutation is necessary for the standalone CSV probe below.

```bash
git switch main
git pull --ff-only
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml build backend frontend
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml up -d database
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml run --rm backend alembic upgrade head
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml up -d backend frontend
curl -fsS http://localhost:8000/api/v1/position-monitoring/quote-sources/frankfurt/health | jq
```

No migration is introduced by this change. Health must show `public_website`,
`bid_ask_supported=false`, `delay_seconds=null`, and `execution_usable=false`.
Configuration readiness is not a live-data success signal.

Run the real retrieval through the installed client for this exact instrument,
without guessing UUIDs or changing user data. The temporary input is inside the
container; `mktemp` prevents overwriting an existing file or report:

```bash
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml exec -T backend sh -eu -c '
  probe_dir=$(mktemp -d)
  printf "ISIN;WKN\nDE000VH2LU21;VH2LU2\n" > "$probe_dir/input.csv"
  python -m app.providers.frankfurt_quotes.probe \
    --input "$probe_dir/input.csv" --output "$probe_dir/result.csv"
  cat "$probe_dir/result.csv"
'
```

Expected semantics: source `deutsche-boerse-public`, provider exchange `XSC`,
source mode `OFFICIAL_WEBSITE_LAST_TRADE`, last price/time when returned,
bid/ask empty, delay unknown, execution false. A fresh last trade is INSUFFICIENT
with `FRANKFURT_POST_TRADE_ONLY`; an old one is STALE with
`FRANKFURT_LAST_TRADE_STALE`. `{}` is an error (`FRANKFURT_PUBLIC_EMPTY_RESPONSE`),
never READY or proof that a security does not exist. This public mode is skipped
by the bid/ask resolver, so valuation does not waste requests on known Last-only
data; Vontobel and the other appropriate sources continue independently.

```bash
curl -fsS \
  'http://localhost:8000/api/v1/position-monitoring/trades/dd8338bd-a092-42c0-94c0-c068a9094f77/product-valuation' | jq
```

This user's live database/container cannot be accessed from the repository work
environment. The above deployed check must be run there; mocked route tests and
the public HTTP observation do not establish a completed test of that database.
In the work environment the public HTTP response was retrieved with curl and
validated through the new parser. The default Python transport could not make a
direct external connection there; the environment requires a SOCKS proxy whose
optional Python dependency is absent. No sandbox/network workaround or proxy
configuration is added to production code to hide that validation limitation.

## Bid/ask access still needed: user and cost decision

The best verified Frankfurt-specific candidate is the dedicated
[Börse Frankfurt Certificates and Warrants data product](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/spot-markets/B-rse-Frankfurt-Certificates-and-Warrants-1341024):
it explicitly includes traded prices, best bid/ask and volumes. The product's
information fee is currently described as free until further notice. This is
not a promise of free connectivity, a free vendor API or unrestricted usage.
Xetra Core's inclusion of these instruments explicitly excludes their best bid/ask.

Before purchasing or activating anything, obtain confirmation from Deutsche
Börse Market Data Services or an entitled distributor for:

1. Coverage of `DE000VH2LU21` and the actual portfolio by ISIN, including Frankfurt
   warrant best bid/ask, sizes and exchange timestamps (not only last trades).
2. A technical endpoint/exporter for the dedicated information product. The
   [feed overview](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Real-time-data-feeds)
   describes CEF Core access; its listed Cloud Stream API products do not establish
   Frankfurt warrant coverage. No undocumented CEF decoder is invented here.
3. Rights for the intended private/commercial automated monitoring and any future
   non-display/trading use, plus connection/vendor charges and request limits.
   The [agreements page](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/agreements)
   separates dissemination, non-display/trading and connectivity agreements.
4. The concrete service URL, authentication method/secret, delay/SLA and mapping
   of provider venue codes to the actual Frankfurt listing. None are assumed.

No exact subscription price, API-key name or confirmed warrant entitlement was
available to verify. Until supplied, the existing normalized import is ready for
an approved exporter; Frankfurt public last trades cannot unlock order decisions.

## Why no guessed public bid/ask endpoint

Primary-source review on 2026-09-12:

- The official information product includes traded prices, best bid/ask and volumes:
  https://www.mds.deutsche-boerse.com/mds-en/real-time-data/spot-markets/B-rse-Frankfurt-Certificates-and-Warrants-1341024
- The delayed service describes 15-minute delay and once-per-minute publication,
  but specifically lists Certificates and Warrants **Post-Trade**:
  https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Delayed-data
  https://mfs.deutsche-boerse.com/DXSC-posttrade
- The website describes five recent realtime quotes and a historical archive
  updated at least 20 times daily, not a documented production API:
  https://live.deutsche-boerse.com/zertifikate/historische-daten/historische-quotes

Consequently `LAST_TRADE` is inspectable but never becomes a bid/ask quote.
There is no HTML scraping, anti-bot bypass, subscription or paid service activation.
Pricing and permitted non-display use must be established with the vendor;
a zero exchange data fee does not establish free technical access or usage rights.

## Application-owned normalized snapshot contract

`frankfurt-quotes-v1` is **our schema**, not a claimed Deutsche Boerse wire format.
A producer sends exactly one record per ISIN/MIC in a snapshot, with uppercase
identifiers, ISO currency and explicit UTC/offset timestamps. Vendor/segment
venue codes must be reconciled upstream to verified Frankfurt operating MIC
`XFRA`; `XETR`, `XSTU`, `.F` symbols and exchange names are not aliases here.

Synthetic example, not a market observation:

```json
{
  "schema_version": "frankfurt-quotes-v1",
  "source": "approved-vendor",
  "generated_at": "2026-09-11T12:00:00Z",
  "delay_seconds": 0,
  "records": [
    {
      "isin": "DE000VH2LU21",
      "wkn": "VH2LU2",
      "mic": "XFRA",
      "currency": "EUR",
      "kind": "BID_ASK",
      "bid": "0.32",
      "ask": "0.33",
      "bid_at": "2026-09-11T11:59:59Z",
      "ask_at": "2026-09-11T11:59:59Z",
      "bid_size": 1000,
      "ask_size": 2000,
      "trading_status": "OPEN"
    }
  ]
}
```

Sizes are optional quantities in units of this security, not trade volume,
minimum quoting obligations or currency notional. Missing sizes are not guessed.
The detailed probe exposes them without granting execution permission.
Trading status is `OPEN`, `CLOSED`, `SUSPENDED` or `UNKNOWN`; the adapter does not
invent calendars/holidays or infer that a market is open from a recent download.

For `LAST_TRADE`, use `last_price` and `last_at`; the reason is
`FRANKFURT_POST_TRADE_ONLY` and the provider result contains no quote.
Unknown fields/schema versions, duplicate JSON keys, non-finite/non-positive
prices, contradictory identity and duplicate matching records fail closed.
Unrelated instruments' malformed price fields do not contaminate a valid target.

## Freshness, provenance and fallback

The declared feed delay and the actual age of the **older bid/ask side** must
both fit `max_quote_age_seconds` (default 900; cannot exceed 900). Generated,
retrieved and side timestamps must be consistent. Every read reassesses current
age, including cache hits; cached retrieval time never resets quote age.
900.000 seconds passes, 900.001 seconds fails. A feed released after 15 minutes
and polled once per minute may therefore exceed the strict budget. It does not
receive an undocumented extra minute. The configured `feed_delay_seconds`
must match the snapshot declaration; this also controls the attempt's delayed flag.

Closed/old quotes are inspectable with explicit reasons but not selected as
current Frankfurt quotes. Existing other providers' LAST_AVAILABLE and stale
indicative-analysis behavior is unchanged. Rejected Frankfurt results allow
fallback. The optional provider-neutral `reason_code` is propagated into
`source_attempts`. Missing active mapping is skipped before network I/O;
an existing inconsistent mapping is an error. No read creates/modifies master
data, trades, positions or mappings.

Frankfurt quotes remain monitoring-only. `execution_usable` is always false.
No broker transport, order operation or automatic execution approval is added.

## Activation

Use the existing nested settings mechanism in the backend environment:

```dotenv
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ENABLED=false
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__USAGE_APPROVED=false
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__CONTRACT_VERIFIED=false
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__SOURCE_NAME=approved-vendor
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__SOURCE_MODE=https_json
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__SNAPSHOT_URL=https://feed.example/portfolio-quotes
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ALLOWED_HOST=feed.example
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__FEED_DELAY_SECONDS=0
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__MAX_QUOTE_AGE_SECONDS=900
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__REFRESH_INTERVAL_SECONDS=15
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__TIMEOUT_SECONDS=10
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__MAX_RESPONSE_BYTES=8000000
# Inject BEARER_TOKEN only through deployment secret configuration when required.
```

`feed.example` is deliberately non-operational. Confirm usage rights, schema
conversion, source identity, instrument coverage and timestamps before setting
all three activation flags true. Never commit tokens or put them in URLs.
For local ingestion set `SOURCE_MODE=local_file` and
`LOCAL_FILE=/var/lib/trading-workspace/frankfurt/quotes.json`; mount the containing
directory read-only and have the producer atomically replace the file.

For Docker, copy `docker/frankfurt.env.example` to `docker/frankfurt.env`
without overwriting an existing file, configure it, and apply the opt-in override:

```bash
docker compose --env-file docker/.env \
  -f docker/compose.yml -f docker/compose.frankfurt.yml up --build -d
```

Use the existing Linux startup procedure first for database initialization and
migrations. The override is required on subsequent Compose commands for this
source; the ordinary startup helper does not automatically select it.
Do not overwrite `docker/.env`. For the local-file mode, place snapshots in
`docker/frankfurt-data/`, which the override mounts as a read-only directory.

Verify an ACTIVE WarrantListing at the actual Frankfurt venue and an ACTIVE
WarrantProviderMapping with provider `FRANKFURT_QUOTES`, symbol exactly the master
ISIN, exchange `XFRA` and `validated_at` set. All workspace owners must match.
No WKN-to-ISIN inference or automatic activation from the research sheet occurs.
The provider enum uses the existing VARCHAR mapping; no new DB tables are added.

The application container shares one adapter/cache per process. Concurrent reads
share a download, refreshed on demand at most every 15 seconds by default.
Public mode keys cache entries by ISIN (bounded to 256 entries) with one shared
request budget across all instruments. Cached timestamps are never refreshed.
Another uncached instrument within that interval receives REQUEST_THROTTLED;
the CSV probe waits one configured interval and retries once. This conservative
local limit is not a claim about the provider's unpublished rate limits.
Failures back off at least 60 seconds. There are no redirects, aggressive retries
or silent reuse of an old success after failure. Timeout and decoded byte limits
apply. Multiple workers need a shared upstream budget/gateway; throttling here is
process-local. A snapshot is portfolio-sized (at most 10,000 records), not a full
1.8-million-product exchange dump. No automatic background schedule is added.

## APIs and coverage probe

```text
GET /api/v1/position-monitoring/quote-sources/frankfurt/health
GET /api/v1/position-monitoring/quote-sources/frankfurt/listings/{listing_id}?workspace_id={workspace_id}
GET /api/v1/position-monitoring/trades/{trade_id}/product-valuation
```

Health reports configuration and transport diagnostics, not verified live
coverage. `CONFIGURED_NOT_PROBED` never promises a valid current quote.
The detailed probe reports status/reason, source, timestamps, actual age, declared
delay, optional sizes, record, correlation and listing identity. It exposes no
configured endpoint, local path or token. Usable current quotes flow through the
existing product-valuation API/UI; no separate frontend screen is added.

A verified ISIN column is required for each CSV row. Missing ISIN receives
`ISIN_REQUIRED_NO_WKN_GUESSING`. The original table is never modified:

```bash
cd backend
python -m app.providers.frankfurt_quotes.probe \
  --input /data/verified-instruments.csv \
  --output /data/frankfurt-coverage-new.csv \
  --delimiter ';' --isin-column ISIN --wkn-column WKN --currency EUR
```

In normalized mode one shared snapshot is fetched, then prices, status/reason, venue, source,
observation timestamp and age are written per input row. An existing output is
never overwritten. Choose column names explicitly for differently named input
columns. This standalone diagnostic does not persist mappings or establish broker
tradability. Tests use synthetic payloads and HTTP mocks, not live-market claims.
In public mode each exact ISIN is requested within the shared rate budget and
Last-only provenance is exported separately. Production bid/ask data access and
135-WKN bid/ask coverage remain unverified prerequisites.
