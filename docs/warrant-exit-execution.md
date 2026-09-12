# Safe warrant exit and execution architecture

## Status

Decision record for automated exit decisions on held warrants and other structured products.
Live order submission is **out of scope and disabled by design**. The implemented domain stops at a manual-approval order proposal.

## Quote semantics

The system must keep these states separate:

1. **Monitoring quote** — sufficient to display/observe a position.
2. **Decision quote** — sufficiently fresh and validated to evaluate an exit rule, but not necessarily executable.
3. **Executable quote** — broker/venue-bound bid/ask with timestamp, size and venue identity suitable for an order proposal.
4. **Order acknowledgement** — broker acceptance/rejection of an order intent.
5. **Execution/fill** — actual execution state and quantity/price.

An issuer indication, including the official Vontobel product-page quote, is at most a monitoring/decision quote. It must never be promoted to executable merely because it has a bid and ask.

## Current provider assessment (2026-09-12)

### Vontobel Markets public product page

The existing adapter is useful for exact ISIN/WKN identity, bid/ask, timestamp, trading status and issuer provenance. The adapter itself correctly labels the source as `OFFICIAL_ISSUER_INDICATION` and warns that it is not an executable exchange order-book quote. It has no broker position, executable size, order acknowledgement or fill channel. **Use: monitoring/decision input only.**

The example `DE000VH2LU21` / `VH2LU2` is publicly listed by Vontobel as a UnitedHealth Group call warrant. This confirms issuer identity but not broker tradability or executable liquidity.

### Interactive Brokers TWS API

IBKR documents `WAR` as a warrant security type, derivative contract lookup, live/delayed market data, contract-specific valid exchanges/order types and separate paper/live API sessions. It is therefore a technically credible broker adapter candidate. However, public documentation alone does not prove that the specific German retail warrant `DE000VH2LU21` is available to the user's account, nor that a particular venue provides executable size for it. That must be resolved after authentication by contract search and entitlement checks. **Use now: architecture target, not assumed coverage.**

Required external validation before enabling even paper integration for this instrument: resolved broker contract/conId, exact ISIN identity, valid exchange(s), currency, market-data entitlement, bid/ask plus sizes, trading schedule, supported order types and actual paper-account support for that contract.

### Saxo OpenAPI

Saxo documents instrument discovery restricted by the authenticated user's access rights, instrument details with supported order types, and order/portfolio APIs including data structures for options, warrants and structured products. This makes it another credible execution-adapter candidate. As with IBKR, public docs do not establish exact availability of `DE000VH2LU21` for a particular account. **Use now: secondary architecture candidate pending authenticated instrument lookup.**

### Vontobel deritrade

Public Vontobel material describes deritrade primarily as a multi-issuer platform for designing and issuing bespoke structured products for professional/intermediary workflows. That is not evidence of a retail broker execution API for an already-issued warrant such as `DE000VH2LU21`. **Do not treat it as the execution path without a contractual/API entitlement proving this use case.**

## Architecture decision

Reuse existing position-monitoring and market-data boundaries. Add execution concepts without conflating identities:

`Open Position -> Position Snapshot -> Executable Quote Resolver -> Exit Policy -> Risk/Data Quality Gates -> Order Proposal -> Manual Approval / Paper Broker -> Broker Order -> Fill Reconciliation -> Audit Trail`

Identity boundaries:

- internal warrant/listing IDs remain workspace identities;
- `provenance_listing_id` records the historical listing used for product selection/purchase provenance;
- `quote_listing_id` records the currently active listing used for the decision quote;
- provider symbol/exchange code belong to `ProviderInstrumentMapping`;
- broker contract/conId belongs to a future `BrokerInstrumentMapping`;
- execution venue/MIC belongs to the executable quote/order intent;
- none of those values may be substituted for another.

## Deterministic policy v1

`WARRANT_EXIT@1.0.0` evaluates hard data-quality/risk gates before any exit rule. Blocking conditions include missing/stale/non-executable quote, missing bid/ask or size, closed market, currency/venue mismatch, excessive spread, insufficient quote liquidity, unknown workspace or broker quantity, missing broker instrument identity, competing exit order, breached risk limit, expiry and missing idempotency identity.

Only after all gates pass are stop price, dynamic stop and target price evaluated. ML/LLM output is not an order trigger.

A triggered policy can only create a manual-approval **limit** proposal. The executable bid is the conservative initial sell limit. There is no automatic conversion to market order. Partial exits require an explicit valid quantity. Any future adaptive cancel/replace strategy must preserve a configured slippage floor, idempotency and reconciliation after every broker acknowledgement/fill.

## Shadow/paper/live boundary

- Shadow mode may evaluate decisions and persist/log proposals, but cannot call a broker order endpoint.
- Paper mode may call only an explicitly configured broker simulation/paper endpoint after exact broker-instrument mapping is validated.
- Manual approval remains required for proposals in the current implementation.
- Live execution must be a separate adapter/configuration, default disabled, requiring renewed user approval and broker credentials. No secret may be committed or emitted.

## Example instrument decision

For `DE000VH2LU21` / `VH2LU2`, the currently available Vontobel source is an official issuer indication. Even if its bid crosses an existing stop/target, policy v1 must return `BLOCKED` with `EXECUTABLE_QUOTE_MISSING` until a broker/venue executable quote with size, current timestamp, exact broker contract identity, venue, currency and broker-held quantity is available. Outside trading hours, stale/closed status adds independent blockers.

## Next broker integration contract

A future `Broker`/`ExecutionVenue` port should expose read-only instrument resolution, executable quote/snapshot, positions, open orders and order-status/fill reconciliation separately from order mutation. Order mutation should be a second capability whose live implementation is absent/disabled by default. The first concrete adapter should be chosen only after authenticated instrument lookup proves coverage for the example warrant; brand recognition is not sufficient.
