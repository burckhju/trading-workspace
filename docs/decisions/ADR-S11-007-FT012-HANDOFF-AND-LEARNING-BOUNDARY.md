# ADR-S11-007 – FT-012-Handoff und Learning Boundary

## Status

Accepted for Sprint 11.

## Kontext

FT-011 besitzt die fachlichen Objekte:

- PostTradeObservation
- ExitReview

FT-012 übernimmt nachgelagert:

- Journal
- Lessons Learned
- Performance

Diese Verantwortlichkeiten dürfen nicht vermischt werden.

Der Prozess bleibt:

Trade schließen
-> Nachbeobachten
-> Exit bewerten
-> Journal / Learning / Performance

## Entscheidung

Der reguläre FT-012-Handoff ist erreicht, wenn:

PostTradeObservation == COMPLETED
AND
ExitReview == FINALIZED
AND
ExitReview currentness == CURRENT

Ein DRAFT ExitReview ist kein abgeschlossener FT-011-Handoff.

Ein FINALIZED + STALE ExitReview bleibt historisch sichtbar, ist aber nicht
die aktuelle Handoff-Wahrheit.

FT-011 erzeugt selbst keine:

- Journal-Einträge;
- Lessons Learned;
- PerformanceRecords;
- aggregierten Performance-Kennzahlen;
- automatischen Modelländerungen;
- automatischen Regeländerungen.

FT-012 konsumiert stabile FT-011-Referenzen.

Der Handoff muss mindestens eindeutig referenzieren können:

- trade_id;
- post_trade_observation_id;
- exit_review_id.

Zusätzlich muss FT-012 auf den relevanten FT-011-Kontext zugreifen können,
insbesondere:

- Full-Exit-Historie;
- Observation-Horizon;
- gepinnte Underlying-Listing-ID;
- Datenvollständigkeit;
- transparente Observation-Metriken;
- historische TradePlan-Provenance, sofern vorhanden;
- historische Product-Selection-Provenance, sofern vorhanden;
- FT-010-Management-Kontext;
- ExitReview-Bewertungen;
- ExitReview-Begründung;
- Finalisierungszeitpunkt;
- Actor;
- CURRENT-/STALE-Semantik.

FT-012 darf diese Fakten konsumieren, aber keine konkurrierende
ExitReview-Wahrheit erzeugen.

Ein External Trade bleibt grundsätzlich handoff-fähig.

Fehlende Plan- oder Product-Selection-Provenance bleibt dabei explizit
unbekannt und wird nicht erfunden.

## Auswirkungen für den Nutzer

Der Benutzerfluss bleibt:

Trade vollständig schließen
-> Nachbeobachtung starten
-> 20 / 20 EOD-Beobachtungen
-> Exit Review durchführen
-> Exit Review finalisieren
-> Journal / Lessons Learned / Performance

Die Begründung im ExitReview wird nicht automatisch zu einer Lesson Learned.

Beispiel:

"Ich bin wegen erhöhter Unsicherheit bewusst früher ausgestiegen."

wird nicht automatisch zu:

"Bei Unsicherheit immer früher verkaufen."

Eine solche Verallgemeinerung gehört in einen späteren Learning-Schritt.

Auch eine Bewertung wie:

TIMING = IMPROVABLE

wird nicht automatisch zu:

schlechter Trade

oder zu einem negativen Performance-Score.

Wird ein bereits finalisierter Review durch korrigierte Ausgangsdaten STALE,
muss der Nutzer ihn zunächst erneut prüfen. FT-012 übernimmt nicht still die
veraltete Bewertung.

## Begründung

PostTradeObservation beantwortet:

Was geschah nach meinem Exit?

ExitReview beantwortet:

Wie bewerte ich meine damalige Exit-Entscheidung?

Journal beantwortet den größeren Zusammenhang:

Was lerne ich aus dem gesamten Trade?

Lessons Learned gehen noch einen Schritt weiter:

Welche Erkenntnisse sind über diesen Einzelfall hinaus relevant?

Diese Ebenen benötigen getrennte fachliche Ownership.

Ein CURRENT + FINALIZED Review ist die richtige Handoff-Grenze, weil damit
sowohl eine bewusste Benutzerentscheidung als auch eine zur aktuellen
Faktenlage passende Bewertung vorliegt.

Referenzbasierter Handoff wird gegenüber einer Kopie der FT-011-Daten
bevorzugt, weil dadurch genau eine fachliche Review-Wahrheit bestehen bleibt.

## Invarianten

### INV-S11-050
FT-011 erzeugt kein Journal.

### INV-S11-051
FT-011 erzeugt keine Lessons Learned automatisch.

### INV-S11-052
FT-011 erzeugt keine aggregierten PerformanceRecords.

### INV-S11-053
Der reguläre FT-012-Handoff benötigt eine COMPLETED PostTradeObservation.

### INV-S11-054
Der reguläre FT-012-Handoff benötigt einen FINALIZED und CURRENT ExitReview.

### INV-S11-055
Ein DRAFT ExitReview ist kein abgeschlossener FT-011-Handoff.

### INV-S11-056
Ein STALE ExitReview ist nicht die aktuelle Handoff-Wahrheit.

### INV-S11-057
FT-012 konsumiert stabile FT-011-Referenzen und erzeugt keine konkurrierende
Review-Wahrheit.

### INV-S11-058
External Trades bleiben grundsätzlich handoff-fähig.

### INV-S11-059
Fehlende Provenance wird nicht erfunden.

### INV-S11-060
Ein ExitReview-Ergebnis wird nicht automatisch zu einer Lesson Learned oder
Performance-Bewertung.
