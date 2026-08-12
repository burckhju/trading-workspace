# Sprint 6 Transition Baseline – FT-007 TradePlan

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokumenttyp | Cross-Sprint Transition / Definition of Ready Baseline |
| Version | 1.0 |
| Status | 🟢 Approved |
| Datum | 2026-08-11 |
| Ausgangsrelease | `v0.5.0-candidate-qualification` |

## Zweck

Dieses Dokument schließt die Planungs- und Governance-Lücke zwischen dem freigegebenen Sprint 5 und dem nächsten fachlichen Umsetzungssprint. Es autorisiert **keine Implementierung**, sondern definiert die verbindliche Ausgangsbasis für die Spezifikation von FT-007.

## Empfohlener nächster Sprint

**Sprint 6 – FT-007 TradePlan**

Begründung:

- FT-006 liefert reproduzierbare Marktanalysen.
- FT-005 liefert langlebige Candidates und immutable CandidateEvaluation-Snapshots.
- Der fachliche Prozess sieht als nächsten Schritt die produktneutrale Trade-Planung vor.
- FT-002/FT-003/FT-004 werden erst für den späteren Produktpfad FT-008 zwingend benötigt und blockieren FT-007 nicht.

## Phase IU0 – Baseline Closure

Vor FT-007 `Approved for Build` werden die folgenden Steuerungsartefakte auf den Sprint-5-Release synchronisiert:

- Product Backlog;
- Module & Feature Catalog;
- Architecture Index;
- Requirements Baseline;
- Model Book;
- Traceability;
- FT-005/FT-006 Status;
- Sprint-5 Technical Closeout mit finalem Release-Nachtrag;
- Domain Map / Produktneutralität des TradePlans.

Diese Baseline Closure ist Dokumentations-/Governance-Arbeit und kein eigener Produktsprint.

## Verbindliche Übergaben aus Sprint 5

1. Candidate ist ein optionaler TradePlan-Ursprung.
2. Bei Candidate-Ursprung wird die konkrete immutable `CandidateEvaluation` referenziert.
3. Candidate-Re-Evaluationen verändern bestehende TradePlans nicht.
4. `READY_FOR_PLANNING` erzeugt und genehmigt keinen TradePlan.
5. TradePlan-Freigabe ist eine separate explizite Benutzeraktion.
6. FT-007 ist produktneutral.
7. FT-007 berechnet keine Markt-, Sektor-, Trend-, Momentum-, MarketContext- oder Relative-Strength-Logik erneut.
8. Candidate Model 1.0 bleibt LONG-only; SHORT wird nicht gespiegelt oder implizit eingeführt.
9. Historische Entscheidungsstände bleiben unverändert referenzierbar.
10. Keine automatische Positionsgrößen-, Ordermengen- oder Orderentscheidung.

## Scope für die FT-007-Spezifikation

Zu spezifizieren sind mindestens:

- TradePlan-Identität und Versionierung;
- Ursprung: CandidateEvaluation oder manuell gewähltes Underlying;
- Trade-Idee / Thesis;
- Richtung für V1;
- Entry-Semantik;
- Stop-/Invalidierungs-Semantik;
- Targets;
- Plan-Risiko und Annahmen;
- Lifecycle;
- explizite Benutzerfreigabe;
- Änderungs-/Amendment-Regeln nach Freigabe;
- Provenance und Audit;
- testbare Akzeptanzkriterien.

## Expliziter Non-Scope

Nicht Bestandteil von FT-007:

- Watchlist-Vollausbau;
- Trading-Venue-/Issuer-/Warrant-Verwaltung;
- Optionsschein- oder Produktkennzahlen;
- Produktsuche und Produktauswahl;
- automatische Positionsgröße;
- Portfolio-Risiko;
- Ordermenge;
- Broker-/Orderausführung;
- Trade-/Positionseröffnung;
- neue Market-/Candidate-Berechnungen;
- SHORT-Candidate-Modell.

## Risk Boundary

Vor Implementierung ist explizit zu trennen:

```text
Plan Risk
≠ Risk Calculation / Decision Support
≠ Position Sizing
≠ Order Quantity
≠ Execution
```

FT-007 darf Planannahmen, Validierungen und transparente Berechnungen enthalten, aber keine automatische Positionsgrößen- oder Orderentscheidung.

## Notwendige ADR-Entscheidungen

Vor `Approved for Build` mindestens prüfen und, soweit langfristig relevant, als ADR festhalten:

1. TradePlan Identity & Versioning.
2. CandidateEvaluation Handoff.
3. TradePlan Lifecycle & Approval.
4. Risk / Position-Sizing Boundary.
5. Product Neutrality.
6. Provenance / Snapshot Policy.
7. Amendment after Approval.
8. LONG-only Scope von TradePlan V1.

Die endgültige Nummerierung folgt der vorhandenen ADR-Konvention.

## Definition of Ready – FT-007

FT-007 darf erst `Approved for Build` werden, wenn:

- [ ] Nutzerproblem und erwarteter Nutzen beschrieben sind.
- [ ] Scope und Non-Scope freigegeben sind.
- [ ] TradePlan-Ownership feststeht.
- [ ] TradePlan-Identität und Versionierung entschieden sind.
- [ ] CandidateEvaluation-Handoff entschieden ist.
- [ ] manueller Underlying-Ursprung definiert ist.
- [ ] LONG-only-/Richtungs-Scope für V1 entschieden ist.
- [ ] Lifecycle definiert ist.
- [ ] Approval explizit definiert ist.
- [ ] Amendment-Regeln definiert sind.
- [ ] Entry-Semantik definiert ist.
- [ ] Stop-/Invalidierungs-Semantik definiert ist.
- [ ] Target-Semantik definiert ist.
- [ ] Plan-Risk definiert und Position Sizing abgegrenzt ist.
- [ ] Produktneutralität bestätigt ist.
- [ ] Provenance-/Snapshot-Regeln definiert sind.
- [ ] Audit-Regeln definiert sind.
- [ ] erforderliche ADRs Accepted sind.
- [ ] testbare Akzeptanzkriterien vorliegen.
- [ ] keine blockierenden fachlichen Entscheidungen offen sind.

## Folgepfad nach FT-007

Aktuelle Planungsreihenfolge:

```text
Sprint 6  FT-007 TradePlan
    ↓
Sprint 7  Reference Data Completion: FT-002 + FT-003
    ↓
Sprint 8  FT-004 Warrant Administration
    ↓
Sprint 9  FT-008 Product Selection
```

Die genaue Sprintgröße von FT-002/FT-003 wird vor Sprint 7 erneut gegen den dann aktuellen Repository-Stand geprüft.
