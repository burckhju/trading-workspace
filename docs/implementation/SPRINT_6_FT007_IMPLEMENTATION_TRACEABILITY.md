# Sprint 6 – FT-007 Implementation & Traceability Closeout

## Status

**Implemented – Architecture Review Pending**

## Implementierter Umfang

- langlebige `TradePlan`-Identität und immutable `TradePlanVersion`-Snapshots;
- manueller Underlying-Ursprung oder konkrete immutable `CandidateEvaluation`;
- V1 vollständig LONG-only;
- Entry `PRICE`, `PRICE_RANGE`, `TRIGGER`;
- Stop/Invalidation, geordnete Targets und Risk Assumptions;
- Lifecycle `DRAFT → READY_FOR_REVIEW → APPROVED` sowie `ABANDONED`/`SUPERSEDED`;
- explizites versionsgenaues Approval mit Actor, Zeitpunkt und Correlation-ID;
- Amendments als neue Version mit `previous_version_id` und `change_reason`;
- append-only Audit-/Lifecycle-Provenance;
- Persistence, Migration, Repository/UoW, Application Service, Query Service und REST API;
- Frontend Create/Read/Lifecycle/Approval/History/Provenance;
- E2E-Nachweis für Manual, CandidateEvaluation und Amendment-Lineage.

## Architekturgrenzen

FT-007 bleibt produktneutral. Es enthält keine Warrant-/Issuer-/Leverage-/Spread-/Ratio-/Expiry-/Product-Score-Felder und erzeugt keine Position Size, Order Quantity oder Execution. Markt-, Sektor-, Trend-, Momentum-, MarketContext- und Relative-Strength-Logik wird nicht neu berechnet.

## Reproduzierbare Entscheidungskette

`CandidateEvaluation → TradePlanVersion → spätere Risk/Product/Execution-Entscheidungen`

Eine spätere Candidate-Re-Evaluation oder Produktauswahl verändert historische TradePlanVersionen nicht.

## Quality Gates

| Gate | Nachweis |
|---|---|
| Backend Regression | 274/274 Unit-Tests zuletzt vollständig grün vor den rein Frontend/E2E-orientierten Folgeunits |
| Frontend Typecheck | grün |
| ESLint | grün |
| Prettier | grün |
| Frontend Tests | 59/59 grün |
| Coverage | Statements 91.42 %, Branches 77.60 %, Functions 83.47 %, Lines 91.42 % |
| Production Build | `tsc -b && vite build` grün |
| E2E | 8/8 Playwright-Tests grün |

## Traceability zu ADRs

| Entscheidung | Umsetzung |
|---|---|
| ADR-S6-001 Identity & Versioning | TradePlan + immutable TradePlanVersion |
| ADR-S6-002 Origin / CandidateEvaluation | exakte Evaluation-Provenance, kein latest-Fallback |
| ADR-S6-003 Lifecycle & Approval | explizite Commands + Approval Record/Audit |
| ADR-S6-004 Amendment | neue Version, Lineage, Supersede-Semantik |
| ADR-S6-005 Risk Boundary | Plan-Risk ohne Position Sizing/Order Quantity |
| ADR-S6-006 Product Neutrality | keine Produkt-/Warrantattribute |
| ADR-S6-007 Provenance | versionsgenaue Source-/Lifecycle-/Approval-Ausgabe |
| ADR-S6-008 LONG-only | Domain-, DTO- und UI-Vertrag LONG-only |

## Verbleibender Sprint-Schritt

S6-15 Architecture Review prüft die Implementierung gegen ADRs, Domain Boundaries, Persistenz-/API-/Frontend-Konventionen und Quality-Gate-Nachweise. Erst danach erfolgt der Sprint-6 Closeout.
