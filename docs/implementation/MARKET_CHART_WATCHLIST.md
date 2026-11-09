# S&P 500 und 30 ETFs: dauerhaft aktualisierte Diagrammübersicht

## Auftrag und Ergebnis

Die Diagrammseite soll nach einer einmaligen Einrichtung aktuelle gespeicherte
Tageskurse des direkten S&P 500 und eines nachvollziehbaren ETF-Universums zeigen.
Der Nutzer muss keine 30 Folgen aus Stammdatenanlage, Providerzuordnung,
Validierung und Historienimport wiederholen.

Die neue Standardansicht von `/market-charts` enthält 31 eigenständige Karten:
einen direkten Index, elf US-Sektor-ETFs, zehn breite oder regionale Aktien-ETFs
und neun Anleihe-ETFs. Der [Quellenkatalog](../research/SP500_ETF_CHART_UNIVERSE_20261109.md)
belegt die konkreten US-Listings. Die Auswahl ist eine globale Marktübersicht,
keine Rangliste nach Vermögen oder eine Anlageempfehlung.

Jede Karte zeigt ihre eigene Preisachse und Einheit, den letzten beobachteten
Handelstag, die tatsächliche Kursquelle sowie vorhandene Datenlücken. Originalwerte
und Quelleninformationen bleiben in einer Tastatur-erreichbaren Tabelle lesbar.
Der vorhandene Detailvergleich bleibt auf maximal vier Reihen begrenzt.

## Einmalige Aktivierung und Fortsetzung

`GET /api/v1/market-charts/watchlist` liest vor der Aktivierung den versionierten
Quellenkatalog und anschließend die dauerhafte Mitgliedschaft mit Ownerfakten.
Der GET erzeugt keine Providerabfrage, keine Zuordnung und keinen Import.

`POST /api/v1/market-charts/watchlist/activate` akzeptiert ausschließlich die
angezeigte `catalog_version` und `confirmed: true`. Die Aktivierung speichert den
Katalog samt Prüfsumme, Quellen, Benutzerbeleg und Reihenfolge workspaceweit.
Wiederholungen desselben Auftrags erzeugen keine weitere Mitgliedschaft. Ein
abweichender Katalog wird nicht stillschweigend übernommen.

Der POST startet keine lange Kette von 31 synchronen Providerimporten. Der
vorhandene Kursabruf-Scheduler übernimmt ausstehende Einträge aus der Datenbank.
Ein Browserwechsel oder Backendneustart verliert diesen Auftrag nicht. Globale
Einstellungen wie `auto_configure`, Providerfreigabe, Monitoring oder Telegram
werden durch die Aktivierung nicht geändert.

Die Datenbankmigration `20261109_0049` ergänzt nur `chart_watchlists` und
`chart_watchlist_members`. Sie aktiviert keine Mitgliedschaft, ändert keine
gespeicherten Kurse und führt keine Providerabfragen aus. Die Mitgliedschaft
enthält Einrichtungs- und Prüfbelege; die angezeigten Zustände werden aus den
vorhandenen Ownerdaten abgeleitet. Es entsteht keine neue fachliche Statusmaschine.

## Bestehende Zuständigkeiten

| Aufgabe | Weiterhin zuständiger Owner |
| --- | --- |
| ETF als Wertpapier, ISIN und Listing | Market: `UnderlyingService`, `ListingService` |
| Handelsplatz und Währung | Bestehende Market-Administrationsservices |
| Providerzuordnung, Validierung und Marktidentität | Market Data: Mappingadministration und Instrumentidentität |
| Direkter S&P 500 ohne Wertpapierlisting | Top-Down-/MarketReference-Owner |
| Revisionsgebundene Indexbedeutung | Bestehender Reference-Series-Definition-Owner |
| EOD-Historie der ETFs | Vorhandener `DailyPriceImportService` |
| EOD-Historie des direkten Index | Vorhandener `ReferenceMarketDataService` |
| Zeitreihenvergleich und Normalisierung | Vorhandener Analysis-Vertrag, maximal vier Reihen |
| Ausführung und Wiederholungsabstände | Vorhandene `UNDERLYINGS`-Scheduler-Lane und Deployment-Leadersperre |
| Darstellung | Lokale Komponenten im bestehenden Market-Charts-Host |

