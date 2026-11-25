# Enger P01-Ownerread auf dem installierten PC

Dieser einmalige Hostaufruf liefert die aktuellen privaten Bindungen für die
vorhandene Listing-, Mapping- und Originalimportvorschau. Aufgabenstatus,
Zuständigkeiten und Abnahme bleiben ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).
Der [Hosthelfer](../../scripts/read-p01-gettex-binding.py) verwendet die bereits
installierten Reader aus v1.5.55. Er verändert keine Anwendungskonfiguration,
Listings, Mappings, Evidenzen oder Quellenauswahl und startet keinen Refresh.

## Voraussetzung und Aufruf

Der gelieferte Helfer wird außerhalb des verwalteten Programmordners gespeichert
und über den in der konkreten Übergabe angegebenen unveränderlichen Git-Commit
sowie SHA256 bezogen. Er ist ein separat bereitgestellter Hostaufruf; er wird
nicht als bereits in v1.5.55 enthaltenes Modul vorausgesetzt. Die installierte
Anwendung muss v1.5.55 auf
`eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c` verwenden. Dafür ist kein erneutes
Anwendungsupdate nötig.

Den Helfer als bisherigen Installationsbenutzer mit Python 3 ausführen. Seine
Hostseite benötigt nur die Standardbibliothek. `--base` bezeichnet das
übergeordnete Verzeichnis der vorhandenen Ordner `trading-workspace-app` und
`trading-workspace-state`; Standard ist `~/Boerse`. `--reference-archive`
nimmt den absoluten Pfad des ursprünglichen vollständigen privaten
Diagnosearchivs vom 22.11. entgegen. Ohne dieses Argument fragt der Helfer
interaktiv nach dem Pfad. Die unveränderte Datei bleibt auf dem PC; sie muss
nicht erneut vollständig hochgeladen werden.

Das ursprüngliche Paket enthält `summary.json`, `monitoring-private.json`,
`installation-before.json`, `installation-after.json` und `schema.json`.
Die späteren P02- und Quellenkandidatenpakete sind keine Ersatzreferenz.
Die bestehende Archivprüfung kontrolliert vollständig die historische
Sammlung und deren Pseudonymzuordnung; danach wird ausschließlich das
vollständige archivgebundene P01-Element an den Backendprozess übergeben.
Aus der heutigen Positionssortierung wird keine neue P01 gebildet.

Ohne `--output-dir` entsteht ein neues privates Verzeichnis
`~/trading-workspace-p01.<Zufallsanteil>/`. Ein ausdrücklich angegebener
Ausgabeordner muss neu sein und außerhalb jedes Git-Checkouts liegen.
Das Verzeichnis erhält Modus 0700, die einzige Ergebnisdatei
`p01-owner-read-private.json` Modus 0600. Nur diesen engen Auszug privat
zurückgeben; er enthält Depotkennungen und gehört nicht in das öffentliche
Repository.

## Tatsächlich gelesener Umfang

Der Helfer prüft zuerst die exakten Bytes des installierten Collectors. Dessen
bestehende Installationsprüfung bindet Checkout, Deploymentstatus, vier
Container und Anwendungsimages vor und nach dem Read. Aktuell erwartet wird
Schema `20261124_0061`; der archivierte Schema0060-Beleg bleibt historisch
unverändert. Ein veränderter Installationsstand verhindert einen vollständigen
Erfolgsstatus.

Innerhalb der bestehenden begrenzten `REPEATABLE READ READ ONLY`-Transaktion
liest der Helfer ausschließlich die archivgebundene P01 und ihre Referenzen:

- Position und Produktidentität, archivierte und aktuelle Quellenauswahl sowie
  die zugehörige gespeicherte V2-Bewertung;
- aktuelle Produkt-, Terms- und KID-Revision, vorhandene Produktprüfung;
- P01-Listings samt Version, Handelsplatz, Aktivität und Währung sowie den
  gezielt gelesenen MUND-Handelsplatz für einen gegebenenfalls nötigen
  Product-Owner-Schritt;
- aktuelle ergänzende Einheitenrevision je Listing; für aktive MUND/EUR-
  Listings zusätzlich den bestehenden Product-Einheitenreader;
- ausschließlich ausgewählte gettex-, Refresh- und Monitoringparameter:
  Aktivierung, vorhandene Privatnutzungsbestätigung, Download-/Zeitgrenzen,
  Fallback/Backoff, Taktung, Workspace, automatische Quellenauswahl und
  Reviewmodus. Zugangsdaten und vollständige Settings werden nicht ausgegeben.

Der enge Read verwendet keine globalen HTTP-Inventare oder Quellenkandidaten-
Endpunkte und ruft keinen Provider ab. Original-PDFs, Original-KID-Bytes und
rohe Pretrade-Zeilen gelangen nicht in die Ausgabe. Der vorhandene
Collector-Sanitizer begrenzt freie Texte und entfernt rohe Quellenreferenzen.

## Auswertung und Grenze

`COMPLETE_P01_OWNER_READ_NOT_PREVIEW_OR_ACCEPTANCE` bedeutet ausschließlich:
identifizierte, unveränderte Installation und vollständiger enger Ownerread.
Fehlende oder mehrdeutige MUND/EUR-Listings dürfen auch in einem vollständig
gelesenen Ergebnis vorkommen. Die Anzahl aller aktiven MUND-Listings wird
getrennt von der Anzahl der EUR-Listings geführt, weil
`configure_gettex_warrant` selbst nicht nach EUR filtert. Außerdem wird dessen
fest vorgegebener Workspace mit dem tatsächlichen archivgebundenen Workspace
verglichen.

Der ergänzende Product-Einheitenreader verwendet den tatsächlichen
Lesezeitpunkt. Das ist kein Nachweis seiner Anwendbarkeit auf das
Quellenereignis einer V2-Verbraucherquote. Die gelesenen Betriebsparameter
beweisen weder einen ausgeführten Schedulerzyklus noch Cachewirkung oder
Wiederanlauf.

`mapping_preview_executed` und `original_import_preview_executed` bleiben
ausdrücklich `false`. Die echte Mappingvorschau verwendet anschließend den
vorhandenen Command ohne `--apply`, mit den nun belegten Kennungen. Die echte
Originalimportvorschau benötigt außerdem die vier tatsächlichen Regeldateien
und eine vollständige lokale gettex-Datei. Ein Fingerprint wird erst von dieser
ausgeführten, datenbankgebundenen Vorschau übernommen. Dieser Hostaufruf legt
kein Listing an und ersetzt keinen der ursprünglichen Abnahmepunkte.

## Prüfung des Hosthelfers

Die gezielten Tests stehen in
[test_read_p01_gettex_binding.py](../../tests/unit/backend/test_read_p01_gettex_binding.py).
Sie verwenden synthetische Referenzen und abgefangene Aufrufe. Der bestehende
Collector, Anwendungscode, Datenbankschema und der veröffentlichte Release
bleiben unverändert. Lokale Helfertests sind kein ausgeführter PC-Read.
