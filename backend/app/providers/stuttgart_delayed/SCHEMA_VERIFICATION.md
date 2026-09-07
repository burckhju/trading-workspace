# Börse Stuttgart XSTU schema verification

The XSTU delayed pre-trade payload schema was verified on 2026-09-06 against the official Börse Stuttgart file `XSTU-pretrade-20260904T1311.json.gz` and re-verified locally on 2026-09-07 against `XSTU-pretrade-20260907T1849.json.gz`. The provider remains disabled by default; activation is explicit per deployment.

## Source boundary

The payload must originate from the official Börse Stuttgart XSTU pre-trade data. The official index is:

`https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/mifir-ii-delayed-data/xstu-pre-trade/`

Do not use screenshots, product pages, copied third-party samples, or inferred prices.

The adapter supports three transport modes that all feed the same verified parser and exact ISIN/XSTU identity checks:

- `index` — fetch the official Börse Stuttgart HTML index and its official `ddl.service.boerse-stuttgart.de` download link;
- `local_directory` — read the newest correctly named `XSTU-pretrade-YYYYMMDDTHHMM.json.gz` from a configured read-only directory;
- `direct_url` — fetch a configured absolute HTTPS URL that serves the latest official XSTU gzip payload, for example a controlled deployment mirror or object endpoint.

The `direct_url` mode is a transport option, not a license to substitute another market-data source. Operators are responsible for ensuring that the endpoint serves the unmodified official XSTU payload and that its use complies with the applicable data terms.

## Verified payload shape

The first inspected file contained 156,323 records in one top-level JSON array. A later official file from 2026-09-07 contained 26,526 records with the same relevant flat schema. The relevant fields are:

- `Isin` — instrument ISIN;
- `VenueOfPublication` — publication venue/MIC;
- `Bid` and `Ask` — separate numeric quote-side fields;
- `PriceCurrency` — quotation currency;
- `TransactionTime` — UTC ISO-8601 timestamp for quote records;
- `TransactionTimestamp` — present on non-quote/status records, not used for quote selection.

The production mapping is pinned to `records_path=$`, `Isin`, `VenueOfPublication`, `Bid`, `Ask`, `PriceCurrency`, and `TransactionTime` under schema version `xstu-pretrade-flat-2026-09-04`.

## Verified quote semantics

Records represent successive updates rather than one current row per listing. The adapter selects the newest matching quote by `TransactionTime`; it does not aggregate the best price across the file history.

Zero prices occur legitimately in the feed. A zero `Bid` or `Ask` means that quote side is unavailable and is mapped to `None`. Negative prices remain invalid. If multiple rows share the latest timestamp, quote sides may be combined only within that same timestamp; historical rows must not influence the result.

## Structural probe

From the `backend` directory run:

```bash
python -m app.providers.stuttgart_delayed.schema_probe /path/to/XSTU-pretrade-YYYYMMDDTHHMM.json.gz
```

The probe prints only structural metadata: candidate record-array paths, leaf field paths, observed JSON types, and name-based field hints. It intentionally does not print market-data values and does not modify application configuration.

## Deployment activation

`market_data.stuttgart_delayed.enabled` remains `false` by default. Choose one transport mode explicitly.

For Docker with a host or server directory containing official XSTU files:

```text
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=true
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__SOURCE_MODE=local_directory
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__LOCAL_DIRECTORY=/var/lib/trading-workspace/xstu
STUTTGART_DELAYED_SOURCE_DIRECTORY=/absolute/host/path/to/xstu-files
```

The Docker mount is read-only. The adapter selects the newest file by the timestamped official filename, not by filesystem modification time.

For a server-side controlled HTTPS endpoint or mirror that always serves the latest official XSTU gzip payload:

```text
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=true
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__SOURCE_MODE=direct_url
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__DIRECT_URL=https://market-data.example/xstu/latest.json.gz
```

The historical `index` mode remains available, but Börse Stuttgart's Cloudflare-protected HTML index returned HTTP 403 from both hosted CI and one verified local environment. Do not bypass Cloudflare or hard-code expiring signed CloudFront URLs. Prefer `local_directory` or a controlled `direct_url` transport when automated index access is unreliable.
