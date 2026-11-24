# P01: aktueller Listing-Einheitenbeleg beim Product-Owner

## Ergebnis und Reichweite

Der zusätzliche Product-Anschluss ist im Arbeitsstand von PR #370 implementiert.
Er kann eine im aktuellen KID fehlende Preiseinheit durch einen separat
qualifizierten, exakt listinggebundenen Originalbeleg ergänzen. Der öffentliche
Nachweis enthält keine Depotkennungen, Einzelpreise oder individuellen Produkt-URLs.
Aufgabenstatus und der eine verbleibende Versorgungsauftrag stehen ausschließlich
im [Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

**Noch keine neue P01-Betriebsabdeckung:** Das Produktionsregister geprüfter
Regelpakete bleibt leer. Drei erforderliche Regel-PDFs sind als Webtext gelesen,
aber in dieser Umgebung nicht als Originalbytes verfügbar. Ein Import meldet
deshalb `LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED`. Weder Tests noch die frühere
Kursdateiprobe werden als produktive Quellenqualifikation verwendet. Die
P01-Listing-/Mappingauswahl und ein frischer gespeicherter V2-Entscheid bleiben
am PC nachzuweisen.

Ausgangsstand dieser Umsetzung ist PR-Commit
`066c24db72b8ee2e489eebf11c261fc13164f057`, Tree
`51e22b36dc3ea7bc8903205de00282dd9237f42d`. Main bleibt
`9a5e59dac3bb219cbc40641e62e75871eb2ed131`, Version 1.5.54. Der letzte
belegte PC-Quellenread stammt vom 24.11.2026, **20:33:55–20:33:58 Uhr MEZ**,
Schema0060. Die neue Migration0061 ist damit nicht als installiert belegt.

## 1. Belegkette und konkrete Umsetzung

| Grenze | Umsetzung / Nachweis |
| --- | --- |
| Originalregeln → qualifiziertes Paket | Vier getrennte Rollen: Börsenordnung, Freiverkehrsordnung, Ausführungsbestimmungen und Produktklassifikation. Vollständige Originalbytes müssen exakt zu den hinterlegten SHA256 und Quellenrollen passen. Keine frei eingebbare Freigabe oder per CLI registrierbare Hashliste. |
| Vollständige gettex-Datei → konkretes Listing | Lokaler Import prüft den gesamten gzip-Strom mit dem bestehenden Parser einschließlich CRC, Zielkonflikten und Dateihash; danach Originalzielzeile, Zeilenhash, Dateifenster, MUND und EUR. Ein frei zusammengesetztes JSON oder ein behaupteter Dateihash erhält keine Importberechtigung. |
| Produkt → Listing | Bestehende Workspace-, Produkt-, Emittenten-, Basiswert-, Terms-, Listing- und Handelsplatzbindung; aktive Referenzen, Listing-/Venue-Versionen und aktuelle KID-Währung müssen zusammenpassen. Der enge erste Klassenadapter verlangt den belegten KID-Produktkopf für einen Call-Optionsschein auf eine Aktie. |
| Speicherung | Additive Tabelle `product_listing_unit_evidence`, Migration0061, eigene unveränderliche Revisionskette je Listing. Vorgänger, Request-ID, Quellenpaket, ursprüngliche KID-Revision und Bindung werden erhalten. Datenbankguards verhindern Scopewechsel und Änderung/Löschung der Historie. |
| Product-Read | `ListingUnitEvidenceReader` prüft gespeicherte Originale, aktuellen KID und aktuelle Bindung erneut. Fehlende, beschädigte oder nicht mehr qualifizierte Quellen führen zu konkreten Gründen; kein Rückgriff auf eine ältere gute Revision. |
| Product → V2 | `current_for_review` ergänzt ausschließlich eine fehlende Einheit. Der V2-Aufrufer reicht seine tatsächliche gespeicherte `GETTEX_DELAYED`-Route weiter. KID-Provenienz und ergänzende Listing-Provenienz bleiben getrennt und gehen gemeinsam in die Bewertung ein. |

Code: [DTOs](../../backend/app/features/product/domain/listing_unit_evidence.py),
[Originalqualifikation](../../backend/app/features/product/service/listing_unit_sources.py),
[Import/Reader](../../backend/app/features/product/service/listing_unit_evidence.py),
[Persistenz](../../backend/app/features/product/persistence/listing_unit_evidence.py),
[Migration](../../backend/migrations/versions/20261124_0061_listing_unit_evidence.py),
[V2-Komposition](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py).

**Präzisierte Implementierungsentscheidung:** Die zuvor erwogene Erweiterung
der `product_review_documents`-Belegarten wurde durch eine eigene additive
Listing-Revisionskette ersetzt. KID und bisherige Fristbelege behalten dadurch
ihre bestehenden Constraints und Auswahlregeln. Zuständig bleibt Product;
es entsteht kein neuer fachlicher Owner und keine neue Überwachungsregel.

## 2. Zeit, Qualität und unveränderte Grenzen

Die ergänzte Einheit lautet `CURRENCY_PER_WARRANT`. Der Qualitätsgrad bleibt
`CURRENT_UNIT_HISTORY_ASSUMED`: aktuell belegte Einheit mit ausdrücklich
angenommener historischer Kontinuität. Eine gettex-Regel und eine einzelne
Quellenzeile ergeben keine historische `UNCHANGED_ORIGINAL`-Periode.

Regel-Fassungsdatum, tatsächlicher Beobachtungsstand, optional gesondert
belegtes Inkrafttreten, Dateiereignis, Abruf, Review und Speicherung sind
verschiedene Fakten. Fehlt ein ausdrücklich belegtes `effective_from`, darf
die Regelpaketqualifikation erst für Quellenereignisse ab ihrem beobachteten
Stand verwendet werden. Diese konservative Nutzungsgrenze behauptet kein
historisches Inkrafttreten. Ein späterer Importzeitpunkt oder eine neue,
inhaltlich gleichartig gebundene KID-Revision erzwingt dagegen keinen täglichen
Neuimport. Die ursprüngliche KID-Revision bleibt als Herkunft erhalten; der
aktuelle KID wird bei jedem Read auf Währung, Klasse und Bindung geprüft.

Der Zusatz heilt weder fehlende historische Ausführungswährung noch
Basiswertkonflikte, geänderte Terms, abweichende Listingwährung oder beschädigte
KID-Originale. Bekannte `ADJUSTMENT_REQUIRED`- und `WITHDRAWN`-Belege sperren
weiter. Ein geeigneter strenger historischer Maßstab bleibt vorrangig.
V1 und B04/B57/B58 erhalten diesen Quellenzusatz nicht.

Ein unbrauchbarer optionaler Listingbeleg bleibt separat `UNSUITABLE`, liefert
aber keine aktuelle Einheit: Der kombinierte Product-Read bleibt deshalb
`MISSING`. Die fehlende Anwendbarkeit des Zusatzes allein verdrängt keine
unabhängig vollständige dokumentierte Historie. Ohne diese Historie ist der
V2-Vergleich weiterhin nicht auswertbar. Eine ausdrücklich belegte KID-Währung
ungleich der Listingwährung bleibt dagegen schon vor der Zusatzquellenprüfung
ein harter Konflikt; sonstige KID-/Terms-/Basiswertkonflikte bleiben erhalten.

Für V2 gilt weiterhin: positiver Bid, tatsächliche gemeinsame gettex-Quellenzeit
mit **0–1800 Sekunden** Alter, getrennte Empfangszeit und mindestens 20 zum
Quellenereignis abgeschlossene Basiswertsitzungen. `original_bid_at` wird aus
der gemeinsamen Quellenzeit nicht erfunden. B58-Original-Bidzeit, geeigneter
instrumentbezogener OPEN-Status, Produktfristen und B06 bleiben eigenständige
Lücken. Die ältere Datei vom 24.11. dient nur dem Listingbeleg, nicht als
jetzt frischer Verbraucherpreis.

## 3. Lokaler Import und passive Diagnose

Der [Importhelfer](../../backend/app/tools/import_listing_unit_originals.py)
liest ausschließlich begrenzte lokale reguläre Dateien. Er ruft keine URLs ab
und akzeptiert keine Symlinks, Spezialdateien oder frei behaupteten
Qualifikationsflags. Das neue begrenzte Originalpaket erlaubt je Regeldokument
höchstens 4 MB, zusammen 16 MB; die vollständige gzip-Datei höchstens 1 GiB.
Die bisherigen KID-/Fristimportgrenzen bleiben unverändert.

Standard ist eine Vorschau in einer eigenen `REPEATABLE READ READ ONLY`-
Transaktion. `--apply` benötigt zusätzlich eine Request-ID und den exakt
bestätigten Previewfingerprint. Der Product-Owner prüft die Bindung unter Lock
erneut. Wiederholte identische Requests erzeugen keine weitere Revision;
geänderte Bindungen oder konkurrierende Vorgänger werden abgewiesen.
Die umfangreiche Dateiprüfung findet vor einer Schreibtransaktion statt.

Der neue passive Endpunkt lautet:

```text
GET /api/v1/warrants/{warrant_id}/listings/{listing_id}/current-unit-evidence
```

Er verwendet Serverzeit, vorhandene Listing-/Venue-Daten und einen separaten
Read-only-Snapshot mit begrenztem SQL-Timeout und abschließendem Rollback.
Queryparameter, historisch vorgegebene Uhren und HTTP-Imports sind ausgeschlossen.
Die Antwort enthält Quellenreferenzen, Hashes und Gründe, aber keine Original-PDFs
oder rohe Kurszeile. Ein erfolgreicher Listing-Read ist noch keine persönliche
Quellenauswahl für eine Position.

## 4. Tatsächlich beschaffte öffentliche Originale

Die offiziellen Einstiegsseiten
[gettex](https://www.gettex.de/handel/regelwerk) und
[Börse München](https://www.boerse-muenchen.de/handel-support/regelwerk)
wurden am 24.11. erneut geprüft. Die auf der zweiten Seite tatsächlich
verlinkten Originale lieferten ebenfalls HTTP403. Die begrenzten Abrufe
erfolgten zwischen **21:31:27 und 21:32:59 Uhr MEZ**. Zugangssperren wurden
nicht umgangen. Daraus folgt keine Aussage über die Erreichbarkeit vom Nutzer-PC.

| Erforderliches Original | Konkreter Beschaffungsstand |
| --- | --- |
| [261102_Boersenordnung.pdf](https://www.gettex.de/fileadmin/Regelwerke/261102_Boersenordnung.pdf), Stand 02.11.2026, §§34/55/63 | Webtext gelesen; Originalbytes fehlen. Der Deckblattstand ersetzt keinen Beleg der tatsächlichen Veröffentlichung gemäß §82. |
| [180103_Handelsordnung_Freiverkehr.pdf](https://www.gettex.de/fileadmin/Regelwerke/180103_Handelsordnung_Freiverkehr.pdf), gedruckter Stand 03.01.2017, §§1/2 | Webtext gelesen; Originalbytes fehlen. Der Dateiname wird nicht als Fassungsdatum interpretiert. |
| [250117_Ausfuehrungsbestimmungen.pdf](https://www.gettex.de/fileadmin/user_upload/www.gettex.de/Downloads/Regelwerk/250117_Ausfuehrungsbestimmungen.pdf), Stand 17.01.2025, §11(2)(d) | Webtext gelesen; Originalbytes fehlen. Quotierungsausnahmen belegen keinen aktuellen offenen Produktmarkt. |
| [BSW-Kurzklassifikation](https://www.derbsw.de/static/c30a7862c1e493be34b39789823b76d0/24_07_11_BSW_Produktklassifizierung_Kurzversion_dt_5923f67334.pdf), Seiten2/3 | HTTP200, vollständige PDF, 2.835.859 Bytes, vier Seiten; unverändert gesichert am 24.11., 21:33:52 Uhr MEZ. Optionsscheine sind den Hebelprodukten zugeordnet. |

SHA256 der öffentlichen BSW-PDF:
`5c776afd4194f20786d31f7f7e019bdf98b6171dbd0a8e11904672bad6d9b5b1`.
Die ebenfalls vollständig gesicherte BSW-HTML-Einstiegsseite umfasst 956.862 Bytes,
SHA256 `b1d5349f7b5958eec5de62855ab45741f28ba3c3558a783fbab6a53865505454`.
Die zusammengefasste lokale Beschaffungsnotiz hat SHA256
`07fd2e80e4c2fa616344f563639361bc6a94eab8a25355eb356e910fa2a72272`.
Diese öffentlichen Dokumenthashes sind von privaten Produktoriginalen getrennt.

**Kleinste fehlende Beschaffung:** Genau die drei oben benannten Börsen-PDFs
als unveränderte Dateien aus einem normal zugänglichen offiziellen Download
bereitstellen. Anschließend Bytes und Fassungs-/Seitenbefunde vergleichen und
die geprüfte Regelpaketversion im Repository fest hinterlegen. Die vorhandene
BSW-Datei, P01-KID-Prüfung und Gesamtdateiprobe müssen dafür nicht wiederholt
werden. Ein erneuter Depotexport ist zur Klärung dieser Lücke unnötig.

## 5. Technische Qualifikation

Gezielte Tests prüfen passive HTTP-Grenzen, getrennte KID-/Listingprovenienz,
fehlende Pflichtdaten, Originalintegrität, vollständigen gzip-Scan, Bindungswechsel,
zeitliche Geltung, Wiederholung und konkurrierende Revisionen. Datenbanktests
verwenden ausschließlich ausdrücklich freigegebene isolierte PostgreSQL-
Testdatenbanken und synthetische Quellen; Testregeln gelangen nicht in das
Produktionsregister. Die ausführbaren Nachweise liegen bei den jeweiligen
Codekomponenten. Lokale Läufe und reguläre CI bleiben von einer PC-Installation
und einer tatsächlichen P01-Verbraucherabnahme getrennt.

**Tatsächlicher lokaler Abschlusslauf am 24.11.2026:** 178 Tests bestanden,
vier PostgreSQL-Fälle ausdrücklich übersprungen, weil hier keine freigegebene
Testdatenbank-URL vorliegt. Der Lauf umfasst die drei neuen Product-Unitdateien,
den neuen CLI-Test, den bestehenden KID-Reader sowie
`test_indicative_entry.py`, `test_indicative_entry_v2.py` und
`test_indicative_entry_inputs.py`. Die vier Fälle in
[test_listing_unit_evidence_postgres.py](../../tests/integration/backend/database/test_listing_unit_evidence_postgres.py)
müssen in der regulären PostgreSQL-CI tatsächlich laufen: sequenzieller und
konkurrierender Import, Revisions-/KID-Zeitbindung und vollständige gespeicherte
V2-Verbraucherkette einschließlich harter historischer Gegenbelege.

Der vollständige Backend-Ruff-Aufruf und Black mit `backend/pyproject.toml`
sowie `mypy app` über 677 Dateien sind lokal erfolgreich. Alembic meldet
genau den Head `20261124_0061`; dies ist noch kein ausgeführtes PostgreSQL-Upgrade.
Alle Läufe verwendeten den tatsächlichen CI-Arbeitskontext `backend/`.
Im Review wurden ein CLI-Wiederholungsfehler und eine zu breite
MUNC-/Währungsweitergabe an den engen MUND/EUR-Adapter korrigiert und durch
gezielte Fälle abgesichert. Ein weiterer Vorrangfall ist korrigiert: Ein
unqualifizierter oder zeitlich nicht anwendbarer Zusatzbeleg hebt die strengere
vollständige Historie nicht auf. Sechs Kombinationen mit und ohne dokumentierte
Historie sowie ein echter KID-Währungskonflikt sind gezielt abgesichert.
Die bestehende Alembic-Metadatenregistrierung ist
erhalten und nur um die neue Tabelle ergänzt.

1.421 relative Dokumentverweise und 577 Anker wurden ohne Fehler geprüft.
Der öffentliche Diff wurde gegen 669 private Vergleichswerte einschließlich
gebundener Kennungen und privatem KID-Originalhash geprüft: keine Treffer. Der historische Roadmapblob
bleibt `919ed7570580b1d883a409f864ed15747fbfda3e`. Die regulären PR-Läufe und
ihr tatsächlicher Head werden im [PR #370](https://github.com/burckhju/trading-workspace/pull/370)
zugeordnet; frühere erfolgreiche Prüfungen werden nicht auf neuen Code übertragen.
