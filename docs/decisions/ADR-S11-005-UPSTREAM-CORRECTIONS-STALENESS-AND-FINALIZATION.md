# ADR-S11-005 – Upstream-Korrekturen, Staleness und Finalisierung

## Status

Accepted for Sprint 11.

## Kontext

FT-011 konsumiert effektive historische Fakten aus vorgelagerten Features.

Dazu gehören insbesondere:

- effektive ExecutionRecords;
- Full-Exit-Zeitpunkt;
- tatsächliche Exit-Preise und Mengen;
- effektive TradeManagementEvents;
- historische Plan-/Produkt-Provenance;
- verwendete DailyPrice-Marktdaten.

FT-010 korrigiert Execution- und Management-Fakten über Supersession, ohne
historische Ursprungsdatensätze still zu überschreiben.

Damit kann sich die effektive Faktenbasis einer bereits gestarteten oder
bewerteten PostTradeObservation nachträglich ändern.

## Entscheidung

FT-011 behandelt die effektive Upstream-Historie als Source of Truth.

Eine Upstream-Korrektur erzeugt keine zweite PostTradeObservation.

Solange noch kein finalisierter ExitReview geschützt werden muss, dürfen
abgeleitete Observation-Read-Models und Metriken aus der aktuellen effektiven
Faktenlage neu berechnet werden.

Dies gilt insbesondere für:

- tatsächliche Exit-Historie;
- Full-Exit-Zeitpunkt;
- Observation-Startgrenze;
- Observation Points;
- Stop-/Target-Crossings;
- weitere transparente Counterfactual-Metriken.

Eine COMPLETED PostTradeObservation bedeutet nur, dass ihr Horizon erreicht
wurde. Sie bedeutet nicht, dass Upstream-Fakten nie wieder korrigiert werden
dürfen.

Ein finalisierter ExitReview wird bei einer semantisch relevanten Änderung
seiner Input-Basis niemals still umgeschrieben.

Stattdessen wird seine Aktualität:

CURRENT -> STALE

STALE bedeutet:

Der Review wurde auf Basis einer inzwischen
geänderten effektiven Faktenlage finalisiert.

Der historische Review bleibt erhalten.

Der Nutzer muss die geänderte Evidenz erneut prüfen und den Review erneut
finalisieren.

Eine reine technische Aktualisierung ohne fachlich andere Inputs erzeugt keine
Staleness.

Relevant können insbesondere sein:

- geänderter effektiver Full-Exit;
- geänderte Exit-Menge;
- geänderter Exit-Preis;
- geänderter Exit-Zeitpunkt;
- geänderte effektive Management-Level;
- fachlich geänderte verwendete DailyPrice-Daten.

Der konkrete technische Mechanismus zur Erkennung wird in der
Implementierungsspezifikation definiert, bevorzugt über einen reproduzierbaren
Input-Fingerprint oder eine äquivalente Revision.

## Auswirkungen für den Nutzer

Ein Eingabefehler kann weiterhin korrigiert werden.

Beispiel:

ursprünglich:
SELL 100 @ 4,20 um 14:20

korrigiert:
SELL 100 @ 4,20 um 16:20

Eine noch nicht final bewertete Nachbeobachtung kann anschließend die
korrigierten Fakten verwenden.

Hat der Nutzer den Exit Review bereits finalisiert, ändert das System seine
Bewertung nicht heimlich.

Stattdessen kann die Oberfläche anzeigen:

Review erneut prüfen

Seit der Finalisierung wurden relevante
Ausgangsdaten geändert.

Die alte Bewertung bleibt historisch nachvollziehbar.

## Begründung

Vor einer finalen Benutzerentscheidung ist die aktuelle effektive Faktenlage
die sinnvollste Grundlage.

Nach Finalisierung besitzt die Bewertung dagegen selbst historische Bedeutung.

Würde das System ihre zugrunde liegenden Fakten still verändern, könnte
dieselbe Benutzerbewertung plötzlich etwas anderes bedeuten als zum Zeitpunkt
der Finalisierung.

STALE schützt daher gleichzeitig:

- aktuelle fachliche Richtigkeit;
- historische Nachvollziehbarkeit.

## Invarianten

### INV-S11-032
Upstream-Korrekturen erzeugen keine zweite PostTradeObservation.

### INV-S11-033
Nicht finalisierte Auswertungen dürfen aus aktueller effektiver Historie neu
abgeleitet werden.

### INV-S11-034
Ein finalisierter Review wird niemals aufgrund späterer Input-Änderungen still
umgeschrieben.

### INV-S11-035
Semantisch relevante Änderungen der Review-Basis machen ihn STALE.

### INV-S11-036
Ein STALE Review bleibt historisch nachvollziehbar.

### INV-S11-037
Ein STALE Review wird nicht automatisch wieder CURRENT.

### INV-S11-038
Reine technische Refreshes ohne fachliche Änderung erzeugen keine Staleness.
