# Warrant quote coverage and provider decision

## Root cause: DE000VH2LU21 / VH2LU2

The internal listing fix from PR 172 removed the dangerous `UNH` underlying-symbol mapping, but
did not create upstream coverage. Six non-empty official XSTU pre-trade snapshots contained no
record whose `Isin` was `DE000VH2LU21`. Empty later snapshots additionally masked the last good
file; PR 173 fixes that independent defect.

The product is verifiably listed in Börse Stuttgart's Freiverkehr, but the public Easy Euwax page
currently reports a **BidOnly** situation. Therefore listing existence does not imply inclusion in
the XSTU MiFIR delayed pre-trade download. The exact reason for omission is not published in the
feed contract; the evidence supports an upstream feed-coverage gap, not a local parser or symbol
problem. We must not invent an Euwax MIC or silently change the listing venue.

## Verified quote observation

On 2026-09-12 the official Vontobel Markets product page for the exact ISIN exposed a structured
`__NEXT_DATA__` product payload with:

- identifiers: ISIN `DE000VH2LU21`, WKN `VH2LU2`, Vontobel valor `148276720`;
- bid `0.24` EUR, ask `0.25` EUR;
- quote timestamp `2026-09-11T19:59:13Z`;
- `tradingHours.isOpen=false`.

This is an official issuer indication, not proof of an executable order-book quote. Freshness and
trading status remain explicit, and position valuation still uses BID only.

## Provider comparison

| Source | Exact identity / coverage | Quote fields | Access and delay | Decision |
|---|---|---|---|---|
| Vontobel Markets | ISIN/WKN verified; issuer-wide catalogue | Bid, ask, latest, timestamp, trading status | Public official structured page payload; no key or published limit; issuer indication | **Primary for Vontobel warrants**. Monitor with freshness guard; confirm exits at broker/exchange. |
| Börse Stuttgart / Easy Euwax | Exact ISIN/WKN and XSTU listing verified | UI has bid/ask and BidOnly status | Public UI; no stable documented quote API found | Evidence/diagnostics only; do not scrape. |
| XSTU delayed MiFIR pre-trade | ISIN absent in six non-empty snapshots | Bid, ask, timestamp, currency for covered rows | Official gzip/JSON; delayed | Optional fallback for exact ISIN+MIC matches; not coverage for this warrant. |
| gettex MUND/MUNC delayed | Files exist; this ISIN/schema not verified | Potential pre-trade bid/ask | Public gzip/CSV; up to 15 minutes | Fail closed pending exact schema and identity evidence. |
| Frankfurt / Tradegate | No reliable exact listing evidence found | Unknown | No suitable free supported API verified | Not configured; never infer a venue. |
| EODHD | No verified European structured-warrant coverage | Extended bid/ask is documented for US equities | Key/subscription | Excluded from Warrant fallback; retained for existing EOD capabilities. |
| Twelve Data / Finnhub / FMP | No documented coverage proof for this universe | Generic quotes only | Key/subscription | Unsuitable without written ISIN/venue/bid-ask coverage confirmation. |
| LSEG / Bloomberg / ICE / FactSet | Entitlement-dependent institutional coverage | Real-time bid/ask and venue fields by package | Paid licence and redistribution rights | Best independent production fallback after exact-ISIN coverage proof. |

Public evidence:

- Vontobel product: <https://markets.vontobel.com/de-de/produkte/hebel/optionsscheine/DE000VH2LU21>
- Stuttgart product: <https://easyeuwax.boerse-stuttgart.de/de-de/produkte/hebelprodukte/optionsscheine/stuttgart/vh2lu2>
- Vontobel Reference Data API: <https://api-docs.deritrade.com/>
- Authenticated Vontobel Pricing and Trading API: <https://api-docs.deritrade.com/api/quoting-trading/>

## Runtime strategy and fail-closed rules

`Warrant -> WarrantListing -> WarrantProviderMapping -> WarrantListingQuoteProvider` is the
governing path. A Vontobel mapping uses the ISIN as `provider_symbol` and `ISSUER` as the explicit
provider exchange code; it never overwrites the listing symbol or MIC.

Resolution order:

1. `VONTOBEL_MARKETS` issuer indication for an active exact mapping;
2. `BOERSE_STUTTGART_DELAYED` only when enabled and for an exact XSTU ISIN+MIC row.

EODHD is deliberately absent. Redirects, schema changes, identifier/WKN/currency mismatches,
invalid prices or timestamps, stale observations, missing BID, and inactive mappings yield no
usable valuation. Responses preserve provider, provider identity, provider exchange code, ISIN,
WKN, bid, ask, timestamp, source mode, trading status, and every source attempt.

### Closed-session freshness

`DE_WARRANT_SESSION_FRESHNESS_V1` distinguishes wall-clock age from the next expected German
warrant trading session. A quote that exceeds the ordinary one-hour limit is `LAST_AVAILABLE`
only when all of these conditions hold:

- the provider explicitly reports `CLOSED`;
- the observation is no earlier than one freshness window before the regular 22:00 Europe/Berlin
  close;
- no later weekday trading session should have completed;
- the next session's 08:00 opening plus a 15-minute grace period has not passed.

Weekends and the regular full-day Frankfurt/Xetra closures (New Year, Good Friday, Easter Monday,
1 May, 24-26 December, and 31 December) are skipped. After the next opening grace period the quote
is `STALE` again. `LAST_AVAILABLE` permits a clearly indicative BID valuation but always sets
`execution_usable=false`; an issuer indication also remains non-executable when fresh. Increasing
the general maximum quote age is deliberately avoided.

## Local activation and end-to-end check

Enable the adapter (no secret required):

```dotenv
TRADING_WORKSPACE_MARKET_DATA__VONTOBEL_MARKETS__ENABLED=true
```

Create an ACTIVE `warrant_provider_mappings` row through the deployment's administrative database
workflow for listing `8fd2a716-9a96-4c8b-ac20-521e96c18b32`, provider `VONTOBEL_MARKETS`, provider
symbol `DE000VH2LU21`, and exchange code `ISSUER`. This is operational configuration and is
intentionally not hardcoded by a migration.

Then query the trade owning warrant `8ee5ab84-86ce-491e-b4b0-d98a0379d0c3`:

```bash
curl -fsS http://localhost:8000/api/v1/position-monitoring/trades/<TRADE_ID>/product-valuation | jq
```

Expect `AVAILABLE` while the BID is fresh, or `LAST_AVAILABLE` for the immediately preceding close
while the market is closed. Other outcomes remain `STALE`, `MISSING`, `UNAVAILABLE`, or `ERROR`,
never a synthetic price.
