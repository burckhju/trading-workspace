# Sprint 1 – Fachliche Architektur und FT-001-Spezifikation

## Ziel

Sprint 1 schafft die fachliche Grundlage und macht das erste Referenzfeature `FT-001 Basiswertverwaltung` implementierungsreif. Sprint 1 enthält bewusst noch keine produktive Handelslogik.

## Umfang

### Arbeitspaket S1-01 – Domain Map

Zu definieren sind mindestens:

- Basiswert,
- Börse und Handelsplatz,
- Emittent,
- Instrument und Optionsschein,
- Datenprovider und Datenquelle,
- Watchlist und Kandidat,
- Analyse,
- TradePlan,
- Produktauswahl,
- Trade und Position,
- Trade Event,
- Nachbeobachtung,
- Exit Review,
- Journal,
- Performance Record,
- Modell und Modellversion.

Ergebnis: Aggregate, Beziehungen, Ownership, Identitäten und zentrale Invarianten.

### Arbeitspaket S1-02 – Trading-Prozessmodell

Zu dokumentieren sind:

- Eintritt und Ergebnis jeder Prozessphase,
- Benutzerentscheidungen,
- unterstützende Systemaktionen,
- Statusübergänge,
- Abbruch- und Rücksprungpfade,
- Nachweis- und Historisierungspflichten.

### Arbeitspaket S1-03 – Architekturentscheidungen

Mindestens folgende ADRs werden entschieden:

1. Single-User/Single-Workspace für Version 1.0
2. UUID-Strategie für fachliche IDs
3. fachliche Deaktivierung und endgültige Löschung
4. Audit-Metadaten und Zeitstempel
5. manuelle Datenpflege versus Provider-Ownership
6. Anlageuniversum Version 1
7. Trennung Basiswert und Notierung
8. technische Feature-Zuordnung `underlying`
9. Identifikatoren und Eindeutigkeit

### Arbeitspaket S1-04 – Governance-Freigabe

Folgende Dokumente werden inhaltlich geprüft, harmonisiert und auf `Approved` gesetzt:

- `docs/foundation/REQUIREMENTS.md`
- `docs/foundation/TRACEABILITY.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/technical/FEATURE_IMPLEMENTATION_TEMPLATE.md`

### Arbeitspaket S1-05 – FT-001 Feature Book

Unter `docs/features/underlying/` werden mindestens erstellt:

```text
FEATURE.md
REQUIREMENTS.md
DATA.md
API.md
UI.md
TESTS.md
DECISIONS.md
CHANGELOG.md
```

Die Spezifikation umfasst:

- Basiswert anlegen,
- Basiswert anzeigen und suchen,
- Basiswert bearbeiten,
- Basiswert deaktivieren und reaktivieren,
- Eindeutigkeitsregeln,
- Identifikatoren wie ISIN/WKN/Ticker nur soweit fachlich entschieden,
- Herkunft und Aktualisierungszeitpunkt,
- Fehler- und Konfliktfälle,
- Audit-Metadaten,
- API- und UI-Akzeptanzkriterien.

## Sprint-Abnahmekriterien

Sprint 1 ist abgeschlossen, wenn:

- Domain Map und Prozessmodell fachlich freigegeben sind,
- alle blockierenden ADRs entschieden sind,
- Governance-Dokumente konsistent und freigegeben sind,
- FT-001 den Status `Approved for Build` besitzt,
- Traceability von Anforderungen zu Tests vorbereitet ist,
- noch kein ungeklärtes Datenfeld in die Implementierung übernommen werden muss.

## Empfohlene Folge

Nach Sprint 1 beginnt Sprint 2 mit der vertikalen Umsetzung von FT-001:

```text
Migration → Domain → Repository → Service → API → Frontend → E2E → Abnahme
```


## Entscheidungsstand 2026-08-03

Die ADRs S1-001 bis S1-013 sind akzeptiert. Domain Map und Trading-Prozessmodell sind fachlich freigegeben. FT-001 besitzt den Status `Architecture Approved – Approved for Build`. Sprint 1 ist fachlich abgeschlossen; Implementierung beginnt erst nach explizitem Start von Sprint 2.
