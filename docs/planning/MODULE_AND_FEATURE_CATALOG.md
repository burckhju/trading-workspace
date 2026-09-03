# Module and Feature Catalog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | MODULE_AND_FEATURE_CATALOG.md |
| Dokumenttyp | Product Architecture |
| Version | 1.4 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-09-03 |

## Zweck

Dieses Dokument ist die zentrale Zuordnung zwischen Roadmap-Meilensteinen, fachlichen Modulen und implementierbaren Features. Es verhindert parallele Definitionen und bildet die Grundlage für Backlog, Traceability und Releaseplanung.

## Abgrenzung

- **Meilenstein:** fachlicher Zielzustand der Roadmap.
- **Modul:** zusammengehöriger Verantwortungsbereich der Anwendung.
- **Feature:** einzeln spezifizierbare, testbare und abnehmbare Fähigkeit.
- **Modell:** versionierte Berechnungs- oder Bewertungslogik innerhalb eines Features.

## Feature-Katalog

| ID | Feature | Primäres Modul | Roadmap | Fachliches Ergebnis | Abhängigkeiten |
|---|---|---|---|---|---|
| FT-001 | Basiswertverwaltung (`underlying`) | Reference Data | M1 | Aktien als Basiswerte inklusive Notierungen zentral erfassen, ändern, deaktivieren und suchen | Fundament |
| FT-002 | Börsen und Handelsplätze | Reference Data | M1 | Provider-neutrale Handelsplätze zentral verwalten und mit möglichst wenig Nutzereingabe konsumieren | FT-001 |
| FT-003 | Emittenten | Reference Data | M1 | Emittenten als eigenständige Referenzobjekte verwalten | Fundament |
| FT-004 | Optionsscheinverwaltung | Reference Data | M1/M4 | Optionsscheine eindeutig einem Basiswert und Emittenten zuordnen | FT-001–FT-003 |
| FT-005 | Watchlisten und Kandidaten | Market Discovery | M2 | Top-down-Kandidaten qualifizieren, nachvollziehbar bewerten und Benutzerstatus verwalten; Watchlist-Vollausbau bleibt eigener Restscope | FT-001, FT-006 |
| FT-006 | Marktanalyse | Market Discovery | M2 | Markt- und Basiswertanalysen nachvollziehbar dokumentieren | FT-001, FT-003, Governance |
| FT-007 | TradePlan | Trade Preparation | M3 | produktneutralen LONG-TradePlan versioniert planen und konkrete Version explizit freigeben | FT-001; FT-005/FT-006 optional als Candidate-Ursprung |
| FT-008 | Produktauswahl | Product Selection | M4 | Optionsscheine vergleichen und Benutzerwahl dokumentieren | FT-004, FT-007, Governance |
| FT-009 | Trade und Position / Purchase Execution Capture | Execution Record | M5 | Tatsächliche Erst- und Nachkäufe low-input erfassen und daraus die offene Position ableiten; kein Verkauf/Trade-Management in V1 | FT-004, FT-007, FT-008 |
| FT-010 | Trade Management | Trade Management | M5 | Stops, Teilverkäufe, Produktwechsel und Events dokumentieren | FT-009 |
| FT-011 | Nachbeobachtung und Exit Review | Post Trade Learning | M6 | geschlossene Trades virtuell weiterverfolgen und Ausstieg bewerten | FT-009, FT-010 |
| FT-012 | Journal, Lessons Learned und Performance | Evaluation | M7/M8 | Entscheidungen, Regelabweichungen und Ergebnisse auswerten | FT-009–FT-011 |
| FT-013 | Modellkatalog und Modellbewertung | Model Governance | M9 | Modelle versionieren, vergleichen, freigeben und historischen Ergebnissen zuordnen | MODEL_BOOK, TRACEABILITY |

## Technische Querschnittsfähigkeiten

| Kennung | Fähigkeit | Verantwortung | Konsumierende Features |
|---|---|---|---|
| TC-001 | Marktdaten-Infrastruktur (`market_data`) | Providerunabhängiger Abruf, Qualitätsprüfung, Herkunft, Cache und Persistenz von Marktdaten; keine Handelsentscheidung | FT-004, FT-006, FT-008, FT-013 sowie spätere Analysefähigkeiten |

TC-001 verändert die fachliche Feature-Nummerierung nicht. Eine benutzerverwaltete Providerkonfiguration bleibt ein separates, später zu spezifizierendes Feature.

## Noch nicht nummerierte Capability in Technical Review

Die Capability **Position Monitoring, Alerting and Outbound Notifications** ist auf dem Feature-Branch `feat/position-monitoring-alert-notification` implementiert und befindet sich im Technical Review. Im aktuell freigegebenen Katalog ist dafür keine FT-Nummer reserviert; deshalb wird hier bewusst keine Nummer erfunden.

