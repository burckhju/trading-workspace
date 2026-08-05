# Product Backlog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | PRODUCT_BACKLOG.md |
| Dokumenttyp | Product Backlog |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-03 |

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
| 6 | PB-006 | FT-001 Backend | P1 | Not Started | Migration, Domain, Repository, Service und API erfüllen Contract und Tests | PB-005 |
| 7 | PB-007 | FT-001 Frontend | P1 | Not Started | Basiswerte können gesucht, angelegt, bearbeitet und deaktiviert werden | PB-006 |
| 8 | PB-008 | FT-001 Integration und Abnahme | P1 | Not Started | E2E, Traceability, Dokumentation und fachliche Abnahme abgeschlossen | PB-006/007 |
| 9 | PB-009 | FT-002 Börsen/Handelsplätze | P1 | Not Started | Handelsplätze sind zentral und referenzierbar verwaltet | PB-008 |
| 10 | PB-010 | FT-003 Emittenten | P1 | Not Started | Emittenten sind als eigenständige Referenzobjekte verwaltet | PB-008 |
| 11 | PB-011 | FT-004 Optionsscheine | P2 | Not Started | Optionsscheine sind eindeutig, historisierbar und Basiswert/Emittent zugeordnet | PB-009/010 |
| 12 | PB-012 | FT-005 Watchlisten/Kandidaten | P2 | Not Started | Beobachtung und Kandidatenstatus sind ohne Handelsentscheidung nutzbar | PB-008 |
| 13 | PB-013 | FT-006 Marktanalyse | P2 | Not Started | Analysen speichern Quellen, Eingaben, Modellversion und Ergebnis | PB-004, PB-012 |
| 14 | PB-014 | FT-007 TradePlan | P2 | Not Started | Benutzer kann vollständigen TradePlan erstellen und freigeben | PB-013 |
| 15 | PB-015 | FT-008 Produktauswahl | P2 | Not Started | Produkte werden nachvollziehbar verglichen; Auswahl bleibt Benutzerentscheidung | PB-011, PB-014 |
| 16 | PB-016 | FT-009 Trade/Position | P2 | Not Started | Trades und Positionen werden manuell und vollständig erfasst | PB-014/015 |
| 17 | PB-017 | FT-010 Trade Management | P2 | Not Started | alle Änderungen am aktiven Trade erscheinen in unveränderbarer Event-Historie | PB-016 |
| 18 | PB-018 | FT-011 Nachbeobachtung | P3 | Not Started | geschlossene Trades können ohne reales Risiko weiterbeobachtet werden | PB-017 |
| 19 | PB-019 | FT-012 Journal/Performance | P3 | Not Started | Prozess- und Ergebnisqualität werden getrennt ausgewertet | PB-018 |
| 20 | PB-020 | FT-013 Modellkatalog | P3 | Not Started | Modellversionen sind freigebbar, vergleichbar und historisch zugeordnet | PB-004, PB-019 |

## Nächster Umsetzungsschnitt

Der nächste freizugebende Schnitt umfasst ausschließlich PB-001 bis PB-005.

### Lieferobjekte

1. `DOMAIN_MAP.md`
2. `TRADING_PROCESS_MODEL.md`
3. ADR zur Workspace-Grenze
4. freigegebene Governance-Dokumente
5. vollständiges Feature Book für FT-001

### Nicht Bestandteil

- Markt- oder Produktscoring,
- externe Kursdatenintegration,
- automatische Kandidatenermittlung,
- Orderausführung,
- Depot-Synchronisation,
- KI-basierte Empfehlungen.

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
