# MS, JPMorgan und UniCredit: erneute Quellenqualifikation

## Nachqualifikation von PR #305 auf Main 1.5.33

Erneut über GitHub verifiziert am 30.10.2026: Main und Tag `v1.5.33` zeigen auf
`d161132c05666d43a324dcbcad0a0038c511a332`; die Quellversion ist **1.5.33**.
#302, #303, #306 und #307 sind integriert. Ein separates GitHub-Releaseobjekt
für `v1.5.33` existiert nicht; `releases/latest` nennt weiterhin
`v1.0.0-product-selection`. Ein installierter PC-Stand wurde nicht geprüft.

Der bisherige Head von #305, `5d56a0bd092a28395a52edb668662236ea53da18`, hat
inzwischen alle vier GitHub-Workflows bestanden: Backend `41101193859`,
Frontend `41101193861`, End-to-End `41101193924` und Veröffentlichungsschutz
`41101193825`. Die Checkout-Logs belegen aber ausschließlich den Testmerge
`0da149a977c17c5dfc4867c2cefa852fe10c7a28` gegen `4f70760c...`.
Diese Ergebnisse ersetzen keine Prüfung des nachfolgend aktualisierten Heads.
Reviews, Reviewthreads und Kommentare waren beim erneuten Abgleich leer.

Der aktuelle Main wurde konfliktfrei ausschließlich in den bestehenden Branch
`fix/gettex-qualified-coverage-20261030` übernommen. Die vorhandene Kursgeschichte,
Retention, fünf Scheduler-Lanes, Retryplanung, API-Schemas und UI bleiben erhalten.
Der vollständige PR-Diff betrifft sechs Pfade: zwei vorhandene Runtime-Dateien,
drei Testdateien und diese Notiz. Dabei wurden drei belegte Restprobleme korrigiert:

1. **Wiederholte große Fehlversuche:** Nach einem fehlgeschlagenen Dateidownload
   sperrt das vorhandene `unavailable_retry_seconds`-Intervall weitere Downloads
   derselben MIC/Datei, auch bei weiterhin erweiterter ISIN-Menge und anderen
   Workspaces. Die Sperre wird nicht durch Wiederholungen verlängert; abgelaufene
   Einträge werden entfernt. Der vorherige gültige Cache bleibt erhalten.
   Andere MICs und neue Dateifenster bleiben unabhängig; nur HTTP 404 erlaubt
   weiterhin den vorhandenen Rückgriff auf ein vorheriges Veröffentlichungsfenster.
2. **Monitoring nach HTTP 429:** Der tatsächliche HTTP-Fehler bleibt
   `GETTEX_DELAYED_RATE_LIMITED`. Ein lokal unterdrückter Aufruf erhält
   `GETTEX_DELAYED_REQUEST_THROTTLED`, weiterhin als `MarketDataRateLimitError`
   mit sinkendem `retry_after`. Die vorhandene Diagnostik aus #307 behandelt ihn
   als Wartephase: kein weiterer Providerfehler, keine Änderung des letzten
   Fehlerzeitpunkts und keine behauptete Wiederherstellung.
3. **Erhaltene Fehlerkategorien:** Die bestehende Refreshdiagnostik ordnet
   gettex-Zugriffs-/Mappingfehler als Konfiguration und ungültige Datei-/Kursdaten
   als Datenqualität ein. Eine verworfene ungültige Antwort ohne angenommenen
   Kurs erscheint als `INVALID`; ein gespeicherter Kurs behält seine eigenen
   Zeitpunkte und Qualitätsbelege. Es entsteht kein zweites Monitoring.

Die Regressionen reproduzieren die Download-/Sperrlücken mit dem alten Adapter
(16 gezielte Fehler) sowie die Monitoringlücken vor der Korrektur (40 gezielte
Fehler). Mit den Korrekturen bestehen die vollständigen gettex-Adapter-/Parsertests
(73 Fälle) und die drei Diagnose-Suites (112 Fälle). Ergänzende echte
SQL-/JSON-Retentionstests prüfen Fehler, lokale Sperre und erfolgreiche Erholung
mit und ohne historischen Kurs; eine gebundene Route verwendet keine Alternativquelle.

