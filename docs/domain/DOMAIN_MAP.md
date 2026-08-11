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

Ein Candidate ist ein langlebiger, vom Benutzer beobachteter oder qualifizierter Basiswert im Marktprozess. Er referenziert ein Underlying, dupliziert dessen Stammdaten aber nicht. Systemqualifikation und Benutzer-Lifecycle sind getrennt. Jede erneute fachliche Bewertung erzeugt eine unveränderliche, versionierte CandidateEvaluation mit konkreter Analyse-Provenance.

### Market Reference und Sector

Market References repräsentieren providerneutrale Benchmark- oder Sektorreferenzen für Market Discovery. Sektoren und zeitlich gültige Underlying-/Reference-Zuordnungen sind kontrollierte Referenzdaten. Provider-Symbole sind keine Domainattribute dieser Objekte.

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
Candidate  1 ── n CandidateEvaluation
Underlying 1 ── n UnderlyingSectorAssignment
Underlying 1 ── n UnderlyingBenchmarkAssignment
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
| Candidate, CandidateEvaluation | FT-005 |
| Market Reference, Sector und Top-down-Zuordnungen | Reference Data / Market Discovery; konsumiert von FT-006 und FT-005 |
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

## Verbindliche Übergaberegeln ab Sprint 5

Die in Sprint 5 eingeführten Top-down-Referenzen erweitern **nicht** den fachlichen `Underlying`-Typ aus FT-001. Für Version 1 bleibt `UnderlyingType = STOCK`. Benchmarks und Sektorreferenzen werden ausschließlich über `MarketReference` (`INDEX`, `SECTOR_INDEX`) modelliert und über historisierte Zuordnungen auf analysierbare Listings abgebildet. Damit bleibt die in Sprint 2 freigegebene Underlying-Grenze unverändert.

Für nachfolgende Features gelten folgende Übergaben:

- FT-007 darf einen Candidate als Ursprung referenzieren, muss bei Übernahme die konkrete `CandidateEvaluation` festhalten. Eine spätere Re-Evaluation verändert einen bestehenden TradePlan nicht.
- `READY_FOR_PLANNING` ist ausschließlich eine Benutzerentscheidung zur Prozessfortsetzung und keine TradePlan-Freigabe.
- FT-007 darf Markt-, Sektor-, Trend-, Momentum- oder Relative-Strength-Logik nicht duplizieren. Benötigter Analysekontext wird über versionierte FT-006-/FT-005-Ergebnisse referenziert.
- Candidate Model 1.0 ist LONG-only. Nachfolgende Features dürfen daraus keine SHORT-Qualifikation ableiten. Ein SHORT-Candidate-Modell benötigt eine eigene fachliche Freigabe und Modellversion.
- FT-007 bleibt produktneutral. Warrant-spezifische Kennzahlen und Produktauswahl gehören zu FT-008/FT-004. Ein Produktwechsel darf den TradePlan nicht rückwirkend verändern.
- Risiko im TradePlan ist eine vom Benutzer festgelegte Planannahme. Automatische Positionsgrößen- oder Orderentscheidungen bleiben außerhalb FT-007, solange dafür kein separates freigegebenes Modell existiert.
- FT-008 darf Candidate Qualification oder MarketContext als Kontext anzeigen/referenzieren, aber nicht als implizite Produktentscheidung verwenden. Die Produktauswahl bleibt eine explizite Benutzeraktion.
- FT-009/FT-010 übernehmen ausschließlich freigegebene Plan-/Produktauswahl-Referenzen und erzeugen keine rückwirkenden Änderungen an CandidateEvaluation oder TradePlan.
- Alle späteren berechnenden Features übernehmen das in Sprint 4/5 etablierte Muster aus Modell-ID, Modellversion, Inputs, Quelle, Ergebnis, Zeitpunkt und Qualitätsstatus.
