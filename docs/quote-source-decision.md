# Optionsschein-Kursquellen: konsolidierter Entscheidungsstand

**Status:** Entscheidungsentwurf, nur Dokumentation  
**Stand:** 17.09.2026  
**Repository-Basis:** `main` nach #221 und #222  

Dieses Dokument konsolidiert die vorhandene Quellenrecherche mit der inzwischen
verfügbaren read-only Depot-Coverage-Diagnose. Es aktiviert keinen Provider,
ändert keine Produktdaten und erteilt keine Bewertungs- oder Orderfreigabe.
Konkrete lokale Depotbestände, ISINs und Häufigkeiten werden bewusst nicht in
dieser öffentlichen Dokumentation wiederholt.

Relevante bestehende Dokumente:

- [Automatischer Market-Data-Refresh](automatic-market-data.md)
- [Gettex Schema Probe](GETTEX_SCHEMA_PROBE.md)
- [Aufbewahrung validierter Optionsscheinkurse](retained-warrant-quotes.md)
- [Frühere Emittenten-/Quellenrecherche](issuer-quote-coverage.md)

## 1. Gesicherter aktueller Systemstand

Der aktuelle `main` trennt drei Aussagen ausdrücklich:

1. ob ein Provider konfiguriert ist;
2. ob für ein Produkt eine exakt verifizierte Route existiert;
3. ob eine gespeicherte Beobachtung einen verwendbaren Geldkurs innerhalb des
   Altersbudgets enthält.

`GET /api/v1/market-data/warrants/quote-coverage` ist rein lesend. Der Aufruf
startet keinen Providerabruf, aktiviert keinen Scheduler und ändert keine
Mappings. Gespeicherte Evidenz ist keine Live-Bewertung; `execution_usable`
bleibt `false`.

Ein lokaler Betreiberlauf nach vollständigem Scheduler-Durchlauf hat bestätigt,
dass fehlende Routen und reine Referenzpreise als unterschiedliche reale
Zustände bestehen bleiben. Die exakten lokalen Instrumente und Counts gehören
in die private Betriebsdiagnose, nicht in dieses Dokument.

## 2. Bereits vorhandene Quellen-Evidenz

### 2.1 UniCredit / gettex delayed pre-trade

Die bisherige Recherche hat einen offiziellen verzögerten gettex-Pre-Trade-Weg
mit maschinenlesbaren Geld-/Briefdaten nachgewiesen. Für den geprüften MUND-Feed
wurden ein headerloses CSV-Format, exakte Instrumentidentität, UTC-Zeit und
getrennte Geld-/Briefwerte beobachtet.

Die aktuell veröffentlichten gettex-Bedingungen nennen für verzögerte Daten:

- File-Service für MUNC und MUND;
- maximal 15 Minuten Verzögerung;
- UTC-Zeitstempel;
- Verfügbarkeit für mindestens 24 Stunden;
- Nutzung nur durch natürliche Personen ausschließlich für private Zwecke;
- keine Weitergabe an Dritte und keine Nutzung zum kommerziellen Vorteil Dritter;
- Bestätigung dieser Bedingungen durch den Download.

Die offizielle Pre-Trade-Seite beschreibt die Dateien zugleich als Daten des
jeweiligen MIC der letzten 24 Stunden und listet einzelne MUND-/MUNC-Dateien im
15-Minuten-Raster auf. Aktuelle read-only Probes vom Deployment-Host bestätigen:

- öffentliche gettex-Seite erreichbar;
- Dateiserver auf Port 8000 über HTTPS erreichbar;
- Range-Requests liefern `206 Partial Content`;
- MUND und MUNC verwenden dasselbe beobachtete Schema ohne Header:
  `ISIN,UTC-Uhrzeit,Währung,Geld,Geldvolumen,Brief,Briefvolumen`;
- für den Dateistempel `21.00` beginnen die beobachteten Datensätze bei `20:45`;
- die vollständig gelesene kleine MUNC-Datei endete bei `20:59:59` und belegt
  damit für diesen Fall ein 15-Minuten-Fenster;
- eine frühere vollständig gelesene große MUND-Datei zeigte ebenfalls genau ein
  15-Minuten-Fenster.

Damit besteht eine dokumentierte Inkonsistenz zwischen dem Website-Satz
„letzte 24 Stunden“ und dem tatsächlich beobachteten File-Service. Eine spätere
Implementierung darf daraus keine 24-Stunden-Dateiannahme ableiten. Sie muss die
Dateiliste als Quelle der Intervalle verwenden, jede Datei eigenständig
validieren und Zeit-/Dateigrenzen fail-closed behandeln.

Der Deployment-Zugriff und das MUNC-Schema sind damit technisch geprüft. Ein
erneuter vollständiger Download einer großen MUND-Datei ist für diese
Entscheidungsunterlage nicht erforderlich; die Implementierung selbst muss vor
einem Checkpoint vollständige GZip-Dekompression und Integritätsprüfung
verlangen.

Eine Umsetzung müsste hinter dem bestehenden `WarrantListingQuoteProvider`
liegen und erfolgreiche Beobachtungen in der vorhandenen dauerhaften
Quote-Ablage speichern. Eine parallele Kurs-Historienarchitektur ist nicht
begründet.

### 2.2 Morgan Stanley

Die vorhandene Recherche hat auf offiziellen Produktseiten für die geprüften
Produkte Geldkurse und überwiegend auch Briefkurse beobachtet. Der Seitenclient
weist auf einen strukturierten Streaming-Zugang hin.

Das reicht noch nicht für einen produktiven Adapter. Vor Implementierung müssen
mindestens folgende Punkte geklärt sein:

