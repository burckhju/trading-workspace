# ADR-S6-006 – TradePlan Product Neutrality

Status: Accepted – Sprint 6

## Context

FT-007 liegt vor FT-004/FT-008 im Prozess. Ein TradePlan muss unabhängig vom später gewählten Finanzprodukt bleiben.

## Decision

FT-007 kennt keine Warrant-ID, Issuer, Leverage, Spread, Ratio, Expiry, Product Score, Warrant-Preis oder produktbezogene Orderparameter. Der TradePlan bezieht sich fachlich auf Underlying, Thesis, Entry, Invalidation, Targets und Plan-Risiko.

Eine spätere Product Selection referenziert eine konkrete Approved-TradePlanVersion und verändert sie nicht.

## Consequences

- FT-007 kann vor Reference-Data-Completion und Warrant Administration umgesetzt werden.
- Produktwechsel verändern keinen historischen TradePlan.
- Domain Map darf keine Warrant-Referenz als Attribut des TradePlans modellieren.
