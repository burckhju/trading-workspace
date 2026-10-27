# UI5 – Referenzdaten- und Mapping-Eingaben konsolidieren

Datum: 26.10.2026. Ursprünglicher Umfang: gemeinsamer administrativer Eingabeweg, gezielte Tests und Draft-PR.
Die ursprüngliche Freigabe umfasste keine Versionsanhebung oder Veröffentlichung; der folgende ausdrückliche Nutzerauftrag erweitert diese Grenze.

## Nachträgliche Freigabe für Merge und PC-Bereitstellung

Nach der vollständigen Qualifikation des integrierten UI5-Heads `a6b29c2a4e7b0d65a6d50c4def8623e91baa331e` hat der Nutzer ausdrücklich beauftragt: **„Wenn grün mergen und für den pc bereitstellen“**. Damit sind die erneute Prüfung des tatsächlichen Release-Heads, der reguläre Merge und die versionierte Bereitstellung über den bestehenden PC-Updateweg freigegeben. Eine tatsächliche Installation oder fachliche Liveabnahme am Nutzer-PC wird damit nicht behauptet.

Der enge Releasezusatz bereitet **1.5.23** vor. Er passt die fünf Versionswerte in vier Dateien an und ergänzt die [Release-Notiz und den vorhandenen PC-Updateweg](../releases/V1.5.23-REFERENCE-DATA-CONSOLIDATION.md). Dependencies, Lockauflösung, Backendverträge, Migrationen, Launcher, Prüfsummenbindung und Veröffentlichungsgates bleiben erhalten.

Beim Release-Abgleich war der bisherige Main-Push-Frontendlauf `40352178360` wegen eines Bestandsfalls in `WarrantCreateWithListing.test.tsx` fehlgeschlagen. Dessen Testaufbau wartete nur auf eine statische Überschrift und band einen Fehler an den nächsten beliebigen GET. Ein noch auslaufender alter Leseablauf konnte dadurch die für das neu angelegte Produkt gedachte Antwort verbrauchen. Der gesondert ausgewiesene Testzusatz wartet auf den abgeschlossenen Initialread und bindet den Fehler an die angelegte Produkt-ID; sämtliche fachlichen Assertions bleiben bestehen. Produktivcode und Timeouts werden dadurch nicht geändert.

Der neue Release-Head muss die regulären PR-Gates bestehen. Danach müssen Backend, Frontend und End-to-End auf dem tatsächlichen aktuellen Main-Push erfolgreich abschließen, bevor der unveränderte Publisher den neuen Tag anlegt. Genaue Head-/Tree-/Run-/Merge-/Tagbezüge und der tatsächlich geprüfte Updatebefehl stehen nach ihrem Readback in PR #288 und der Übergabe. Frühere grüne Läufe ersetzen diesen neuen Nachweis nicht.

## Integration des inzwischen aktualisierten Main vor dem Releasezusatz

Während der regulären UI5-CI wurde UI4 / PR #287 separat nach Main integriert. Der UI5-Draft übernahm deshalb Main **`36db3910eae714d0cb0ad0ae16169955006a5976`** mit dem bestehenden Main-Tree `a905af1a0908cb4eac233474a024e2dd683a64d3`. Bei dieser damaligen Integration vor dem Releasezusatz wurde die dort bereits enthaltene Version **1.5.22** unverändert übernommen. Die ursprüngliche UI5-Implementierung führte keine eigene Versionsanhebung oder Veröffentlichung aus.

Die Zusammenführung war konfliktfrei. Ein unabhängiger Git-Objektvergleich bestätigt: Alle **27 UI5-Code-/Testdateien** sind gegenüber dem unten dokumentierten Implementierungscommit `50b3aea9…` in Inhalt und Dateimodus unverändert. Die 28 von UI4/Main übernommenen Pfade überschneiden sich mit keinem UI5-Pfad. Guard, Router und Versions-/Manifestdateien entsprechen vollständig dem neuen Main. Vor diesem Dokumentationsnachtrag war auch der gesamte UI5-Diff gegenüber der neuen Main-Basis bytegleich zum ursprünglichen UI5-Diff.

Das unveränderte vollständige Frontend-Gate wird auf diesem integrierten Stand erneut ausgeführt. Dessen tatsächliche Ergebnisse sowie die erneut ausgelösten regulären PR-Gates werden mit **aktuellem Integrations-Head, Gesamtbaum und Testmerge in der PR-Beschreibung** gebunden. Die nachstehenden früheren lokalen Qualifikationen bleiben ausdrücklich dem ursprünglichen Implementierungsbaum zugeordnet. Sie werden nicht als neue vollständige Integrationsläufe ausgegeben. Die exakte lokale SQL-Zeile belegt weiterhin denselben unveränderten UI5-Eingabeweg.

## Ausgangsstand und erste Prüfbindung

