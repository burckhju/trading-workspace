# Frankfurt quotes: implementation and activation boundary

## Implemented scope

`FRANKFURT_QUOTES` is an opt-in provider behind the existing
`WarrantListingQuoteProvider` and `MultiSourceWarrantQuoteResolver`. It reads a
bounded JSON snapshot over HTTPS or an atomically replaced local JSON file.
It is tried before existing sources **for each eligible active listing**.
The existing cross-listing order remains unchanged; this is not a global
best-price aggregator. Historical evaluation/purchase listings are not rewritten.

This is a functional **normalized import boundary**, not a reverse-engineered
Frankfurt website API or a completed connection to a named vendor. An upstream
licensed vendor/exporter must supply the contract below. No production endpoint,
credentials, entitlement or live coverage has been verified here. The earlier
WKN research is not live-feed evidence and is not imported as active mappings.
No portfolio table is committed.

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

One shared snapshot is fetched, then prices, status/reason, venue, source,
observation timestamp and age are written per input row. An existing output is
never overwritten. Choose column names explicitly for differently named input
columns. This standalone diagnostic does not persist mappings or establish broker
tradability. Tests use synthetic payloads and HTTP mocks, not live-market claims.
The production data access and 135-WKN coverage remain activation prerequisites.