Der fachlich saubere Zuschnitt bleibt:

- **Position Monitoring & Alert Domain:** konsumiert bestehende Position-, TradePlan- und Trade-Management-Zustände sowie providerneutrale Marktdaten; persistiert deterministische, deduplizierte Alerts.
- **Notification Delivery & Telegram Adapter:** erzeugt providerneutrale Notifications und persistente Delivery Attempts; Telegram bleibt austauschbarer outbound-only Adapter.

Die endgültige FT-Zuordnung ist eine separate Produktplanungsentscheidung. Die Implementierungs- und Scope-Dokumentation liegt unter `docs/features/POSITION_MONITORING_ALERT_NOTIFICATION.md`.

## Ownership der Kernobjekte

| Domänenobjekt | Schreibender Owner | Lesende Features |
|---|---|---|
| Basiswert (Aktie) und Listing-Zuordnung | FT-001 | FT-004–FT-008, FT-012 |
| Börse/Handelsplatz | FT-002 | FT-004, FT-008, FT-009 |
| Emittent | FT-003 | FT-004, FT-008 |
| Datenprovider/Datenquelle | separates Providerfeature | FT-004, FT-006, FT-008, FT-013 |
| Instrument/Optionsschein | FT-004 | FT-008–FT-010, FT-012 |
| Watchlist/Kandidat | FT-005 | FT-007 |
| Analyse | FT-006 | FT-005, FT-007, FT-012, FT-013 |
| TradePlan / TradePlanVersion | FT-007 | FT-008–FT-012 |
| Produktauswahl | FT-008 | FT-009, FT-012 |
| Trade / Execution Record / Position | FT-009 | FT-010–FT-012, Position Monitoring |
| Trade Event | FT-010 | FT-011, FT-012, Position Monitoring |
| Alert / Monitoring Rule State | Position Monitoring & Alert Capability (FT noch offen) | Notification Capability, spätere UI |
| Notification / Delivery Attempt | Notification Capability (FT noch offen) | Delivery Adapter, spätere UI |
| Nachbeobachtung/Exit Review | FT-011 | FT-012, FT-013 |
| Journal/Performance Record | FT-012 | FT-013 |
| Modell/Modellversion | FT-013 | alle berechnenden Features |

## Statusmodell für Features

```text
Idea → Analysis → Specified → Approved for Build → In Development
     → Technical Review → Business Review → Accepted → Released → Observed
```

Der Status wird im Product Backlog gepflegt. Ein Feature darf nicht den Status `Approved for Build` erhalten, solange fachliche Entscheidungen oder Abhängigkeiten offen sind.

## Regeln für Featurezuschnitt

1. Ein Feature besitzt genau eine primäre fachliche Verantwortung.
2. Stammdatenobjekte werden nicht in mehreren Features parallel gepflegt.
3. Berechnungsmodelle sind keine implizite Service-Logik, sondern versionierte Artefakte.
4. Ein Feature kann ohne UI umgesetzt werden, wenn es ausschließlich eine technische oder Governance-Verantwortung besitzt; dies muss begründet werden.
5. Jedes Benutzerergebnis muss auf seine Eingaben und Quellen zurückführbar sein.
6. Produktvorschläge oder Scores bleiben Entscheidungshilfen; die endgültige Auswahl ist eine Benutzeraktion.

## Referenzfeature

`FT-001 Basiswertverwaltung` mit der technischen Kennung `underlying` ist das Referenzfeature für:

- Feature-Dokumentation,
- CRUD-API-Konventionen,
- Persistenz und Migration,
- Validierung und Konfliktbehandlung,
- Listen, Filter und Suche,
- Frontend-Formulare und Tabellen,
- Audit-Metadaten,
- Tests und Traceability.


## Verbindliche Entscheidungen für FT-001

- Version 1 unterstützt Aktien als Basiswerte und Optionsscheine als getrennte Produkte.
- Basiswert und Notierung sind getrennte fachliche Objekte.
- FT-001 besitzt das technische Feature `underlying`.
- Version 1 ist Single-User/Single-Workspace.
- Referenzierte Basiswerte werden deaktiviert, nicht gelöscht.
- UUID ist die interne Identität; ISIN/WKN sind optional und bei Angabe eindeutig; Ticker ist nur mit Markt eindeutig.


## Sprint-6 Implementierungsstatus

FT-007 ist funktional umgesetzt: Domain, Persistence/Migration, Repository/UoW, Application Services, versionsgenaue CandidateEvaluation-Provenance, Lifecycle/Approval, Amendment-Lineage, REST API, Frontend und E2E. Status vor Closeout: **Implemented – Architecture Review Pending**.
