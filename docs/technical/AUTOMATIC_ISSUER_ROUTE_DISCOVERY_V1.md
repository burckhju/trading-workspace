# Automatische Emittentenrouten für Optionsscheine – v1

> Historischer Paketstand. Für den Git-Stand ab 1.4.0 gelten die
> [aktuelle Betriebsanleitung](ISSUER_MONITORING_OPERATIONS.md) und die
> [Release-Notizen](../releases/V1.4.0-ISSUER-MONITORING.md).
> Ab 1.4.5 ersetzt die [JPMorgan-Korrektur](ISSUER_MONITORING_OPERATIONS.md#jpmorgan-produktseiten-ohne-dom-uhrzeitfeld-ab-145)
> die historische Pflicht zu einem JPMorgan-DOM-Zeitfeld. Der folgende Pakettext
> beschreibt weiterhin den damaligen Stand; der Morgan-Stanley-Vertrag bleibt erhalten.

Stand: 28.09.2026. Aufbauend auf Quellenauswahl v1 und Schema 20260922_0041.

## Ablauf

1. Der bestehende Katalogscan findet aktive Optionsscheine. Offene Positionen haben Vorrang.
2. Der aktive Emittentenstammsatz dient als Suchhinweis für JPMorgan oder Morgan Stanley.
   Die entsprechende Quelle muss konfiguriert und aktiviert sein.
3. Bereits verifizierte Routen bleiben erhalten. Vorhandene gesperrte, widersprüchliche
   oder unverifizierte Zuordnungen werden nicht überschrieben oder umgangen.
4. Für ein neues Produkt wird genau ein aktives EUR-Listing mit aktivem Handelsplatz
   und aktiver Währung benötigt. Es werden keine Produkt-/Listing-Stammdaten erfunden.
5. Die offizielle Produktseite muss die angefragte ISIN in ihrer Produkttabelle bestätigen:
   Produkttyp Optionsschein, konsistente WKN (soweit vorhanden), Bewertungstag nicht
   abgelaufen und passende Währung. Die Geld-, Brief- und Zeitfelder müssen dieselbe
   exakte Stream-Kennung für diese ISIN verwenden. Geld und Brief müssen EUR ausweisen.
   Die Kennung wird aus dem DOM gelesen, niemals aus einem vermuteten Präfix aufgebaut.
   Währung/Datum des Basiswerts gelten nicht für den Optionsschein.
6. Nach der HTTP-Anfrage werden Stammdaten, Versionen, aktive Referenzen und bestehende
   Zuordnungen erneut unter Datenbanksperren geprüft. Nur bei unverändertem Befund wird
   eine neue Mapping-Zeile samt Nachweis angelegt. Globale Eindeutigkeitskonflikte blockieren.
7. Die bestehende Wiederprüfung der Positionsquellen wird ausgeführt. Bei mehreren
   passenden Quellen bleibt die Auswahl mehrdeutig; bestehende Auswahlen werden erhalten.
8. Der folgende Katalogscan plant den Emittentenkursabruf. Neue Kennungen fließen in die
   bestehenden Adapter, Speicherung, Bewertung und indikativen Monitoring-Regeln ein.
   Kursverfügbarkeit wird beim Abruf gesondert geprüft; ein Mapping garantiert keinen Kurs.

Neue Käufe verwenden sofort eine bereits verifizierte eindeutige Route. Wenn diese noch
fehlt, entsteht zunächst der entsprechende Fehlstatus; die Hintergrundsuche und anschließende
Wiederprüfung ergänzen die Bindung später. Die Erkennung benötigt keinen Kauf: aktive
Stammdaten werden ebenfalls geprüft.

## Quellenvertrag und Grenzen

| Anbieter | Offizielle Produktseite | Stream-Grid | Uhrzeitfeld |
|---|---|---|---|
| JPMorgan | https://www.jpmorgan-zertifikate.de/zertifikate-detail/ISIN | staticgrid | quotetime |
| Morgan Stanley | https://zertifikate.morganstanley.com/produktdetails/isin | instruments | lastquotetimestamp |

Die Felder und Produktmetadaten wurden am 28.09.2026 im Browser an DE000JE7KTY8 und
DE000MJ3QFV9 geprüft. Automatisierte Tests verwenden ausdrücklich synthetische DOM-Beispiele
und simulierte Streams; sie sind kein Live-Nachweis weiterer handelbarer Produkte.

Die Quelle bleibt indikativ: JPMorgan liefert bislang eine Uhrzeit ohne verifiziertes
Kursdatum und ohne Zeitzone. Morgan Stanley liefert lokale Datums-/Zeittexte ohne verifizierte
Zeitzone. `quote_observed_at` bleibt deshalb null, Originaltexte und Empfangszeit bleiben
getrennt. Ein Bewertungstag der Produktstammdaten ist kein Kursdatum. `execution_usable`
bleibt false. Fehlende Briefkurse bleiben null; Preisrücknahmen werden nicht mit alten
Feldern aufgefüllt. Bestehende Aufbewahrungs- und Regelrichtlinien gelten weiterhin.

DE000MN2ZUN2 bleibt als bereits ausgeschlossener Morgan-Stanley-Schein gesperrt. Die
Automatisierung reaktiviert ihn nicht. Neue abgelaufene Produkte werden ebenfalls blockiert.

Der Browserzugriff beweist nicht, dass anonyme HTTP-Anfragen vom Backend erreichbar sind.
Transportfehler, Zugangsbeschränkungen, HTML-Änderungen oder fehlende Angaben erscheinen als
Prüfstatus. Es gibt keine Übernahme von Browser-Cookies, Passwörtern oder Schutzumgehung.
Keine automatische Umschaltung bestehender Quellen, keine automatische Orderausführung,
keine zusätzliche Suche bei anderen Emittenten und keine automatische Masterdatenanlage.

## Speicherung und Identität

Migration 20260928_0042 ergänzt `warrant_provider_mappings.identity_evidence` (nullable JSON).
Der Nachweis enthält Schema-/Parserfassung, Anbieter, ISIN, exakte Stream-Kennung, EUR,
Produkttyp, Bewertungstag, offizielle URL, SHA-256 der Seite, Prüfzeit sowie Workspace-,
Warrant-, Listing- und Mapping-Versionen. Die Prüfung ist rein lesend bei jeder
Identitätsauflösung; widersprüchliche, veraltete oder abgelaufene Nachweise sperren die Route.
Eine Stammdatenänderung, die den Nachweis ungültig macht, verlangt erneute gezielte Prüfung;
vorhandene Mappings werden nicht automatisch repariert.

Dynamische Identitätsfingerprints enthalten zusätzlich Stream-Kennung und Seitenhash.
Die zuvor manuell belegten festen Emittentenrouten behalten ihre alten Fingerprints und
Policy-Versionen. Damit bleiben ihre Positionsbindungen und gespeicherten Kurse kompatibel.
Die alten festen Listen sind lediglich dieser Kompatibilitätspfad. Neue Produkte müssen
nicht mehr in diese Listen aufgenommen werden.

## Planung, Grenzen, Betrieb

`auto_discover_issuer_routes` ist im Code standardmäßig false und im neuen Compose-Overlay
true. Die neue Lane `ISSUER_DISCOVERY` gehört zum bestehenden Prozess mit dem vorhandenen
Leader-Lock. Sie läuft unabhängig von Emittentenkursen, Börsenkursen und Basiswerten.
Keine zusätzliche Queue, kein weiterer Hintergrundprozess.

HTTP: 2 MB maximale entpackte Seite, 20 Sekunden Gesamtablauf, maximal drei Requests pro
Redirect-Kette, nur eigene HTTPS-Produktpfade, keine fremden Redirects. Mindestens 15 Sekunden
Abstand je Anbieter. 401/403/429: eine Stunde Anbietersperre; Transportfehler: fünf Minuten.
Zurückgestellte Aufgaben übernehmen die verbleibende Wartezeit. Die Katalogprüfung läuft
mit ihrem bestehenden Intervall; fachliche Fehlfälle werden mit dem Discovery-Intervall
(standardmäßig eine Stunde) erneut geprüft. Erfolgreich bestehende Routen brauchen keine
weitere Seitenanfrage.

Streams: nur derzeit verifizierte aktive Bindungen des Workspace, höchstens 64 Produkte pro
Session. Alle Aufrufer eines Anbieters teilen Sperre, Cache und Startbudget (höchstens ein
Netzwerkstart pro `cache_seconds`). Größere Bestände werden in Gruppen rotierend bedient;
dadurch kann sich das Abrufintervall verlängern. Cache-Inhalte werden niemals zwischen
Workspaces oder abweichenden Bindungen wiederverwendet. Abgelaufene/fehlende Snapshots
werden nicht aus früheren Batches zusammengesetzt.

## Prüfung und Rücknahme

`python -m app.tools.audit_issuer_route_discovery` liest Versionen, Konfiguration,
Leaderstatus, eindeutige Auswahlen, Nachweise und Discovery-Jobs. Es öffnet keine Provider-
Verbindungen und schreibt keine Daten. `RUNTIME_VERIFIED` besagt, dass die Laufzeit korrekt
installiert/aktiviert ist. Für neue Produkte sind zusätzlich erfolgreiche Discovery-Jobs,
Auswahl und Kursstatus zu betrachten. Null neue Nachweise sind bei vollständig bestehenden
Routen erwartbar und kein Nachweis eines Fehlers oder erfolgreicher neuer Webabrufe.

Die Schemaänderung ist additiv; vorhandene Zeilen werden nicht geändert. Eine PostgreSQL-
DDL-Sperrwartezeit über fünf Sekunden bricht die Migration ab. Der Installer prüft Hashes
und Schema vorab, baut Images, migriert mit dem neuen Backend-Image und startet erst danach
Backend/Frontend mit allen bisherigen Overlays. Ein Migrationsfehler verhindert den Neustart.
Die Installation selbst führt keine Tests in den Produktionscontainern aus.

`run.sh pause` stoppt nur die Suche nach weiteren Emittentenprodukten. Bereits verifizierte
Routen, Kursabruf, Monitoring und Quellenauswahl bleiben aktiv. Dies ist die bevorzugte
Rücknahme. Ein vollständiger Code-Rückbau deaktiviert außerdem den dynamischen Kompatibilitätspfad;
neu registrierte Routen sind im alten Code dann nicht nutzbar. Daten/Nachweise bleiben erhalten.
Die Migrationsdatei wird auch beim Code-Rückbau behalten. Kein automatisches Downgrade;
die Migration verweigert ein Downgrade, sobald gespeicherte Nachweise existieren.

Validierung: Parser- und HTTP-Grenzfälle, echte SQL-Registrierung/Selektion/Beobachtungsspeicherung
mit SQLite, beide Adapter und Streamdekoder, manipulierte/abgelaufene Nachweise, Versionwechsel,
Fremdworkspace-/Mehrdeutigkeits-/Sperrfälle, unabhängige Lanes und Anbieterbudget, Migration
mit Bestandsschutz, bestehende Auswahl-/Refresh-/Monitoringtests. SQLite ersetzt keine
PostgreSQL-Sperrprüfung. TypeScript und Produktionsbuild werden lokal geprüft; Docker-
Installationsabläufe werden mit einem simulierten Docker-Aufruf geprüft.
