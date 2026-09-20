# Optionsschein-Kursquellen: konsolidierter Entscheidungsstand

**Status:** Aktueller Architektur- und Entscheidungsstand

**Stand:** 20.09.2026

**Repository-Basis:** `main` nach #233 (`bc07ae5`)

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

Der aktuelle `main` trennt vier Ebenen ausdrücklich:

1. ob ein Provider zur Runtime konfiguriert und zugelassen ist;
2. ob für ein Listing eine exakt verifizierte Provider-Route mit gültiger
   Instrumentidentität existiert;
3. welche dieser verifizierten Routen für eine konkrete offene Position
   persistent ausgewählt wurde;
4. welchen Health-/Freshness-Zustand die gespeicherten Quote-Beobachtungen dieser
   gebundenen Route haben.

Für offene Depotpositionen ist der produktive Pfad:

`Position`
→ `PositionQuoteSourceSelection`
→ exakte Revalidierung von Listing, Mapping, Provider, Mapping-Version,
Identity-Key und Währung
→ genau der persistierte Provider
→ Quote Health/Freshness
→ Monitoring.

Eine persistierte `SELECTED`-Route darf beim Lesen nicht still auf einen anderen
Provider ausweichen. Der dafür verwendete `resolve_selected()`-Pfad löst genau
die gebundene Quelle auf; die allgemeine Multi-Source-Auflösung bleibt für
Discovery, Diagnose und andere nicht positionsgebundene Reads getrennt.

Persistierte Source Decisions unterscheiden mindestens:

- `SELECTED`;
- `NO_VERIFIED_QUOTE_SOURCE`;
- `AMBIGUOUS_SOURCE`.

Eine fachlich fehlende oder mehrdeutige Quelle wird damit als expliziter
fail-closed Zustand gespeichert und nicht durch geratenes Provider-Fallback
ersetzt.

Bei der Neuanlage einer Position wird die Source Decision innerhalb derselben
Unit of Work wie die Position persistiert. Eine unerwartete technische Störung
bei dieser Entscheidung darf keine teilweise gespeicherte Position hinterlassen.

`GET /api/v1/market-data/positions/quote-coverage` ist die read-only Diagnose für
diese positionsbezogene Bindung. Sie projiziert unter anderem fehlende Bindung,
Source-Selection-Status, Mapping-/Identity-Konflikte, Provider-Verfügbarkeit und
Quote Health aus gespeicherter Evidenz. Der Aufruf startet keinen Providerabruf
und ändert keine Mappings.

`LEGACY_UNBOUND` bleibt dabei ein expliziter Diagnosezustand für Positionen ohne
persistierte Source Selection. Er ist kein gewünschter zweiter
Produktionsarchitekturpfad.

Die produktbezogene Diagnose
`GET /api/v1/market-data/warrants/quote-coverage` bleibt separat sinnvoll für
Route-, Discovery- und Quote-Evidenz. Produkt-Coverage ersetzt jedoch keine
persistierte Source Selection einer offenen Position.

## 2. Bereits vorhandene Quellen-Evidenz

### 2.1 GETTEX delayed pre-trade

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
„letzte 24 Stunden“ und dem tatsächlich beobachteten File-Service. Die
implementierte GETTEX-Anbindung darf daraus keine 24-Stunden-Dateiannahme
ableiten. Dateiliste und einzelne Intervalle müssen eigenständig validiert und
Zeit-/Dateigrenzen fail-closed behandelt werden.

Der Deployment-Zugriff und das MUNC-Schema sind damit technisch geprüft. Ein
erneuter vollständiger Download einer großen MUND-Datei ist für diese
Entscheidungsunterlage nicht erforderlich; die Implementierung selbst muss vor
einem Checkpoint vollständige GZip-Dekompression und Integritätsprüfung
verlangen.

GETTEX ist inzwischen als `GETTEX_DELAYED` hinter der bestehenden
`WarrantListingQuoteProvider`-Grenze integriert. Erfolgreiche Beobachtungen
werden in der vorhandenen dauerhaften Quote-Ablage gespeichert.

GETTEX-Routen sind venue-korrekt an eigene `MUND`-/`MUNC`-Listings gebunden.
Provider-Exchange und Listing-MIC müssen dabei übereinstimmen; frühere
XFRA/GETTEX-Mischidentitäten sind kein zulässiger produktiver Pfad.