Die Änderung erzeugt keine neue gemeinsame Hostkomponente und verändert keine
UX-1-Arbeitsbereichs-, UX-2-Navigations- oder UX-3-Ausführungszuständigkeit.

## Identitätsprüfung und Schutz bestehender Daten

Der statische Katalog enthält ISIN, Börsenticker, Segment-MIC, Listingwährung und
Primärquellen. Er enthält keine als bestätigt ausgegebenen Providerkennungen.
Der neue ETF-Katalogreader prüft aktuelle EODHD-Antworten auf genaues Instrument,
ETF-Typ, Währung und Handelsplatz. Ein fehlendes Katalog-ISIN darf nur durch einen
exakten, konfliktfreien ISIN-Suchtreffer ergänzt werden; ein ähnlicher Name oder
Ticker genügt nicht. Ein widersprechendes Katalogfeld wird nicht überschrieben.

EODHDs zusammengesetztes `US` ist kein einzelner Handelsplatz. `NYSE ARCA` bzw.
`NASDAQ` aus dem Providerkatalog und die überprüften Listingbelege bleiben
getrennte Nachweise. Insbesondere beweist das allgemeine Providerlabel NASDAQ
allein nicht den Segment-MIC `XNMS`. Die Quellenprüfung belegt 24 `ARCX`- und
sechs `XNMS`-Listings. Kein Segment wird auf einen Operating-MIC umgeschrieben.

Providerkataloge nutzen den bestehenden Client, Call-Budget, Limiter und
Wiederholungsmechanismus. Gültige Katalogantworten werden für 24 Stunden gemeinsam
zwischengespeichert. Weder ein neuer Provider noch eine neue Kursberechnung wird
eingeführt.

Identische aktive, validierte Zuordnungen behalten ihre Revision. Fremde oder
absichtlich deaktivierte Zuordnungen werden nicht überschrieben oder automatisch
reaktiviert. Für eigene unvollständige Mappinganlagen werden Mapping-ID und
Revision atomar mit dem Ownercommit belegt; so ist eine Fortsetzung nach einem
Abbruch möglich, ohne eine fremde Deaktivierung zu übergehen.

Der erfolgreiche Einrichtungsbeleg bindet die Mitgliedschaft an die tatsächlich
geprüfte Mapping-ID, Revision und Providerkennung. Eine spätere Änderung wird
sichtbar als solche ausgewiesen. Der automatische Indexabruf verlangt weiterhin
diese genaue Bindung. Workspacefremde Ownerbindungen werden zusätzlich durch
Datenbank-Constraints/Trigger abgewehrt.

