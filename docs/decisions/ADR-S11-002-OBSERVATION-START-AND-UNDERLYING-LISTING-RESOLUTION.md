# ADR-S11-002 – Observation-Start und Underlying-Listing-Auflösung

## Status

Accepted for Sprint 11.

## Kontext

FT-011 V1 beobachtet nach vollständigem wirtschaftlichem Exit die weitere
Entwicklung des Underlyings.

Der tatsächliche Exit besitzt einen präzisen Execution-Zeitpunkt.

Die vorhandene historische Market-Data-Basis ist EOD und an eine konkrete
Underlying-Listing-ID gebunden.

Ein Underlying kann mehrere Listings besitzen. Das aktuelle Primary Listing ist
veränderbare Referenzinformation und darf eine bereits gestartete historische
Observation später nicht still verändern.

## Entscheidung

Der tatsächliche Full-Exit-Zeitpunkt bleibt ein unveränderter FT-010-
Execution-Fakt.

FT-011 rundet diesen Zeitpunkt nicht auf EOD.

Da V1 keine Intraday-Auflösung der DailyPrice-Serie besitzt, gilt:

Intraday Full Exit an Handelstag D
-> Same-Day-EOD wird nicht als sicherer erster
   Post-Exit-Observation-Point verwendet
-> erster Observation Point frühestens nächster Handelstag

Beim Start einer PostTradeObservation wird genau eine konkrete
Underlying-listing_id aufgelöst.

Diese Listing-ID wird für die gesamte Observation gepinnt:

PostTradeObservation
-> genau eine underlying_listing_id

Eine bereits gestartete Observation fragt nicht später erneut nach dem jeweils
aktuellen Primary Listing.

Die Resolver-Priorität lautet:

1. belastbare historische Underlying-Listing-Provenance, sofern eindeutig
   vorhanden;
2. aktive Primary Listing des Underlyings zum Startzeitpunkt;
3. eine eindeutig und deterministisch auflösbare alternative verwendbare
   EOD-Serie.

Sind mehrere alternative Kandidaten gleichwertig, erfolgt keine zufällige
Auswahl.

Die Anwendung muss Mehrdeutigkeit sichtbar machen beziehungsweise eine
explizite Auswahl verlangen.

Ein historisches WarrantListing ist nicht automatisch das Underlying Listing.

## Auswirkungen für den Nutzer

Ein Exit am Dienstag um 14:20 wird nicht so dargestellt, als sei der
Dienstagsschlusskurs bereits eine vollständig nachgelagerte Beobachtung.

Der erste EOD-Observation-Point ist frühestens der folgende Handelstag.

Eine laufende Nachbeobachtung bleibt außerdem auf derselben Börsenserie.

Wird später das Primary Listing des Underlyings geändert, verändern sich bereits
gestartete Reviews dadurch nicht still.

Kann keine eindeutige geeignete Serie bestimmt werden, sieht der Nutzer einen
klaren Hinweis statt einer zufällig ausgewählten Kursreihe.

## Begründung

Same-Day-EOD enthält bei einem Intraday-Exit Marktbewegungen vor und nach dem
tatsächlichen Exit und kann ohne Intraday-Daten nicht sauber als reine
Post-Exit-Beobachtung interpretiert werden.

Eine gepinnte Listing-ID macht Observationen reproduzierbar.

Die Verwendung des jeweils aktuellen Primary Listings würde historische
Auswertungen durch spätere Stammdatenänderungen verändern.

Eine zufällige alternative Listing-Auswahl wäre fachlich nicht nachvollziehbar
und könnte andere Preise, Währungen, Handelszeiten oder Datenqualitäten
verwenden.

## Invarianten

### INV-S11-010
Der tatsächliche Full-Exit-Zeitpunkt bleibt ein Execution-Fakt.

### INV-S11-011
Same-Day-EOD ist in V1 kein sicherer erster Post-Exit-Observation-Point.

### INV-S11-012
Eine PostTradeObservation verwendet genau eine gepinnte
Underlying-listing_id.

### INV-S11-013
Eine spätere Primary-Listing-Änderung wechselt eine bestehende Observation
nicht automatisch.

### INV-S11-014
Ein WarrantListing ist nicht automatisch die Underlying-Kursserie.

### INV-S11-015
Mehrdeutige Listing-Auflösung wird nicht zufällig gelöst.

### INV-S11-016
Fehlende oder mehrdeutige Kursserien bleiben für den Nutzer sichtbar.
