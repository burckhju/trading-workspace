# Automatic underlying mappings: verified catalog evidence

## Incident and cause

The reported portfolio had values for all 20 warrant positions, but eight
underlying monitoring checks returned `NO_ACTIVE_MAPPING`. Their refresh jobs
were blocked at `UNAMBIGUOUS_ISIN_CURRENCY_VENUE_MATCH_REQUIRED`; subsequent EOD
imports therefore returned `VALIDATED_EODHD_MAPPING_REQUIRED`. All eight had an
ISIN, automatic configuration was enabled, and no inactive mapping was reported.
This is a separate path from warrant reference valuation and quote freshness.

Previously, discovery accepted an ISIN search result only when other active
workspace mappings associated its provider exchange code with exactly one venue.
That cannot establish the first venue mapping. Furthermore, `US` is a composite
provider code: existing NYSE and NASDAQ mappings can make that historical
association ambiguous, while only one known venue can incorrectly exclude the
other. The old generic rejection did not identify which condition failed.

The supplied diagnostics do not include each listing's MIC/currency or raw
provider candidates. They prove the blocked discovery path, not that every local
listing is correct or that all eight instruments are covered. Deployment must
establish those facts using the configured account. No user-specific ISIN,
symbol, mapping or venue is seeded by this change.

## Decision and identity checks

Missing stock mappings use the existing EODHD adapter's authenticated exchange
and active-symbol catalogs. Exact ISIN, row currency, stock type and venue are
required, with exactly one provider symbol. Duplicate conflicting identities,
unverified segments and missing ISINs block creation. An ADR is never replaced
by the ordinary share, nor a stock by an index. Local ticker names are not evidence.

`exchanges-list` supplies provider codes and operating MICs. A single-MIC code
requires the symbol row to identify that exchange. The US catalog additionally
requires its row's `Exchange` to be `NASDAQ` or `NYSE`, matching `XNAS` or `XNYS`.
Discovery queries the documented venue sublist but retains `US` for EOD requests.
Other composite codes and segment MICs need separate verification before support.
Source: [EODHD exchange catalogs](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours).

The two US label/MIC associations were checked on 2026-09-13 against the
[ISO 10383 registry](https://www.iso20022.org/market-identifier-codes):
NASDAQ — ALL MARKETS (`XNAS`) and NEW YORK STOCK EXCHANGE, INC. (`XNYS`). This
does not create global reference data or equate all US execution venues.

Existing `ProviderMappingAdministrationService`, venue reconciliation, neutral
instrument identities and audit events remain authoritative. A scoped resolver
rechecks the current workspace/listing/underlying/venue and the catalog evidence
age during validation. The mapping validation message and audit retain ISIN,
currency, MIC, provider identity, catalog endpoint and retrieval times. Catalog
evidence is scoped to one listing; it does not rewrite historical venue evidence.
Existing mappings are preserved, including intentionally disabled mappings.

## Access, quota and freshness

Use the already configured EODHD key; no new secret or subscription is enabled.
According to the [catalog API documentation](https://eodhd.com/financial-apis/exchanges-api-list-of-tickers-and-trading-hours),
these endpoints are included in all plans and consume one API call per request.
The adapter's configured budget, reserve, limiter and retry policy apply. Valid
catalogs are cached for 24 hours with concurrent requests coalesced. The first
needed venue incurs a symbol-list request plus the shared exchange-list request;
retries, expiration and process restarts can incur further calls. Empty exchange
catalogs and malformed payloads are rejected. Empty symbol lists establish no
coverage. Cached catalogs are not reused after expiry or silently promoted to
verified new observations. No account limits are raised automatically.

The resulting prices are completed EOD prices for underlying monitoring. They
do not become warrant bid/ask, live prices or execution permission. Existing
indicative product values and their source/freshness warnings remain available.

## Local deployment and acceptance

With refresh, auto-configuration and EODHD already enabled:

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

The helper rebuilds/restarts containers and runs `alembic upgrade head`. No new
migration or manual mapping activation is required. Restarting clears the
process-local schedule, so missing mappings are checked in the first batch;
held instruments are prioritized. Allow the batch to finish at the configured
request spacing. Opening the browser is unnecessary.

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '{running, current_job, pending_jobs,
      jobs: [.jobs[] | select(.held == true)
        | select(.job | startswith("EODHD_MAPPING:") or startswith("UNDERLYING_EOD:"))
        | {name, isin, listing_id, status, reason, listing_mic, listing_currency,
           provider_identity, provider_exchange_code, candidate_currencies,
           catalog_endpoint, catalog_retrieved_at, processed}]}'
```

Success is `EODHD_MAPPING_ACTIVE` followed by `COMPLETED_EOD_IMPORTED`, then
monitoring health `OK` when the other monitoring prerequisites are satisfied.
Later scans report `EXISTING_MAPPING_PRESERVED`. `AVAILABLE` alone is not proof
of current or executable prices. The eight previously affected names were
Thales, General Dynamics, Constellation Energy, Lam Research, TSMC ADR, Lonza,
Vertiv and Nasdaq Inc. Do not infer their listing markets from these names.

| Discovery reason | Required next step |
| --- | --- |
| `EODHD_ISIN_NOT_FOUND_ON_VENUE` | Check current master ISIN and listing; obtain provider coverage evidence. Do not infer a replacement identity. |
| `EODHD_LISTING_CURRENCY_MISMATCH` | Compare `listing_currency` and `candidate_currencies`; correct master data only after verifying the intended listing. |
| `EODHD_VENUE_NOT_IN_CATALOG` | Verify the local MIC and provider coverage. |
| `EODHD_VENUE_DETAIL_UNSUPPORTED` | Verify a specific instrument venue for the composite/segment before extending support. |
| `EODHD_VENUE_CATALOG_AMBIGUOUS` / `EODHD_STOCK_IDENTITY_AMBIGUOUS` | Resolve conflicting provider evidence; no automatic selection. |
| `EODHD_INSTRUMENT_VENUE_MISMATCH` | Provider row does not substantiate the requested venue. |
| `EODHD_STOCK_TYPE_REQUIRED` / `EODHD_PROVIDER_SYMBOL_UNSUPPORTED` | Verify provider identity/type; no substitution or unsafe request path. |
| `EXISTING_MAPPING_PRESERVED` with `BLOCKED` | Review the existing disabled/unvalidated mapping explicitly. |
| Provider authentication/quota/transport error | Resolve access or wait for the existing budget/cooldown; do not increase subscription automatically. |

## Regression coverage

Unit tests cover US venue discrimination, first mappings at single-MIC venues,
currency/ISIN/type mismatches, ADR identity, duplicates, stale evidence, workspace
scope, inactive master data, malformed catalogs, caching, concurrency and quota.
The PostgreSQL test exercises scheduled discovery at four venues, neutral
identity constraints, mapping audit, EOD persistence, repeated scans and disabled
mapping preservation with deterministic provider responses. Live account and
portfolio verification must occur in the user's deployment.
