# Product Backlog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | PRODUCT_BACKLOG.md |
| Dokumenttyp | Product Backlog |
| Version | 1.2 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-10 |

## Zweck

Das Product Backlog übersetzt Roadmap und Feature-Katalog in priorisierte, überprüfbare Arbeitspakete. Die Reihenfolge berücksichtigt fachliche Abhängigkeiten und reduziert frühe Architekturentscheidungen auf das notwendige Minimum.

## Prioritätsklassen

- **P0:** Voraussetzung für jede fachliche Implementierung
- **P1:** nächster umsetzbarer Produktwert
- **P2:** benötigt für den vollständigen Tradingprozess
- **P3:** Auswertung, Lernen und Optimierung

## Backlog

| Rang | ID | Titel | Priorität | Status | Ergebnis / Abnahmekern | Abhängigkeit |
|---:|---|---|---|---|---|---|
| 1 | PB-001 | Fachliche Domain Map | P0 | Done | Kernobjekte, Aggregate, Beziehungen und Ownership sind freigegeben | Sprint 0 |
| 2 | PB-002 | End-to-End-Prozessmodell | P0 | Done | Prozess von Marktanalyse bis Modellverbesserung inklusive Statusübergängen ist dokumentiert | PB-001 |
| 3 | PB-003 | ADR Benutzer-/Workspace-Grenze | P0 | Accepted | Single-Workspace-Entscheidung und spätere Erweiterungsgrenze sind festgelegt | Sprint 0 |
| 4 | PB-004 | Governance-Baselines freigeben | P0 | Proposed | REQUIREMENTS, TRACEABILITY, MODEL_BOOK und FEATURE_LIFECYCLE sind geprüft und freigegeben | PB-001/002 |
| 5 | PB-005 | FT-001 Feature Book | P1 | Approved for Build | Basiswertverwaltung ist implementierungsreif spezifiziert | PB-001, PB-003 |
| 6 | PB-006 | FT-001 Backend | P1 | Done | Migration, Domain, Repository, Service und API erfüllen Contract und Tests | PB-005 |
| 7 | PB-007 | FT-001 Frontend | P1 | Done | Basiswerte können gesucht, angelegt, bearbeitet und deaktiviert werden | PB-006 |
| 8 | PB-008 | FT-001 Integration und Abnahme | P1 | Done | E2E, Traceability, Dokumentation und fachliche Abnahme abgeschlossen | PB-006/007 |
| 9 | PB-009 | FT-002 Börsen/Handelsplätze | P1 | Technical Review | Provider-neutrale Handelsplätze sind zentral administrierbar, providerseitig reconciliert und in normalen Nutzerflüssen low-input konsumierbar; Release-Gates stehen aus | PB-008 |
| 10 | PB-010 | FT-003 Emittenten | P1 | Not Started | Emittenten sind als eigenständige Referenzobjekte verwaltet | PB-008 |
| 11 | PB-011 | FT-004 Optionsscheine | P2 | Not Started | Optionsscheine sind eindeutig, historisierbar und Basiswert/Emittent zugeordnet | PB-009/010 |
| 12 | PB-012 | FT-005 Watchlisten/Kandidaten | P2 | Technical Review | Kandidatenqualifikation, Lifecycle und Top-down-Nachvollziehbarkeit sind ohne Handelsentscheidung nutzbar; Watchlist-Vollausbau bleibt offen | PB-008, PB-013 |
| 13 | PB-013 | FT-006 Marktanalyse | P2 | Technical Review | Analysen speichern Quellen, Eingaben, Modellversion und Ergebnis; Sprint-4-RC ist fachlich abgenommen, externe Release-Gates bleiben offen | PB-004, PB-008 |
| 14 | PB-014 | FT-007 TradePlan | P2 | Released (`v0.6.0-trade-plan`) | Benutzer kann einen produktneutralen, versionierten LONG-TradePlan erstellen und eine konkrete Version explizit freigeben; Candidate-Ursprung referenziert die konkrete CandidateEvaluation | PB-013; FT-005-Integration optional, aber bei Candidate-Ursprung versioniert |
| 15 | PB-015 | FT-008 Produktauswahl | P2 | Not Started | Produkte werden nachvollziehbar gegen den freigegebenen TradePlan verglichen; Auswahl bleibt Benutzerentscheidung und verändert den TradePlan nicht | PB-011, PB-014 |
| 16 | PB-016 | FT-009 Trade/Position | P2 | Not Started | Trades und Positionen werden manuell und vollständig erfasst | PB-014/015 |
| 17 | PB-017 | FT-010 Trade Management | P2 | Not Started | alle Änderungen am aktiven Trade erscheinen in unveränderbarer Event-Historie | PB-016 |
| 18 | PB-018 | FT-011 Nachbeobachtung | P3 | Not Started | geschlossene Trades können ohne reales Risiko weiterbeobachtet werden | PB-017 |
| 19 | PB-019 | FT-012 Journal/Performance | P3 | Not Started | Prozess- und Ergebnisqualität werden getrennt ausgewertet | PB-018 |
| 20 | PB-020 | FT-013 Modellkatalog | P3 | Not Started | Modellversionen sind freigebbar, vergleichbar und historisch zugeordnet | PB-004, PB-019 |

