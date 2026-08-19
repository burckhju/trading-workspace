# Sprint 11 – FT-011 Specification Baseline

## Status

Accepted after repository-first S11 review.

## Ziel

FT-011 implementiert Nachbeobachtung und Exit Review für einen vollständig
wirtschaftlich geschlossenen Trade.

## Verbindlicher V1-Flow

Full Economic Exit
-> FT-011 eligible
-> expliziter Start PostTradeObservation
-> 20 abgeschlossene Underlying-EOD-Beobachtungen
-> ExitReview
-> explizite Finalisierung durch den Nutzer
-> FT-012 Handoff

## Scope

- PostTradeObservation
- Underlying-basierte EOD-Nachbeobachtung
- transparente Actual-vs.-Counterfactual-Evidenz
- historische Plan-, Produkt- und Management-Provenance
- ExitReview als Benutzerbewertung
- Staleness bei relevanten späteren Korrekturen
- definierter FT-012-Handoff

## Non-Scope

- reale Orders oder neue reale Executions
- Reaktivierung geschlossener Positionen
- Intraday-Nachbeobachtung
- virtuelle Warrant-P&L
- Optionsschein-Pricing, Greeks oder IV-Rekonstruktion
- Exercise-/Settlement-Simulation
- automatischer Exit-Quality-Score
- automatische Lessons Learned
- Journal-Finalisierung
- Performance-Aggregation

## Kernentscheidungen

1. FT-011 startet nur nach vollständigem wirtschaftlichem Exit.
2. Eligibility erzeugt keine Observation automatisch.
3. Pro Trade existiert höchstens eine PostTradeObservation.
4. Standard-Horizon: 20 abgeschlossene Underlying-EOD-Beobachtungen.
5. Same-Day-EOD nach Intraday-Full-Exit zählt nicht als erster Observation Point.
6. Beim Start wird eine Underlying-listing_id gepinnt.
7. DailyPrice bleibt Market-Data Source of Truth.
8. Fehlende Marktdaten werden nicht synthetisch ergänzt.
9. Actual Execution Facts und Counterfactual Observation bleiben getrennt.
10. Historische Provenance wird nicht durch heutige Stammdaten umgedeutet.
11. Warrant-Maturity ist Kontext, beendet aber nicht automatisch die Underlying-Beobachtung.
12. PostTradeObservation und ExitReview sind getrennte Objekte.
13. Finalisierte Reviews werden bei relevanten Input-Änderungen STALE statt still umgeschrieben.
14. Benutzerbewertung bleibt von System-Evidenz getrennt.
15. FT-012 konsumiert den abgeschlossenen FT-011-Kontext referenzbasiert.

## ExitReview V1

Bewertungsdimensionen:

- TIMING
- PROCESS_ADHERENCE
- RISK_DECISION
- OVERALL_EXIT_DECISION

Bewertungswerte:

- GOOD
- ACCEPTABLE
- IMPROVABLE
- NOT_ASSESSABLE

Es gibt keinen automatisch berechneten Gesamt-Score.

## FT-012-Handoff

Regulär nur bei:

PostTradeObservation == COMPLETED
AND
ExitReview == FINALIZED
AND
ExitReview currentness == CURRENT

## Technischer DoR

Vor Implementierung müssen zusätzlich vorhanden sein:

- ADR-S11-001 bis ADR-S11-010
- physisches Datenmodell
- Migration ab Alembic-Head 20260817_0018
- Review-Versionierung und Input-Fingerprint
- Repository-/UoW-Contracts
- REST-/Fehlercontract
- Backend Acceptance Tests
- Frontend Acceptance Tests
- minimaler Frontend-Flow
