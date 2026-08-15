# ADR-S7-006 – Warrant Provider and Market-Data Boundary

## Status
Accepted for Sprint 7C after S7C-00 review.

## Decision
FT-004 reference data is independent from provider discovery and time-dependent market data. Bid, ask, spread, current price, volume, Greeks and implied volatility are not Warrant master data.

The current EODHD implementation does not prove a complete Warrant product-reference contract. No Warrant-specific EODHD adapter or automatic reconciliation is implemented until capability and field semantics are demonstrated by the real provider path.

Existing provider mappings remain unchanged because their released contract binds provider instruments to FT-001 listings.

## Consequences
FT-004 V1 can ship with manual/reference administration while provider support remains an explicit follow-up gap. FT-008 market-data needs will extend TC-001 rather than polluting reference data.

## User impact
Initially, warrant reference data may require manual administration/import rather than automatic EODHD discovery. The trade-off is that provider data cannot silently create or overwrite trusted product records.
