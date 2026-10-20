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

Missing stock mappings first use the existing EODHD adapter's authenticated exchange
and active-symbol catalogs. Exact ISIN, row currency, stock type and venue are
required, with exactly one provider symbol. The sparse-ISIN fallback described below
can corroborate a missing catalog ISIN through the official Search API. Duplicate conflicting identities,
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
| `EODHD_PROVIDER_IDENTITY_ALREADY_MAPPED` | Review the reported owner listing and mapping; the provider identity is not reassigned automatically. |
| Provider authentication/quota/transport error | Resolve access or wait for the existing budget/cooldown; do not increase subscription automatically. |

## Regression coverage

Unit tests cover US venue discrimination, first mappings at single-MIC venues,
currency/ISIN/type mismatches, ADR identity, duplicates, stale evidence, workspace
scope, inactive master data, malformed catalogs, caching, concurrency and quota.
The PostgreSQL test exercises scheduled discovery at four venues, neutral
identity constraints, mapping audit, EOD persistence, repeated scans and disabled
mapping preservation with deterministic provider responses. Live account and
portfolio verification must occur in the user's deployment.

## Sparse ISIN catalogs and alternative venues (2026-09-14)

After an explicit same-currency venue decision, use the
[verified underlying venue switch](underlying-venue-switch.md). It stages and
imports the target data before changing the primary listing; automatic discovery
continues to leave the venue decision untouched.

A later 52-position deployment report showed 20 underlying discoveries with
`EODHD_ISIN_NOT_FOUND_ON_VENUE`, all on existing XETR/EUR listings. This proves
that the requested venue catalog did not return their ISINs. It does **not**
prove that the stocks are unavailable throughout EODHD, or whether their local
catalog rows have a missing ISIN. Both possibilities must be distinguished using
the configured account; the report did not contain those raw provider rows.

Automatic refresh now uses an additional, bounded verification path **only**
after `EODHD_ISIN_NOT_FOUND_ON_VENUE`:

1. Query the official Search API with the exact underlying ISIN (`limit=500`).
   Ignore names, local ticker guesses, other ISINs and Search's price fields.
2. Corroborate each candidate using the existing exchange and symbol catalogs.
   The candidate symbol must actually occur at that venue, in the same currency,
   as a stock. A missing catalog ISIN can be supplied by Search's exact ISIN;
   a conflicting catalog ISIN, currency, type or venue cannot be overridden.
3. Activate through the existing audited mapping administration only when the
   requested venue and currency have one unambiguous, corroborated identity.
   The next underlying EOD job then follows the existing import path. Existing
   mappings, including disabled ones, remain unchanged.
4. If that fails, expose checked alternatives in the refresh job. Even a verified
   alternative is **not** substituted into the existing primary listing. Different
   currencies require review of the rule price basis; even the same currency at a
   different venue requires an explicit listing decision. A US composite symbol
   still needs NASDAQ/NYSE symbol-catalog evidence to establish its MIC.

This extends identity verification within the existing provider boundary. It
creates no additional listings, switches no primary flags, changes no stop/target
values, converts no currencies, and writes no user-specific reference seeds.
No schema change is needed. A verified identity establishes a provider address,
not available EOD history, live prices, executable quotes or a successful monitoring
cycle. Warrant valuation and missing issuer coverage are separate paths.

