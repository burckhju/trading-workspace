# gettex: qualifiziertes Originalpaket für die aktuelle Listingeinheit

## Ergebnis und Nachweisgrenze

Die drei angeforderten Börsen-PDFs wurden am 25.11.2026 vom Nutzer als Dateien
bereitgestellt. Zusammen mit der erneut vollständig bezogenen BSW-Kurzklassifikation
liegen alle vier erforderlichen Originalrollen vor. Inhalte, gedruckte Fassungen,
Seiten, SHA256 und die heute offiziell verlinkten Bezugswege sind geprüft.
Das bisher leere Register enthält nun genau ein fest gebundenes Paket:
`gettex-mund-eur-equity-call-unit-20261125-v1`.

**Die Beschaffungslücke der Regeloriginale ist geschlossen.** Die unabhängige
lokale Ausführung des bestehenden Qualifiers mit den vier echten Dateien ergibt
`QUALIFIED_RULE_ORIGINALS_ONLY`; sieben gezielte Negativproben werden korrekt
abgewiesen. Das ist noch kein vollständiger gettex-Dateiscan, Product-Import,
gespeicherter P01-V2-Entscheid oder B58-Nachweis. Aufgabenstatus und der einzige
verbleibende Auftrag stehen im [Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

Ausgangscode: `f971d23444fb1e0d09843754cf7846c3fc7bfe81`, dessen vier reguläre
Workflows erfolgreich abgeschlossen sind. Main wurde am 25.11. erneut als
`9a5e59dac3bb219cbc40641e62e75871eb2ed131`, Version 1.5.54, gelesen.
Der jüngste belegte PC-Stand bleibt der
[Read vom 24.11., 20:33:55–20:33:58 Uhr MEZ](DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md):
Schema0060, keine ausgewählte P01-Quotequelle oder Mappingroute. Dieser Bericht
behauptet keinen neueren PC-Zustand.

## 1. Vollständige Originale und Herkunft

| Rolle | Original, gedruckter Stand, Seiten | Bytes | SHA256 |
| --- | --- | ---: | --- |
| `EXCHANGE_RULES` | [Börsenordnung](https://www.gettex.de/fileadmin/Regelwerke/261102_Boersenordnung.pdf), 02.11.2026, 54 Seiten | 343776 | `8cb44437079ca807becd54fc3742c76b26cd0ee32cda724d5b2fc97d8c7315d8` |
| `OPEN_MARKET_RULES` | [Handelsordnung Freiverkehr](https://www.gettex.de/fileadmin/Regelwerke/180103_Handelsordnung_Freiverkehr.pdf), **03.01.2017**, 2 Seiten | 11755 | `b27b0659d8cb9e6fb28ff1ed61311bfe40d1e99d2e4d96b7ef305dda9d8b48fb` |
| `EXECUTION_RULES` | [Ausführungsbestimmungen](https://www.gettex.de/fileadmin/user_upload/www.gettex.de/Downloads/Regelwerk/250117_Ausfuehrungsbestimmungen.pdf), 17.01.2025, 25 Seiten | 229466 | `fb59419ceb252792c924ddaeb850c078d5b64c78a50d27f6ca4ccb25176a26fa` |
| `PRODUCT_CLASSIFICATION` | [BSW-Kurzklassifikation](https://www.derbsw.de/static/c30a7862c1e493be34b39789823b76d0/24_07_11_BSW_Produktklassifizierung_Kurzversion_dt_5923f67334.pdf), 4 Seiten | 2835859 | `5c776afd4194f20786d31f7f7e019bdf98b6171dbd0a8e11904672bad6d9b5b1` |

Die drei Börsendateien sind nutzerbereitgestellte Originale. Ihre Deckblätter,
Seitenzahlen und die tragenden Regelstellen stimmen mit den am 25.11. über die
offiziellen Links gelesenen PDF-Inhalten überein. Die aktuellen Einstiegsseiten
[gettex](https://www.gettex.de/handel/regelwerk) und
[Börse München](https://www.boerse-muenchen.de/handel-support/regelwerk)
verlinken dieselben Dateifassungen. Ein heutiger vollständiger Bytevergleich
dieser drei Uploads mit einem eigenen Download vom Börsenserver ist **nicht**
belegt. Die gestrigen HTTP403-Antworten werden weder als heutiger Abruf noch
als generelle Unerreichbarkeit beim Nutzer ausgegeben.

BSW wurde am 25.11. von **06:05:42.269140 bis 06:05:48.926229 Uhr MEZ**
mit einem begrenzten öffentlichen GET erneut bezogen: HTTP200,
`application/pdf`, vollständige 2.835.859 Bytes. Der Hash stimmt mit dem
am 24.11. geprüften Original überein. Die
[offizielle Klassifikationsseite](https://www.derbsw.de/de/bsw-produktklassifizierung/)
verlinkt exakt dieses PDF. HTTP-`Last-Modified`, PDF-Metadaten und Dateinamen
werden nicht als historische Veröffentlichungs- oder Wirksamkeitszeit verwendet.
Die Börsenuploads erhalten kein erfundenes ursprüngliches `retrieved_at`.

Die PDFs bleiben außerhalb des öffentlichen Repositorys. Dieser Bericht und
der [maschinenlesbare Prüfbeleg](evidence/GETTEX_LISTING_UNIT_ORIGINALS_20261125.json)
enthalten ausschließlich öffentliche Quellenmetadaten und technische Ergebnisse.

## 2. Fachliche Ableitung und Grenzen

| Originalstelle | Belegte Aussage | Verwendung im engen Adapter |
| --- | --- | --- |
| Börsenordnung §34, PDF S.28 | Einordnung derivativer Wertpapiere anhand der BSW-Klassifikation | Produktklasse zusätzlich zum unveränderten aktuellen Original-KID prüfen |
| Börsenordnung §42(1), S.35, und §55, S.43 | Stückpreis; abweichende Währung möglich, gesonderte Prozentnotierung für Rententitel | Einheit nur mit tatsächlich belegter EUR-Originalzeile und genauem MUND-Listing verwenden |
| Freiverkehrsordnung §§1/2(2), S.2 | gettex ist erfasst; handelsbezogene Börsenregeln und Ausführungsbestimmungen werden einbezogen | Börsenkonvention ist für diesen Freiverkehrspfad einschlägig |
| Ausführungsbestimmungen §11(2)(d), S.14 | Hebelprodukte werden in Stücknotiz geführt; Anlageprodukte mit Prozentnotiz sind gesondert genannt | Keine Übertragung auf beliebige Schuldverschreibungen oder prozentnotierte Produkte |
| BSW, S.2/3 | Optionsscheine gehören zu den Hebelprodukten; Call-Optionsscheine werden ausdrücklich beschrieben | Engen KID-Kopf eines Call-Optionsscheins auf eine Aktie beibehalten |
| Börsenordnung §63(2), S.46 | Veröffentlichung der jeweils letzten aktuellen Quotes | Kein Ersatz für die Originalzeit eines konkreten Bid oder für Instrumentstatus |

Die genannten Seiten wurden zusätzlich als Bilder gelesen. Insbesondere ist
die Tabelle in §11 eine Tabelle zu Quotierungsvolumina: Anzahl und Gegenwert
sind keine Umrechnungsfaktoren für den Preis. Die Ausnahmen in §11(3)/(4) und
die Anzeigevorschrift in §11(6), S.15/16, beweisen weder einen tatsächlich
verfügbaren Bid noch OPEN oder die Fortgeltung eines früheren Status.

Die Schlussfolgerung lautet ausschließlich: Für den gebundenen
`CALL_WARRANT_ON_EQUITY`-Fall auf `GETTEX_DELAYED`/MUND/EUR kann der Product-Owner
eine fehlende aktuelle KID-Einheit um `CURRENCY_PER_WARRANT` ergänzen. Produkt,
Emittent, Basiswert, Terms, aktives Listing, Währung und beide Originalbelege
müssen weiterhin zusammenpassen. Die Qualität bleibt
`CURRENT_UNIT_HISTORY_ASSUMED`; dokumentierte Historie ist vorrangig,
`ADJUSTMENT_REQUIRED`/`WITHDRAWN` und echte Widersprüche bleiben Sperren.

## 3. Zeitliche Bedeutung

Der feste Beobachtungsstand ist **25.11.2026, 06:07:22 Uhr MEZ**
(`2026-11-25T05:07:22Z`), nach der inhaltlichen und visuellen Originalprüfung.
`effective_from=None`: §82 der Börsenordnung und §4 der Freiverkehrsordnung
knüpfen das Inkrafttreten an Veröffentlichung/Bekanntmachung, soweit kein
späterer Zeitpunkt festgelegt ist. Die Dokumenttitel belegen diesen Vorgang
nicht. Der Dateiname `180103` ändert den tatsächlich gedruckten Stand
03.01.2017 nicht auf 2018.

Die bestehende Zeitgrenze gilt für das **Ereignis der aktuellen V2-Verbraucherquote**.
Ein Quote vor dem beobachteten Regelstand wird vom ergänzenden Reader nicht
qualifiziert. Die Quellenzeit muss zusätzlich 0 bis einschließlich 1800 Sekunden
alt sein; Empfangszeit bleibt separat und ein unbekannter Bidzeitpunkt wird
nicht erfunden.

Die einmalige vollständige Pretrade-Datei erfüllt eine andere Funktion:
Sie belegt Produkt-/Listing-Mitgliedschaft mit eigenem Dateifenster, Originalzeile,
Hash und CRC-Prüfung. Ein unverändertes vollständig geprüftes File vom 24.11.
kann diesen Listingbeleg weiterhin liefern. Sein damaliger Preis wird dadurch
weder aktuell noch als Verbraucherquote importiert. Es wird keine neue
Zeitbedingung für diese Mitgliedschaftszeile eingeführt.

## 4. Implementierung und tatsächliche Prüfung

Der [feste Katalog](../../backend/app/features/product/service/listing_unit_rules.py)
enthält genau die vier oben genannten Rollen, öffentliche Bezugswege und Hashes.
Der [bestehende Qualifier](../../backend/app/features/product/service/listing_unit_sources.py)
übernimmt diesen Katalog; Product-Service, CLI und Reader verwenden ihren
bestehenden Anschluss. API-/CLI-Aufrufer können keine Pins, fremden Regeln
oder Freigabeflags hinzufügen. Eine neue Migration oder ein neuer Regelmodus
ist für diesen Schritt nicht erforderlich.

Die isolierte Prüfung am **25.11., 06:09:45.677090 Uhr MEZ** verwendete die
vier vollständigen tatsächlichen Originaldateien mit dem Produktionskatalog.
Ergebnis: vier Rollen qualifiziert; Paketfingerprint
`56ab502378fd58ff2400deffef9b566ac15392ce991e773029ee899157bbee6c`.
Je ein geändertes Byte in jedem Original, vertauschte Quellenrollen, ein
fehlendes Original und ein Prüfzeitpunkt vor dem beobachteten Regelstand
wurden mit den vorgesehenen konkreten Fehlercodes abgewiesen. Die sieben
Negativproben und der tatsächliche Laufzeitpunkt stehen im JSON-Prüfbeleg.
Dabei gab es weder Datenbankverbindung noch Netzwerkzugriff.

61 gezielte synthetische Tests für Listing-Owner, Product-Komposition und CLI
sind erfolgreich. Die Negativprüfung weist Test-PDFs auch unter den offiziellen
Dateinamen ab; vorhandene Ereigniszeit- und Bindungsprüfungen bleiben erhalten.
Die echten Börsen-/BSW-PDFs werden nicht als Testfixtures veröffentlicht.
Die vollständigen Backend-Ruff-/Black-Gates sind erfolgreich; mypy prüft
678 App-Dateien ohne Fehler. Der neue Katalog wird ausdrücklich reexportiert,
damit der bestehende Service-Alias auch unter der strengen Typprüfung gültig
bleibt. Weder Qualifierlogik noch API, CLI oder Datenbankschema wurden gelockert.
1.444 relative Dokumentverweise und 582 Anker sind fehlerfrei. Der öffentliche
Änderungsumfang wurde gegen 837 private Vergleichswerte einschließlich
gebundener Kennungen und des privaten KID-Hashs geprüft: keine Treffer.
Der historische Roadmapblob bleibt `919ed7570580b1d883a409f864ed15747fbfda3e`.

Der genaue neue Head, vollständige Gates und die tatsächlich zugehörige CI
werden im [PR #370](https://github.com/burckhju/trading-workspace/pull/370)
ausgewiesen. Der vorige erfolgreiche Backend-Lauf auf `f971d234` umfasst
6.444 Tests einschließlich aller vier neuen PostgreSQL-Fälle, ersetzt aber
nicht die Qualifikation des jetzt geänderten Katalogstands.

## 5. Vorbereitete P01-Import- und Mappingvorschau

Die fachlich vorgeschlagene Route steht fest: das archivgebundene P01-Produkt,
gettex/MUND, EUR, belegte Stückeinheit und der vorhandene V2-Modus
`DELAYED_SOURCE_BID`. Private Kennungen werden hier nicht veröffentlicht.

| Vorbereitung | Bestehender Owner / ausführbarer Weg | Erforderlicher echter Nachweis |
| --- | --- | --- |
| Installation und P01-Bindung prüfen | Vorhandener Linux-Betriebsweg, Positions-/Product-Owner | Ausgelieferter geprüfter Code mit Schema0061; dieselbe archivgebundene offene Position und aktuelle Produkt-/Terms-/KID-Revision |
| Genaues Listing prüfen | `GET /api/v1/warrants/{warrant_id}/listings`, bei Bedarf `WarrantService.add_listing` | Genau ein aktives MUND/EUR-Listing; ein fehlendes Listing ist ein eigener vorbereiteter Schreibschritt, kein geschätzter UUID-Wert |
| Mapping vorschauen | `python -m app.tools.configure_gettex_warrant --isin PRIVATE_ISIN --mic MUND` ohne `--apply` | Passendes Listing und konfliktfreie Zuordnung; vorhandene Provider-/Privatnutzungseinstellungen vor Anwendung eng lesen und erhalten |
| Originalimport vorschauen | `python -m app.tools.import_listing_unit_originals` ohne `--apply` | Vier Originaldateien, vollständige lokale gettex-gzip-Datei, aktuelle Produkt-/Listing-/KID-IDs, Reviewzeit und Reviewreferenz; Ergebnis `READ_ONLY_PREVIEW`/`READY_TO_IMPORT` mit Fingerprint |
| Anwendung und Verbraucherabnahme | Vorhandene Product-/Mapping-Commands, `PositionQuoteSourceSelector`, regulärer Refresh und V2-Reader | Nur nach überprüfter konkreter Vorschau; anschließend gespeicherte aktuelle Quote, Einheit, Sitzungen und V2-Assessment lesen |

Die neue Import-CLI erhält `--warrant-id`, `--listing-id`, `--kid-revision-id`,
die fünf Dateiflags `--exchange-rules-file`, `--open-market-rules-file`,
`--execution-rules-file`, `--product-classification-file`, `--pretrade-file`
sowie `--reviewed-at` und `--review-reference`. Eine bestehende Einheitenrevision
benötigt ihren aktuellen `--previous-revision-id`. `--apply` ist für diese
Vorschau nicht vorgesehen; später würde die Anwendung zusätzlich Request-ID
und bestätigten Previewfingerprint benötigen.

**Grenze der hier vorbereiteten Vorschau:** Ein Zugriff auf die tatsächliche
PC-Datenbank steht hier nicht zur Verfügung. Das vorhandene alte Gesamtarchiv
bindet P01, enthält aber keine aktuelle MUND-Listing-ID oder heutige KID-Revision.
Diese Werte werden nicht erfunden. Die frühere vollständige gettex-Datei und
P01-KIDbytes sind in der heutigen lokalen Arbeitskopie nicht verfügbar;
der dokumentierte damalige Nachweis bleibt datiert gültig, ersetzt aber keine
erneute Ausführung eines Vollscans mit einer tatsächlich vorhandenen Datei.
Deshalb gibt es hier noch keinen echten DB-Previewfingerprint oder Importerfolg.
Für die geklärten Ursachen ist kein neuer Gesamt-, P02- oder Kandidatenexport
erforderlich. Nach Lieferung genügen die genannten engen Ownerreads im Rahmen
der konkreten P01-Vorschau.

Der regelmäßige gettex-Abruf benötigt eine konkrete Betriebsprüfung: Die
beobachtete Einzeldatei war rund 657 MB groß. Gemeinsamer Cache, Taktung,
Bandbreite, Wiederanlauf und vorhandene Einstellungen sind vor der Anwendung
eng zu prüfen. Die Originalprüfung aktiviert keinen Provider, Scheduler oder Import.
Original-Bidzeit, instrumentbezogener Status, historische Maßstabsstrenge,
Produktfristen und B06 werden dadurch nicht als erfüllt ausgegeben.

## 6. Bereits vorhandener gettex-Betriebsweg

Die erneute enge Auswertung des vorhandenen privaten Gesamtreadbacks vom
22.11. ergibt einen konkreten bestehenden gettex-Pfad. Sie löst keinen neuen
PC-Abruf aus. Unter `refresh_before/body/jobs/*/source_attempts` und den
zugehörigen `quotes` sind zehn gettex-Routen für nicht gehaltene Produkte
gespeichert; `refresh_after` bestätigt denselben Bestand. Die öffentliche
[Zusammenfassung](evidence/GETTEX_EXISTING_PATH_READBACK_20261122.json)
enthält nur Counts, Zeitgrenzen und Qualitätsmerkmale, keine Produktkennungen
oder Einzelpreise.

Die Versuche vom **22.11., 20:43:11–20:50:09 Uhr MEZ** melden jeweils
`LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED` und
`GETTEX_DELAYED_RECENT_FILE_NOT_AVAILABLE`. Gleichzeitig sind zehn frühere
MUND/EUR-Bids im Modus `OFFICIAL_DELAYED_PRETRADE` mit `retained=true`
vorhanden: neun Quellenquote-/Empfangstage vom 20.11., einer vom 06.10.
Refresh war `enabled/running/leader=true`, Intervall 300 Sekunden,
`auto_configure=false`, `auto_select_position_sources=true`.
Das beweist zuvor gespeicherte gettex-Daten und einen benutzten Schedulerpfad,
aber weder P01-Abdeckung noch heutige Frische oder heutige Downloadleistung.

Der [Container](../../backend/app/core/di/container.py) erstellt den Adapter
nur bei `enabled=true`; die [Settingsvalidierung](../../backend/app/core/config/gettex.py)
verlangt dann `private_use_confirmed=true`. Daraus folgt ein datierter
technischer Beleg der konfigurierten Privatnutzungsbestätigung, kein gesonderter
Nachweis darüber, wer wann externe Bedingungen akzeptiert hat. Eine neue
pauschale Providerfreigabe oder ein Login-/Cookie-Consent wird nicht erfunden.

Der [vorhandene Adapter](../../backend/app/providers/gettex_delayed/adapter.py)
fasst aktive MUND-Produkte in einem gemeinsamen Dateiscan und Cache zusammen;
P01 benötigt daher nicht automatisch eine zusätzliche Vollfileübertragung je
Produkt. Vor Anwendung sind die vorhandenen aktuellen Limits und Einstellungen
zu erhalten und die tatsächliche Verbraucherfrische zu prüfen. Die reine
Mappingvorschau bestätigt diese Settings nicht: `configure_gettex_warrant`
prüft die beiden Providerflags erst im ausdrücklichen Anwendungszweig.