Die vollständigen lokalen Ergebnisse, der endgültige Head und Baum sowie die
neuen GitHub-Läufe werden in [PR #305](https://github.com/burckhju/trading-workspace/pull/305)
geführt. Erst erfolgreiche aktuelle Backend-, Frontend-, PostgreSQL-, E2E- und
Veröffentlichungsschutzprüfungen qualifizieren diesen Integrationsstand.
Die bestehenden Qualitätsgrenzen werden unverändert angewendet.

#220 bleibt offen als historische Recherchegrundlage. #205, #207, #187 und #197
sind ebenfalls offen und werden nicht geändert. Es gibt keinen neuen Liveabruf,
keine belegte zusätzliche Providerberechtigung und keine Provideraktivierung.
Die nachfolgenden Quellenbeobachtungen bleiben datierte historische Befunde,
keine erneute Bestätigung heutiger Liveabdeckung. Main-Merge, Release, Tag,
Deployment, PC-Installation und fachliche Abnahme sind nicht Teil dieser
technischen PR-Qualifikation.

## Ursprünglicher Prüfstand und Entscheidung

Stand: 30.10.2026. Geprüfte Main-Basis:
[`e8703a65ce8c1ba48ed1c9be3a8b7b8ff4dac37f`](https://github.com/burckhju/trading-workspace/commit/e8703a65ce8c1ba48ed1c9be3a8b7b8ff4dac37f).
Die Quellversion ist weiterhin **1.5.31**. Der unveränderte Tag `v1.5.31` zeigt
auf `5f1b675e09bd993da8e0576067e3e466c5b5bbdb`; Main enthält zusätzlich die
Dokumentationsintegration #301 und den Positionskursverlauf aus #302.
Das GitHub-Release-API führt als jüngstes veröffentlichtes Release nur
[`v1.0.0-product-selection`](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection)
vom 16.08.2026. Git-Tag, Quellversion, GitHub Release und tatsächlich installierter
Serverstand sind unterschiedliche Nachweise. Ein PC-/Produktionsstand wurde nicht geprüft.

Während der PR-Erstellung wurde #303 unabhängig von diesem Auftrag nach Main
integriert. Neuer Main-Stand:
[`4f70760c0dcf0448e470eef85e79253d897189e5`](https://github.com/burckhju/trading-workspace/commit/4f70760c0dcf0448e470eef85e79253d897189e5).
Die acht geänderten Monitoringpfade überschneiden sich nicht mit den vier Pfaden
dieses Schnitts. Dieser Main wurde konfliktfrei ausschließlich in den Feature-Branch
übernommen. Der separate [Draft-PR #305](https://github.com/burckhju/trading-workspace/pull/305)
führt Tests und CI für den aktualisierten Integrationscommit; frühere grüne
Ergebnisse werden nicht auf ihn übertragen. Quellversion und Tag bleiben unverändert.

**Alle drei relevanten Providerpfade sind inzwischen implementiert.** Der
verbleibende sichere Änderungsschnitt korrigiert eine reproduzierbare Abdeckungslücke
im bestehenden gettex-Dateicache und dessen HTTP-Fehlerbehandlung. Es wird keine
zusätzliche externe Quelle integriert, weil dafür kein neuer ausreichender
Zugangs-, Nutzungs- und Produktkursnachweis vorliegt.

## PR #220 und seitdem integrierte Funktionen

[#220](https://github.com/burckhju/trading-workspace/pull/220) ist offen, kein Draft,
Head `40da0f23dea50cf6c70f1232f61ffd83f825dd19`. Vollständiger geprüfter Umfang:

- `docs/GETTEX_SCHEMA_PROBE.md`;
- `docs/issuer-quote-coverage.md`;
- das neue `docs/issuer-quote-research-expanded.md`.

Es sind ausschließlich September-Recherche und Probehinweise. Die abgerufene
Diskussion enthält keine Kommentare oder Reviews. Die dort dokumentierten
Providerplanungen dürfen nicht über die heutige Implementierung kopiert werden.
Die alte Forschung bleibt nachvollziehbar; **#220 sollte als historischer
Forschungs-/Dokumentations-PR getrennt bleiben**. Vor einem späteren Merge braucht
sein Text eine datierte Einordnung des inzwischen integrierten Standes.
Dieser Auftrag verändert weder seinen Branch noch seinen Integrationsstatus.

Neuere Main-Nachweise gegenüber #220:

| Bereich | Bereits vorhandener Stand |
|---|---|
| gettex | [Adapter](../../backend/app/providers/gettex_delayed/adapter.py) und [Parser](../../backend/app/providers/gettex_delayed/parser.py), explizite Privatnutzungsbestätigung, MUND-/MUNC-Identität, UTC-Fenster, vollständige GZip-Prüfung, Fehlerisolation pro ISIN und dauerhafte Retention. |
| Morgan Stanley | [Streamadapter](../../backend/app/providers/morganstanley/adapter.py), neun historische zulässige Produktbindungen, dynamische Routenevidenz und ausdrückliche Sperre eines weiteren Produkts. |
| JPMorgan | [Streamadapter](../../backend/app/providers/jpmorgan/adapter.py), sieben historische Bindungen, dynamische Routenerkennung, privater Zustimmungsspeicher und bereits integrierter Preisbindungsfix aus v1.4.5. |
| Historie | Kanonische Quote-Beobachtungen/-Samples und Reader; Positionsdarstellung aus #302 ist Main. Keine zusätzliche Persistenz erforderlich. |

Die jüngere [Integrationsprüfung vom 28.10.2026](REMAINING_WORK_INTEGRATION_2026-10-28.md)
und die [Betriebsanleitung](../technical/ISSUER_MONITORING_OPERATIONS.md) stimmen
mit diesen Codebefunden überein. Alte, ausdrücklich historische Dokumentabschnitte
sind keine gegenwärtige Aussage über fehlende Adapter.

## Vorhandene Architektur und fachliche Grenzen

`WarrantListingQuoteProvider.get_warrant_listing_quote(WarrantQuoteRequest)`
bleibt die gemeinsame Grenze. `build_warrant_quote_resolver` verbindet Morgan
Stanley, JPMorgan, Frankfurt, Vontobel, Stuttgart delayed und gettex delayed.
EODHD liefert separat insbesondere verifizierte Basiswert-/EOD-Daten; daraus
wird keine Optionsscheinnotierung abgeleitet.

Die aktive Route bindet Workspace, Warrant, Listing, Provider, Mappingversion,
ISIN, Handelsplatz und Währung. Bei gettex müssen Listing-MIC und Provider-MIC
identisch MUND oder MUNC sein. XFRA/XSTU werden nicht umgedeutet. Die vorhandene
[Identitätsprüfung](../../backend/app/features/market_data/persistence/quote_identity.py)
und [Retention](../../backend/app/features/market_data/service/retained_quotes.py)
prüfen die Route vor und nach I/O. Erfolgreiche Originalbeobachtungen bleiben bei
Fehlern erhalten und bekommen im Readback einen ausdrücklichen Aktualisierungsfehler.

`resolve_selected()` verwendet genau den persistent gebundenen Provider. Ein
Ausfall erlaubt weder den Wechsel zur Basiswertnotierung noch zu einem anderen
Provider, MIC oder einer anderen Währung. Der allgemeine Mehrquellenresolver
ersetzt diese Positionsbindung nicht. Ein 404 eines gettex-Dateifensters darf
innerhalb derselben Quelle/MIC die konfigurierten vorherigen Fenster prüfen;
429, Zugriffssperren, ungültige Daten und Transportfehler erlauben diesen
Fallback nicht. Originalzeit, Delay und Altersprüfung bleiben maßgeblich.

Es bestehen fünf getrennte Scheduler-Lanes: Emittentenquotes, Börsenquotes,
Emittentenerkennung, Börsenerkennung und Basiswerte. Die gettex-Korrektur ändert
weder ihre Planung noch die gemeinsame Fehler-/Retry-Schnittstelle. Transportfehler
bleiben strukturierte `MarketDataError`-Unterklassen mit providerbezogenen Codes.
Die Retention erhält den Code, leitet aber `retry_after` nicht als Schedulerauftrag
weiter. Deshalb muss gettex sein 429-Abrufverbot selbst vor dem nächsten HTTP-Aufruf
einhalten; hierfür ist kein neuer Scheduler und keine wartende Schleife notwendig.

Bekannte Qualitätsgrenzen bleiben bestehen: fehlende Seiten bleiben unbekannt;
Geld, Brief und Referenzpreis sind getrennt; keine FX-Schätzung; alte oder
indikative Daten sind keine ausführbaren Quotes. MS enthält einen lokalen
Zeittext ohne verifizierte Zeitzone, JPMorgan nur eine Zeit ohne verifiziertes
Datum/Zeitzone. Beide erhalten `observed_at=None` und ihre jeweiligen
Indikations-/Zeitbasiskennungen. Empfangszeit wird nicht als Kurszeit ausgegeben.

## Ursprüngliche Abdeckungslücken erneut eingeordnet

Die Kennungen stammen ausschließlich aus der schon veröffentlichten Forschung.
Es wurde kein aktuelles Depot, privater Zustimmungsspeicher oder produktives
Mapping gelesen. Historische Nachweise sind keine heutigen Live-Kurse.

| Gruppe / ISINs | Tatsächlich neuerer Nachweis | Verbleibende Grenze |
|---|---|---|
| MS: DE000MM02AF0, DE000MJ3QMM4, DE000MK8B3F2, DE000MN50FN0, DE000MN25S42, DE000MM02M95, DE000MM34MJ0 | Bekannte technische Routen; die bereits vorhandene Nutzer-Serverprobe vom 21.09.2026 enthält positive Geld-/Briefwerte. | Heutige Versorgung und Produktlaufzeit nicht erneut live belegt; Zeitzone unbekannt. |
| MS: DE000MJ3QFV9 | Bekannte Route, historischer positiver Geldkurs; Quell-Ask nullwertig und korrekt als fehlend behandelt. | Kein erfundener Briefkurs oder Spread. |
| MS: DE000MJ7DUX3 | Bekannte Route, historische positive Geld-/Briefwerte mit nullwertigen Volumina. | Explizite Volumenwarnung; kein Ausführbarkeitsnachweis. |
| MS: DE000MN2ZUN2 | Alle Quellfelder der neueren Probe fehlen; `PRODUCT_EXPIRED_SETTLEMENT_REVIEW_REQUIRED`. | Bewusste Sperre vor Quellenauswahl, keine normale Providerlücke und kein zulässiger Fallback zur Umgehung. |
| JPM: DE000JY557T1, DE000JE85E17, DE000JZ0V6V0, DE000JY27NF1, DE000JY10A58, DE000JE7KTY8, DE000JY3SF71 | Sieben bereits verifizierte historische Streambindungen im bestehenden Adapter. | Kein heutiger vollständiger Quote-/Zustimmungsnachweis; Datum/Zeitzone unbekannt. |
| JPM: DE000JZ91459 | In der späteren [Renderer-Qualifikation](../technical/ISSUER_RENDERED_DISCOVERY_V1_1.md) dokumentierter Produktzugang; bestehende dynamische Discovery ist vorgesehen. | Keine aus einem Präfix geratene statische Streamkennung und keine neue bestätigte Live-Quote. |
| UC: DE000UN37224 | #220 dokumentiert drei genaue Treffer in einer vollständig geprüften MUND-Datei vom 14.09.2026: 538.279.151 komprimierte Bytes, 29.884.150 Zeilen, EUR, getrennte Seiten, UTC. MUNC wurde laut späterem [Entscheidungsnachweis](../quote-source-decision.md) ebenfalls separat geprüft. | Kein heutiger Feed-/Handelbarkeitsnachweis aus dieser Umgebung. Die alte Aussage „MUNC ungeprüft“ ist überholt. |

Die MS-Probe liegt bereits in
`tests/fixtures/morganstanley/user-snapshots-20260921.json`. Es wurden keine neuen
Rohquotes in das Repository übernommen. Für gettex wurden keine umfangreichen
Marktdatendateien erneut heruntergeladen.

## Externe Quellenprüfung am 30.10.2026

Die Suchfunktion lieferte bei mehreren unabhängigen Aufrufen nur leere Fehler.
Die nachfolgenden Beobachtungen stammen deshalb aus begrenzten normalen
HTTPS-Leseabrufen der offiziellen URLs. Ein 403 wurde als Zugriffshindernis
behandelt; Header, Sitzung, Standort oder Browseridentität wurden nicht zur
Umgehung verändert. Ein 200 ohne Kursdaten gilt nicht als Quote-Nachweis.

| Quelle | Identität / Seiten / Währung / Zeit | Heutiger technischer Befund | Nutzungs- und Integrationsentscheidung |
|---|---|---|---|
| [MS-Bedingungen](https://zertifikate.morganstanley.com/nutzungsbedingungen/) | Historische produktbezogene EUR-Indikationen im Repository; Zeitpunktqualität bleibt eingeschränkt. | Bedingungen HTTP 200. Kein neuer Stream oder Serienabruf der zehn Produktseiten. | Websitepreise sind indikativ und möglicherweise verzögert. Kopieren/Weitergabe unterliegen Zustimmungsvorbehalten; kein neuer unterstützter API-/Speichervertrag oder Abruflimit bestätigt. Bestehender Adapter wird nicht erweitert oder aktiviert. |
| [JPM, exakte JE7KTY-Produktseite](https://www.jpmorgan-zertifikate.de/zertifikate-detail/DE000JE7KTY8) | Kein aktueller produktbezogener Bid-/Ask-/Währungs-/Zeitpayload erhalten. | HTTP 200, 30.243 Bytes, aber Zustimmungstext. SHA-256 `e0882ed9adcfecc59cd88d0b6929c820ac913232ea4d6e43c2810539cb1a9d69`. | Keine persönlichen Erklärungen bestätigt, keine Zustimmung gespeichert, kein Streamzugang versucht. Vorhandener Consent-Vertrag bleibt maßgeblich. |
| [Onvista-Bedingungen](https://www.onvista.de/nutzungsbedingungen) | #220 enthält alten JE7KTY-Produktpayload mit getrennten JPM-/Stuttgart-Quellen, EUR, Geld/Brief und UTC-Offsets; Intel-USD-Kurse sind Basiswertdaten. | Bedingungen HTTP 200; keine neue Kursabfrage. | Abschnitt 6 verlangt weiterhin ausdrückliche Einwilligung für automatisierte Abfragen. Kein Poller, keine Serienprüfung. Providerkennungen `_STU`/`@_JPML` sind keine ungeprüft übernehmbaren MICs. |
| [gettex delayed](https://www.gettex.de/en/trading/delayed-data), [Dateiliste](https://www.gettex.de/en/trading/delayed-data/pretrade-data/) | Historisch exakte ISIN, MUND/MUNC, getrennte Seiten, Währung und UTC-Fenster; 900 Sekunden deklarierter Delay im Adapter. | Beide Seiten HTTP 403; gettex-Antwort nennt `error code: 1010`. Kein aktueller Dateiabgleich. | Dokumentierter früherer Privatnutzungsrahmen gilt als datierter Nachweis, heute nicht erneut bestätigt. Aktivierung bleibt aus und erfordert die vorhandene explizite Privatbestätigung. Keine Aussage allgemeiner Nichtverfügbarkeit. |
| [UniCredit/onemarkets](https://www.onemarkets.at/de/productpage.html/DE000UN37224) | Historische Produktidentität UN3722, UniCredit Bank GmbH, Call auf BNP Paribas; kein heutiger Quote-Payload. | Direkter Abruf HTTP 403. | Keine neue direkte Website-/API-Anbindung qualifiziert. |
| [Stuttgart-Vertragsdokumente](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/zugang-zu-boersendaten/vertragsdokumente/) | Website-Produktnotierung ist kein Deckungsbeweis des bestehenden Delayed-Feeds. | Direkter Abruf HTTP 403. | Keine neuen Vertrags-/Preis-/Abdeckungsangaben bestätigt. XSTU ist kein stiller Ersatz für MUND. |
| [ARIVA MDS OpenAPI](https://mds.ariva-services.de/swagger-ui/openapi.yml) | Dokumentierte Instrument-/Quellen-/Währungsidentität, Bid/Ask, Zeit und Qualität. | HTTP 200, Version 0.6.25 statt 0.6.20 in #220; OAuth2 Client Credentials. | Keine ausgestellten Zugangsdaten/Quellenrechte und keine echten Quotes der benötigten ISINs geprüft. Dokumentierter Kandidat, keine qualifizierte zusätzliche Versorgung. |
| [FactSet Real-Time Quotes](https://developer.factset.com/api-catalog/real-time-quotes-api) | Frühere API-Dokumentation ist kein neuer ISIN-/Quellenbeleg. | HTTP 200, lediglich 3.124-Byte-App-Shell. | Kein aktueller Quote-/Vertragsnachweis. SIX und Infront bleiben ebenfalls lediglich dokumentierte kommerzielle Kandidaten; kein individueller Zugang geprüft. |

Offen sind damit konkrete Nutzungs-/Speicherfreigaben, persönliche Zustimmung
bei JPMorgan, heutige produktbezogene Live-Abdeckung, MS-/JPM-Zeitbasis sowie
gegebenenfalls ausgestellte Vendor-Zugänge und Quellenrechte. Es wurden keine
Anbieter angeschrieben, Abonnements bestellt oder privaten Zugangsdaten gesucht.

## Kleiner Implementierungsumfang

Die Änderungen sind auf den vorhandenen gettex-Adapter und deterministische
Regressionen begrenzt:

1. **Tatsächlich gescannte ISIN-Menge im Dateicache.** Ein Treffer setzt voraus,
   dass alle aktuell verfolgten ISINs bereits in diesem Batch mitgeprüft wurden.
   Das umfasst auch fehlende und fehlerhafte Produkte. Eine neue verifizierte
   Zuordnung führt im selben Fenster zu einem gemeinsamen erneuten Scan;
   unveränderte oder kleinere Mengen verwenden den Cache weiter. Es entsteht
   kein Dateiabruf pro Position. Ein zusätzliches Mapping kann allerdings einen
   erneuten großen Download auslösen; dieses begrenzte Kostenverhalten ist
   ausdrücklich Teil der Korrektur. Keine neuen automatischen Mappings.
2. **429 im vorhandenen Fehlervertrag.** `GETTEX_DELAYED_RATE_LIMITED` verwendet
   `MarketDataRateLimitError`. Der Transport respektiert eine gemeinsame monotone
   Sperre für beide MICs und alle Workspaces derselben Adapterinstanz. Es gibt
   keine interne Retry-Schleife oder Wartezeit. Ein gültiger bereits gescannter
   Cache bleibt verwendbar; Originalzeiten werden dabei nicht verändert.
3. **Ungültige HTTP-Länge fail-closed.** Fehlerhafte Längenangaben erhalten einen
   stabilen Providerfehler statt eines unstrukturierten `ValueError`. Größenlimit
   und vollständige GZip-Validierung bleiben wirksam. Ein fehlgeschlagener neuer
   Download ersetzt keinen erfolgreichen Cache oder gespeicherten Kurs.

Es gibt keine neue Quelle, Produktfreischaltung, API-/Schemaänderung,
Währungsumrechnung, Historienmigration, Versionserhöhung oder produktive Aktivierung.

## Tests und Integrationsnachweise

Die neuen HTTP-/GZip-Daten werden synthetisch erzeugt. Kein externer Marktdienst
ist Voraussetzung für CI. Die Regressionen prüfen neue ISINs bei gleichem
Dateinamen, unveränderte/reduzierte Mengen, Cache- und Fehlerisolation, Rate Limits,
Zeitüberschreitungen, Zugriffsfehler, veränderte Antworten und unveränderte
Retentions-/Positionsbindung. Die vorhandenen Suiten ergänzen MUND/MUNC,
Produkt-/Basiswertidentität, Bid/Ask, fehlende/veraltete Kurse, Währungskonflikte,
UTC-Tageswechsel, MS-/JPM-Streams, Discovery und Scheduler-Lanes.

Die Retention-Regression führt echte lokale SQL-/JSON-Roundtrips mit synthetischen
Daten aus: mit und ohne alten Kurs, Originalzeit und Quellidentität bleiben
erhalten, Fehler bleiben sichtbar, der alternative Provider wird niemals
aufgerufen. Diese SQLite-Prüfung ersetzt keine PostgreSQL-Integration.

Die endgültigen ausgeführten Befehle, Ergebnisse, Commit-/Baum-SHAs und GitHub-
Run-IDs werden in der Beschreibung des separaten Implementierungs-PRs geführt.
Es gelten unverändert Ruff, Black, mypy und die vorhandenen CI-/Coverage-Gates.

Bereits abgerufene Basisergebnisse, ausdrücklich **kein Testbeleg neuer Änderungen**:

- Main `e8703a65`: [Backend](https://github.com/burckhju/trading-workspace/actions/runs/41094918378),
  [Frontend](https://github.com/burckhju/trading-workspace/actions/runs/41094918399),
  [End-to-End](https://github.com/burckhju/trading-workspace/actions/runs/41094918310): erfolgreich.
- #220 `40da0f23`: Backend `34885796940`, Frontend `34885796699`, End-to-End
  `34885796621`: erfolgreich, jeweils nur für den alten Recherche-Head.

## Parallelkompatibilität und Status

| Strang / geprüfter Head | Abgrenzung |
|---|---|
| #205 `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Tatsächlich Konzept und zwei Hilfsworkflows. Die Umsetzung #302 ist bereits Main. Keine Chart-, Reader- oder Historienänderung in diesem Schnitt. |
| #303 `b95409ada22a731cd59785b7904cdfd72cea79e4` | Im ursprünglichen Schnitt als `4f70760c...` konfliktfrei übernommen. Die spätere Integration mit #307 ergänzt ausschließlich gettex-Fehlercodes und lokale Wartezustände in der bestehenden Diagnostik; siehe Nachqualifikation oben. |
| #197 `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Historischer Forschungsworkflow und Kollektoren. Keine gemeinsamen geänderten Pfade und keine historischen Datenabrufe/-migrationen. |
| #220 `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Bleibt getrennte Forschung. Dieses neue datierte Dokument überschreibt keinen der drei alten PR-Pfade. |

Die vorhandenen Interfaces und geteilten Modelle werden lediglich verwendet,
nicht verändert. Der aktuelle Freigabestatus wird in PR #305 geführt. Recherchiert, historisch
technisch beobachtet, für eine konkrete Nutzung zulässig, implementiert, getestet,
in Main integriert und produktiv aktiviert werden jeweils separat ausgewiesen.
Insbesondere sind vorhandene Main-Adapter kein Nachweis heutiger Quellennutzung
und die neue gettex-Korrektur ist vor einem späteren autorisierten Merge nicht Main.
