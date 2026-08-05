# Domain Map

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokumenttyp | Fachliches Domänenmodell |
| Version | 1.0 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-03 |

## Zweck

Dieses Dokument definiert die fachlichen Kernobjekte, ihre Verantwortungsgrenzen und Beziehungen. Es beschreibt keine Tabellen, REST-Endpunkte oder UI-Komponenten.

## Unveränderliche Systemgrenze

Trading Workspace unterstützt den Benutzer bei Analyse, Planung, Auswahl, Dokumentation und Auswertung. Das System trifft keine Kauf-, Verkaufs-, Halte-, Produkt- oder Positionsgrößenentscheidung. Die Domain entscheidet ausschließlich über fachliche Gültigkeit, Konsistenz und Regelkonformität.

## Domänenbereiche

### Reference Data

Verantwortet stabile fachliche Referenzobjekte.

- Underlying (Basiswert)
- Listing (Notierung)
- Trading Venue (Markt/Handelsplatz)
- Issuer (Emittent)
- Warrant (Optionsschein)
- Data Provider und Data Source

### Market Discovery

- Watchlist
- Candidate
- Market Analysis
- Underlying Analysis

### Trade Preparation

- Trade Idea
- Trade Plan
- Risk Plan
- Entry, Stop und Target Rules

### Product Selection

- Product Search
- Product Comparison
- User Product Selection

### Execution and Position

- Trade
- Position
- Execution Record
- Trade Event

### Post Trade Learning

- Post Trade Observation
- Exit Review
- Journal
- Lesson Learned
- Performance Record

### Model Governance

- Model
- Model Version
- Rule
- Rule Version
- Calculation Record

## Kernobjekte

### Workspace

Version 1 besitzt genau einen technisch angelegten, für den Benutzer unsichtbaren Workspace. Workspace-gebundene Fachobjekte referenzieren diesen Workspace. Benutzer-, Rollen- und Teamverwaltung sind nicht Bestandteil von Version 1.

### Underlying

Ein Underlying ist der wirtschaftliche Basiswert, auf den sich Analysen, Kandidaten, Trade-Pläne und Produkte beziehen.

Für Version 1 gilt:

- Es werden ausschließlich Aktien als Underlyings unterstützt.
- `UnderlyingType` hat in Version 1 nur den Wert `STOCK`.
- Ein Optionsschein ist kein Underlying.
- Ein Underlying ist unabhängig von einer konkreten Börsennotierung.

Identität und Regeln:

- unveränderliche interne UUID,
- verpflichtender fachlicher Name,
- getrennter Lebenszyklusstatus und Datenqualitätsstatus,
- optionale ISIN und WKN,
- ISIN und WKN sind nach Normalisierung innerhalb des Workspace eindeutig, sobald vorhanden,
- operative Nutzung setzt mindestens eine aktive primäre Notierung voraus,
- ein referenziertes Underlying darf nicht endgültig gelöscht werden.

Status:

```text
ACTIVE ⇄ INACTIVE
```

Eine Reaktivierung verwendet dasselbe Objekt und dieselbe UUID.

### Listing

Ein Listing repräsentiert die konkrete Notierung eines Underlyings an einem Markt.

Eigenschaften:

- interne UUID,
- Referenz auf genau ein Underlying,
- Markt/Handelsplatz,
- Ticker,
- Handelswährung,
- Status,
- Kennzeichnung als primäre Notierung.

Regeln:

- ein Underlying besitzt mindestens eine Notierung für operative Nutzung,
- genau eine aktive Notierung ist primär,
- Ticker ist nur zusammen mit Markt eindeutig,
- eine Änderung der primären Notierung ändert nicht die Identität des Underlyings,
- historische Referenzen müssen weiterhin nachvollziehbar bleiben.

### Warrant

Ein Warrant ist ein handelbares Produkt und kein Basiswert.

Regeln für Version 1:

- `ProductType = WARRANT`,
- jeder Warrant referenziert genau ein Underlying,
- ein Underlying kann von mehreren Warrants referenziert werden,
- Warrants werden nicht durch FT-001 gepflegt,
- Produktauswahl bleibt eine Benutzerentscheidung.

### Trading Venue

Beschreibt einen Markt oder Handelsplatz. FT-001 referenziert einen Markt, besitzt ihn aber nicht. FT-001 referenziert eine versionierte kontrollierte Markt-/Handelsplatzliste. Ownership und Pflege liegen außerhalb FT-001.

### Candidate

Ein Candidate ist ein vom Benutzer beobachteter oder qualifizierter Basiswert im Marktprozess. Er referenziert ein Underlying, dupliziert dessen Stammdaten aber nicht.

### Trade Plan

Dokumentiert Handelsidee, Annahmen, Einstieg, Stop, Ziele und Risiko. Er kann einen Basiswert und später einen ausgewählten Warrant referenzieren. Die Freigabe ist eine explizite Benutzeraktion.

### Calculation Record

Persistiert für fachlich relevante Berechnungen mindestens:

- Datenquelle,
- Modell oder Regel,
- Modell-/Regelversion,
- Eingabedaten,
- Ergebnis,
- Berechnungszeitpunkt.

Reine technische UI-Transformationen sind keine fachlichen Calculation Records.

## Beziehungen

```text
Workspace 1 ── n Underlying
Underlying 1 ── n Listing
Underlying 1 ── n Warrant
Underlying 1 ── n Candidate
Underlying 1 ── n TradePlan
Warrant    1 ── n ProductSelection
TradePlan  1 ── 0..1 UserProductSelection
Trade      1 ── n TradeEvent
Trade      1 ── 0..1 PostTradeObservation
Trade      1 ── 0..1 ExitReview
Trade      1 ── 0..1 Journal
Model      1 ── n ModelVersion
ModelVersion 1 ── n CalculationRecord
```

## Ownership

| Objekt | Schreibender fachlicher Owner |
|---|---|
| Underlying, Listing-Zuordnung, Primärnotierung | FT-001 `underlying` |
| Trading Venue | FT-002 |
| Issuer | separates Emittentenfeature |
| Data Provider, Data Source | separates Providerfeature |
| Warrant | FT-004 Produkt-/Optionsscheinverwaltung |
| Candidate | FT-005 |
| Trade Plan | FT-007 |
| Product Selection | FT-008 |
| Trade, Position | FT-009 |
| Trade Event | FT-010 |
| Observation, Exit Review | FT-011 |
| Journal, Performance Record | FT-012 |
| Model, Model Version | FT-013 |

## Spätere, nicht FT-001-blockierende Erweiterungen

- Globale versus workspacebezogene Wiederverwendung von Referenzdaten über Version 1 hinaus.
- Fachliche Historisierung einzelner Stammdatenfelder.
- Vollständiges Identitätsmodell des Warrants.
- Provider-Feldownership und Konfliktregeln.