- unterstützter technischer Zugang statt Browser-/Website-Scraping;
- erlaubte automatisierte private Nutzung;
- Instrumentidentität und Zeitsemantik des Streams;
- Verhalten bei fehlender Briefseite, Marktstatus und Unterbrechungen.

Bis diese Punkte bestätigt sind, bleibt Morgan Stanley recherchiert, aber nicht
integrationsfreigegeben.

### 2.3 J.P. Morgan

Für mindestens ein untersuchtes Produkt wurde in einem strukturierten
Drittanbieter-Payload eine konkrete Quote beobachtet. Der untersuchte Zugang
weist jedoch ausdrücklich auf eine Einwilligungsanforderung für automatisierten
Abruf hin.

Daraus folgt keine Freigabe für einen Poller. Vor jeder Automatisierung braucht
es einen unterstützten Zugang oder eine ausdrückliche Einwilligung sowie eine
separate Deckungsprüfung der tatsächlich benötigten Instrumente.

### 2.4 ARIVA und weitere kommerzielle Anbieter

ARIVA MDS sowie FactSet, SIX und Infront bleiben mögliche lizenzierte
Alternativen. Aus dokumentierten API-Fähigkeiten allein darf jedoch keine
konkrete Instrumentabdeckung, Aktualität oder private Nutzungsberechtigung
abgeleitet werden.

Ein kommerzieller Zugang ist erst dann sinnvoll zu bewerten, wenn

- die benötigten Instrumente vor Vertragsabschluss abgedeckt sind;
- Geld/Brief, Zeit, Quelle und Qualitätsstatus maschinenlesbar vorliegen;
- Preis und private Nutzungsrechte geklärt sind.

## 3. Architektur- und Datenintegritätsregeln für jede neue Quelle

Jede neue Quelle muss die vorhandene Architektur wiederverwenden:

- `WarrantListingQuoteProvider` als Provider-Grenze;
- exakte ISIN/Listing/MIC/Währung-Identität;
- ursprünglichen Kurszeitpunkt getrennt vom Abrufzeitpunkt erhalten;
- Geld, Brief und Referenzpreis semantisch getrennt halten;
- erfolgreiche Beobachtungen in der vorhandenen dauerhaften Quote-Ablage
  speichern;
- einen späteren Fehler oder fehlenden Treffer nicht als Nullkurs über eine
  letzte gültige Beobachtung schreiben;
- keine stille Umdeutung von Referenzpreis zu Geldkurs;
- keine automatische Order- oder Bewertungsfreigabe aus einer neuen Route
  ableiten.

Die read-only Coverage-Diagnose bleibt die Abnahmequelle für Route,
Beobachtungsqualität und Schedulerstatus.

## 4. Entscheidungstore

### Gate A — gettex delayed

**Technisch entscheidungsreif für einen separaten Implementierungs-PR**, unter
der Voraussetzung, dass die konkrete Nutzung die veröffentlichten Bedingungen
für natürliche Personen und private Zwecke erfüllt.

Der Implementierungs-Scope muss eng bleiben:

- Dateiliste statt angenommener 24-Stunden-Datei als Intervallquelle;
- zentraler Download einer neuen Datei genau einmal;
- vollständige GZip-/CSV-Validierung vor Checkpoint;
- Filterung nur auf konfigurierte/benötigte ISINs;
- Datum aus verifiziertem Dateinamen und UTC-Zeit mit strikter Intervallprüfung;
- kein Überschreiben einer letzten gültigen Beobachtung durch fehlenden Treffer,
  Teil-Download oder Parserfehler;
- vorhandene `WarrantListingQuoteProvider`- und Retention-Architektur nutzen;
- keine Produkt-/Depotmigration und keine Orderfreigabe.

### Gate B — Morgan Stanley

**Noch keine Implementierung.** Erst unterstützten Stream-/API-Zugang und
Nutzungsrecht bestätigen. Öffentliche Produktseiten sind Evidenz für
Kursverfügbarkeit, aber kein belastbarer automatisierter Vertrag.

### Gate C — J.P. Morgan

**Noch keine Implementierung.** Kein automatisierter Abruf über einen Zugang mit
ungeklärter oder ausdrücklich zustimmungspflichtiger Nutzung.

### Gate D — kommerzieller Mehranbieter-Zugang

Erst prüfen, wenn die gezielten Wege A bis C die benötigte Abdeckung nicht mit
vertretbarem Betriebsaufwand liefern. Keine Vorab-Entscheidung allein aufgrund
einer allgemeinen Produktbeschreibung.

## 5. Was ausdrücklich nicht zusammengelegt wird

Die folgenden Probleme bleiben getrennte Arbeitspakete:

- Produkte ohne verifizierte Route;
- Produkte mit verifizierter Route, aber nur Referenzpreis;
- Produkte mit Geldkurs außerhalb des Altersbudgets;
- Provider-Zugangs- oder Lizenzfragen.

Ein zusätzlicher Provider behebt diese vier Zustände nicht automatisch zugleich.

## 6. Nächster zulässiger Schritt

Für **Gate A (gettex delayed)** kann nun ein eigener, begrenzter
Implementierungs-PR vorbereitet werden. Vor Aktivierung in einer konkreten
Installation muss der Betreiber die veröffentlichten privaten Nutzungsbedingungen
bewusst bestätigen. Der PR muss mit synthetischen/öffentlichen Testfixtures und
einer Wegwerf-Testdatenbank qualifiziert werden; echte Depotdaten sind dafür nicht
erforderlich.

Die ältere Quellenrecherche bleibt als Evidenz erhalten, soll aber nicht direkt
als Implementierungsfreigabe oder als aktueller lokaler Depotstatus gelesen
werden.