- Main-Basis bei Arbeitsbeginn: `eb443bdf7569b5a187b4be97dba1e1fcb7a0ed0f`, VERSION **1.5.21**.
- Der Startprompt nannte noch `f8f61a11…`. Bei Arbeitsbeginn war UI3 / PR #286 bereits als `eb443bdf…` integriert. Diese Änderungen sind enthalten und bleiben unverändert.
- UI4 / Draft-PR #287 war vor dem Erstellen des UI5-PR noch offen. Sein ursprünglicher Head `c293a6778b7c9ab80c366329041096d97984757f` wurde separat auf `c8844b931388b28e72759a3ec46936b656887c43` fortgeführt; dessen Basis war ebenfalls `eb443bdf…`. UI5 zog diesen parallelen Releaseumfang nicht vor. Nach dessen eigenständiger Integration wurde der neue Main wie oben beschrieben übernommen.
- Implementierungs- und Testcommit: [`50b3aea94e4bc80aef1dd44e440eea21c016f13c`](https://github.com/burckhju/trading-workspace/commit/50b3aea94e4bc80aef1dd44e440eea21c016f13c).
- Vollständiger lokal geprüfter und auf GitHub identischer erster Implementierungsbaum: **`26c18c5fba198ddb0e4b3b48a56b1a48e741fa9b`**. 27 Code-/Testdateien geändert. Der erste anschließende Dokumentationscommit ergänzte ausschließlich dieses Dokument; aktueller Integrations-Head und Gesamtbaum stehen in der PR-Beschreibung.
- Arbeitsbranch: `refactor/reference-data-ui-consolidation`.

Die hier genannten Ergebnisse wurden auf den neuen Dateiinhalten ausgeführt. Frühere grüne UI3-/UI4- oder Release-Checks werden nicht als UI5-Nachweise verwendet.

## Bedienweg vorher und nachher

Vorher hatten `/top-down-admin` und `/chart-setup` eigene Formulare für dieselben sieben Zuordnungs-, Mapping- und Importaktionen. Chart-Setup wertete `action` nicht aus, ersetzte beim Nachladen des Basiswerts eine ausdrücklich gewählte Notierung durch das Primary Listing und verwendete für Validierung/Import den ersten passenden Mappingtreffer. Bestehende Mappingwerte wurden nicht strukturiert vorausgefüllt. Vorschläge und Eingaben erschienen gleichzeitig ohne gemeinsamen Entwurfsschutz.

Jetzt bleibt `/chart-setup` der einzige Eingabeort für diese sieben Vorgänge. `/top-down-admin` prüft ihren Kontext und ersetzt den alten Einstieg durch die kanonische Route. Es bleibt dort kein zweites Formular. Auch ein direkter Aufruf von `/chart-setup` wird geprüft; eine Weiterleitung allein ist kein Vertrauensnachweis.

1. **Candidate-Reparatur:** konkreten blockierten Schritt öffnen → aktuelle Aktion und Identitäten prüfen → gebundenen gemeinsamen Editor anzeigen → nur fehlendes Ziel beziehungsweise tatsächlich änderbare Werte eingeben → ausdrücklich bestätigen → genau einen bestehenden API-Befehl senden → aktuelle Daten und Readiness lesen → zum konkreten Candidate zurückkehren.
2. **Chart-Einrichtung:** vorhandenen Chartkontext öffnen → Objekt und dazugehörige Aktion wählen → genau einen aktiven Editor verwenden → explizit speichern/prüfen/importieren → aktuelle Daten lesen → zur bisherigen Chartauswahl zurückkehren.
3. **Einrichtungshilfe:** Sektor-/ETF-Vorschläge ausdrücklich anzeigen → Quellen prüfen → ein Anlageformular vorbereiten. Vorbereiten schreibt nichts. Ein offener Entwurf wird erst nach bewusster Verwerfung ersetzt.

Die Objektwahl ist kompakte Navigation. Der gewählte Kontext zeigt Namen, Wertpapierart, gegebenenfalls ISIN sowie Listing/MIC/Währung einmal zusammenhängend; technische IDs ergänzen diese Anzeige. Symbol und Exchange werden ausschließlich im Mappingeditor bearbeitet. Status und Validierung sind kompakte Hinweise, keine zweite vollständige Datenkarte. Freie Listing-ID-Eingaben entfallen.

## Aktionen und Kontextvertrag

| Bestehende Workflow-Aktion | Kanonische Aktion | Festes Ausgangsobjekt / wählbares Ziel | `resource_id` als Legacy-Fallback |
|---|---|---|---|
| `ASSIGN_BROAD_MARKET_BENCHMARK` | `stockMarket` | Basiswert fest; Marktbenchmark wählen | Kein Vertrag, widersprüchliche Verwendung sperrt |
| `ASSIGN_SECTOR` | `stockSector` | Basiswert fest; Sektor wählen | Kein Vertrag, widersprüchliche Verwendung sperrt |
| `ASSIGN_SECTOR_REFERENCE` | `sectorReference` | Sektor fest; aktive `SECTOR_INDEX`-Referenz wählen | Sektor |
| `ASSIGN_REFERENCE_LISTING` | `proxy` | Referenz fest; bestehendes Wertpapier und Listing wählen | Marktreferenz |
| `CREATE_EODHD_MAPPING` | `listingMapping` | Listing und tatsächlicher Listing-Basiswert fest; vorhandene Mappingfelder bearbeiten oder fehlende Kennungen eingeben | Listing |
| `VALIDATE_EODHD_MAPPING` | `listingValidate` | Listing und konkrete Mapping-ID fest | Mapping |
| `IMPORT_DAILY_PRICE_HISTORY` | `listingImport` | Listing und Mapping fest; Zeitraum ausdrücklich bestätigen | Listing |

`proxy` bleibt der interne vorhandene Aktionsname. Die Oberfläche bezeichnet den Vorgang allgemein als Referenz→Listing. Erst ein tatsächlich ausgewähltes ETF-Wertpapier wird als ETF-Proxy gekennzeichnet. Eine normale Aktie wird nicht als ETF dargestellt; fehlende Indexdaten bewirken keinen automatischen Ersatz.

`referenceDataContext.ts` vereinheitlicht Query-IDs und JSON-`action_params`, übersetzt `market_reference_id` nach `referenceId` und prüft doppelte beziehungsweise widersprüchliche Angaben. Dieselbe Ressource wird niemals gleichzeitig als Sektor, Listing und Mapping interpretiert. Unbekannte Aktionen, fehlende erforderliche Workflow-Ausgangsobjekte und ungültige Identitätsketten bleiben gesperrt.

Der frische Candidate-Workflow wird gegen **alle konkreten blockierten Schritte** geprüft. Aktion, vorhandene Parameter, Ressourcenkennung und gegebenenfalls `step_code` müssen passen. Mehrere Schritte sind ausdrücklich erlaubt; `next_action` wird nicht als einzig erlaubter Einstieg behandelt. Vor dem Write erfolgt der Abgleich erneut. Ein inzwischen erledigter oder geänderter Schritt löst keinen Write und keinen stillen Wechsel zu einem anderen Schritt aus.

Nur die beiden Basiswert-Zuordnungen müssen zum analysierten Candidate-Basiswert gehören. Listingreparaturen dürfen einen anderen tatsächlichen Owner besitzen, etwa den Basiswert einer Markt- oder Sektor-ETF-Notierung. Dieser Owner kommt aus Workflowparametern und vorhandenen Stammdaten, nicht aus einer pauschalen Candidate-Zuweisung.

Ein explizites Listing bleibt erhalten, auch wenn es nicht primär ist. Bei Listing-Links ohne Owner wird die Identität über den vorhandenen persistierten Chart-Serien-Read gelesen und anschließend gegen die vollständigen Basiswert-Listings geprüft. Das Primary Listing wird ausschließlich ohne explizite Wahl vorausgewählt. Widersprüchliche Zugehörigkeit oder mehrere Primary-Treffer sperren.

## Unveränderte fachliche Owner und Quellen

Die vier Zuordnungen bleiben **neue Datensätze per POST**. Ihre Valid-Time- und Überlappungsprüfung bleibt im Backend. Ein Chartkontext zu einem Stichtag ist keine vollständige administrative Bearbeitungsversion einer Zuordnung. Die UI bietet deshalb weder Schein-Updates noch ein vermeintliches Umbinden durch einen überlappenden POST an.

| Einstieg / Vorgang | Herkunft | Quellenbeleg | Wirksame Gültigkeit |
|---|---|---|---|
| Chart-Zuordnung | `CHART_SETUP` | ausdrücklich eingegebener Beleg | sichtbar gewähltes `valid_from`, `valid_to: null` |
| Candidate-Zuordnung | `MANUAL_ADMIN` | `Candidate live workflow` | sichtbarer UTC-Tagesbezug; ein inzwischen veralteter Tag sperrt den Write |
| Sektor→Referenz aus beiden Einstiegen | Herkunft wie oben | **kein zusätzlich gespeicherter `source_reference`**; weder irreführendes Feld noch Persistenzbehauptung | wie oben |
| Index-Renditegrundlage | bestehender eigener Bestätigungsvertrag | gesonderter HTTPS-Beleg | exakt `mapping_id` und `mapping_version` |

`quality_status: GOOD` und das offene Gültigkeitsende bleiben sichtbar. Der vorhandene Chart-Startwert für die Datumswahl bleibt erhalten; ein Quellenwechsel auf den Candidate-Default findet nicht still statt. Der Router von Sektor→Referenz verwirft `source_reference` ausdrücklich; der gemeinsame Client sendet dieses Feld dort nicht mehr.

Bootstrap, Sektoranlage und Sektorreferenzanlage bleiben eigene ausdrückliche Aktionen. Name, Code, Klassifikation, Region und Version bestehender Stammdaten werden nicht über erfundene Update-Endpunkte geändert. Für eine neue Sektorreferenz ist die zuvor implizite Region im Formular sichtbar.

Die verbleibenden Top-down-Aktionen für Reaktivierung, Primary-Listing-Verweis und `RUN_MARKET_ANALYSIS` bleiben funktionsfähig. Die Primary-Pflege bleibt in der Basiswertverwaltung. Modellaktivierung und Candidate-Evaluation werden nicht in den neuen Editor verlagert oder automatisch ausgelöst.

## Mapping, Validierung und Indexgrundlage

Die Frontend-Typen entsprechen dem bestehenden `ProviderMappingResponse`: nullable `listing_id` und `market_data_instrument_id`, `provider`, `version`, Status, Validierungszeitpunkt/-meldung sowie vorhandene Workspace-/Zeitfelder. Es gibt keine neue Einzelmapping-GET-API. Der vorhandene vollständige Mapping-Read wird nach exakter Listing-ID und `EODHD` aufgelöst. Eine vorgegebene Mapping-ID muss genau dazugehören; fremde oder mehrdeutige Treffer sperren.

Für direkte Indexreferenzen wird die Kette **Referenz → Instrument → Mapping-ID/Revision** aus dem Chartkatalog gegen den vollständigen Mappingdatensatz geprüft. `listing_id` muss null sein. Ein Index erhält keinen künstlichen FT-001-Basiswert und kein Listing. Symbol und Exchange kommen aus den strukturierten Mappingfeldern; `provider_identity` wird nicht zerlegt und Ticker/MIC werden nicht als Providerkennung geraten.

- Der bestehende PUT erhöht die Revision, setzt `DISABLED` und entfernt die vorherige Validierung. Die Oberfläche erläutert dies vor dem Schreiben.
- Ohne wirksame Änderung gibt es keinen PUT, auch nicht bei äußerem Leerraum oder anderer Groß-/Kleinschreibung entsprechend der Backendnormalisierung.
- Validierung und Import sind eigenständige, bestätigte Aktionen. Auch erneute Validierung erhöht die Revision.
- `MATCHED`, `CONFLICT`, `AMBIGUOUS` und `UNRESOLVED` bleiben getrennt sichtbar. Ein technisch aktives Mapping ist kein eindeutiger Handelsplatznachweis. Der Editor sperrt Listingimport ohne `MATCHED`; er startet weder Import noch Venue-Wechsel automatisch und behauptet keinen erfolgreich geklärten Reparaturschritt.
- Die Indexgrundlage wird nur bei passender Instrument-, Mapping- und Revisionsidentität angezeigt. Nach PUT oder erneuter Validierung wird der Chartkatalog neu gelesen. Alte Evidenz wird nicht auf die neue Revision übertragen; die Grundlage erscheint wieder als `UNKNOWN`, bis sie gesondert belegt bestätigt wurde.

Ein erfolgreicher Mapping-Write wird an seine tatsächlich bestätigte Mapping-ID gebunden, bevor das Nachlesen beginnt. Auch die erste Anlage darf beim Readback nicht unbemerkt auf ein anderes Mapping wechseln.

### Nebenläufigkeitsgrenze

Vor dem Write liest der Editor den sichtbaren Datenstand erneut. Erkennbare Änderungen an Mappingrevision, Identitäten, Status oder relevanten Grundlagen verlangen eine erneute Prüfung. Der eingegebene Entwurf bleibt dabei erhalten; eine neue Bestätigung ist erforderlich.

Diese Prüfung ist **keine atomare Konkurrenzsperre**. Mapping-PUT und Validierung besitzen kein `expected_version`, `request_id` oder Compare-and-swap. Eine konkurrierende Änderung unmittelbar nach dem Read bleibt möglich. Auch der Venue-GET liefert keine Mappingrevision; eine Änderung zwischen Mapping-Read und Venue-Read kann nicht atomar ausgeschlossen werden. Erkennbare falsche Listing-Venue-Identitäten oder unvollständige Venue-Antworten werden als gestörter Readback ausgewiesen.

## Entwürfe, laufende Vorgänge und Fehler

Genau ein `PendingNavigationGuard` mit unveränderter globaler API schützt die kanonische Seite. Eine lokale Verwerfungsentscheidung schützt Objekt-/Aktionswechsel und Vorschlagsübernahme. Query-Navigation und Browser-Vor/Zurück laufen durch den echten Data-Router-Guard. Während einer Mutation gibt es keine Kontextverwerfung; ein synchroner Ref-Lock verhindert den zweiten Submit vor dem nächsten React-Render.

Reads sind an Kontext und Generation gebunden und werden abgebrochen beziehungsweise bei verspäteter Antwort ignoriert. Der A→B→A-Fall wird ausdrücklich getestet. Bis zur anfänglichen geprüften Kontextauflösung sind lokale Wechsel gesperrt. Ein erneuter Read desselben Kontexts remountet den Editor nicht und überschreibt keine offenen Mappingeingaben. Eingabe-, Ziel- oder relevante Grundlagenänderungen setzen die Bestätigung zurück.

Schreibabschluss und Nachlesen sind getrennte Zustände:

| Ergebnis | Verhalten |
|---|---|
| Bestätigte erfolgreiche Schreibantwort, erfolgreicher Readback | Abschluss anzeigen, neue Mapping-/Chartdaten und gegebenenfalls Readiness zeigen; keine Folgeaktion |
| Erfolgreiche Validierung, danach Venue-GET fehlgeschlagen | Write bleibt abgeschlossen; ausschließlich „Nur Lesestand erneut laden“ anbieten; kein erneuter Validierungs-POST |
| Spezifischer 409-/422-/Validierungsfehler | bestehenden Fehlercode/-text erhalten, Eingaben bewahren, Bestätigung zurücksetzen |
| Transportabbruch oder unvollständige/widersprüchliche Erfolgsantwort | Abschluss unbekannt; zunächst aktuellen Zustand lesen; automatischen Replay unterlassen und Schreibaktion sperren |
| Passender aktueller Wert nach unbekanntem Request | als aktuellen Lesestand anzeigen; er beweist **nicht** den Abschluss des eigenen Requests |

Der Receipt-Validator prüft nur Felder der tatsächlich vorhandenen Response-DTOs. Referenz-Mappingantworten besitzen beispielsweise keine zusätzliche `reference_id` und keine vollständigen GET-Zeitfelder; solche Nachweise werden nicht erfunden. Normale GETs, Kontextweiterleitung, Auswahl und Vorschlagsvorbereitung lösen keine Provideraufrufe oder fachlichen Writes aus. Die vorhandene allgemeine Basiswertsuche besitzt einen Provider-Fallback; der gemeinsame Editor nutzt deshalb eine gezielte Suche ausschließlich in vorhandenen lokalen Stammdaten.

Candidate-Rückwege werden intern als `/candidates?candidate=…` erzeugt. Chartlinks erhalten ihre bestehenden erlaubten Queryfelder über `chart_context`; der Rückweg bleibt intern unter `/market-charts`. Freie externe Rücksprungadressen werden nicht verarbeitet. Die minimalen Änderungen an `MarketChartsPage` und `TimeSeriesChart` betreffen ausschließlich diese Links. Reihen, Berechnungen, Detailwerte und gespeicherte Chartansichten bleiben unverändert.

## Erste abgeschlossene lokale Prüfungen

Diese konkreten Zahlen und Laufzeitangaben gehören zum ersten Implementierungsbaum `26c18c5f…`. Die erneute Qualifikation nach Übernahme des inzwischen integrierten Main wird separat am aktuellen PR-Head ausgewiesen.

| Prüfung | Ergebnis und Grenze |
|---|---|
| Unverändertes `bash scripts/check-frontend.sh` | **1.182 Tests in 136 Dateien bestanden**; TypeScript, ESLint ohne Warnungen, Prettier, unveränderte Coverage-Gates und Produktionsbuild erfolgreich |
| Coverage desselben Gesamtgates | Statements/Lines **94,87 %**, Branches **88,88 %**, Functions **88,49 %**; unveränderte Grenzen: Lines/Functions/Statements jeweils 80 %, Branches 70 % |
| Direkte Kontext-/Top-down-/Navigationstests | **72 Fälle** als Teilmenge des Gates; davon **14** kanonische Navigationsfälle mit `createMemoryRouter` und `RouterProvider` |
| Mapping-, Response- und Client-Verträge | **96 Fälle** als Teilmenge des Gates; Methode, Endpunkt, genaue IDs, Herkunftspayloads, alle Venue-Zustände und unklare Responses geprüft |
| Gemeinsame Seite | **26 Fälle** als Teilmenge des Gates; die vorhandenen Regressionstests für `MarketChartsPage`, `TimeSeriesChart` und `CandidatePage` einschließlich historischer Evaluationen sind unverändert im vollständigen Gate enthalten |
| Bestehende Backend-Regressionen | **80 bestanden, 0 Skips/Fehler**, 14 unterschiedliche Dateien in zwei disjunkten Läufen; einschließlich der beiden echten PostgreSQL-Dateien unten |
| Neuer Python-Testhelfer | Black mit `backend/pyproject.toml`, Ruff und `git diff --check` bestanden |
| Abschließender Browserlauf | **8 bestanden, 0 Skips/Fehler/Flaky, alle retry: 0**, 13,643 s; ein echter API-/PostgreSQL-Fall, sieben geroutete UI-Fälle einschließlich zweier unveränderter Marktchartfälle |
| Visuelle Bedienprüfung | Desktop, Tastatur/Fokus und 390×844; keine überlappenden Bedienelemente oder horizontaler Dokumentüberlauf; zusätzliche rein lesende Aufnahmen des gespeicherten synthetischen Candidate-/Sektorkontexts |
| Dateiintegrität | 427 Frontend-/Browserquellen und Konfigurationsdateien vor/nach dem finalen Browserlauf identisch; Manifest-SHA-256 `1212d74eb914c8137be01d7b20f3755999b9b4803482adada738f5c80fc23280` |

Die Teilmengen werden nicht zu den 1.182 Frontendtests addiert. Vorhandene React-`act`-Hinweise einzelner unveränderter Tests und der bekannte Vite-Hinweis auf große Chunks bleiben in den Logs sichtbar. Beide Backendläufe enthalten die bestehende Starlette-/AnyIO-DeprecationWarning. Kein fehlgeschlagener Entwicklungsversuch wird als grünes Gate gezählt.

### Echter administrativer Browser-/API-/PostgreSQL-Weg

`tests/e2e/reference-data-consolidation.spec.ts` erzeugt über bestehende APIs einen ausschließlich synthetischen Basiswert, Sektor und Candidate. Der Browser öffnet den tatsächlich vorhandenen Link für `ASSIGN_SECTOR`, obwohl `next_action` eine andere Aktion ist. Nach der Kontextweiterleitung bleibt der Basiswert fest; nur der Sektor wird gewählt. Bestätigung plus Doppelklick erzeugen genau einen administrativen POST. Danach werden aktuelle Readiness und der tatsächliche Rückweg geprüft. Dieser Fall verwendet **keine** API-Interception.

Der zusätzliche `tests/e2e/support/reference_data_postgres.py`-Reader prüft in einer schreibgeschützten Transaktion exakt die gespeicherte Zeile. Er verlangt Loopback, den vorhandenen Testdatenbanknamen, einen zufälligen passenden Datenbankmarker sowie synthetische Objektidentitäten. Es entsteht keine Produktiv-Lese-API.

```text
assignment_id:     fca4ec13-b348-488a-93d1-4eced7801d11
candidate_id:      00ab2eb4-a0a9-4449-8303-3f9085f243dd
underlying_id:     81e1abfb-d9cd-4592-be53-5b02db4bd07e
sector_id:         a01b0ee6-3135-4943-ac27-52eed5036181
assignment count: 1
valid_from:        2026-10-26
valid_to:          null
source:            MANUAL_ADMIN
source_reference:  Candidate live workflow
quality_status:    GOOD
PostgreSQL:        16.15
Alembic:           20261017_0047
```

Der neue Realfall nutzt in der bestehenden regulären Smoke-CI deren vorhandene explizite Freigabe `TRADE_E2E_WRITES_ALLOWED=1`. Lokal wurde `REFERENCE_DATA_E2E_WRITES_ALLOWED=1` für den eigens identifizierten Wegwerfstack verwendet. Der optionale SQL-Read erfordert zusätzlich seinen passenden lokalen Marker. Keine CI-Identität, bestehende Runnerprüfung oder Portschutzregel wurde geändert.

Der zweite Teil derselben Browserdatei verwendet kontrollierte API-Antworten für Vorbefüllung, unbekannte Transporte, Providerfehler und Venue-Konflikte. Diese Fälle beweisen UI-Verhalten; sie werden ausdrücklich nicht als PostgreSQL-Schreibnachweise bezeichnet. Dasselbe gilt für den bestehenden Memory-UoW-Top-down-Fixturetest.

### Backend-Auswahl

Der erste Lauf bestand mit 35 Tests:

```text
tests/unit/backend/features/market/test_top_down_admin_api.py
tests/unit/backend/features/market/test_top_down_administration_service.py
tests/unit/backend/features/market/test_top_down_reference_domain.py
tests/unit/backend/features/market/test_top_down_readiness_instrument_chain.py
tests/unit/backend/features/market_data/test_mapping_administration.py
tests/unit/backend/features/market_data/test_provider_mapping_instrument_boundary.py
tests/unit/backend/features/market_data/test_reference_market_data_service.py
tests/integration/backend/database/test_market_charts_postgres.py
tests/integration/backend/database/test_provider_mapping_instrument_guard_postgres.py
```

Der zweite, disjunkte Lauf bestand mit 45 Tests:

```text
tests/unit/backend/features/market/test_chart_context.py
tests/unit/backend/features/analysis/test_chart_service.py
tests/unit/backend/features/candidate/test_live_workflow_api.py
tests/unit/backend/features/candidate/test_top_down_domain.py
tests/integration/backend/test_top_down_fixture_e2e.py
```

Die beiden genannten Datenbankdateien enthalten je einen tatsächlich ausgeführten PostgreSQL-Fall. Der vorhandene Chart-Persistenzanker prüft weiterhin gespeicherte Markt-/Sektor-/Aktienidentitäten und immutable Indexevidenz.

### Laufzeit, Befehle und Ausführungsgrenzen

Verwendet wurden **Node 22.16.0 / npm 10.9.2**, **Python 3.12.14**, **Chromium 1187** und eine eigene native **PostgreSQL-16.15**-Instanz. Repository-Manifeste, Lockdateien, Runner und Workflows bleiben unverändert. `npm ci` und die gepinnten Backend-Abhängigkeiten wurden verwendet.

Die Frontendqualifikation lief über den unveränderten Repository-Befehl. Die beiden ausgewählten Backendläufe verwendeten Pytest vom Repository-Stamm mit `PYTHONPATH=backend:.`, `-c backend/pyproject.toml` und den jeweils oben vollständig aufgeführten Dateien. Der finale Browseraufruf wählte ausschließlich:

```text
tests/e2e/reference-data-consolidation.spec.ts
tests/e2e/market-charts.spec.ts
```

Playwright verwendete den vorhandenen `frontend/playwright.config.ts`, einen Worker und `retries: 0`. Der native Stack hatte eigene Loopback-Ports und einen zufälligen Identitätsmarker. Provider, Refresh, Monitoring und Notifications waren deaktiviert; die API startete mit bereinigter Umgebung. Der temporäre API-Launcher untersagte externe Python-Socket-Verbindungen. Dies wird nicht als Kernel- oder Netzwerk-Namespace-Isolation ausgegeben.

API, Vite und PostgreSQL wurden nach den Prüfungen geordnet gestoppt; ihre drei eigenen Ports wurden anschließend als geschlossen verifiziert. Produktive Stammdaten oder echte Providerkonten wurden nicht verwendet.

Frühe Entwicklungsversuche mit blockiertem Sandbox-Teardown, provisorischem Vite-Teststart, unvollständigen Mock-Responses beziehungsweise durch HMR unterbrochenen Browserläufen sind keine bestandenen Qualifikationen. Die oben ausgewiesenen abschließenden Läufe sind vollständig beendet und erfolgreich. **Die vollständige Backend-/PostgreSQL-17-/Container- und übrige reguläre PR-CI wurde lokal nicht ersetzt.** Deren Ergebnisse werden erst nach tatsächlicher Ausführung am neuen PR-Head separat in der PR-Beschreibung dokumentiert.

## Abnahmezuordnung

| Kriterium aus dem Auftrag | Implementierung / Nachweis |
|---|---|
| 1–2: ein Eingabeort, vorhandene Einstiege erhalten | sieben explizite Aktionsmappings, geprüfte Top-down-Weiterleitung, direkte Routen- und Bestandsregressionen |
| 3: bekannte Identitäten, keine doppelten Vollformulare | ein Formular, kompakte Objektwahl, gebundener Candidate-Kontext, strukturierte Mappingvorbelegung |
| 4–5: nichtprimäres Listing, richtiger Owner | Kontext-/Mappingtests und Browservorbelegung; Candidate-Owner darf bei Markt-/Sektorlisting abweichen |
| 6: Herkunft/Gültigkeit/keine Scheinänderung | exakte vier POST-Verträge, Sektor→Referenz ohne Quellenfeld, echte SQL-Zeile mit Tagesbezug und Herkunft |
| 7: Index/ETF/Referenz→Listing unterscheiden | listingfreie Indexkette, echte ETF-Typanzeige, kein Daten-/Proxyfallback |
| 8–9: Vorbelegung und getrennte Revision/Aktivierung | DTO-Reads, normalisierter No-op-Schutz, eigener PUT/Validate/Import und Receipt-/Readbacktests |
| 10: vier Venue-Zustände, Readbackfehler | Komponenten-/Seiten-/Browserfälle; erfolgreicher Write bleibt abgeschlossen, Wiederholung nur des GET |
| 11–12: alte Evidenz und Konkurrenz/Transport | exakte Revisionsbindung, bewusste erneute Prüfung, unklarer Abschluss ohne Replay oder Mappingwechsel |
| 13–14: Entwürfe, A→B→A, Navigation, Doppelklick | 14 echte Data-Router-Navigationstests plus Browser-/SQL-Doppelklicknachweis |
| 15: richtige Rückkehr, keine Folgeaktionen | interne Candidate-/Chartwege, frische GETs, keine Evaluation/Analyse-/Importkette |
| 16: Tastatur/Fokus/schmale Darstellung | Guard-Fokusprüfungen, Chromium/Desktop/390-Pixel-Aufnahmen und Overflowprüfung |
| 17: echte Persistenz und unterscheidbare Nachweise | ein Browser/API/PostgreSQL-Write, zwei bestehende PostgreSQL-Regressionsfälle, separate Mock-/Memory- und lokale/CI-Grenzen |

## Folgeverträge und Integration

Offen bleiben eigenständige Backendumfänge für Update/Beendigung vorhandener Zuordnungen samt vollständiger administrativer Historie; Änderungen bestehender Sektor-/Referenzstammdaten; atomare Mapping-Versionsprüfung beziehungsweise Request-/Replaygarantien; sowie ein gegebenenfalls revisionsgebundener Venue-Read. UI5 simuliert diese Verträge nicht.

UI3 besitzt weiterhin Learning und seine Hypothesenanbindung. UI4 besitzt weiterhin Trade und die Alert-Timeline-Anbindung. Keine dieser Dateien oder Browserfälle wird hier geändert. `CandidatePage`, Router, globale Guard-API, Backend-Domain/DTOs/Persistenz, Migrationen, Scheduler, Modell-/Tradingregeln, Finanzberechnungen und CI-Workflows bleiben unverändert. VERSION wird ausschließlich durch den oben beschriebenen Releasezusatz angehoben.

Gemeinsame Integrationsstellen sind die beiden bestehenden Chart-Komponenten ausschließlich mit ihren Einrichtung-/Rücklinks sowie die vorhandenen Administrations-/Chart-Setup-Clients. Die aktuelle UI4-Dateiliste überschneidet sich nicht mit den geänderten UI5-Anwendungsdateien. `PRODUCT_BACKLOG.md` und `TRACEABILITY.md` werden in diesem Schnitt bewusst nicht parallel fortgeschrieben; dieses Dokument liefert den UI5-Nachweis für eine spätere gezielte Einordnung in PB-013 „Sektoren und Referenzen“. Historische Nachweise und fremde Statusabschnitte bleiben erhalten.

Maßgebliche bestehende Verträge: [MARKET_CHARTS](MARKET_CHARTS.md), [D01-B](D01B_PROVIDER_MAPPING_INSTRUMENT_BOUNDARY.md), [D01-E](D01E_MARKET_REFERENCE_LIVE_PATHS.md), [ADR-S5-008](../decisions/ADR-S5-008-TOP-DOWN-REFERENCE-ADMINISTRATION.md), [ADR-S5-012](../decisions/ADR-S5-012-ACTIONABLE-LIVE-WORKFLOW.md) und [ADR-CHARTS-001](../decisions/ADR-CHARTS-001-EOD-COMPARISON-AND-ETF-IDENTITY.md). Die späteren listingfreien Indexverträge begrenzen die älteren Listingannahmen ausdrücklich.

Der ursprüngliche UI5-Auftrag endete mit dem geprüften **Draft-PR**. Der oben dokumentierte anschließende Nutzerauftrag gibt Merge bei erfolgreichen Prüfungen und die versionierte PC-Bereitstellung frei. Eine tatsächlich ausgeführte PC-Installation bleibt ein eigener Betriebsnachweis.

## Folgeprüfung vom 27.10.2026: gelesene Mappingwerte sichtbar prüfen

### Aktuelle Basis und enger verbleibender Befund

Der erneut vorgelegte UI5-Startprompt nannte einen inzwischen überholten Ausgangsstand. Die aktuelle Basis ist **`eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4`**, Tree **`a864274c4c050698e1fc61134a98dfb03dcf1441`**, VERSION **1.5.23**. UI3 / #286, UI4 / #287 und UI5 / #288 sind darin bereits integriert. Die sieben kanonischen Eingabewege werden deshalb übernommen; sie werden nicht erneut implementiert. Die Nachprüfung von Kontext, Herkunft, Listingowner, Guard, Revisionsbindung und Transportgrenzen ergab dort keinen weiteren belegten Fehler.

Ein konkreter Bedienfehler blieb bei der Konkurrenzprüfung: Der Preflight erkannte eine neue Mappingrevision und erhielt den lokalen Entwurf. Die anschließend verlangte Prüfung zeigte jedoch nur die neue Revision und den Status. Das tatsächlich gelesene neue Symbol und der Exchange-Code waren unsichtbar. Auch bei der eigenständigen Validierung, beim Import und bei der Renditebestätigung fehlte diese kompakte Provideridentität.

Der Folgefix ergänzt eine ausdrücklich als **„Gelesene Providerkennung“** bezeichnete Zeile aus `provider`, `provider_symbol` und `provider_exchange_code` des bereits vorhandenen vollständigen Mappingdatensatzes. Sie enthält keine aus Ticker, MIC oder `provider_identity` abgeleiteten Werte.

| Bedienzustand | Anzeige nach dem Folgefix |
|---|---|
| Normales Listing-/Index-Mapping bearbeiten | Kennungen weiterhin ausschließlich in den vorausgefüllten Eingabefeldern; keine zusätzliche Datenkarte |
| Geänderter Lesestand verlangt erneute Prüfung | Kompakte gelesene Kennung und Revision sichtbar; lokaler Symbol-/Exchange-Entwurf bleibt unverändert im einzigen Editor |
| Unbekannter Schreibabschluss | Gelesene Kennung sichtbar; weder Receiptbehauptung noch automatischer erneuter Write |
| Listing-/Index-Validierung, Import oder Index-Renditebestätigung | Gelesene Kennung vor der gesonderten ausdrücklichen Aktion sichtbar |

Der Prüfhinweis stellt klar, dass der Entwurf noch nicht gespeichert ist. Reads, Bestätigung, Preflight, Guard, synchroner Submit-Lock und Write-/Readbackzustände bleiben unverändert. Insbesondere entsteht keine atomare Konkurrenzsperre: Die bestehenden Mappingbefehle besitzen weiterhin weder `expected_version` noch Request-/Replaygarantien. Die oben beschriebenen fehlenden Update-/Beendigungs-/Historienverträge für Zuordnungen und Stammdaten bleiben eigenständiger Backendumfang.

### Neue lokale Prüfbindung

- Implementierungs-/Testcommit: **`459f43bdbb832fb56390e63f017df8738d1f2dba`**.
- Lokal und über die GitHub-Git-API identischer Code-/Test-Tree: **`566e4eaf1ababa64ee50ee4b05c9916e60f7d518`**. Der nachfolgende Dokumentationscommit ändert keine Anwendung oder Tests.
- Laufzeit: Node **22.16.0**, npm **10.9.2**, Chromium **140.0.7339.16** (Playwright-Browserrevision **1187**, Playwright **1.55.0**); Installation aus unveränderter Frontend-Lockdatei.
- Rot-/Grün-Nachweis: Mit den neuen Assertions und unverändertem Anwendungscode scheiterten **8** Prüfungen exakt an der fehlenden Providerkennung; **33** bestanden. Nach dem Fix bestanden die identischen beiden Testdateien mit **41/41** Fällen. Erhalten bleiben die bestehenden Assertions zu Quelle, Identität, Entwurf und exaktem Write.
- Neuer kontrollierter Browserfall: externer Symbol- und Exchange-Wechsel, sichtbarer gelesener Vergleichswert, erhaltene lokale Eingaben, genau ein Formular, kein Write vor bewusster Neuprüfung, zurückgesetzte Bestätigung und anschließend genau ein exakter PUT per Tastatur. Ein langes Symbol wird bei **390 × 844** ohne horizontalen Dokumentüberlauf dargestellt; Screenshot visuell geprüft.
- Lokaler Chromium-Lauf: **8 bestanden, 1 erwarteter Skip, 0 Fehler/Flaky, sämtliche ausgeführten Fälle mit Retry 0**. Ausgeführt wurden die sechs kontrollierten UI5-Fälle und beide unveränderten Marktchartfälle. Der bestehende echte administrative Browser/API/PostgreSQL-Fall blieb lokal ohne eigenen disponiblen Datenbankstack gesperrt. Diese acht UI-Fälle verwenden synthetische API-Antworten und sind ausdrücklich kein neuer PostgreSQL-Nachweis.

Die fokussierten Befehle waren:

```bash
cd frontend
npm test -- --run src/features/administration/components/MappingEditor.test.tsx src/features/analysis/pages/ChartSetupPage.test.tsx
npx playwright test ../tests/e2e/reference-data-consolidation.spec.ts ../tests/e2e/market-charts.spec.ts --workers=1 --retries=0 --reporter=list,json
```

Der Browserlauf nutzte den vorhandenen konfigurierten Chromium-Pfad und einen eigenen Loopback-Testserver. Keine Providerkonten, produktiven Stammdaten, zusätzlichen fachlichen Aktionen oder vorgetäuschte CI-Identität wurden verwendet. Der eigene Testserver wurde danach beendet.

Der erste neue vollständige Aufruf von **`bash scripts/check-frontend.sh`** bestand TypeScript, ESLint und Prettier; bei Vitest bestanden **1.231/1.233** Tests. Zwei unveränderte `ProductSelectionPage`-Fälle trafen das bereits in `UI_LESSON_CONSOLIDATION.md` dokumentierte Timingfenster beim Wechsel auf die kanonische Run-URL. Die Produktseite und ihre Tests sind bytegleich zur Main-Basis. Die unveränderte isolierte Datei bestand anschließend **4/4**; Tests, Timeouts, Worker-Konfiguration und Gates wurden nicht geändert. Der fehlgeschlagene Erstlauf wird nicht als grünes Gate ausgewiesen.

Der anschließende **identische vollständige Aufruf** auf demselben Code-/Test-Tree endete mit **Exit 0**: TypeScript, ESLint, Prettier, **1.233 Tests in 136 Dateien**, unveränderte Coverage-Grenzen und Produktionsbuild bestanden. Coverage: Statements/Lines **95,18 %**, Branches **88,82 %**, Functions **89,54 %**. Vorhandene React-`act`-Hinweise und die Vite-Meldung zu großen Chunks bleiben sichtbar. Die fokussierten Testzahlen sind Teilmengen und werden nicht zur Gesamtzahl addiert. `git diff --check` sowie der unabhängige Code-/Dokumentationsreview ergaben keine Blocker.

### Integration und aktuelle Auftragsgrenze

Der Folgediff umfasst ausschließlich die beiden UI-Komponenten, deren direkte Tests, die gezielte Erweiterung des vorhandenen UI5-Browserfalls und diesen Nachtrag. Der echte administrative PostgreSQL-Browserfall und sein SQL-Reader bleiben unverändert. Alle elf bei Arbeitsbeginn offenen PR-Dateilisten wurden abgeglichen; es gibt keine Dateiüberschneidung mit diesem Folgediff. Insbesondere bleiben UI6 / #289 und UI8 / #290 eigenständig.

`PRODUCT_BACKLOG.md`, `TRACEABILITY.md`, Router, `CandidatePage`, `MarketChartsPage`, globale Guard-API, Backendverträge, Migrationen, Scheduler, VERSION, Dependencies und CI-Workflows erhalten keinen Folgediff. Die im ursprünglichen UI5-Schnitt gemeinsam genutzten Chartlinks und Clients bleiben erhalten; PB-013 kann später anhand dieses Berichts gezielt ergänzt werden.

Die reguläre neue PR-CI wird nach tatsächlichem Abschluss mit **finalem Head, vollständigem Tree, Testmerge und Run-IDs in der PR-Beschreibung** gebunden. Historische Main-/PR-Ergebnisse und der damalige lokale SQL-Zeilennachweis oben ersetzen keinen Lauf am neuen Stand. **Dieser Folgeauftrag endet mit dem geprüften Draft-PR; die historische Merge-/Releasefreigabe für #288 wird nicht auf den neuen PR übertragen.**