## Nächster Umsetzungsschnitt

PB-014 / FT-007 TradePlan ist funktional implementiert und durch Backend-, Frontend- und E2E-Gates abgesichert. Vor Sprint-Closeout steht noch der Sprint-6 Architecture Review aus. Der generische Watchlist-Restscope aus PB-012 blockiert FT-007 nicht.

### Lieferobjekte

1. FT-005 Candidate-/Top-down-Dokumentation
2. Sprint-5-ADRs
3. migrations- und API-konsistente Candidate-Implementierung
4. nachvollziehbare Top-down-Evaluation und Live-Readiness
5. Sprint-5-Architecture-Review und Traceability

### Nicht Bestandteil

- aggregierter Candidate-Score,
- automatische Handelsentscheidung,
- automatische Produktauswahl,
- Orderausführung,
- Depot-Synchronisation,
- KI-basierte Empfehlungen.

## Randbedingungen für nachfolgende Features

Die Sprint-5-Erweiterungen ändern die Roadmap-Reihenfolge nicht. Sie präzisieren jedoch die Übergaben:

1. **FT-007 TradePlan:** Candidate ist optionaler Ursprung. Bei Candidate-Ursprung muss die konkrete immutable CandidateEvaluation referenziert werden; `READY_FOR_PLANNING` ist keine Planfreigabe. FT-007 bleibt produktneutral.
2. **FT-008 Produktauswahl:** benötigt FT-004 und einen explizit freigegebenen TradePlan. Candidate-/MarketContext-Ergebnisse dürfen erklärt, aber nicht als automatische Produktauswahl interpretiert werden.
3. **FT-009/010 Execution:** keine automatische Order- oder Positionsgrößenentscheidung aus Candidate-/TradePlan-Modellen ableiten. Tatsächliche Ausführungen bleiben Benutzerbestätigungen.
4. **FT-011/012 Learning:** historische CandidateEvaluation, TradePlan-Version und Produktauswahl müssen unverändert referenzierbar bleiben, damit spätere Entscheidungsqualität getrennt vom Ergebnis bewertet werden kann.
5. **FT-013 Model Governance:** MarketContext 1.0.0, Relative Strength 1.0.0 und TOP_DOWN_CANDIDATE 1.0.0 sind künftig als governte Modellartefakte zu übernehmen; Änderungen erzeugen neue Modellversionen.
6. **SHORT-Unterstützung:** Candidate Model 1.0 bleibt LONG-only. SHORT ist ein eigener späterer Fachentscheid und darf nicht durch Spiegelung der LONG-Regeln eingeführt werden.
7. **Reference Data:** `Underlying` bleibt in V1 `STOCK`; Benchmark-/Sektorobjekte bleiben `MarketReference` und dürfen nicht in FT-001 als neue Underlying-Arten eingeschleust werden.
8. **Watchlist:** ein generisches Watchlist-Aggregat bleibt Restscope von FT-005, ist aber keine technische Voraussetzung für FT-007, da der Prozess auch einen manuell gewählten Basiswert als TradePlan-Ursprung zulässt.

## Definition of Ready

Ein Backlog-Element ist umsetzungsbereit, wenn:

- Nutzerproblem und erwarteter Nutzen beschrieben sind,
- Scope und Nicht-Scope feststehen,
- Akzeptanzkriterien testbar sind,
- Daten- und Objekt-Ownership geklärt ist,
- Abhängigkeiten erfüllt oder geplant sind,
- offene Entscheidungen keine Implementierung blockieren.

## Definition of Done

Ein Backlog-Element ist abgeschlossen, wenn:

- spezifizierte Funktionen implementiert sind,
- automatisierte Tests erfolgreich sind,
- fachliche Abnahme dokumentiert ist,
- Traceability und Changelog aktualisiert sind,
- keine kritischen offenen Punkte verbleiben,
- der Git-Arbeitsstand sauber und versioniert ist.
