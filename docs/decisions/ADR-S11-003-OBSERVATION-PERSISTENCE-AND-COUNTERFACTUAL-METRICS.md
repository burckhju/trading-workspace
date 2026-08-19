# ADR-S11-003 – Observation-Persistenz und Counterfactual-Metriken

## Status

Accepted for Sprint 11.

## Kontext

FT-011 V1 verwendet persistierte Underlying-EOD-Marktdaten.

Die Market-Data-Domain besitzt mit DailyPrice bereits die autoritative
providerneutrale Persistenz für historische EOD-Kurse.

FT-011 muss reproduzierbare Nachbeobachtung ermöglichen, darf dafür aber keine
zweite konkurrierende Marktdatenwahrheit schaffen.

Actual Exit Facts stammen aus der effektiven FT-010-Execution-Historie.

## Entscheidung

### DailyPrice bleibt Source of Truth

FT-011 kopiert keine vollständige DailyPrice-Zeitreihe in eigene
Observation-Point-Tabellen.

Es gilt:

Market Data Truth
=
market_data.DailyPrice

Observation Points werden als Read Model abgeleitet:

PostTradeObservation
+ pinned underlying_listing_id
+ DailyPrice
=
Observation Points

Die PostTradeObservation speichert ausschließlich eigene FT-011-Fakten, zum
Beispiel:

- observation_id;
- trade_id;
- pinned underlying_listing_id;
- Lifecycle;
- Observation-Start;
- Horizon;
- Actor-/Audit-Kontext;
- Completion-Information.

Die konkrete physische Struktur folgt in der Implementierungsspezifikation.

### Keine synthetischen Kursdaten

Fehlende DailyPrice-Daten werden nicht ersetzt durch:

- Nullwerte;
- Forward Fill;
- Interpolation;
- synthetische Candles;
- künstliche Trading Dates.

Fehlende Evidenz bleibt fehlende Evidenz.

### Actual und Counterfactual bleiben getrennt

ACTUAL
=
effektive FT-010 Execution-/Management-Historie

COUNTERFACTUAL
=
spätere beobachtete Underlying-EOD-Entwicklung

Counterfactual Facts erzeugen niemals:

- ExecutionRecord;
- Position;
- reales Risiko;
- realized P&L.

### Transparente V1-Metriken

FT-011 darf deterministisch ableiten:

- available_observation_count;
- highest_observed_high;
- zugehörigen trading_date;
- lowest_observed_low;
- zugehörigen trading_date;
- final_observed_close;
- historische Target-Crossings;
- historische Stop-Crossings;
- separate Crossings späterer FT-010-Management-Level.

Für LONG V1 gilt beispielsweise:

DailyPrice.high >= historical target
-> Target-Niveau wurde später beobachtet

und:

DailyPrice.low <= historical stop
-> Stop-Niveau wurde später beobachtet

Diese Aussagen sind deskriptiv.

Sie bedeuten nicht:

Der Nutzer hätte dort garantiert verkaufen können.

### Keine virtuelle Warrant-P&L

Der tatsächliche Trade betrifft einen Warrant.

Die V1-Nachbeobachtung betrifft jedoch das Underlying.

Deshalb gilt:

Warrant Exit Price
!=
Underlying Price

und:

Underlying movement
!=
Warrant return

FT-011 V1 berechnet keine virtuelle Warrant-P&L.

### Kein automatischer Exit-Quality-Score

Aus:

Target später erreicht

folgt nicht automatisch:

Exit war schlecht

Ebenso folgt aus einem späteren Kursrückgang nicht automatisch ein guter Exit.

Die qualitative Bewertung bleibt Aufgabe des ExitReview.

## Auswirkungen für den Nutzer

Der Nutzer kann jede Kennzahl auf konkrete EOD-Beobachtungen zurückführen.

Beispiel:

Höchstes beobachtetes Underlying-High:
152,40 am 08.09.2026

Die Anwendung kann außerdem zeigen:

Historisches Target 150
später erreicht am 08.09.2026

Sie zeigt aber nicht:

Du hast 12,40 Gewinn verschenkt.

Eine solche Aussage würde zusätzliche, nicht belegte Annahmen über Warrant-
Preis, Liquidität, Haltedauer und tatsächliche Ausführung enthalten.

Originale Plan-Level und spätere Management-Level bleiben getrennt sichtbar.

## Begründung

Das Kopieren von DailyPrice-Daten würde:

- Daten duplizieren;
- Korrektursemantik verdoppeln;
- unterschiedliche Qualitätsstände ermöglichen;
- die Source-of-Truth-Frage unnötig verkomplizieren.

Deterministische Metriken wie max(high), min(low) und Level-Crossings können
direkt aus stabilen Inputs reproduziert werden.

Die Beschränkung auf Underlying-Evidenz vermeidet Scheingenauigkeit bei der
hypothetischen Warrant-Bewertung.

## Invarianten

### INV-S11-017
DailyPrice bleibt die autoritative EOD-Marktdatenwahrheit.

### INV-S11-018
FT-011 kopiert keine vollständige DailyPrice-Serie als zweite Wahrheit.

### INV-S11-019
Observation Points sind aus gepinnter Listing-ID und DailyPrice reproduzierbar.

### INV-S11-020
Actual Exit Facts stammen aus effektiver FT-010-Historie.

### INV-S11-021
Counterfactual Facts erzeugen keine reale Execution, Position oder P&L.

### INV-S11-022
Fehlende Marktdaten werden nicht synthetisch ersetzt.

### INV-S11-023
Target-/Stop-Crossings sind Beobachtungen, keine Qualitätsurteile.

### INV-S11-024
Originale Plan-Level und spätere Management-Level bleiben unterscheidbar.

### INV-S11-025
FT-011 V1 erzeugt keine virtuelle Warrant-P&L.
