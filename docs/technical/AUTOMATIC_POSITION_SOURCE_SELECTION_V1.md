# Automatische Auswahl verifizierter Positionskursquellen

> Historischer Paketstand. Für den Git-Stand ab 1.4.0 gelten die
> [aktuelle Betriebsanleitung](ISSUER_MONITORING_OPERATIONS.md) und die
> [Release-Notizen](../releases/V1.4.0-ISSUER-MONITORING.md).

Stand: 28.09.2026. Erweiterung des vorhandenen Auswahlverfahrens,
`VERIFIED_ROUTE_RECONCILIATION_V1`. Keine Schemaänderung.

## Verhalten

Bei der Erfassung einer Position prüft `select_once` vorhandene, verifizierte
Zuordnungen innerhalb der Kauftransaktion. Es führt keine Netzwerkabfragen aus.
Die Auswahl berücksichtigt den Workspace, aktive Produkte/Emittenten/Notierungen,
aktive Währungen/Handelsplätze, verifizierte Produktidentität und Mapping-Version,
aktivierte Anbieter sowie die gespeicherte Währungs- und Notierungspräferenz.

| Ergebnis | Entscheidung |
| --- | --- |
| Genau eine zulässige Route | `SELECTED` |
| Keine zulässige Route | `NO_VERIFIED_QUOTE_SOURCE` |
| Mehrere zulässige Routen | `AMBIGUOUS_SOURCE`; keine erfundene Rangfolge |

Eine bevorzugte Notierung wird wie bisher berücksichtigt, sofern eine passende
Route dafür existiert. Eine vorgegebene Währung bleibt zwingend.

Mit `market_data.refresh.auto_select_position_sources=true` prüft der reguläre
Optionsschein-/Emittenten-Abruf vor dem Netzwerkzugriff die offenen Positionen
des Produkts erneut. Dies erfasst bisher ungebundene Positionen sowie negative
Entscheidungen der bekannten automatischen Richtlinie. Die Prüfung greift beim
nächsten vorgesehenen Abruf; Anbieter-Wartezeiten können diesen verzögern.

Bereits ausgewählte Routen bleiben stabil, auch bei Abruffehlern. Es gibt keinen
automatischen Wechsel zu einem anderen Anbieter. Unbekannte/manuelle Richtlinien,
unbekannte Gründe oder beschädigte frühere Auswahlbedingungen werden erhalten.
Geschlossene und stornierte Positionen werden ausgeschlossen.

## Emittenten und Monitoring

Die Auswahl und die Regelprüfung teilen die Indikationsverträge in
`market_data/domain/issuer_indications.py`:

| Anbieter | Auswahlrichtlinie | Zeitbasis |
| --- | --- | --- |
| JPMorgan | `JPMORGAN_ISSUER_INDICATION_V1` | Datum und Zeitzone unbekannt |
| Morgan Stanley | `MORGAN_STANLEY_ISSUER_INDICATION_V1` | Lokales Datum bekannt, Zeitzone unbekannt |

Die bisherige generische Auswahlrichtlinie konnte bei neuen Emittentenpositionen
zu einer Ablehnung durch die Stop-/Zielprüfung führen. Neue Auswahlen erhalten
jetzt den passenden Vertrag. Alte automatische, generisch gespeicherte
Emittentenauswahlen werden ausschließlich bei erneuter Prüfung derselben Route,
Mapping-ID/-Version und Identitätskennung durch einen Nachfolger korrigiert.

Eine erfolgreiche Quellenauswahl bedeutet noch keinen verfügbaren oder frischen
Kurs. Die vorhandenen Prüfungen auf Kursidentität, bestätigte Regelpreisbindung,
Währung, positiven Geldkurs, Abruffehler und Empfangsalter bleiben erhalten.
Datum/Zeitzone werden nicht ergänzt oder geraten. Emittentenkurse bleiben
indikativ; eine Handelsausführung wird dadurch nicht freigegeben.

## Historie und Transaktionen

Position und aktive Auswahl werden gesperrt. Ein Nachfolger wird mit
`previous_selection_id`, Akteur, Algorithmus und Kandidatennachweisen gespeichert;
die alte Entscheidung erhält `superseded_at`. Beides geschieht atomar. Der
vorhandene partielle PostgreSQL-Index erlaubt nur eine aktive Entscheidung je
Workspace/Position. Wiederholungen mit identischem Ergebnis und denselben
Nachweisen erzeugen keine neuen Datensätze. Geänderte Nachweise werden historisiert.
Ausführungen, Mengen, Einstandspreise, Stop-/Zielwerte werden nicht verändert.

Die Quellenauswahl verwendet einen eigenen kurzen Datenbankvorgang vor dem
Kursabruf. Sie verursacht selbst keine Anbieteranfrage. Der bestehende
Refresh-Leader und die getrennten Abrufgruppen bleiben bestehen.

## Betrieb und Grenzen

Die Grundeinstellung bleibt aus; das Paket `quote-source-selection-v1` aktiviert
sie per Compose-Overlay. Status und Zähler erscheinen im Tool unter
„Automatischer Kursabruf“ nach „Abrufstatus laden“ sowie in
`/api/v1/market-data/refresh/status` je Aufgabe als `source_selection`.

Das Paket ergänzt keine dynamische Suche nach neuen JPMorgan-/Morgan-Stanley-
ISINs. Deren bestehende verifizierte Produktlisten bleiben in Kraft. Auch
`DE000MN2ZUN2` bleibt vom bestehenden Morgan-Stanley-Adapter ausgeschlossen.
Neue Produkte außerhalb dieser Listen benötigen weiterhin einen gesondert
verifizierten Anbieterpfad. Weitere Entwicklung: beleggestützte Produktregistrierung
und anschließend eine ausdrücklich definierte Auswahl bei mehreren Quellen.

Lokal geprüft: 127 Backend-Tests inklusive SQL/JSON-Historie, Rollback,
Währungs-/Workspace-/Statusgrenzen und realer Emittenten-Regelvalidierung;
TypeScript und Produktionsbuild. SQLite deckt die Persistenzlogik ab, aber keine
PostgreSQL-Sperren unter Last. Der Installer prüft den vorhandenen Schema-Stand
`20260922_0041`; die Betriebsprüfung erfolgt auf dem Zielsystem.
