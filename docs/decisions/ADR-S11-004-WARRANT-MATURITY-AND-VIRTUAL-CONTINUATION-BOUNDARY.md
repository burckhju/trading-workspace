# ADR-S11-004 – Warrant-Maturity und Grenze der virtuellen Weiterführung

## Status

Accepted for Sprint 11.

## Kontext

Der reale Trade betrifft in V1 einen Warrant.

Historische WarrantTermsVersion enthält unter anderem:

- option_direction;
- strike;
- maturity_date;
- ratio.

Die belastbare historische Nachbeobachtungsbasis von FT-011 V1 ist jedoch die
Underlying-EOD-Serie.

FT-011 muss deshalb klar zwischen Produktlaufzeit und zugrunde liegender
Marktidee unterscheiden.

## Entscheidung

### Historische Maturity

Wenn historische Product-Selection-Provenance vorhanden ist, verwendet FT-011
die exakt referenzierte WarrantTermsVersion.

Deren maturity_date ist der maßgebliche historische Laufzeitkontext.

Die heute aktuelle Terms-Version darf diesen historischen Kontext nicht
ersetzen.

### Maturity beendet die Underlying-Observation nicht

Der 20-EOD-Horizon bleibt eine Underlying-Nachbeobachtung.

Daher gilt:

Warrant maturity
!=
automatisches Ende der Underlying-Observation

Auch wenn der Warrant innerhalb des Observation-Horizonts ausläuft, kann das
Underlying bis zum vorgesehenen 20-EOD-Horizon weiter beobachtet werden.

### Pre- und Post-Maturity bleiben unterscheidbar

Observation Points müssen fachlich als vor oder nach Warrant-Maturity
interpretierbar sein.

Beispielsweise:

PRE_MATURITY
POST_MATURITY

oder durch eine äquivalente deterministische Ableitung.

### Keine Warrant-Bewertung nach Maturity

FT-011 darf insbesondere nach Fälligkeit nicht behaupten:

- welcher Marktwert der Warrant gehabt hätte;
- welchen Verkaufserlös der Nutzer erzielt hätte;
- welche virtuelle Rendite entstanden wäre.

### Keine Exercise-/Settlement-Simulation

FT-011 V1 führt keine implizite Engine ein für:

- Exercise;
- Cash Settlement;
- Rückzahlungsbetrag;
- issuer-spezifische Abrechnung;
- theoretische Optionsbewertung.

### Kein synthetischer Warrant-Preis

FT-011 konstruiert keinen historischen Warrant-Preis aus:

- Underlying;
- Strike;
- Ratio;
- Option Direction;
- Maturity.

Es gilt:

intrinsic value
!=
historical market price

Zeitwert, implizite Volatilität, Spread, Liquidität und Emittentenpricing würden
sonst unberücksichtigt bleiben.

## Auswirkungen für den Nutzer

Wenn der Warrant während der Nachbeobachtung ausläuft, sieht der Nutzer diesen
Kontext ausdrücklich.

Beispiel:

Full Exit:            18.08.2026
Warrant-Maturity:     28.08.2026
Observation-Horizon:  20 EOD-Beobachtungen

Die Anwendung kann erklären:

Der Basiswert wird nach der Warrant-Fälligkeit weiter beobachtet.
Für den hypothetischen Warrant-Wert nach Fälligkeit wird keine Aussage gemacht.

Damit kann der Nutzer weiterhin beurteilen, ob seine zugrunde liegende
Marktidee später richtig oder falsch verlief, ohne dies mit einem fiktiven
Optionsschein-Ertrag gleichzusetzen.

## Begründung

Die Frage:

Wie entwickelte sich meine Marktidee nach dem Exit?

ist fachlich nicht identisch mit:

Was wäre mit exakt diesem Warrant passiert?

Die erste Frage ist mit Underlying-EOD-Daten belastbar analysierbar.

Die zweite benötigt historische Warrant-Preise oder ein separat spezifiziertes
Bewertungs-/Settlement-Modell.

Ein Abbruch der Underlying-Nachbeobachtung an Maturity würde außerdem den
20-EOD-Lernhorizont abhängig von der konkreten Restlaufzeit des Produkts machen.

## Invarianten

### INV-S11-026
Historische Maturity stammt aus der historischen WarrantTermsVersion.

### INV-S11-027
Warrant-Maturity beendet die Underlying-Nachbeobachtung nicht automatisch.

### INV-S11-028
Pre- und Post-Maturity-Beobachtungen bleiben unterscheidbar.

### INV-S11-029
Nach Maturity wird kein hypothetischer Warrant-Marktwert erzeugt.

### INV-S11-030
FT-011 simuliert keine Exercise-/Settlement-Logik.

### INV-S11-031
Underlying-Bewegung wird nicht als Warrant-Rendite dargestellt.