Source: [EODHD Search API](https://eodhd.com/financial-apis/search-api-for-stocks-etfs-mutual-funds)
and the exchange catalog documentation linked above, checked 2026-09-14.

### Access and request limits

The path uses the configured EODHD account and its existing shared daily budget,
rate limiter and retries. No subscription change or additional secret is made.
Search consumes provider quota (the documentation lists one API call per request);
access to the requested markets/history remains account-dependent. Authentication,
authorization, quota and transport errors remain visible.

Successful search responses, including empty results, are cached for 24 hours
with at most 256 ISIN keys in the single backend process. Catalogs share their
existing 24-hour cache. Concurrent discoveries share a lock; repeated empty
searches do not consume quota each scan. Expiry, eviction or restart permits a
new request. Invalid payloads are not cached.

An exactly full 500-row Search response cannot establish uniqueness and blocks
activation. More than 12 candidates at the requested provider venue also blocks
activation. At most 12 candidate rows are checked across venues; additional
alternative candidates are explicitly reported as truncated. US candidates may
require two subvenue catalogs. A verified current listing returns immediately
without fetching unrelated foreign catalogs. Direct catalog success and existing
catalog conflicts do not trigger Search at all.

### Diagnostics and local verification

Deploy with the existing configuration:

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

The helper rebuilds/restarts the services and runs `alembic upgrade head`. Keep
`market_data.refresh.enabled` and `auto_configure` enabled. The first catalog
pass after restart performs discovery in the independent underlying queue.
It no longer waits for the warrant queue, but provider pacing and earlier jobs
within the same queue can still delay completion for a large portfolio.
An immediate status request may therefore still show pending jobs. See
[queue diagnostics](automatic-market-data.md#independent-warrant-and-underlying-queues-2026-09-14).
No per-instrument SQL repair or additional credentials are required to run the verification.

After discovery, inspect held underlying mappings:

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '[.jobs[]
         | select(.held == true and (.job | startswith("EODHD_MAPPING:")))
         | {name, isin, listing_id, status, reason, discovery_source,
            listing_mic, listing_currency, provider_identity,
            search_reason, search_retrieved_at, alternative_candidates}]'
```

| Result | Meaning / next action |
| --- | --- |
| `EODHD_MAPPING_ACTIVE`, source `EODHD_ISIN_SEARCH_AND_CATALOG` | Existing listing repaired using both official payloads. Check its subsequent `UNDERLYING_EOD` job for `COMPLETED_EOD_IMPORTED` and then monitoring health. |
| `EODHD_SEARCH_ISIN_NOT_FOUND` | Search also returned no exact ISIN. Verify master identity and request provider coverage evidence. |
| Candidate `identity_verified: true` | Symbol, currency and MIC are corroborated. This candidate has not automatically changed the primary listing or monitoring rules. |
| `requires_listing_review: true` | Alternative venue and/or currency; review and explicitly maintain the intended listing. |
| `requires_rule_currency_review: true` | Never compare this candidate's foreign-currency prices with existing thresholds without an explicit rule-basis decision. |
| Candidate `EODHD_SEARCH_CATALOG_CONFLICT` | Search and catalog disagree; no automatic activation. |
| Candidate `EODHD_SEARCH_SYMBOL_NOT_IN_VENUE_CATALOG` | Search alone does not prove the venue. For US candidates, one missing subvenue alongside a verified other subvenue is expected. |
| `EODHD_SEARCH_RESULT_LIMIT_REACHED` / `EODHD_SEARCH_CANDIDATE_LIMIT_REACHED` | Verification was incomplete; no automatic selection. |
| `EODHD_SEARCH_ALTERNATIVES_TRUNCATED` | Bounded, partial alternative list; no automatic selection. |

The mapping audit stores `EODHD_ISIN_CATALOG_V1` provenance in compact JSON:
`isin`, `ccy`, `mic`, `symbol`, `exchange`, `catalog`, `catalog_at`,
`exchanges_at`, `search`, `search_at`. The exchange metadata endpoint is always
`/exchanges-list/`. All three original retrieval timestamps are rechecked before
activation. They are metadata verification times, not quote times.

Regression tests cover absent versus conflicting catalog ISINs, exact ISIN and
ADR isolation, US subvenues, foreign-currency and same-currency alternatives,
ambiguous and unsafe symbols, result bounds, cache expiry/eviction/concurrency,
quota, scoped evidence and disabled mappings. The PostgreSQL regression exercises
scheduler discovery, audited mapping activation, EOD persistence and repeat scans
without changing the primary listing. Live coverage of the reported 20 stocks
still requires the user's configured deployment; tests use controlled payloads.