Die Quellen- und Nutzungsevidenz dieses Abschnitts bleibt trotz erfolgter
Implementierung relevant. Eine parallele Kurs-Historienarchitektur ist weiterhin
nicht begründet.

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

## 3. Architektur- und Datenintegritätsregeln für Quellen

Jede Quote-Quelle muss die vorhandene Architektur wiederverwenden:

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

Für positionsgebundene Reads gelten zusätzliche harte Grenzen:

- die persistierte `PositionQuoteSourceSelection` bestimmt die Quelle;
- Listing, Mapping-ID, Provider, Mapping-Version und Identity-Key werden beim
  Lesen erneut geprüft;
- ein ungültig gewordenes Mapping führt fail-closed zu einem Diagnosezustand;
- `resolve_selected()` darf keinen Cross-Provider-Fallback durchführen;
- Discovery darf eine offene Position nicht still auf eine andere Quelle
  umschalten;
- mehrere gleichwertige verifizierte Kandidaten bleiben als Ambiguität
  fail-closed.

Für `GETTEX_DELAYED` gehört die Venue-Identität zur Instrumentidentität:
`MUND`-/`MUNC`-Provider-Routen dürfen nur auf dem entsprechend passenden
Listing-MIC verwendet werden.

Die read-only Coverage-Diagnosen bleiben die Abnahmequelle für Route,
Source Selection, Beobachtungsqualität und Schedulerstatus.

## 4. Entscheidungstore

### Gate A — GETTEX delayed

**Implementiert; produktive Nutzung bleibt explizit opt-in.**

`GETTEX_DELAYED` ist als verzögerte Pre-Trade-Quelle integriert. Die technische
Integration ist damit kein zukünftiges Entscheidungstor mehr.

Vor produktiver Aktivierung muss weiterhin ausdrücklich bestätigt sein, dass die
konkrete Nutzung die veröffentlichten Bedingungen für natürliche Personen und
ausschließlich private Zwecke erfüllt und keine unzulässige Weitergabe oder
Nutzung zum kommerziellen Vorteil Dritter erfolgt.

Für den Betrieb gelten weiterhin:

- Dateiliste statt angenommener 24-Stunden-Datei als Intervallquelle;
- vollständige GZip-/CSV-Validierung vor erfolgreichem Checkpoint;
- Filterung auf benötigte/verifizierte Instrumentidentitäten;
- Datum und UTC-Zeit mit strikter Intervallprüfung;
- kein Überschreiben einer letzten gültigen Beobachtung durch fehlenden Treffer,
  Teil-Download oder Parserfehler;
- persistierte Quote-Retention statt paralleler Historienablage;
- venue-korrekte `MUND`-/`MUNC`-Identität;
- keine automatische Änderung einer bereits persistierten
  Position-Source-Selection.

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

## 6. Aktueller Erweiterungs- und Betriebsrahmen

GETTEX benötigt keinen eigenen Implementierungs-PR mehr. Weitere Arbeiten daran
sollen sich auf klar abgegrenzte Betriebs-, Parser- oder Coverage-Probleme
beschränken und die persistierte Positionsbindung nicht umgehen.

Für zusätzliche Provider wie Morgan Stanley oder J.P. Morgan gelten die oben
beschriebenen Zugangs-, Nutzungs- und Identitätsgates weiterhin. Eine beobachtete
Website-Quote oder allgemeine Produktabdeckung reicht nicht aus, um einen
produktiven automatisierten Adapter oder eine Positionsroute freizugeben.

Automatische Mapping Discovery ist fail-closed: Der Default für
`market_data.refresh.auto_configure` ist `false`. Discovery muss bewusst
aktiviert werden und aktiviert selbst keinen Provider.

Die ältere Quellenrecherche bleibt als Evidenz erhalten. Sie ist weder ein
aktueller lokaler Depotstatus noch eine automatische Implementierungs-,
Aktivierungs- oder Bewertungsfreigabe.

Für offene Positionen bleibt der Zielzustand eindeutig:

`Position`
→ persistierte `PositionQuoteSourceSelection`
→ exakte Mapping-/Identity-Revalidierung
→ genau ein gebundener Provider
→ Quote/Health
→ Monitoring.
