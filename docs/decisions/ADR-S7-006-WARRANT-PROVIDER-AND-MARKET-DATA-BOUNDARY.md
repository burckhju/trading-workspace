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

## Originaldokumente im gesonderten indikativen Umfang (18.11.2026)

Der [V2-Belegvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-readiness-v2)
ergänzt feste veröffentlichte KID-Dokumentpfade beim Product-Owner und endlich
belegte Kalenderoriginale beim Market-Data-Owner. Dies ist keine neue
Kursquellenpriorität oder Providerzustimmung. Die bestehenden verzögerten
GETTEX-/Stuttgart-Adapter bleiben die Kursbeschaffungsowner; gemeinsame
Quellkurszeit, Original-BID-Seitenzeit, Empfang und instrumentbezogener
Originalstatus bleiben verschieden. Der bewusst begrenzte Originaldateiimport
für Listingtermine aktiviert keinen regelmäßigen Webseitenkursabruf. Die
strengen B58-Quellenanforderungen bleiben unverändert.
