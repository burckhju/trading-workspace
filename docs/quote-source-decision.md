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

Die offizielle Seite beschreibt die Dateien derzeit als Daten des jeweiligen MIC
der letzten 24 Stunden. Die frühere vollständige technische Probe beobachtete in
einer konkreten MUND-Datei dagegen nur ein 15-Minuten-Zeitfenster. Dieser
Widerspruch muss vor Implementierung reproduzierbar geklärt werden; weder die
Website-Beschreibung noch eine Einzelprobe darf stillschweigend zur Parser- oder
Downloadannahme werden.

Noch offen vor einer produktiven Aktivierung:

- MUNC separat verifizieren;
- tatsächlichen Zeitumfang aktueller MUND-/MUNC-Dateien gegen die offizielle
  24-Stunden-Beschreibung verifizieren;
- Tageswechsel/Mitternacht und Dateifenster robust behandeln;
- große Dateien zentral genau einmal laden und streamend auf die benötigten
  Instrumente filtern;
- ausgehenden Zugriff des Deployment-Hosts und die betrieblichen Downloadkosten
  verifizieren;
- Nutzungsbedingungen weiterhin fail-closed behandeln.

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

**Technisch konkret genug für einen separaten Implementierungsentscheid**, sobald
MUNC, tatsächlicher Dateizeitumfang, Tageswechsel, Deployment-Zugriff und
Nutzungsbedingungen abschließend bestätigt sind. Scope muss auf den tatsächlich
durch gettex gedeckten Bedarf begrenzt bleiben.

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

Vor Provider-Code ist für **Gate A (gettex delayed)** eine kleine technische und
rechtliche Abnahme zu dokumentieren: aktuelle offizielle Nutzungsbedingungen,
MUNC, tatsächlicher Dateizeitumfang, UTC-Tageswechsel, vollständige
Dateiintegrität und erreichbarer Deployment-Zugriff. Erst danach kann ein eigener
Implementierungs-PR mit klarer Abnahme und ohne Änderungen an Depot-/Produktdaten
freigegeben werden.

Die ältere Quellenrecherche bleibt als Evidenz erhalten, soll aber nicht direkt
als Implementierungsfreigabe oder als aktueller lokaler Depotstatus gelesen
werden.
