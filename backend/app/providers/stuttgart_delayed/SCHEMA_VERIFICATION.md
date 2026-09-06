# Börse Stuttgart XSTU schema verification

The XSTU delayed pre-trade payload schema was verified on 2026-09-06 against the official Börse Stuttgart file `XSTU-pretrade-20260904T1311.json.gz`. The provider remains disabled by default because transport from hosted/cloud environments to the Börse Stuttgart index and short-link endpoints can be rejected with HTTP 403.

## Source boundary

Use only the official Börse Stuttgart XSTU pre-trade download page:

`https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/mifir-ii-delayed-data/xstu-pre-trade/`

For future re-verification, download a recent `XSTU-pretrade-*.json.gz` file through the official Börse Stuttgart download path. Do not use screenshots, product pages, mirrors, or copied third-party samples.

## Verified payload shape

The inspected file contained 156,323 records in one top-level JSON array. The relevant flat fields were:

- `Isin` — instrument ISIN;
- `VenueOfPublication` — publication venue/MIC;
- `Bid` and `Ask` — separate numeric quote-side fields;
- `PriceCurrency` — quotation currency;
- `TransactionTime` — UTC ISO-8601 timestamp for quote records;
- `TransactionTimestamp` — present on the non-quote/status records inspected, not on normal quote records.

The production mapping is therefore pinned to `records_path=$`, `Isin`, `VenueOfPublication`, `Bid`, `Ask`, `PriceCurrency`, and `TransactionTime` under schema version `xstu-pretrade-flat-2026-09-04`.

## Verified quote semantics

The inspected payload contained 22,335 distinct `(Isin, VenueOfPublication)` keys and up to 184 records for one key, so records represent successive updates rather than one current row per listing. The adapter must select the newest matching quote by `TransactionTime`; it must not aggregate the best price across the entire file history.

`TransactionTime` was present on 155,595 records and always had the shape `YYYY-MM-DDTHH:MM:SS.ffffffZ`. The remaining 728 records had no `TransactionTime`, had neither a positive bid nor a positive ask, and used `TransactionTimestamp` instead. Those records are ignored for quote selection.

Zero prices occur legitimately in the feed. A zero `Bid` or `Ask` means that quote side is unavailable and is mapped to `None`. Negative prices were not observed and remain invalid. If multiple rows share the latest timestamp, quote sides may be combined only within that same timestamp; historical rows must not influence the result.

## Structural probe

From the `backend` directory run:

```bash
python -m app.providers.stuttgart_delayed.schema_probe /path/to/XSTU-pretrade-YYYYMMDDTHHMM.json.gz
```

The probe prints only structural metadata: candidate record-array paths, leaf field paths, observed JSON types, and name-based field hints. It intentionally does not print market-data values and does not modify application configuration.

## Activation boundary

The schema mapping is verified and committed, but `market_data.stuttgart_delayed.enabled` remains `false` by default. Before enabling it in a deployment, verify from that deployment environment that both the official XSTU index and its `ddl.service.boerse-stuttgart.de` download link can be fetched reliably. Hosted CI runners observed HTTP 403 responses from those endpoints even though a directly resolved official file was downloadable.

If the official transport path is not reliable from the target runtime, keep the provider disabled. Do not hard-code signed CloudFront URLs or bypass the official source boundary in production configuration.