Für den exakt validierten direkten `GSPC`/`INDX`-Index umfasst die einmalige
Aktivierung auch die quellengestützte Einordnung als Kursindex ohne Dividenden.
Der vorhandene Owner bindet [FRED/SP500](https://fred.stlouisfed.org/series/SP500)
an die aktuelle Mappingrevision. Ein passender bereits vorhandener Beleg bleibt
erhalten; widersprüchliche Belege werden nicht ersetzt. FRED wird dabei nicht
als zusätzlicher Kursprovider abgefragt.

## Bedeutung von „aktuell“

Die Übersicht verwendet abgeschlossene Tageskurse (EOD). Sie behauptet weder
Intraday-Kurse noch einen aktuellen ausführbaren Preis. Der vorhandene Import
endet am vorherigen UTC-Kalendertag. Ohne Historie werden bis zu 400 Tage
angefordert; danach wird das bestehende Fenster mit sieben Tagen Überlappung
verwendet. Der konfigurierte EOD-Abstand beträgt standardmäßig 3.600 Sekunden.

Die laufende Aktualisierung setzt einen gestarteten Backend-Scheduler und den
konfigurierten, aktivierten Provider voraus. Ausgeschaltete Einstellungen werden
sichtbar ausgewiesen. Ein erfolgreicher Einrichtungsschritt beweist noch keinen
erfolgreichen Historienimport; eine vorhandene Historie beweist keinen aktuell
erfolgreichen Providerzugriff. Letzter Handelstag, Abrufzeit, Quellenzeit,
Mappingstatus und Fehler bleiben getrennt.

Der letzte automatische EOD-Abruf wird aus den vorhandenen Scheduler-Jobfakten
für genau dieses Listing bzw. diese Referenz angezeigt. Ein Abruffehler ändert
nicht nachträglich den Einrichtungsbeleg. Diese Laufzeitinformationen sind
prozesslokal und werden nach einem Backendneustart nicht als persistierte
Abrufhistorie ausgegeben; die gespeicherten Kurs-/Quellenzeiten bleiben separat.
Der aktuelle Provider-Freigabestatus wird ebenfalls sichtbar ausgewiesen.

Der Browser liest den gespeicherten Einrichtungsstand alle 60 Sekunden, solange
der Tab sichtbar ist. Neue Historienbelege aktualisieren die betroffene Reihe.
Serienreads sind auf vier gleichzeitige Anfragen begrenzt. Lokale Filter,
Vergleichsvormerkungen, Tooltip, Tabellenöffnung und Tabellenseiten erzeugen keine
neuen Providerabfragen oder Mutationen. Historische URLs behalten ihr festes
Enddatum; die normale Übersicht führt ihren Stichtag mit dem Tageswechsel weiter.

## Erhaltene Fachgrenzen

- Kein neuer Finanzalgorithmus, keine FX-Umrechnung und keine synthetische
  Zusammenfassung der 31 Reihen.
- Keine Positionen, TradePlans, Journal- oder Lesson-Zustände werden angelegt.
- SELL-Beiträge und abgeschlossene Trades sowie bestehende Backendkennzahlen
  bleiben unverändert außerhalb dieses Implementierungsumfangs.
- Fehlende Werte bleiben fehlend. DATE_ONLY/EOD erhält keine künstliche
  Ausführungszeit. Wochenend-/Feiertagslücken werden nicht mit erfundenen Preisen
  aufgefüllt; der vorhandene ungeprüfte Kalenderstatus bleibt sichtbar.
- Die Karten teilen keine Preisachse und stellen Indexpunkte nicht als ETF-Dollarpreis dar.

## Nachweise und Abnahmegrenzen

Die Regressionstests umfassen Provideridentität, Quote-/Währungstrennung,
persistente Aktivierung, wiederholbare Fortsetzung, Ownerbindungen und
Workspacegrenzen. Frontendtests prüfen alle 31 Karten, begrenzte Reads,
Tageswechsel, historische Links, lokale Interaktionen und unsichere
Aktivierungsantworten. Die Browserfälle liegen in
`tests/e2e/market-watchlist.spec.ts`; bestehende Market-Charts-, Performance-,
Journal- und Governance-Nachweise bleiben bestehen.

Neue automatische Reflowfälle umfassen 320, 390 und 1280 Pixel sowie CSS-Zoom von
200 und 400 Prozent. CSS-Zoom ist kein menschlicher Nachweis des nativen
Browserzooms. Die finalen CI-Ergebnisse werden am konkreten PR-Head dokumentiert.

Offen bleiben menschliche UX-/Domainabnahme, reale Screenreader- und
Touchbedienung sowie nativer Browserzoom. Synthetische CI-Providerantworten
beweisen nicht die reale Tarifabdeckung, Netzverfügbarkeit oder vollständige
Historie aller 31 Reihen auf dem PC. Dort zeigt die Übersicht diese tatsächlichen
Ergebnisse selbst pro Instrument; private Providerkeys werden nicht für CI
benötigt.
