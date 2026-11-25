# Product Backlog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Revision | 25.11.2026: Aktuellen Main, PR-Head und Lieferweg erneut gelesen; v1.5.55 für den vorhandenen P01-gettex-Anschluss konkret vorbereitet. Fünf Versionswerte konsistent, bestehender Launcher unverändert. Das qualifizierte Vierer-Regelpaket bleibt erhalten; BSW-Dateikopie erneut bytegleich bezogen. Veröffentlichung, PC-Update, echte DB-Vorschau und Verbraucherabnahme bleiben eigene Nachweise im selben P01-Auftrag. |
| Erstprüfung | 19.11.2026, 19:31:38 Uhr MEZ (Europe/Berlin), auf `254f0bbd52ab42e0120d381e915dc96c1118796c` / `v1.5.51` |
| Fortschreibung | 20.11.2026, Beginn 13:46:04 Uhr MEZ; Main-/Release-Delta, tatsächliche CI, PR- und Betriebsnachweise erneut geprüft |
| Geprüfter Produktstand | Fachlicher Daten-/Readervertrag auf `c7db441de36297a98d47cdf28c64b4e5d9994692` / v1.5.52; Backendreader und bestehende Betriebshelfer bis zum unten genannten Main unverändert. Die neue Oberfläche bleibt an ihre eigenen #372-Nachweise gebunden. |
| Aktueller Main | `9a5e59dac3bb219cbc40641e62e75871eb2ed131`, Mergecommit #373 vom 22.11.2026, 21:35:28 Uhr MEZ, `VERSION=1.5.54`. Das Delta seit #372/febeb922… ändert ausschließlich Versions-/Liefermetadaten und Dokumentation; Backendpfade unverändert. Main ist kein Nachweis einer PC-Installation. |
| Tatsächlicher PC | v1.5.54 auf `9a5e59dac3bb219cbc40641e62e75871eb2ed131`, zuletzt im Quellenkandidatenpaket vom 24.11.2026, 20:33 Uhr MEZ, vor/nach verifiziert; letzte vollständige Inventur weiterhin vom 22.11. |
| Funktion | Einzige maßgebliche Quelle des aktuellen Aufgabenstatus; bestehende PB-/FT-/M-Kennungen und Owner bleiben erhalten |
| Prüfgrenze | Vollständiger Checkout, Quellprüfung, Gesamtreadback vom 22.11., P02- und Quellenkandidatenreads vom 24.11., isolierte gettex-Dateiprobe und freigegebene P01-KID-Prüfung; am 25.11. echte Vierer-Regeloriginalqualifikation. Kein interaktiver PC-/DB-Zugang, neuer DB-Previewfingerprint, Product-Import oder neuer P01-Entscheid aus dieser Originalprüfung |

<a id="p01-lieferung-20261125"></a>
## Fortschreibung — P01-Lieferung konkret vorbereitet, 25.11.2026

**Aktueller Standabgleich:** Main und veröffentlichter Tag v1.5.54 stehen
weiterhin auf `9a5e59dac3bb219cbc40641e62e75871eb2ed131`. PR #370 war zu
Beginn dieser Fortsetzung offen, unverändert auf dem vollständig geprüften
Head `305293395b767d963ec6ec3c4834da169ef34feb`; neue PR-Kommentare,
Reviews, Releases oder PC-Betriebsnachweise wurden nicht gefunden. Die
6.445 Backendtests, 2.838 Frontendtests und erfolgreichen E2E-/Versionsgates
bleiben an diesen Head gebunden und wurden nicht erneut angestoßen.

**Umgesetzt im bestehenden Lieferweg:** Ein Merge mit unverändertem
`VERSION=1.5.54` könnte keinen neuen PC-Tag veröffentlichen, weil der Publisher
bestehende Tags nie verschiebt. Die [Releasevorbereitung v1.5.55](../releases/V1.5.55-P01-GETTEX-PC-DELIVERY.md)
schließt diese konkrete Lieferlücke mit fünf Versionswerten in vier Dateien.
Anwendungscode, Abhängigkeiten, Regelkatalog, Migration0061 und Updatehelfer
bleiben gegenüber dem geprüften PR-Head unverändert. Der vorhandene
Versions-/Publicationtest ist mit neun bestandenen Fällen ausgeführt.
Die erforderliche CI des neuen Release-Heads wird im [bestehenden PR #370](https://github.com/burckhju/trading-workspace/pull/370)
eigenständig nachgewiesen; anschließend gelten normale Integration,
Main-Gates und automatischer Tagpublisher. Vorbereitung ist noch keine
Veröffentlichung oder PC-Installation. Ein Updateaufruf wird erst mit dem
tatsächlich veröffentlichten Tagcommit ausgefüllt; die neue Import-CLI wird
nicht für den zuletzt belegten alten PC-Stand vorausgesetzt.

**Tatsächliche Zugangs- und Dateigrenze:** Im neuen Arbeitsraum sind weder
der private archivgebundene P01-Bezug noch eine vollständige gettex-Datei
vorhanden. Die verfügbaren Zugänge liefern keinen identifizierten Zugriff
auf den Nutzer-PC oder seine Datenbank. Die BSW-Kopie wurde am 25.11.,
07:54:37–07:54:56 Uhr MEZ, im selben begrenzten Abruflauf erneut vollständig
und bytegleich zum qualifizierten Pin beschafft. Je ein normaler Abruf der
drei Börsen-PDFs ergab HTTP403; diese Dateikopien fehlen hier weiterhin.
Das öffnet keine bereits abgeschlossene fachliche Quellenqualifikation und
belegt keine generelle Unerreichbarkeit auf dem Nutzer-PC.

**Fortsetzung desselben P01-Auftrags:** Nach nachgewiesener Lieferung und
Installation genügt ein gebündelter enger PC-Schritt: aus dem vorhandenen
privaten Archiv ausschließlich P01 binden, aktuelle Position, Produkt,
Terms, KID und MUND/EUR-Listings samt Revisionen sowie die vorhandenen
gettex-/Refresh-/V2-Einstellungen lesen; vier tatsächliche Regeldateien und
eine vollständige lokale Pretrade-Datei für die konkrete Vorschau bereitstellen.
Der alte Gesamt-, P02- oder Quellenkandidatenexport wird nicht wiederholt.
Product-/Mappingvorschau, Anwendung und gespeicherte Verbraucherabnahme
verwenden die vorhandenen Owner; heute sind weder aktuelle IDs noch ein
DB-Previewfingerprint oder ein neuer P01-Entscheid belegt. Product, Market Data
und Position Monitoring bleiben zuständig. Der [einzige Auftrag](#naechster-schnitt)
und sämtliche ursprünglichen Abnahmekriterien bleiben offen.

<a id="p01-originalpaket-20261125"></a>
## Fortschreibung — Regeloriginale qualifiziert, 25.11.2026

**Observed / Implemented:** Die drei gelieferten Börsen-PDFs und die vollständig
bezogene BSW-Klassifikation sind [geprüft und fest hinterlegt](../reviews/GETTEX_LISTING_UNIT_ORIGINALS_2026-11-25.md).
Alle vier tatsächlichen Originalrollen passieren den bestehenden Qualifier;
sieben Negativproben werden korrekt abgewiesen. Der enge feste Katalog trägt
`gettex-mund-eur-equity-call-unit-20261125-v1`, Beobachtungsstand
**25.11., 06:07:22 Uhr MEZ**, ohne erfundenes historisches Inkrafttreten.
61 gezielte Tests sind erfolgreich. Die aktuelle Head-/CI-Zuordnung steht im
[PR #370](https://github.com/burckhju/trading-workspace/pull/370); der frühere
erfolgreiche Head f971d234 ist kein Ersatz für die neue Katalogqualifikation.

**Geschlossene Lücke:** Die drei Regeldateien müssen nicht erneut beschafft
werden. Ein Stückmaßstab ist für den eng gebundenen gettex-MUND/EUR-Call-Fall
belegt; historische Kontinuität bleibt im V2-Modus ausdrücklich angenommen.
Die Grenze des beobachteten Regelstands gilt für das aktuelle Verbraucher-
Kursereignis. Eine ältere vollständige Originaldatei darf separat die
Listing-Mitgliedschaft belegen, aber keinen frischen Verbraucherpreis ersetzen.

**Verbleibend im selben Auftrag:** geprüfte Lieferung und aktuelle P01-Owner-
Bindungen für die echte Listing-/Mapping-/Importvorschau sowie danach der
gespeicherte V2-Entscheid. Hier gibt es keinen interaktiven PC-Zugang und
keinen behaupteten DB-Previewfingerprint. Alte Paketkennungen ersetzen keine
aktuelle Listing-/KID-Revision. Der bestehende gettex-Pfad wurde schon im
22.11-Archiv vom Scheduler angesprochen und hatte zuvor Quotes gespeichert;
eine pauschale neue Providerfreigabe wird nicht erfunden. Aktuelle Konfiguration,
gemeinsamer Dateicache und ausreichende Frische sind eng am PC zu prüfen.
Kein neuer unveränderter Gesamt-, P02- oder Kandidatenexport ist nötig.

<a id="p01-listingeinheit-20261124"></a>
## Fortschreibung — Product-Anschluss für die aktuelle Listingeinheit, 24.11.2026

**Implemented:** Der [ergänzende Einheitenpfad](../reviews/P01_LISTING_UNIT_IMPLEMENTATION_2026-11-24.md)
ist in PR #370 als additive Product-Revision je Listing umgesetzt: vollständiger
lokaler Originaldateiscan, gebundene Regeloriginale, passive Vorschau, expliziter
Import mit Wiederholungs-/Konfliktschutz, Read-only-Diagnose und Weitergabe der
tatsächlichen gettex-Route an V2. KID und ergänzender Beleg bleiben getrennt
nachvollziehbar. Bekannte historische Sperren und B58 werden nicht verändert.
Die eigene Tabelle ersetzt die frühere Implementierungsskizze einer zusätzlichen
KID-Dokumentart; der fachliche Owner und Regelumfang bleiben gleich.
Lokal sind 216 betroffene Tests, Backend-Ruff/Black und mypy erfolgreich.
Die vier lokal übersprungenen PostgreSQL-Fälle wurden anschließend auf
Head f971d234 tatsächlich erfolgreich in der regulären CI ausgeführt:
6.444 Tests bestanden, 90,07% Coverage, Abschluss 24.11., 22:55:58 Uhr MEZ.
Die [Prüfnachweise](../reviews/P01_LISTING_UNIT_IMPLEMENTATION_2026-11-24.md#5-technische-qualifikation)
trennen lokale Läufe, diesen tatsächlichen CI-Stand und späteren neuen Code.
Der zusätzliche Review korrigiert den Vorrang dokumentierter Historie:
Ein bloß ungeeigneter ergänzender Listingbeleg bleibt als fehlende aktuelle
Einheit sichtbar und verdrängt keinen vollständig belegten Maßstab; echte
Produkt-/Währungskonflikte bleiben hart.
Die vorhandenen expliziten Persistenz-/End-to-End-Schemaguards erwarten nun 0061;
der Vorgänger 0060 bleibt ausdrücklich unzulässig. Die neue Tabelle wird ohne
Schutzausnahme in ihren dynamischen Bestandsprüfungen berücksichtigt.

**Damals fehlende Beschaffung, am 25.11. erledigt:** Die drei offiziellen
Börsen-PDFs wurden nach den dokumentierten HTTP403-Antworten vom Nutzer
bereitgestellt. Zusammen mit BSW sind sie nun als echtes Originalpaket
[qualifiziert](#p01-originalpaket-20261125); das feste Register ist gefüllt.
Keine erneute KID-Abfrage oder Depotinventur ist für diese Ursachenklärung nötig.

**Noch kein Observed für P01-V2:** Die bisherige PC-Installation enthält diesen
Anschluss nicht. Konkrete Listing-/Mapping-/Importvorschau
und frischer gespeicherter Verbraucherentscheid bleiben Bestandteile desselben
[einzigen Auftrags](#naechster-schnitt). Technische Tests ersetzen diese
Betriebsabnahme nicht.

<a id="depotquellen-20261124"></a>
## Fortschreibung — Quellenkandidaten und konkreter P01-Datensatz, 24.11.2026

**Der einmalige Kandidatenexport ist ausgeführt und ausgewertet.** Der
[Readback von 20:33:55–20:33:58 Uhr MEZ](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md)
belegt P01/P03/P04 als weiterhin offen und archivgebunden, dieselbe
Installation v1.5.54/9a5e59d… und vollständigen passiven Transport.
Alle drei haben keine ausgewählte Quotequelle, keine Mappingrouten und
leere gespeicherte Auswahlkandidaten; die V2-Heads bleiben `UNAVAILABLE`.
Die KID-Beschaffung ist jeweils erfolgreich. P01/P03 fehlt die ausdrücklich
belegte Preiseinheit; P04 benötigt zusätzlich Basiswert- und Kalenderklärung.

**Neue konkrete Quellenevidenz:** Eine vollständig gelesene offizielle
gettex-MUND-Datei enthält einen passenden positiven Bid und Ask für P01,
EUR, gemeinsame Quellenzeit 24.11., 18:57:23.707737 Uhr MEZ. Die Gesamtdatei
wurde ohne Übermittlung privater Produktkennungen abgerufen und mit dem
vorhandenen Parser einschließlich CRC geprüft. P03/P04 fehlen ausschließlich
in diesem Dateifenster. Der ältere P01-Treffer ist keine aktuelle V2-Abnahme
und noch nicht im PC-Datenbestand gespeichert. Der Dateiumfang von rund
657 MB macht Bandbreite und Taktung zu einer konkreten Betriebsbedingung.

**Genau ein nächster Auftrag:** [P01 über die vorhandenen Quellen- und
Produktowner für V2 versorgen](#naechster-schnitt). Für diese Ursachenklärung
ist kein erneuter Gesamt-, P02- oder Kandidatenexport erforderlich.

**Originalfrage abgeschlossen, 21:07 Uhr MEZ:** Nach ausdrücklicher Freigabe
wurde das offizielle P01-KID abgerufen und bytegleich zur PC-Revision
verifiziert. Alle drei Seiten enthalten keine ausdrückliche Stückpreisnotiz;
`unit=null` ist korrekt, kein Parserfix. Die
[ergänzende Quellenprüfung](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md#gettex-listingeinheit)
belegt eine explizite gettex-Quote-Konvention auch für den Freiverkehr.
Zusammen mit Produktklasse und exaktem MUND/EUR-Datensatz ist damit ein
gesonderter aktueller Listing-Einheitenbeleg vorbereitet. Der
[anschließende Product-Anschluss](#p01-listingeinheit-20261124) ist inzwischen
implementiert. Die [Regeloriginalqualifikation vom 25.11.](#p01-originalpaket-20261125)
schließt die anschließende Dokumentbeschaffungslücke. Offen bleibt die
tatsächliche P01-Listing-/Mapping-/Verbraucherabnahme. Eine KID-Wiederholung
ist für die bereits geklärte Parserursache unnötig.

<a id="depotdiagnose-20261124"></a>
## Fortschreibung — P02-Ursache und gespeicherte V2-Teilabdeckung, 24.11.2026

**Der enge P02-Auftrag ist ausgewertet.** Das neue private Paket bindet
die archivierte Position, ihre ursprünglichen Bewertungsinputs und den
heutigen gespeicherten Quellenbestand eindeutig. Der
[Einzelnachweis](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md) belegt
die tatsächliche PC-Installation **v1.5.54/9a5e59d…**, Schema0060 und vier
gesunde laufende Dienste. Sammlung: **24.11., 18:23:08–18:23:10 Uhr MEZ**.

**Konkreter Fortschritt:** Der historische Unterbrechungsgrund lautet
`JPMORGAN_SNAPSHOT_TIMEOUT`. Der zuvor empfangene gespeicherte Quote war
bidlos; dessen ursprüngliche Rohpreis-/Normalisierungsursache bleibt
unbekannt. Die Gap-Erfassung kann einen gecachten Fehler wiedergeben und
ist kein sicherer ursprünglicher Netzwerkfehlerzeitpunkt. Auf derselben
gebundenen Route liegt inzwischen eine tatsächlich gespeicherte
V2-Bewertung vom **24.11., 18:21:41 Uhr MEZ** vor: `BELOW_ENTRY` /
`INDICATIVE_BID_BELOW_GROSS_ENTRY`, Bid vorhanden, Empfangsalter **10,456 s**.

**Verbleibende fachliche Grenze:** `ORIGINAL_MARKET_STATUS_NOT_DELIVERED`
belegt den fehlenden Originalstatus, aber keine neue V2-Preisunterbrechung.
Original-Bidzeit mit Datum/Zeitzone, passender Original-OPEN-Status und
seine zeitliche Geltung bleiben für B58 unbelegt. Der Einzelread enthält
keine neue Gesamtinventur, keine vollständige Verlaufshistorie und keine
neuen Produktfrist-/B06-/Zustellbelege. Aus der alten Vierer-Matrix wird
keine heutige „1/4“-Abdeckungsquote abgeleitet.

**Technische Qualifikation getrennt:** Die vier regulären PR-Prüfungen für
`41a0cf80b1f0702d3322bcf268ed83da8cf84de2` sind erfolgreich abgeschlossen
([CI-Belege](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md#6-codequalifikation-und-weiterführung)).
Das betrifft den noch offenen Diagnose-/Resolverfix, der auf diesem PC
nicht installiert ist. Die neue Preisbeobachtung wird ihm nicht
zugeschrieben. Der heutige Dokumentationsnachtrag ändert keinen Anwendungscode.

**Genau ein nächster Auftrag:** [Eine weitere tatsächlich offene Position
über die bestehenden Quellen- und Produktowner versorgen](#naechster-schnitt).
Die damals noch offenen Kandidatenfragen für P01/P03/P04 sind durch den
[späteren Read von 20:33 Uhr](#depotquellen-20261124) beantwortet; P01 ist
nach der zusätzlichen gettex-Probe der konkrete nächste Versorgungsfall.
Eine erneute P02-Sammlung ist für den abgeschlossenen engen Befund unnötig.

**Fortsetzung desselben Auftrags am 24.11.:** Der
[gezielte Quellenkandidatenread](../technical/ISSUER_MONITORING_OPERATIONS.md#gezielter-quellenkandidatenread)
mit `--source-coverage-from` ist implementiert, erfolgreich auf dem PC
ausgeführt und ausgewertet. Der
[Umsetzungsnachweis](../reviews/DEPOT_SOURCE_COVERAGE_COLLECTOR_2026-11-24.md)
bewahrt technische Qualifikation und den korrigierten CI-Importsortierfehler;
der [Betriebsread](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md)
belegt die tatsächlichen Routen-/Produktlücken. Der eine Versorgungsauftrag
wird auf P01 konkretisiert, statt denselben Export erneut anzufordern.

<details>
<summary>Readback und P02-Vorbereitung vom 20.–23.11.2026 — damalige Arbeitsstände</summary>

Die folgenden datierten Texte bleiben als Historie erhalten. Die damals
noch fehlende enge P02-Ergänzung liegt seit dem 24.11. vor; maßgeblich sind
die Fortschreibung oben und der eine aktuelle Auftrag unten.

<a id="depotdiagnose-20261122"></a>
## Fortschreibung — tatsächliche Depotversorgung, 22.11.2026

**Diagnoseschnitt abgeschlossen:** Der Nutzer hat den vorbereiteten Collector
auf dem bestehenden PC ausgeführt und das vollständige private Archiv
bereitgestellt. Der [belegte Readback](../reviews/DEPOT_DATA_READBACK_2026-11-22.md)
umfasst alle vier offenen Positionen, sämtliche sechs Pflichtreader je
Position, Runtime/Inventar/Refresh vor und nach sowie den tatsächlichen
Installations- und Schemastand. Die frühere Zugangslücke für diesen
Verbraucherbefund ist geschlossen. Privater Direktzugriff bleibt weiterhin
nicht vorhanden; Rohdateien bleiben außerhalb des Repositories.

**Jetzt beobachtet:** v1.5.52 / `c7db441…`, Schema `20261118_0060`, vier
laufende gesunde Dienste. Readback **22.11.2026, 20:50:41–20:50:45 Uhr MEZ**;
letzter regulärer V2-Zyklus **20:44:54–20:45:35 Uhr MEZ**. V2-Einstand und
Produktfrist jeweils vier ausgewertete Positionen, vier Datenprobleme,
null technische Positionsfehler. Alle 30 Diagnose-GETs erfolgreich;
kein global atomarer Snapshot. Ältere gespeicherte Assessmentzeiten sind
mit der belegten Deduplizierung unveränderter Eingänge vereinbar.

**Fortschritt am Datenbestand:** Käufe, historische Kaufwährungen und
Restmengenbasis sind vierfach vorhanden. Produktende und Zahlung sind bei
allen vier Fristassessments getrennt; der frühere falsche Datumswiderspruch
fehlt. Das belegt Verbraucherwirkung, nicht die vollständige private
Parser-/Originalupgrade-Idempotenz. Die Datenversorgung bleibt unvollständig:
drei unbestätigte Kursrouten, eine bestätigte JPMorgan-Route ohne verwendbaren
Bid, zusätzliche Einheits-/Basiswert-/Kalenderlücken sowie vier fehlende
Exitlisting-/Letzthandelstagsbelege. B04/B57 bleibt deaktiviert; strenge
B58-Inputs und B06-Grundevidenz/Verarbeitung sind gesondert offen.

**Abgeschlossen ist die vollständige Verbraucher-Ursachenmatrix, keine
fachliche Depotabnahme.** Die konkrete Ursache des fehlenden Bids und der gemeldeten Unterbrechung
ist in den vorhandenen Antwortprojektionen noch nicht vollständig sichtbar.
Der bereits gespeicherte Journal-/Assessmentkontext ist genau als
fehlender Teilbeleg benannt. Der [einzige nächste Ownerauftrag](#naechster-schnitt)
löst diese eng abgegrenzte P02-Ursache auf und qualifiziert die entsprechende
Korrektur; ein weiterer unveränderter Gesamtcollector wird nicht verlangt.

**Fortsetzung desselben Auftrags, 22.11.2026:** Die Fehlerweitergabe im
Resolver ist im Arbeitsbranch korrigiert: Bei gültiger Qualität ohne Bid
und ohne Referenzpreis bleibt `BID_MISSING` sichtbar; Abruffehler, Retention,
Providerhinweis und Zeitqualität werden getrennt bis zur API weitergegeben.
Ungültige Qualität bleibt ein Fehler. Der bestehende Collector besitzt
einen gezielten Modus `--source-gap-from … --position-label P02`, der die
Bindung aus dem gelieferten Archiv übernimmt und ausschließlich vorhandene
Journal-/Assessmentdaten liest. Die [Umsetzungs- und Prüfbelege](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#p02-fortsetzung-20261122)
trennen Codequalifikation, den noch benötigten PC-Read und eine mögliche
spätere Preisversorgung. Ein App-Update ist für diesen Export nicht nötig;
der Fix ist damit noch nicht auf dem PC installiert. Der Gesamtauftrag
bleibt bis zum gebundenen Originalgrund und seiner Auswertung offen.

**Auslieferungsabgleich, 23.11.2026:** Der erste enge Nutzeraufruf lief gegen
eine alte lokale Datei mit ausschließlich `--base` und endete vor jeder
Datensammlung. Die geprüfte neue Fassung wird bytegleich unter einem
eindeutigen Downloadnamen bereitgestellt; kein App-Update erforderlich.
Die CI des veröffentlichten Fixes hat außerdem genau ein veraltetes
synthetisches Browserfixture nachgewiesen: sechs Attempts benötigen die
drei additiven Diagnosefelder. Diese 18 erwarteten Werte wurden anhand
des vollständigen CI-Diffs ergänzt und gegen das gesamte tatsächliche
CI-Ergebnis geprüft, ohne die Prüfung abzuschwächen.
[Nachweis und genaue CI-Grenzen](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#p02-auslieferungsabgleich-20261123).
Der eine aktuelle Auftrag bleibt der gebundene P02-Journalread und seine
Auswertung; eine tatsächliche neue Bidversorgung ist weiterhin unbelegt.

<details>
<summary>Vorbereitung und Quellenanalyse vom 20./21.11.2026 — damaliger Stand</summary>

Die folgenden datierten Texte erhalten die damalige Diagnosevorbereitung
und Anbieterrecherche. Aussagen über noch fehlenden PC-Readback und den
seinerzeit nächsten Auftrag sind durch den Nachtrag vom 22.11. überholt.

<a id="depotdiagnose-20261121"></a>
## Fortsetzung des nächsten Auftrags — passive PC-Diagnose, 21.11.2026

Der Nutzerauftrag „Nächster Schritt“ setzt die bereits priorisierte
[vollständige lesende Verbraucherdiagnose](#naechster-schnitt) fort.
Die bestehende PC-Installation und ihre Datenbank sind in der bereitgestellten
Arbeitsumgebung nicht zugänglich; ein neuer PC-Readback liegt nicht vor.
Main wurde auf `febeb922…` / `VERSION=1.5.53` fortgeschrieben. Die
benötigten Backendreader und ihre Responseverträge sind gegenüber dem
geprüften Produktstand unverändert. [#371](https://github.com/burckhju/trading-workspace/pull/371)
belegt die Bereitstellung von v1.5.53, [#372](https://github.com/burckhju/trading-workspace/pull/372)
die Oberflächenintegration; beide Beschreibungen und Diskussionen enthalten
keinen neueren privaten Installations-, Zyklus- oder Abdeckungsbeleg.

**Konkreter Fortschritt:** Der vorbereitete Abruf wird als einzelne
[herunterladbare Pythondatei](../../scripts/collect-depot-data-supply.py)
mit privatem Diagnosearchiv bereitgestellt. Der bisherige Aufruf
`trading-workspace status` ist aus diesem Ablauf entfernt: Er kann über den
Deploymentvalidator Lock-/Wartungsdateien schreiben und einen
Validatorcontainer starten. Stattdessen werden nur gezielte Git-/State-/
Container-/Imagebelege vor und nach der Sammlung gelesen. Ein ausdrücklicher
READ-ONLY-SELECT über die konfigurierte Backend-Datenbank ergänzt den
bislang fehlenden tatsächlichen Schemastand. Der fachliche GET-Pythonteil
mit vollständigem Inventar und sechs Readern je Position bleibt bytegleich.
[Ausführung und Nachweisgrenzen](../technical/ISSUER_MONITORING_OPERATIONS.md#lesende-depot-datenversorgungsdiagnose).

**Qualifikation des Helfers:** 19 isolierte Tests, gezieltes Black-/Ruff-Gate
und Syntaxprüfung für den Host ab Python 3.10 erfolgreich. Die Tests prüfen
unter anderem erlaubte Leseoperationen, private Ausgaben, falsche
Installationsbindungen, unvollständige Readerantworten und den
READ-ONLY-Schemaread; sie ersetzen keinen PC-Lauf.
[Prüfbeleg](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md#8-prüfung-dieser-dokumentation).

**Verbleibend:** einmalige Ausführung auf dem bestehenden PC und Auswertung
des privaten Archivs; erst daraus folgen positionsgenaue Gründe und
beurteilbare Abdeckung. Der Helfer verbessert die Durchführbarkeit und
Integrität der Diagnose, nicht bereits die Datenversorgung einer Position.
Keine neue Quellen-/Regelfreigabe oder Depotabnahme. Der einzige nächste
Auftrag unten bleibt maßgeblich; seine Abnahmekriterien werden durch den
vorbereiteten Collector noch nicht als erfüllt geführt.

<a id="datenversorgung-20261120"></a>
## Aktuelle Fortschreibung — Datenversorgung, 20.11.2026

**Priorität dieses Auftrags ist die geeignete Versorgung der tatsächlichen
Depotpositionen.** Die Softwareprüfung ist an
`c7db441de36297a98d47cdf28c64b4e5d9994692` / `v1.5.52` gebunden.
Der neuere Main `6c0f9160b91bee4c6c45849c9c47d4c4b5a3bf56`
integriert mit #369 ausschließlich die hier erhaltene Dokumentkonsolidierung;
Anwendungscode und Version sind gegenüber dieser Produktbasis unverändert.
Neue Aussagen trennen Softwarestand, Dokumentstand und beobachteten PC-Betrieb. Der [Datenversorgungsnachweis](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md)
enthält Datenvertrag, vollständige Consumerketten, Fehlerklassen, aktuelle
Primärquellen und fünf Versorgungsszenarien. Er führt keinen Aufgabenstatus.

**Tatsächlicher Fortschritt:** Anforderungen und Beschaffungswege sind
anhand von Quellen, Code und öffentlichen Betriebsbelegen bis zum Verbraucher abgeglichen. Der am
19.11.2026 in #368 veröffentlichte neuere vollständige Readback umfasst vier
damals offene Positionen unter v1.5.51/V2, jeweils vier Einstands-/Fristdatenprobleme.
Sein Rohdiagnosezeitpunkt ist nicht veröffentlicht; technische Fehlerfreiheit
ist gesondert im früheren Zyklus belegt. Er ergänzt den zeitlich
genau belegten früheren Sechserzyklus aus #367. Zahlungstag/Produktende und
Kalender-HTTP-403 sind konkrete Ursachen; die Datumsreparatur und ein enger
Kalenderoriginalimport sind mit v1.5.52 ausgeliefert. Die Wirkung auf dem
PC ist noch nicht belegt.

**Verbleibend:** aktuelle positionsgenaue Zuordnung der Fehler, fehlende
Kursrouten/Stückmaßstäbe, eine falsche Basiswertbindung, historische
Währungs-/Skalen-/Tradebelege, Exitwahl/letzter Handelstag/Kalenderjahre und
Produktschluss; strenge B58-Originalstatusversorgung sowie B06-/F207-2- und
F207-5-Reste. Der tatsächliche Broker und ein berechtigter geeigneter
Feedzugang sind nicht festgestellt. ARIVA-Schema 0.6.26 wurde tatsächlich
gelesen; darin ist keine eigene Statuszeit ausgewiesen. Keine Beschaffung,
Providerfreigabe, Regeländerung oder aktuelle Depotabnahme erfolgte.

Die maßgeblichen Teilfähigkeitsfelder unten sind entsprechend fortgeschrieben.
**Genau nächster Auftrag:** [vollständige lesende Verbraucherdiagnose](#naechster-schnitt)
mit automatischer Inventur über den vorhandenen Coverage-Reader, konkreten
Gründen je Position/Regel und privatem Rohbeleg. Runtimezähler allein erfüllen
die Abnahme nicht. Die historischen Aufträge unten bleiben ausdrücklich
historische Nachweise.

**Ergänzung zur Mehrquellenidee, 20.11.2026:** Die bereitgestellten
Portalbeispiele und aktuelle Primärquellen belegen einen konkreten weiteren
Versorgungsansatz. Öffentliche geeignete Quellen vorrangig prüfen;
ein kostenpflichtiger Feed ist keine Vorbedingung. Vorhandener Refresh
liest bereits mehrere verifizierte Routen, der Positionsowner hat aber
keine Auswahl „aktuellste“ oder „zwei identisch“ und keinen automatischen
Wechsel bei Ausfall. [Befunde und vorgeschlagene Auswahlrichtlinie](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md#webquellen-mehrfachpruefung)
trennen Preisart/Listing/Zeit/Herkunft, Zugangsrechte und V2-/B58-Grenzen.
Onvista verlangt Zustimmung für automatisierte Abrufe. Neue Adapter,
Rangfolge, Vergleichstoleranzen und Ersatzquellen sind **Analysis**, nicht
implementiert oder freigegeben. Der bestehende nächste Diagnoseschnitt
erfasst diese Möglichkeiten je tatsächlicher Position mit; keine zweite
aktuelle Aufgabenliste und keine neue Provideraktivierung.

**Quellen- und Kostenprüfung der neun Emittenten, 20.11.2026:**
Die [neue Quellenübersicht](../reviews/ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md)
prüft DZ, BNP, HSBC, JPM, UniCredit, UBS, Vontobel, SG Effekten und Morgan
Stanley anhand aktueller Primärunterlagen. Kostenloser Sicht-/Exportzugang,
private Kopien, ausdrücklich genehmigungspflichtige Abrufe und offene
Automationskonditionen sind getrennt. gettex liefert einen dokumentierten
kostenlosen Dateiweg für BNP/HSBC/UniCredit; Stuttgart dokumentiert
kostenlose Downloads mit noch zu klärendem Dauerabrufumfang. TAI-PAN nennt
49 EUR/Monat API plus 29 EUR/Monat Global; tatsächliche ISIN-/Listingdeckung,
Gesamtpreis, Speicherung und Instrumentstatus sind nicht bestätigt.
Der Bericht trennt die plausible Annahme einer angezeigten Bid-Zeit von
belegter Originalzeit und weist die übrigen B58-Bedingungen ausdrücklich
aus. **Fortschritt:** Beschaffungsoptionen und Kosten konkreter belegt.
**Verbleibend:** tatsächliche Verbraucher-/Positionsprobe, Rechte-/Feldvertrag
und gezielte Integration. **Arbeitsstatus: Analysis** für neue Quellen und
Auswahlrichtlinie; keine neue Providerfreigabe. Der einzige nächste
lesende Diagnoseschnitt und seine Abnahmekriterien bleiben maßgeblich.

</details>

</details>

<a id="aktueller-stand"></a>
## Aktuelle Einstiegssicht — 24.11.2026

**Der Gesamtbacklog bleibt offen.** Alle ursprünglichen M0–M11-Zusagen
sind weiterhin vollständig [zugeordnet](#originalzuordnung). Erneut gelesener
Main ist `9a5e59dac3bb219cbc40641e62e75871eb2ed131` / `VERSION=1.5.54`.
Die relevanten Backendreader bleiben an die unveränderte Produktbasis
`c7db441de36297a98d47cdf28c64b4e5d9994692` gebunden. Genau diese Basis ist
unverändert im aktuellen Main enthalten. **v1.5.54 ist durch den privaten
Read vom 24.11. auf dem PC installiert belegt.** Release-/Main-/PC-Stand
bleiben getrennt; ältere CI-Nachweise gelten nur für ihre jeweiligen Commits.

**PC-Lieferumfang dieser Planung:** [PR #369](https://github.com/burckhju/trading-workspace/pull/369) wurde am **20.11.2026 um 15:01:46 Uhr MEZ** als `6c0f9160b91bee4c6c45849c9c47d4c4b5a3bf56` gemergt. Der reine [Bereitstellungsrelease v1.5.53](../releases/V1.5.53-PLANNING-PC-DELIVERY.md) macht diesen Dokumentstand zusammen mit dem unveränderten Produktumfang v1.5.52 über den vorhandenen PC-Updateweg lieferbar. Die konkreten PR-/Main-Prüfungen und der endgültige unveränderliche Tag-Commit werden im Release-PR protokolliert. Dieser Lieferverweis ergänzt den datierten Audit; er ändert keine Teilfähigkeitsbewertung und belegt keine PC-Installation oder fachliche Wirkung. Der [eine nächste Fachauftrag](#naechster-schnitt) gilt auch nach einem Update auf den einschließenden Folgerelease.

**Zusätzlich abgeschlossen seit der Erstprüfung:** Die [Trennung von Produktende und Zahlungstag, erneute Auswertung gespeicherter Originale und der enge lokale XSTU-2026-Originalimport](#market-data-evidence) sind implementiert, qualifiziert, integriert und mit v1.5.52 ausgeliefert. Die früheren Lieferreste für #368 sind damit geschlossen. Ein bereitstehender Importweg belegt keinen tatsächlich ausgeführten Import; der neue private Readback belegt die getrennten Datumsrollen am Verbraucher. Die vollständige Originalupgrade-/Importabnahme bleibt davon getrennt.

**Zuletzt belegter Betrieb ist v1.5.54:** Der
[Quellenkandidatenread vom 24.11., 20:33 Uhr](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md)
bestätigt Installation, Schema, gesunde Dienste und drei offene, weiterhin
quellen-/produktblockierte Positionen. Der frühere
[P02-Read](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md) belegt seinen
gespeicherten V2-Entscheid mit Bid am selben Tag um 18:21 Uhr. Die letzte vollständige Inventur und Zyklusdiagnose stammen vom
[22.11.](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): damals vier offene
Positionen, beide Prüfpfade mit 4/4 Datenproblemen und null technischen
Positionsfehlern. Historische Sechser-/Viererbefunde und der neue Einzelread
bleiben eigene Zeit-/Mengenschnitte ([Betriebsevidenz](#betriebsnachweis)).

**Bisherige Teilabschlüsse bleiben erhalten:** Persistente [feste Chart-Watchlist](#pb-012-watchlist) mit S&P 500 und 30 ETFs; [Journal](#pb-019-journal), [Evidence](#pb-019-materialization), [Lessons](#pb-019-lessons) und [historische Korrekturen](#pb-018-currentness); [Bruttoauswertungen](#pb-019-performance-evaluations), [vier Basisstatistiken](#pb-019-performance-statistics) und [Verkaufsbeitragsgrafik](#pb-019-performance-dashboards); [konkrete Kandidaten-Governance mit gesonderter Aktivierung und Rückkehr](#pb-020-candidate-family). Die zugehörigen Funktionspfade sind gegenüber der Produktbasis `c7db441…` unverändert; die genannten Regressionsergebnisse sind ausschließlich an diese Produktbasis gebunden. Ihre Implementierung wird nicht erneut eingeplant; offene Fachabnahmen und reale Quellenabdeckung bleiben getrennt.

**Wesentliche Reste:** P02 hat einen konkretisierten historischen Gapgrund und einen jüngeren auswertbaren V2-Entscheid. P01/P03/P04 sind inzwischen aktuell gebunden und gelesen: keine Mappingrouten/Kandidaten, erfolgreiche KID-Beschaffung ohne Preiseinheit; P04 zusätzlich Basiswert-/Kalenderlücke. Ein P01-gettex-Bid ist in einer getrennten Originaldateiprobe belegt, noch nicht als aktueller PC-Input. Persönliche Exitwahl, letzter Handelstag, Produktschluss, strenge Originalkurs-/Statusbelege und B06-Grundevidenz bleiben eigenständige Voraussetzungen. Der allgemeine Watchlistumfang, Scanner, Marktbreite, Produktscore, Produktwechsel sowie weitergehende Lern-, Performance- und Modellanforderungen bleiben mit konkreten Entscheidungs-, Implementierungs- oder Abnahmeresten erhalten. Die strenge B58-Versorgung und übrigen B-/F207-Umfänge werden nicht durch die indikative Alternative geschlossen.

**Genau ein nächster Auftrag:** [P01 für V2 versorgen](#naechster-schnitt).
Die Quellenkandidatenfrage ist beantwortet; jetzt die belegte gettex-Route
über Listing/Mapping anbinden und die Preiseinheit am Original qualifizieren.
Anschließend den ausreichend frischen tatsächlichen V2-Verbraucherinput prüfen. Das Ergebnis ist eine zusätzliche
beurteilbare Position oder ein exakt belegter verbleibender Daten-/
Zugangsblocker; neue Provider- und Kostenentscheidungen bleiben gesondert.

## Pflegevertrag und Statusbedeutung

Nur die **Arbeitsstatus-Felder der aktuellen Teilfähigkeitstabellen** sind maßgeblich. PB-001 bis PB-020 bleiben Container ohne pauschalen Gesamtstatus; unnummerierte Fähigkeiten bleiben unnummeriert. Beschreibende HTML-Anker sind Sprungziele und keine neuen Kennungen. Einstiegssicht, Originalzuordnung, Roadmap, Katalog und Traceability leiten sich von diesen Tabellen ab.

Das vorhandene [Lifecycle-Modell](../technical/FEATURE_LIFECYCLE.md) bleibt maßgeblich: `Idea → Analysis → Specified → Approved for Build → In Development → Technical Review → Business Review → Accepted → Released → Observed`. Ein Feld darf ausdrücklich verschiedene **abgegrenzte Teilumfänge** nennen: einen historisch abgenommenen und ausgelieferten Umfang (`Released`), eine noch zu klärende Erweiterung (`Analysis`) oder eine ausstehende fachliche Prüfung (`Business Review`). `Observed` ist auf den tatsächlich beobachteten Betrieb begrenzt. Historische `Done`-/`Accepted`-/RC-Freigaben behalten ihren damals dokumentierten Geltungsumfang.

Die in Phase 9/10 geforderte **datierte, verantwortete Abnahme** wird weder durch CI noch durch einen Tag ersetzt. Für neu geprüfte Teilumfänge ohne diesen Beleg bleibt `Business Review` beziehungsweise die fehlende Abnahme ausdrücklich offen. Ihre nachgewiesene Implementierung, technische Qualifikation und tatsächlich erfolgte Auslieferung werden in den getrennten Feldern abgeschlossen; die fehlende Abnahme ist eine **Lifecycle-Nachweislücke**, kein Anlass zur Neuimplementierung. Historische Freigaben werden nicht zurückgenommen oder auf spätere Erweiterungen ausgedehnt. Dieser Audit ändert keine Statusdefinition oder Abnahmeregel.

Die Tabellen trennen Implementierung, Tests, fachliche Abnahme, Auslieferung, Betrieb und Restarbeit. **Abgeschlossener Teilumfang** bedeutet den dort beschriebenen erledigten Arbeitsumfang, keinen pauschalen Meilensteinabschluss. Die **Befundklasse** unterscheidet fehlende, unvollständige, vorhandene aber unzureichend nachgewiesene, daten-/entscheidungsblockierte und belegbar abgeschlossene Teile. Jeder offene Rest folgt der Kette **Lücke → erwartetes Benutzerergebnis → bestehende zuständige Komponente → Voraussetzung → überprüfbares Abschlusskriterium**. Erledigte Implementierung wird nicht erneut eingeplant.

Die Erstprüfung galt dem Produktcommit 254f0bbd… / v1.5.51. Für diese Fortschreibung wurden das gesamte Main-Delta und seine betroffenen Verarbeitungspfade geprüft; unveränderte Teilbäume behalten ihren ursprünglichen Quellbefund und erhalten den neuen Main-Regressionsbezug. Die fachliche Bestandsprüfung gilt für c7db441… / v1.5.52, soweit ein Beleg ausdrücklich einen anderen Commit nennt. Die anschließende [P02-Fortsetzung](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#p02-fortsetzung-20261122) ergänzt im Arbeitsbranch den engen Resolver-/Diagnosefix samt eigenem Qualifikationsbezug; dies ist kein bereits installierter PC-Stand. Relative Code-/Testlinks zeigen den jeweiligen Branchstand. Historische Nachträge stehen hinter ausdrücklich bezeichneten Aufklappbereichen; dortige Wörter wie „aktuell“, „nächster“ oder „noch offen“ gelten ausschließlich zum damaligen Datum. Die einzige aktuelle Handlungsanweisung steht unter [Nächster Auftrag](#naechster-schnitt).

## Orientierung und Priorisierung

Die [acht dauerhaften Planungssichten und drei Querschnittsthemen](MODULE_AND_FEATURE_CATALOG.md#planungssichten) sind keine neuen Paketgrenzen. Die [Lieferziele A–D](../foundation/ROADMAP.md#lieferziele) sind keine starre Reihenfolge. **Aktuelle Priorität, am 24.11.2026 fortgeschrieben: Datenversorgung für verlässliche Depotüberwachung in A.** Der frühere Fokus **B: Abschluss/Journal/Lernen** und **C: belastbare Performance** bleibt als ursprüngliches Lieferziel erhalten; die dortigen Daten- und Definitionslücken sind im neuen Versorgungsnachweis ausdrücklich ausgewiesen. D verwendet bestehende Kandidaten-Governance statt Neubau. Governance und Betrieb begleiten alle Ziele. Die positionsweise Verbraucherdiagnose ist seit dem 22.11. ausgewertet; getrennte Produktende-/Zahlungsrollen belegen die begrenzte Verbraucherwirkung des #368-Fixes. Offen bleiben die private Originalupgrade-/Kalenderimport-Detailabnahme und konkrete Datenversorgung. Der enge P02-Read ist am 24.11. ausgewertet; ein gespeicherter V2-Entscheid mit Bid ist belegt. Der spätere Quellenkandidatenread bestätigt P01/P03/P04 als offen und konkret quellen-/produktblockiert; ein offizieller gettex-Dateitreffer macht P01 zum belegten nächsten Versorgungsfall beim bestehenden Owner. Erfolgreicher Runnerbetrieb mit Datenwarnungen ist keine fachliche Positionsabdeckung.

P0–P3 bleiben verwendbar. Weder eine fehlende Betriebsabnahme noch eine offene Umfangsentscheidung erzeugt einen pauschalen Rücksprung aller Implementierungen. Ein enger V1-Ausschluss entfernt keine ursprüngliche Anforderung; dafür wäre eine ausdrückliche datierte Produktentscheidung nötig.

<a id="originalzuordnung"></a>
## Originalzuordnung M0–M11

Vergleichsbasis ist die [unveränderte Roadmap vom 2026-07-22](../foundation/archive/ROADMAP_2026-07-22.md). Die folgenden **63 Inhaltsziel-Vorkommen** werden wortgetreu referenziert; dies ist eine Aussage über Rückverfolgbarkeit, nicht über Produktfertigstellung. Gleichartige ursprüngliche Vorkommen (Scanner, Produktscore) verweisen auf denselben Eintrag. Die Meilenstein-Ziel-/Ergebnisformulierungen bleiben zusätzlich in der Baseline erhalten; weder historische Versionsnamen noch heutige Tags erklären sie pauschal für erfüllt.

<a id="original-m0"></a>
### M0

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Repositorystruktur | [Repositorystruktur](#pb-004-repository) |
| Dokumentation | [Dokumentation und Spezifikationsführung](#pb-004-documentation) |
| Spezifikationen | [Projektweite Spezifikationen](#pb-004-specifications) |
| Terminologie | [Terminologie](#pb-004-terminology) |
| Architektur | [Fachliche Domain Map und Architektur](#pb-001-domain) |
| Entwicklungsstandards | [Entwicklungsstandards und Governance-Baselines](#pb-004-standards) |

<a id="original-m1"></a>
### M1

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Basiswerte | [Basiswerte, Listings und Identitäten im Backend](#pb-006-underlying) |
| Börsen | [Börsen und Handelsplätze](#pb-009-venues) |
| Emittenten | [Emittenten](#pb-010-issuers) |
| Instrumente | [Instrumente und Optionsscheine](#pb-011-warrants) |
| Optionsscheine | [Instrumente und Optionsscheine](#pb-011-warrants) |
| Datenprovider | [Datenprovider und benutzerverwaltete Konfiguration](#provider-configuration) |

<a id="original-m2"></a>
### M2

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Marktübersicht | [Marktübersicht](#pb-013-overview) |
| Scanner | [Scanner und Scanner-Modell](#pb-012-scanner) |
| Marktbreite | [Marktbreite](#pb-013-breadth) |
| Sektoren | [Sektoren und Referenzen](#pb-013-sectors) |
| Watchlist | [Watchlist](#pb-012-watchlist) |
| Kandidaten | [Kandidatenqualifikation](#pb-012-candidate) |

<a id="original-m3"></a>
### M3

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Analyse | [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis) |
| Einstieg | [Einstieg planen](#pb-014-entry) |
| Stopstrategie | [Stopstrategie im TradePlan](#pb-014-stop) |
| Kursziele | [Kursziele im TradePlan](#pb-014-targets) |
| Risiko | [Risikoannahmen im TradePlan](#pb-014-risk) |
| Annahmen | [Annahmen, Freigabe und Herkunft des Plans](#pb-014-assumptions) |

<a id="original-m4"></a>
### M4

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Produktsuche | [Produktsuche und Suchuniversum](#pb-015-search) |
| Produktvergleich | [Produktvergleich und bewusste Auswahl](#pb-015-comparison) |
| Produktscore | [Produktscore und fachliche Modellfamilie](#pb-015-score) |
| Produktwechsel | [Produktwechsel](#pb-017-product-change) |

<a id="original-m5"></a>
### M5

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Trade eröffnen | [Trade eröffnen und tatsächliche Käufe erfassen](#pb-016-opening) |
| Depot | [Depot und abgeleitete offene Positionen](#pb-016-positions) |
| Stopmanagement | [Stop- und Zielmanagement](#pb-017-stop) |
| Teilverkauf | [Teilverkäufe](#pb-017-partial) |
| Trade schließen | [Vollverkauf und Abschluss](#pb-017-close) |
| Event-Historie | [Event-Historie und historische Korrekturen](#pb-017-history) |

<a id="original-m6"></a>
### M6

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Nachbeobachtung | [Zulässige Nachbeobachtung](#pb-018-observation) |
| Virtuelle Weiterführung | [Virtuelle Weiterführung](#pb-018-virtual) |
| Exit Review | [Exit Review und Handoff](#pb-018-review) |
| Vergleich tatsächlicher und virtueller Ausstiege | [Vergleich tatsächlicher und virtueller Ausstiege](#pb-018-exit-comparison) |

<a id="original-m7"></a>
### M7

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Journal | [Journalentwurf und Journalabschluss](#pb-019-journal) |
| Regelabweichungen | [Regelabweichungen dokumentieren](#pb-019-deviations) |
| Lessons Learned | [Belegte Lessons Learned](#pb-019-lessons) |
| Entscheidungsbewertung | [Entscheidungsbewertung getrennt vom Ergebnis](#pb-019-decision-quality) |

<a id="original-m8"></a>
### M8

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Performancekennzahlen | [Performancekennzahlen](#pb-019-performance-metrics) |
| Statistiken | [Tradeübergreifende Statistiken](#pb-019-performance-statistics) |
| Dashboards | [Performance-Dashboards](#pb-019-performance-dashboards) |
| Auswertungen | [Perioden- und Tradeauswertungen](#pb-019-performance-evaluations) |

<a id="original-m9"></a>
### M9

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Marktmodell | [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis) |
| Scanner | [Scanner und Scanner-Modell](#pb-012-scanner) |
| Stopmodell | [Stopmodell](#pb-020-stop-model) |
| Zielmodell | [Zielmodell](#pb-020-target-model) |
| Produktscore | [Produktscore und fachliche Modellfamilie](#pb-015-score) |
| Trade Assistant | [Trade Assistant](#pb-020-assistant) |
| Nachbeobachtungsmodell | [Nachbeobachtungsmodell](#pb-020-observation-model) |

<a id="original-m10"></a>
### M10

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Erinnerungen | [Erinnerungen](#reminders) |
| Benachrichtigungen | [Benachrichtigungen und Zustellzustände](#notification-delivery) |
| Regelüberwachung | [Regelüberwachung und fachliche Alerts](#monitoring-rules) |
| Datenaktualisierung | [Datenaktualisierung und Schedulerzustände](#market-data-refresh) |
| Modellüberwachung | [Modellüberwachung](#model-monitoring) |

<a id="original-m11"></a>
### M11

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Performanceoptimierung | [Performanceoptimierung](#operations-optimization) |
| Stabilität | [Stabilität und sichere Betriebsgrenzen](#operations-stability) |
| Regressionstests | [Regressionstests](#operations-regression) |
| Dokumentationsreview | [Dokumentation und Spezifikationsführung](#pb-004-documentation) |
| Releasevorbereitung | [Releasevorbereitung und Softwarestand](#operations-release) |

<a id="nachweisregister"></a>
## Nachweisregister und tatsächlich durchgeführte Prüfung

**Fortschreibung vom 20.11.2026, ab 13:46 Uhr MEZ (12:46 UTC), erhalten aus #369:** Geprüfte Produktbasis war zu diesem Zeitpunkt `main` / `c7db441de36297a98d47cdf28c64b4e5d9994692` / veröffentlichter Softwaretag `v1.5.52`, Tree `e0c62e8ce82aa8bf1d4b9f247ae05f0b12675b22`. Der vollständige Checkout und die GitHub-Nachweise wurden gegenüber dem vorherigen Stand abgeglichen. `VERSION` und Backend-/Frontend-Versionen gehören zu dieser Produktbasis. Die ursprüngliche Prüfung vom 19.11.2026 und ihre damaligen Main-/PR-/Betriebsbelege bleiben historische Nachweise ihres jeweiligen Umfangs.

Repository-Wurzel und Dokumentbereiche enthalten keine zusätzliche `AGENTS.md`; PROJECT, Entwicklungsanleitung, Feature Lifecycle und Dokumentations-Konsistenzcheckliste wurden berücksichtigt. Die ursprüngliche Roadmap bleibt unverändert, Git-Blob `919ed7570580b1d883a409f864ed15747fbfda3e`. Weder die Fortschreibung noch erfolgreiche CI erzeugen eine neue fachliche Abnahme.

| Aktueller Nachweis | Erneut gelesener Befund | Aussagegrenze |
|---|---|---|
| [Produktcommit](https://github.com/burckhju/trading-workspace/commit/c7db441de36297a98d47cdf28c64b4e5d9994692) / [Softwaretag v1.5.52](https://github.com/burckhju/trading-workspace/tree/v1.5.52) | Produktcommit und Tag identisch; damaliger Main vor der Dokumentkonsolidierung #369; Tree `e0c62e8ce82aa8bf1d4b9f247ae05f0b12675b22`; VERSION `1.5.52`. [#368](https://github.com/burckhju/trading-workspace/pull/368) ist integriert und veröffentlicht | Geprüfte Produktbasis; kein Nachweis einer Installation oder fachlichen Wirkung von v1.5.52 auf dem privaten PC |
| [Backend 44596683043](https://github.com/burckhju/trading-workspace/actions/runs/44596683043) / [Qualityjob 135816735443](https://github.com/burckhju/trading-workspace/actions/runs/44596683043/job/135816735443) | Push auf genau diesen Commit, Versuch 1, erfolgreich: Ruff, Black, mypy für 670 Quelldateien, Migration bis `20261118_0060`, **6.287 Tests, 1 Warnung; 90,05 % Coverage bei 85-%-Gate**. Vorher getrennt: 90 Installer-/Recoverytests und 88 Tests für gespeicherte Originale, Datumssemantik, Reparse und Kalender | Run-/Job-/Stepdaten und Abschlusslogs einschließlich tatsächlichem Checkout direkt gelesen. Die 90 und 88 wiederholten Teilfälle nicht zur Gesamttestzahl addieren. Die Starlette-/AnyIO-DeprecationWarning bleibt dokumentiert |
| [Produktionsimage 135816735246](https://github.com/burckhju/trading-workspace/actions/runs/44596683043/job/135816735246), [Docker-/PostgreSQL-Recovery und Renderer 135816734922](https://github.com/burckhju/trading-workspace/actions/runs/44596683043/job/135816734922) | Beide Jobs erfolgreich, Checkout und relevante Logs direkt gelesen: Produktionsbuild aus restriktiven Quelldateien, Nicht-Root-Imports, Frankfurt-Route und Migration bis 0060; tatsächliche synthetische Legacy-Migration, Recovery, Daten-/Schema-/Imageerhalt und Renderer-Sandbox | Synthetischer CI-Betrieb ersetzt weder private Bestandsprüfung noch PC-Wiederherstellungsabnahme |
| [Frontend 44596682863 / Qualityjob 135816732688](https://github.com/burckhju/trading-workspace/actions/runs/44596682863/job/135816732688) | Versuch 1, erfolgreich: **205 Dateien / 2.713 Tests**, TypeScript, ESLint, Prettier und Produktionsbuild; Checkout und Abschlusslog gelesen. Coverage: Statements/Lines 96,81 %, Branches 91,16 %, Functions 92,81 % | Automatisierte Tests ersetzen keine menschliche fachliche/assistive Bedienabnahme; nicht blockierende Build-/Infrastrukturwarnungen bleiben in den Logs sichtbar |
| [End-to-End 44596682853](https://github.com/burckhju/trading-workspace/actions/runs/44596682853) / [Smoke 135816732978](https://github.com/burckhju/trading-workspace/actions/runs/44596682853/job/135816732978) | Alle vier Jobs erfolgreich. Smoke: **211 vorgesehen, 206 bestanden, fünf beabsichtigte Skips**. Die fünf Guardquellen am exakten Main und die separaten Abschlusslogs wurden gelesen | Die fünf Ownerfälle benötigen eigene isolierte Stacks. Die zusätzlich übersprungenen Schritte zur Erfassung/Übertragung von Containerlogs sind fehlerabhängige Diagnoseschritte |
| [Report-Owner 135816732622](https://github.com/burckhju/trading-workspace/actions/runs/44596682853/job/135816732622), [Journal/Evidence-Owner 135816733249](https://github.com/burckhju/trading-workspace/actions/runs/44596682853/job/135816733249), [Candidate-Owner 135816732897](https://github.com/burckhju/trading-workspace/actions/runs/44596682853/job/135816732897) | Die fünf im allgemeinen Smoke ausgesparten Fälle sind separat bestanden: zwei Reportreisen auf jeweils frischem Stack, zwei Journal/Evidence-Reisen und eine Candidate-A–B–A-Reise. Zusätzlich 91 Journal- sowie 153 kombinierte Governance-/Journal-Contracttests | Native Owner-/PostgreSQL-Reisen und Browserfälle mit abgefangenem HTTP bleiben unterschieden. Contracttest-Teilmengen nicht zu einer neuen Gesamttestzahl addieren; kein privater Liveprovider-End-to-End-Nachweis |
| [Publisher 44601501673](https://github.com/burckhju/trading-workspace/actions/runs/44601501673), [Guards 135833826122](https://github.com/burckhju/trading-workspace/actions/runs/44601501673/job/135833826122), [Tagjob 135833895862](https://github.com/burckhju/trading-workspace/actions/runs/44601501673/job/135833895862) | Versuch 1 erfolgreich; neun Guards bestanden. Tagjoblog: `Published v1.5.52 at fully tested main c7db441de36297a98d47cdf28c64b4e5d9994692.` am **19.11.2026, 20:45:01 Uhr MEZ** (19:45:01.225 UTC) | Tag ist veröffentlicht. Der Tagjob prüft Main, VERSION und erfolgreiche Workflows über die GitHub-API. Ein Softwaretag ist kein PC-Installationsnachweis; ein separater GitHub-„Latest Release“-Datensatz ist nicht die maßgebliche aktuelle Tagreferenz |
| [PR #367](https://github.com/burckhju/trading-workspace/pull/367), datierter Betriebsnachtrag vom 19.11.2026 | Nutzer-Rückmeldungen zu Installation von v1.5.51, Aktivierung und abgeschlossenem V2-Zyklus; öffentliche aggregierte Betriebsevidenz | Historischer Installationsstand; aktueller v1.5.52-Readback unten. Keine eigene PC-Ausführung dieser Prüfung; sechs Datenwarnungen sind keine sechs fachlichen Fristauslöser |
| [Integrierter PR #368](https://github.com/burckhju/trading-workspace/pull/368) / [Releasevertrag v1.5.52](../releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md) | Produktdatumsrollen, erneute Auswertung gespeicherter Originale und begrenzter lokaler XSTU-2026-Originalkalenderimport sind jetzt Bestandteil des geprüften Main und veröffentlichten Tags. Der öffentliche Bericht enthält außerdem den neueren privaten Ursachenbefund für vier offene Positionen auf dem damaligen v1.5.51-Stand | Technischer Fix und Auslieferung sind belegt. Neuer v1.5.52-Readback und getrennte Datumsrollen am Verbraucher sind unten nachgewiesen; vollständige Originalupgrade-/Importabnahme bleibt offen. Die vier historischen Positionen werden nicht allein anhand der Anzahl mit dem neuen Viererbestand gleichgesetzt |

**Dokument-Main nach Integration von #369:** `6c0f9160b91bee4c6c45849c9c47d4c4b5a3bf56`, 20.11.2026, 15:01:45 Uhr MEZ. Der lokale Diff zur Produktbasis umfasst ausschließlich README, ROADMAP, TRACEABILITY, Katalog und diesen Backlog; VERSION und Anwendungscode sind unverändert. #369 liefert keinen zusätzlichen PC-Readback. Die folgenden älteren CI-Belege behalten ihre exakten Commitbindungen.

### Historische CI des bisherigen Dokumentations-Heads #369

Der bisherige Docs-Head `84451218e525673de8728e075758b14082329e8d` war in allen vier Workflows erfolgreich. Die Checkoutlogs binden diese Prüfung ausdrücklich an den **Testmerge `483e468a81dfb002ddfee3b13da3c058d5c5d32b` gegen die damalige Base `254f0bbd52ab42e0120d381e915dc96c1118796c`**. Dieser Nachweis wird weder dem fortgeschriebenen Dokumentations-Head noch der neuen Main-Basis zugerechnet.

| Historischer PR-Lauf | Tatsächlicher Abschluss | Geltungsgrenze |
|---|---|---|
| [Backend 44592507712](https://github.com/burckhju/trading-workspace/actions/runs/44592507712) | Drei Jobs erfolgreich; 6.242 Tests, eine Warnung, 89,90 % Coverage; vorher 90 wiederholte Installer-/Recoverytests | Alter Docs-Head und benannter Testmerge |
| [Frontend 44592507853](https://github.com/burckhju/trading-workspace/actions/runs/44592507853) | 205 Dateien / 2.713 Tests; Qualityjob erfolgreich | Alter Docs-Head und benannter Testmerge |
| [End-to-End 44592507732](https://github.com/burckhju/trading-workspace/actions/runs/44592507732) | Alle vier Jobs erfolgreich; 206 Smokefälle, fünf beabsichtigte Skips und dieselben fünf separat bestandenen Ownerreisen | Kein Nachweis für einen späteren Docs-Head oder eine geänderte Base |
| [Versionsprüfung 44592508047](https://github.com/burckhju/trading-workspace/actions/runs/44592508047) | Neun Guards erfolgreich; eigentlicher Tagjob `135802048239` bei diesem PR-Lauf absichtlich übersprungen | Der Dokumentations-PR hat keinen Softwaretag veröffentlicht |

Alle neun tatsächlich ausgeführten Jobs dieses alten PR-Standes waren erfolgreich; ihre Checkout- und Abschlusslogs wurden gelesen. Der erwartungsgemäß übersprungene Veröffentlichungsjob ist kein fehlgeschlagener Test und kein Auslieferungsnachweis.

**In der übernommenen #369-Konsolidierung tatsächlich geprüft:** ursprüngliche 63 Inhaltsziel-Vorkommen gegen alle vorhandenen Teilfähigkeiten; tatsächliche Services/Domainverarbeitung, Persistenz, API-/UI-Consumer und relevante Testassertionen; historische ADR-/Abnahme-/Releaseunterlagen; PR-Diffs und Main-/Tagidentität. Die Fortschreibung vom 20.11.2026 ergänzt den integrierten #368, die oben direkt gelesenen aktuellen Main-CI-Logs sowie den gesondert gebundenen historischen Dokumentations-PR-Nachweis. Der damalige #369-Dokumentdiff wurde erfolgreich geprüft: fünf Dokumente, 76 Teilfähigkeiten, 63 unverändert zugeordnete Inhaltsziele, 142 Markdown-Tabellen und 726 lokale Linkvorkommen einschließlich 374 Ankerverweisen; UTF-8/LF, balancierte Details-Blöcke, `git diff --check`, unverändertes Archiv und historischer Traceabilitybestand. Der neue dritte Main-Betriebsnachtrag ist wortgleich erhalten, beide Dokumentkonflikte sind aufgelöst. Gegenüber dem damaligen Produkt-Main waren ausschließlich die fünf Planungs-/Verweisdokumente geändert. Diese Zählungen gelten für #369 und werden nicht ungeprüft auf den jetzigen Datenversorgungsnachtrag übertragen.

**Im damaligen Dokumentationsabgleich vom 20.11. nicht lokal oder am PC neu ausgeführt:** vollständige Backend-/Frontend-/Browserprüfungen, Datenbankmigration, PC-Installation, Reparse gespeicherter Originale, Kalenderimport, Providerabruf, Modellaktivierung oder Zustellung. Der Dokumentdiff verändert keine Anwendung. Die oben gelesenen Läufe sind bereits ausgeführte CI-Nachweise, keine Behauptung eines eigenen lokalen Neulaufs. Reguläre CI des fortgeschriebenen Dokumentations-Heads wird im bestehenden PR separat an dessen tatsächlichen Head/Testmerge gebunden. CI-Artefaktarchive wurden für diese Fortschreibung nicht heruntergeladen.

**Aktuelle Zugriffsgrenze:** Gesamtread vom 22.11., P02- und
Quellenkandidatenreads vom 24.11. liegen vor und sind ausgewertet. Heutige
Bindungen, Auswahlkandidaten und Produktbelege der drei übrigen archivierten
Positionen sind damit zugänglich. Interaktiver PC-/DB-Zugang, frühere
P02-Rohpreisfelder und vollständige Zwischenbewertungen fehlen weiterhin.
Der ausdrücklich freigegebene P01-KID-Read ist abgeschlossen; das Original
enthält die Preiseinheit nicht. Der zusätzliche offizielle gettex-Regeltext
ist gelesen, sein direkter PDF-Download antwortete hier mit HTTP 403.
Der ergänzende Product-Anschluss ist inzwischen implementiert; drei
Regel-PDFs und ihre Quellenqualifikation fehlen weiterhin. Der
[nächste Auftrag](#naechster-schnitt) schließt
den konkreten P01-Listing-/Einheiten-/Mapping-/Verbraucherrest; kein erneuter
unveränderter Gesamt-, P02- oder Kandidatenexport und keine erneute KID-Freigabe.

<a id="betriebsnachweis"></a>
### Zeitliche Einordnung der Betriebsevidenz

| Zeitpunkt / Quelle | Belegter Umfang | Heutige Bedeutung |
|---|---|---|
| Frühere 1.5.4/1.5.5-/1.5.47-Vorbereitung und 1.5.49-Installationsmeldungen | Historischer Software-/Installationsstand; V1-Lauf mit Datenproblemen | Erhaltene Historie, keine aktuelle Updateanweisung |
| 19.11.2026, frühe v1.5.50-Versuche, [#366](https://github.com/burckhju/trading-workspace/pull/366) / [#367](https://github.com/burckhju/trading-workspace/pull/367) | Prepare scheiterte vor Apply; zuerst Pakettimeout, dann leere SQLAlchemy-Kandidatenliste; alte vier Dienste gesund | Ursache der ursprünglichen Indexantwort bleibt unbelegt; dieser konkrete Installationsblocker wurde durch den später beobachteten Ersatzrelease überwunden |
| 19.11.2026, PC-Rückmeldung in #367 | v1.5.51 auf `254f0bbd…`, vier Dienste healthy, Readiness 200, Alembic 0060; V2 zentral aktiviert, Review-Zustellung deaktiviert | Installation/Aktivierung dieses Stands als abgegrenzte Teilaufgabe abgeschlossen; historischer PC-Stand, inzwischen durch den datierten v1.5.52-Readback ergänzt; kein allgemeiner Fachabnahmebeleg |
| 19.11.2026, Zyklus 18:06:42–18:07:17 Uhr MEZ; Audit 18:13:12 Uhr MEZ, #367 | 35,307 Sekunden, `enabled=true`, `running=true`, `last_error=null`; Entry und Deadline je 6 bewertet / 6 aktive Datenprobleme / 0 technische Positionsfehler | Tatsächlicher V2-Runnerbetrieb auf v1.5.51 belegt. Die Frist-Hinweise sind Datenwarnungen `POSITION_DATA_UNAVAILABLE`; fachliche Abdeckung bleibt offen |
| Neuere Ursachenbeschreibung in #368, erstmals veröffentlicht am 19.11.2026 ab 19:31:56 Uhr MEZ | Vollständiger lesender Readback für 4 damals offene Positionen auf v1.5.51; jeweils Einstands-/Fristdatenprobleme. Produktende/Zahlungstag falsch verglichen, Kalenderfehler HTTP 403; weitere Beleg-/Zuordnungslücken benannt | Historischer privater Referenzbestand und Ursachenbefund. Dessen exakte Einzelzeilen und Rohdiagnosezeitpunkt fehlen hier. Vier offene Positionen und frühere sechs Laufpositionen sind verschiedene Zeit-/Mengenschnitte; daraus folgt keine heutige Bestandszahl |
| 19.11.2026, Integration von #368 und Veröffentlichung um 20:45:01 Uhr MEZ | Fix in Main `c7db441de36297a98d47cdf28c64b4e5d9994692`, aktuelle CI erfolgreich, Tag v1.5.52 veröffentlicht | Softwareintegration/-auslieferung abgeschlossen. **Inzwischen durch den PC-Readback vom 22.11. ergänzt:** Installation und regulärer V2-Zyklus belegt, am 22.11. damals 0/4 vollständig auswertbar; vollständiger Original-Reparse/Kalenderimport bleibt offen. Kein Betriebsnachweis aus Main-CI abgeleitet |
| 22.11.2026, Readback 20:50:41–20:50:45 Uhr MEZ, letzter Zyklus 20:44:54–20:45:35 Uhr MEZ | [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier gesunde laufende Dienste, 30/30 GETs, vier offene Positionen; beide V2-Pfade je vier Datenprobleme und null technische Positionsfehler | Tatsächliche Installation und vollständige Verbraucherdiagnose belegt. 4/4 Ausführungswährungen vorhanden; drei Routen fehlen, eine ohne Bid; historische/Produkt-/Fristlücken bleiben. Keine Gesamtfachabnahme. |
| 24.11.2026, enger Read 18:23:08–18:23:10 Uhr MEZ; gespeicherte P02-Bewertung 18:21:41 Uhr MEZ | [P02-Nachweis](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060, vier gesunde Dienste; archivierter `JPMORGAN_SNAPSHOT_TIMEOUT`; neuer Bid und `BELOW_ENTRY`, Empfangsalter 10,456 s | Enger Diagnoseauftrag erfüllt; Statusgap ohne neue V2-Preisunterbrechung. Originalzeit/-status weiter unqualifiziert. Keine aktuelle Gesamtinventur, Frist-, B06- oder Verlaufsabnahme. Kein Zusammenhang mit noch nicht installiertem PR-370-Fix behauptet. |
| 24.11.2026, Quellenkandidatenread 20:33:55–20:33:58 Uhr MEZ | [Gebundener Readback](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md): dieselbe v1.5.54-Installation, drei offene Archivkandidaten, keine Mappingrouten/Auswahlkandidaten; erfolgreiche KID-Beschaffung mit fehlenden Einheiten und zusätzlichem P04-Konflikt | Einmalige Diagnosefrage beantwortet; keine aktuelle Gesamtinventur und keine neue fachliche V2-Abdeckung. |
| 24.11.2026, externe Gesamtdatei 20:40:50–20:41:25 Uhr MEZ; Offlineparser 20:43:22–20:43:35 Uhr | [Gettex-Probe](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md#4-offizieller-gettex-dateidienst-neue-praktische-probe): vollständige Originaldatei/CRC; positiver P01-EUR/MUND-Bid, gemeinsame Quellenzeit 18:57:23.707737 Uhr | Historische konkrete Quellendeckung, noch kein PC-Listing/Mapping oder aktueller Verbraucherpreis; P03/P04 fehlen nur im untersuchten Fenster. |
| 24.11.2026, P01-Original gespeichert 21:07:13 Uhr MEZ | [Freigegebene KID-Prüfung](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md#p01-originaleinheit): HTTP 200, drei Seiten, bytegleich zur PC-Revision, Einheit fehlt im Original; offizielle gettex-Konvention als ergänzender Belegweg gelesen | Eindeutige Ursachenklärung; kein Parserfix, kein neuer PC-Entscheid. Zusätzlicher aktueller Listing-Einheitenbeleg ist noch nicht integriert. |

<a id="pr-abgleich"></a>
### Aktuelle PRs gegenüber Main

Der direkte Abruf der offenen Pull Requests am **20.11.2026** zeigt zehn offene PRs: #369 und die neun unveränderten älteren Heads unten. **#368 ist gemergt und in v1.5.52 veröffentlicht**; er gehört zum integrierten Nachweis oben und nicht mehr in die offene Liste. Die offenen Änderungen sind nicht als integrierter Umfang des geprüften Main zu zählen. Historische PR-CI bleibt an den jeweiligen Head und tatsächlichen Testmerge gebunden.

| PR / Head | Tatsächlicher Scope gegenüber Main | Konsequenz für diesen Backlog |
|---|---|---|
| [#369](https://github.com/burckhju/trading-workspace/pull/369), bisheriger Docs-Head `84451218e525673de8728e075758b14082329e8d` | Nachweis- und Statuskonsolidierung in fünf Planungsdokumenten, ursprünglich gegen `254f0bbd…`; frühere CI vollständig erfolgreich auf Testmerge `483e468a81dfb002ddfee3b13da3c058d5c5d32b` | Der vorliegende Dokumentationsauftrag wird gegenüber v1.5.52 fortgeschrieben. Alte grüne CI ist ausdrücklich kein Nachweis des danach entstehenden Heads oder seines neuen Testmerges; keine Produktänderung und kein Softwaretag aus diesem PR |
| [#342](https://github.com/burckhju/trading-workspace/pull/342), Draft; `5d3f017d8f65a51b26ad8aeab3ca1364eff1796c` | Fünf UX-Koordinationsdokumente auf älterer Main-Basis; eigene grüne Neuqualifikation vom 13.11.2026 | Historischer UX-Priorisierungsvorschlag, keine aktuelle gesamtproduktweite Handlungsanweisung und keine menschliche UX-Abnahme |
| [#341](https://github.com/burckhju/trading-workspace/pull/341), Draft; `52640616ed7ef0e8c91f945905ad3857ff263fed` | Lokale Forschungsquellenprüfung im Learning-Owner; eigener Backlognachtrag. Runneränderung separat über #343 integriert | Forschungscode nicht als produktive Learningfähigkeit zählen; integrierten Runner nicht nochmals als fehlend führen |
| [#335](https://github.com/burckhju/trading-workspace/pull/335), Draft; `be746bfeb1b89846a127eaa3274662c8bab0ff05` | Atomare EUR-Bestandskorrektur mit vier neuen Dateien | Kein durchgeführter privater Währungsbackfill und kein Mainbestand; vorhandene Währungs-/Performanceowner bleiben maßgeblich |
| [#315](https://github.com/burckhju/trading-workspace/pull/315), Draft; `d9d85f1af3159c4356c8773d076decbf1dc604e4` | Früher Hinweisvertragsentwurf; auf Main bereits kanonische Zusammenführung unter `docs/ui/ux-3/` | Historische Quelle des Vertrags, kein zweiter Integrationsauftrag für bereits kanonisierte Inhalte |
| [#220](https://github.com/burckhju/trading-workspace/pull/220), offen, kein Draft; `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Drei Quellenrecherchedokumente | Recherche-/Providerbefunde nicht als neue Main-Adapter-/B58- oder Betriebsabdeckung ausgeben |
| [#207](https://github.com/burckhju/trading-workspace/pull/207), Draft; `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Tatsächlicher PR-Diff enthält nur einen Hilfsworkflow, nicht den im Body beschriebenen integrierten Regelcode | Spätere eigenständige Main-Implementierungen über ihre heutigen Quellen nachweisen; #207 schließt keine vollständige Baseline |
| [#205](https://github.com/burckhju/trading-workspace/pull/205), Draft; `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Historienvorschlag und zwei Entwicklungsworkflows | Vorhandene spätere Main-Preis-/Chartpfade separat prüfen; alter Entwurf ist kein heutiger Abwesenheitsbeweis und keine historische Quellenabdeckung |
| [#197](https://github.com/burckhju/trading-workspace/pull/197), Draft; `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Forschungscollector mit begrenztem historischen Datenstichtag | Kein produktiver Feed und kein vollständiger Backtestnachweis |
| [#187](https://github.com/burckhju/trading-workspace/pull/187), Draft; `bad00a420f56994216ad1def6a580b00b0f5772f` | Rekonstruierte Hebeltrader-Regeln/Preview aus Importquellen | Keine Main-Regelfreigabe, laufende vollständige Überwachung oder Modellaktivierung daraus ableiten |

Die früher als offen genannten #204, #249, #259–#261, #263, #271, #278, #284/#285 und #297/#298 sowie nun #368 sind integriert. #90, #225 und #235 sind geschlossen, **nicht gemergt**; vorhandene spätere Lösungen werden über ihre eigenen Mainpfade belegt. Die Zuordnung wurde über PR-Metadaten und Git-Historie geprüft, nicht aus dem Wort „closed“ abgeleitet.

<a id="konfliktaufloesung"></a>
## Statusdrift und Auflösung

| Überholte Aussage | Aktuelle Einordnung |
|---|---|
| Kein vollständiger Checkout, Software 1.5.5 / PC 1.5.4 | Vollständiger Checkout und geprüfter Main/Tag v1.5.52. Letzter belegter PC-Stand weiterhin v1.5.51 aus #367; neuere historische Ursachenbeschreibung in #368. Frühere Zugriffsgrenzen bleiben historisch |
| Watchlist vollständig ungeprüft/offen | Fester persistenter 31er-Katalog ist implementiert, getestet und ausgeliefert; fachliche Abnahme und generischer Mitgliedschaftsumfang bleiben getrennt offen |
| Journal-/Materialisierungs-/Lesson-Korrekturwege noch zu implementieren oder zu integrieren | Echte persistierte Verarbeitung und native PostgreSQL-Browser-Korrekturen vorhanden. Offene Fach-/Bedienabnahme und weitere Umfänge getrennt |
| Trefferquote, Durchschnitt, Median, Profit-Faktor und Diagramme sämtlich geplant | Vier Kennzahlen und SELL-Beitragsgrafik ausgeliefert; noch fehlende weitere Anforderungen benötigen eigenen Vertrag/Nachweis |
| B07-/GOOD-Referenz und Kandidaten-Aktivierung/Rückkehr offen | Konkrete GOOD-Kandidatenreise technisch belegt; andere Modellfamilien bleiben eigenständig |
| Marktmodell/Relative Strength nur Modellinfrastruktur | Feste versionierte Berechnungen und echte Candidate-Consumer vorhanden; separate Governance-Entscheidung offen |
| #204/#249/#271 sowie v1.5.30/31 noch als aktueller Merge-/Releaseauftrag | Integriert bzw. veröffentlicht und im geprüften Produktstand enthalten; Vorbereitungstexte historisch |
| V2 noch nicht installiert / noch kein Zyklus | Durch spätere #367-Rückmeldung für v1.5.51 überholt. Technischer Betrieb dieses Stands belegt, Datenabdeckung nicht; kein Nachweis einer späteren Installation allein aus v1.5.52 abgeleitet |
| Sechs Produktfrist-Hinweise bedeuten sechs erkannte Fristen; vier offene Positionen sind der heutige Bestand | Der datierte v1.5.51-Lauf meldet sechs Datenwarnungen, null technische Fehler; der spätere damalige Readback betrifft vier offene Positionen. Fehlende Belege sind keine fachlichen Fristauslöser; heutiger Bestand und aktuelle Reasons unbekannt |
| #368 ist noch offen; Integration und Veröffentlichung von v1.5.52 fehlen | #368 ist gemergt, durch Main-CI qualifiziert und als v1.5.52 veröffentlicht. Diese technischen Arbeitsschritte sind abgeschlossen; PC-Anwendung und reale Wirkung bleiben gesondert nachzuweisen |
| Software v1.5.52 schließt die vier privaten Datenprobleme automatisch | Fix, Reparse-/Importfähigkeit und Veröffentlichung sind vorhanden. Erst datierter Readback des tatsächlich installierten Stands und der ausgeführten Ownerhandlungen belegt veränderte Datenabdeckung |
| Grüne CI des Docs-Heads `84451218…` gilt für dessen spätere Fortschreibung | Historischer Nachweis ausschließlich für Testmerge `483e468…` gegen `254f0bbd…`; ein neuer Docs-Head benötigt seine eigenen Prüfungen |
| V1-Nicht-Scope, technische Auslieferung oder Softwaretag beendet ursprünglichen Gesamtanspruch | Originalumfang bleibt offen, bis vollständig erfüllt oder ausdrücklich mit datierter Produktentscheidung geändert. Fehlende fachliche Abnahme bleibt bei abgeschlossener Implementierung/Qualifikation/Auslieferung sichtbar |

<a id="abnahmematrix"></a>
## Abnahmematrix – maßgebliche Teilfähigkeiten

Die Felder „Soll“ und „Nicht-Soll“ sind die vor einer Umsetzung zu prüfenden Abnahmegrenzen. Fachliche Entscheidungen fehlen nur für die jeweils betroffenen Reste; unabhängige freigegebene Arbeit bleibt möglich. „Abnahme nicht verifiziert“ entwertet keinen früheren Beleg, sondern begrenzt diese Prüfung. Bereichsziffern beziehen sich auf den Katalog. Lieferzielbuchstaben beziehen sich auf die Roadmap.

### PB-001

[Fachliche Domain Map und Architektur](#pb-001-domain)

<a id="pb-001-domain"></a>
<details>
<summary>PB-001 — Fachliche Domain Map und Architektur</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Architektur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Accepted (historische Dokumentbaseline; Zuständigkeitsnachweis bestätigt) |
| Abgeschlossener Teilumfang | Domain-/Ownergrundlage und konkrete getrennte Handoffs sind vorhanden; kein Architektur-Neubau. |
| Soll / Nicht-Soll | **Soll:** Kernobjekte, Schichten, Beziehungen und ein schreibender Owner je Objekt sind nachvollziehbar. **Nicht-Soll:** Keine Neuaufteilung der Pakete durch die acht Planungssichten. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung (begrenzter Dokumentabgleich). |
| Implementierung / Consumer | [docs/domain/DOMAIN_MAP.md](../../docs/domain/DOMAIN_MAP.md), [docs/foundation/ARCHITECTURE.md](../../docs/foundation/ARCHITECTURE.md) und tatsächliche Owner in `market`, `analysis`, `candidate`, `trade_plan`, `product_selection`, `trade_position` trennen Referenzfakten, Plan, Evaluation und tatsächliche Ausführung. Spätere ETF-/PriceBinding-/Währungsnachträge präzisieren die alte STOCK-Baseline. |
| Test / Commit | [tests/integration/backend/test_candidate_trade_plan_handoff.py](../../tests/integration/backend/test_candidate_trade_plan_handoff.py), [test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py), [test_product_selection_trade_position_handoff.py](../../tests/integration/backend/test_product_selection_trade_position_handoff.py) prüfen Ownerübergaben mit konkreten Identitäten. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | DOMAIN_MAP v1.0 Approved/03.08.2026 und ARCHITECTURE v1.1 Approved bleiben historische Fachbaseline, kein neuer Gesamtentscheid. |
| Software-Auslieferung | Dokumentbaseline im aktuellen Repository; keine eigene Softwarefunktion. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Alte STOCK-only-/Ablaufformulierungen gegenüber ETF- und expliziten Handoffs noch nicht dokumentweit abgeglichen → Leser erkennt den jeweils geltenden Vertragsumfang → bestehende Foundation-/Domain-Dokumentation → spätere freigegebene Feature-/ADR-Nachträge → jede kollidierende Formulierung hat Versions-/Datumsbezug und verweist auf den maßgeblichen Vertrag; keine Änderung der Owner. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-002

[Durchgängiger Prozess und Übergaben](#pb-002-process)

<a id="pb-002-process"></a>
<details>
<summary>PB-002 — Durchgängiger Prozess und Übergaben</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen; übergreifend M2–M9. Bereich/Querschnitt: Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: FT-005–FT-013. Lieferziel: B, D. |
| Arbeitsstatus | Accepted (historische Prozessbaseline); Business Review (gesamte aktuelle Nutzerreise) |
| Abgeschlossener Teilumfang | Technische Handoffs Candidate→Plan→Selection→Kauf und realer Vollverkauf→FT-011-Eignung sind implementiert; nicht erneut planen. |
| Soll / Nicht-Soll | **Soll:** Explizite Übergaben, konkrete historische Versionen und Korrekturen verbinden den Gesamtprozess. **Nicht-Soll:** Kein automatischer Handels- oder Interpretations-Orchestrator; kein Journalentwurf-Gate durch Performance. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [docs/domain/TRADING_PROCESS_MODEL.md](../../docs/domain/TRADING_PROCESS_MODEL.md); tatsächliche Services erzeugen getrennte CandidateEvaluation, immutable TradePlanVersion, ProductSelection, ExecutionRecord, Position und FT-011-Eignung. Die Journal-/Evidence-/Lesson-Strecke ist in PB-018/019 mit eigenen Verarbeitungs-, Consumer- und Testnachweisen belegt; die menschliche Gesamtprozessabnahme bleibt offen. |
| Test / Commit | [tests/integration/backend/test_candidate_trade_plan_handoff.py](../../tests/integration/backend/test_candidate_trade_plan_handoff.py), [test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py), [test_product_selection_trade_position_handoff.py](../../tests/integration/backend/test_product_selection_trade_position_handoff.py); [tests/e2e/ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts), [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | TRADING_PROCESS_MODEL v1.0 Approved/03.08.2026 bleibt erhalten; keine aktuelle menschliche Gesamtabnahme. |
| Software-Auslieferung | Bestehende Übergaben sind in v1.5.52 enthalten; spezifische Erweiterungen mit ihren Releasebelegen. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Eine datierte menschliche Gesamtabnahme der heutigen Abschluss-/Lernreise fehlt → Benutzer kann Abschluss, Korrektur, Journal und Lesson ohne Herkunftsverlust nachvollziehen → vorhandene FT-009/010/011/012-Consumer → synthetischer Referenztrade und fachliche Prüferrolle → dokumentierte Abnahme der vollständigen Nutzerreise einschließlich historischer Korrektur; Fehler bleiben präzise beim jeweiligen PB-018/019-Teilscope. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-003

[Benutzer- und Workspace-Grenze](#pb-003-workspace)

<a id="pb-003-workspace"></a>
<details>
<summary>PB-003 — Benutzer- und Workspace-Grenze</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Architektur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001; alle workspacegebundenen Consumer. Lieferziel: A–D. |
| Arbeitsstatus | Accepted (historischer PB-003-Beleg; technische Identitätsgrenzen vorhanden) |
| Abgeschlossener Teilumfang | Unsichtbarer Workspace und Owner-Isolation implementiert; keine neue Workspacearchitektur erforderlich. |
| Soll / Nicht-Soll | **Soll:** Bestehender unsichtbarer Workspace und Identitätsgrenzen bleiben erhalten. **Nicht-Soll:** Keine Multiuser-Erweiterung; Audit-Actor ist kein Authentifizierungsbeleg. |
| Befundklasse / Lückenart | Belegbar abgeschlossener enger Teilumfang; kein pauschaler Meilensteinabschluss. **Art der Restarbeit:** Kein eigenständiger offener Implementierungsrest im bestätigten Scope. |
| Implementierung / Consumer | [backend/app/core/identity/context.py](../../backend/app/core/identity/context.py), [backend/app/features/market/persistence/models.py](../../backend/app/features/market/persistence/models.py) und explizite `workspace_id`-Abfragen in den Fachservices erhalten unsichtbaren Workspace; er ist kein Multiuser-Authentifizierungsnachweis. |
| Test / Commit | [tests/integration/backend/database/test_chart_watchlist_postgres.py](../../tests/integration/backend/database/test_chart_watchlist_postgres.py) prüft fremde Workspace-/Ownerbindungen; Handoff- und REST-Tests der Fachfeatures. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | Historischer Accepted-Vermerk bleibt; kein Multiuser-/Auth-Umfang nachträglich angenommen. |
| Software-Auslieferung | Bestehender gemeinsamer Identitätsvertrag im veröffentlichten v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Kein eigenständiger nächster Auftrag für die historische Workspacebaseline. Neue Consumer müssen die vorhandenen Workspace-/Owner-Negativtests erhalten; Abschluss jeder solchen Erweiterung ist ein versionsgebundener Negativtest gegen fremde Identität. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-004

[Repositorystruktur](#pb-004-repository) · [Dokumentation und Spezifikationsführung](#pb-004-documentation) · [Terminologie](#pb-004-terminology) · [Entwicklungsstandards und Governance-Baselines](#pb-004-standards) · [Projektweite Spezifikationen](#pb-004-specifications)

<a id="pb-004-repository"></a>
<details>
<summary>PB-004 — Repositorystruktur</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Repositorystruktur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Technical Review — vollständiger Checkout und Struktur-/Diffprüfung abgeschlossen; keine neue Produktänderung. |
| Abgeschlossener Teilumfang | Der alte Zugriffsblocker ist geschlossen: vollständiger Git-Checkout, identischer Main-/Tagbezug und unveränderte Archivbaseline. Der aktuelle Diff beschränkt sich auf die fünf Planungs-/Verweisdokumente. |
| Soll / Nicht-Soll | **Soll:** Quell- und Dokumentstruktur sind nachvollziehbar, Aufgabenänderungen isoliert. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Befundklasse / Lückenart | Belegbar abgeschlossener enger Teilumfang; kein pauschaler Meilensteinabschluss. **Art der Restarbeit:** Kein offener Rest im geprüften Struktur-/Checkoutumfang. |
| Implementierung / Consumer | Vollständiger Git-Checkout mit backend/frontend/docs/tests/scripts/docker/.github; geprüfter Produkt-Main und Tag v1.5.52 identisch auf c7db441de36297a98d47cdf28c64b4e5d9994692. Der frühere Main-/Tagbezug v1.5.51/254f0bbd… bleibt als datierter Erstprüfungsstand erhalten. Keine anwendbare AGENTS.md in der geprüften Repositorystruktur gefunden. |
| Test / Commit | Git-Objekt-/Statusprüfung; Originalarchivblob `919ed7570580b1d883a409f864ed15747fbfda3e`; vorhandene CI-Workflows und Lockdatei. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | Repositorystruktur ist technisch nachgewiesen; keine neue menschliche Foundation-Gesamtabnahme behauptet. |
| Software-Auslieferung | Vollständiger Quellbaum des veröffentlichten Tags liegt vor. |
| Betriebsnachweis | Nicht anwendbar: Prüf-/Repositorygrundlage, keine PC-Nutzerfunktion. |
| Restarbeit / nächste Abhängigkeit | Kein offener Struktur-/Checkoutrest dieses Auftrags. Künftige Änderungen verwenden denselben dokumentierten Repositoryaufbau; ihr Abschluss ist durch begrenzten Diff und vorhandene Qualitätsgates zu belegen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-documentation"></a>
<details>
<summary>PB-004 — Dokumentation und Spezifikationsführung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Dokumentation; M11: Dokumentationsreview. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Technical Review — dieser Nachweis-/Statusabgleich abgeschlossen; Business Review — weitergehende fachliche Gesamtabnahmen. |
| Abgeschlossener Teilumfang | Alle 63 ursprünglichen Inhaltsziel-Vorkommen und 76 bestehenden Teilfähigkeiten konsolidiert; am 20.11.2026 mit dem Main-Delta auf v1.5.52 fortgeschrieben. README-/Backlogkonflikte inhaltlich aufgelöst, neuer Main-Betriebsnachtrag erhalten, aktuelle Statusquelle und genau ein Folgeauftrag verbunden. Archiv und historische Freigaben erhalten; Format-/Link-/Konsistenzprüfung im Nachweisregister. |
| Soll / Nicht-Soll | **Soll:** Eine aktuelle Statusquelle; Baseline, Entscheidungen und Nachweise sind verknüpft. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Prüfung der verbleibenden Produktanforderungen; Dokumentationsauftrag abgeschlossen. |
| Implementierung / Consumer | README, ROADMAP, PRODUCT_BACKLOG, Katalog und TRACEABILITY verwenden die bestehende Single-Status-Source-Struktur. Durch spätere Nachweise überholte Next-Step-/Release-/Checkoutaussagen sind korrigiert oder ausdrücklich historisiert. Die Fortschreibung trennt veröffentlichtes v1.5.52 von zuletzt belegtem v1.5.51-PC-Betrieb. |
| Test / Commit | Originalzuordnung, bestehende PB-/FT-/M-Kennungen, 76 eindeutige Teilfähigkeiten, lokale Pfade/Anker, Tabellen, UTF-8/LF, unverändertes Archiv und historischer Traceabilityblock sowie git diff --check geprüft. Keine Produktdatei geändert. |
| Fachliche Abnahme | Historische Freigaben bleiben historisch; kein automatisches neues Approved für das Gesamtziel. |
| Software-Auslieferung | Planungsdokumente im Repository; dieser Dokumentationsdiff separat nachweisbar. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Fachliche Gesamtakzeptanz der weitergehenden ursprünglichen Ziele ist nicht durch Dokumentkonsolidierung erteilt → fachlich angenommener Zielumfang → bestehende Product-/Domain-Owner → die je Teilfähigkeit präzisierten Entscheidungen und Nachweise → datierte Annahme oder ausdrücklich dokumentierte Umfangsänderung je betroffenem Rest. Dieser Statusabgleich selbst ist abgeschlossen; keine zweite aktuelle Aufgabenliste. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-terminology"></a>
<details>
<summary>PB-004 — Terminologie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Terminologie. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Business Review (vorhandene Terminologie; Freigabe offen) |
| Abgeschlossener Teilumfang | Das Glossar fehlt nicht; bisheriger Rest „GLOSSARY-Inhalt nicht eigenständig verifiziert“ ist durch Lesen abgearbeitet. |
| Soll / Nicht-Soll | **Soll:** Begriffe trennen Fakten, Plan, Bewertung und Beobachtung. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Entscheidung/Prüfung. |
| Implementierung / Consumer | [docs/foundation/GLOSSARY.md](../../docs/foundation/GLOSSARY.md) v1.0 ist vorhanden und trägt Review. Sie trennt TradePlan/Trade/Position/Execution/Observation/Review/ModelVersion; fachliche Ownerverträge konkretisieren diese Begriffe. |
| Test / Commit | GLOSSARY-Volltext/Metadaten und verwendete Domainmodelle geprüft; keine ausführbare Fachfreigabe. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | GLOSSARY bleibt explizit Review; keine dokumentierte Freigabe nachgetragen. |
| Software-Auslieferung | Terminologiedokument vorhanden im Main; keine eigene Softwareauslieferung. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Glossar bleibt Review und später ergänzte Begriffe sind nicht vollständig abgestimmt → gleiche Begriffe für Ausführungsfakt, Plan, indikative Bewertung und Beobachtung → bestehendes GLOSSARY/Domainverträge → fachlicher Ownerreview der relevanten neuen Begriffe → datierter dokumentierter Begriffs-/Freigabeentscheid mit Verweisen; keine stillen fachlichen Umdeutungen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-standards"></a>
<details>
<summary>PB-004 — Entwicklungsstandards und Governance-Baselines</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Entwicklungsstandards. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Business Review (Standards vorhanden und Gates umgesetzt; formale Freigaben offen) |
| Abgeschlossener Teilumfang | Entwicklungs-/Prüfprozess ist dokumentiert und tatsächlich durch CI unterstützt; kein Neuaufbau erforderlich. |
| Soll / Nicht-Soll | **Soll:** Definition of Ready, getrennte Prüf-/Abnahmeschritte und Modellfreigaben sind verbindlich. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Entscheidung. |
| Implementierung / Consumer | [docs/technical/FEATURE_LIFECYCLE.md](../../docs/technical/FEATURE_LIFECYCLE.md) v1.1 definiert Rollen, DoR, DoD, technische/fachliche Prüfung, Abnahme, Auslieferung, Beobachtung; Status Review und Freigegeben durch/Freigabedatum „noch offen“. CODING_STANDARDS/DEVELOPMENT_GUIDE und vorhandene Workflows operationalisieren technische Gates. |
| Test / Commit | Workflow-/Dokumentquellen und Reviewmetadaten geprüft; erfolgreiche Main-CI belegt angewandte technische Gates, nicht Fachfreigabe der Standards. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | REQUIREMENTS v0.2, MODEL_BOOK v0.2 und FEATURE_LIFECYCLE v1.1 tragen weiterhin Review; keine Freigabe behaupten. |
| Software-Auslieferung | Dokumente/Gates in v1.5.52 enthalten. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Formale Freigaben der drei Review-Baselines fehlen → klare Verantwortung und akzeptierte DoR/DoD/Modellgrenzen → bestehende Foundation-/Technical-Dokumente → Product Owner/Modellverantwortlicher bewertet vorhandene Inhalte → je Dokument datierter Freigabeentscheid oder konkret benannte Änderungsanforderungen; grüne CI ersetzt ihn nicht. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-specifications"></a>
<details>
<summary>PB-004 — Projektweite Spezifikationen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: bestehende FT-001–FT-013 und spätere belegte Erweiterungen. Lieferziel: A–D. |
| Arbeitsstatus | Analysis (vorhandene Featureverträge; ursprüngliche Restumfänge noch zu spezifizieren) |
| Abgeschlossener Teilumfang | Implementierte FT-Verträge werden nicht erneut zur Spezifikation eingeplant. |
| Soll / Nicht-Soll | **Soll:** Originalziele haben testbare Verträge mit Soll, Nicht-Soll und Entscheidungskette. **Nicht-Soll:** Ein enger V1-Vertrag entfernt nicht automatisch den weiteren Roadmapanspruch. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Entscheidung/Spezifikation. |
| Implementierung / Consumer | FT-001–013 und spätere FT-019/020-Verträge/ADRs bestehen; FT-007-Versionierung, FT-008-Eligibility und FT-010-Ausführungen sind tatsächlich implementiert. Generischer Scanner, Marktbreite, Produktscore und Produktwechsel haben keine vollständige freigegebene Gesamtbeschreibung. |
| Test / Commit | Gelesene Feature-/ADR-/Service-/Testketten; reine Verzeichnisexistenz nicht als vollständige Spezifikation gewertet. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | Featurebezogene historische Freigaben bleiben erhalten; REQUIREMENTS als projektweite Baseline Review. |
| Software-Auslieferung | Bestehende Spezifikationen im Main; verbleibende Funktionen nicht durch v1.5.52 abgenommen. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Ursprüngliche offene Umfänge ohne testbare Gesamtgrenze → bearbeitbarer Fachauftrag → bestehende zugehörige FT-Owner → jeweilige Umfangs-/Datenentscheidung → jeder betroffene Einzelanker besitzt Soll/Nicht-Soll, Benutzerpfad, Fehlerfälle und prüfbare Abnahmekriterien; maßgeblich sind die dort beschriebenen Reste, keine neue parallele Aufgabenliste. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-005

[FT-001 Feature Book](#pb-005-spec)

<a id="pb-005-spec"></a>
<details>
<summary>PB-005 — FT-001 Feature Book</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen; M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Approved for Build (historische FT-001-Baseline; umgesetzt) |
| Abgeschlossener Teilumfang | FT-001-Spezifikation und deren bestehende Umsetzung sind vorhanden; keine Neuimplementierung. |
| Soll / Nicht-Soll | **Soll:** Basiswert-/Listing-Vertrag und Regeln sind referenzierbar. **Nicht-Soll:** Keine Ableitung aktueller ETF-Grenzen allein aus der alten Aktienbaseline. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachliche Dokumentfreigabe. |
| Implementierung / Consumer | [docs/features/underlying/REQUIREMENTS.md](../../docs/features/underlying/REQUIREMENTS.md) und [FEATURE.md](../../docs/features/underlying/FEATURE.md) spezifizieren Underlying/Listing; [docs/implementation/MARKET_CHARTS.md](../../docs/implementation/MARKET_CHARTS.md) präzisiert ETF-Zulassung. Aktueller `UnderlyingService` und Chart-Setup verwenden dieselben Marketowner. |
| Test / Commit | [tests/unit/backend/features/market/test_service_layer.py](../../tests/unit/backend/features/market/test_service_layer.py); [tests/integration/backend/database/test_chart_watchlist_postgres.py](../../tests/integration/backend/database/test_chart_watchlist_postgres.py) inkl. ETF-/Indexgrenzen. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. |
| Fachliche Abnahme | Historische Approved-for-Build-Baseline bleibt; ETF-Erweiterung nicht als rückwirkende STOCK-Freigabe ausgeben. |
| Software-Auslieferung | Implementierungsfolge im heutigen v1.5.52; ursprünglicher Spezifikationsstatus bleibt historisch. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Historische STOCK-Angaben und ETF-Ergänzung müssen eindeutig versioniert gelesen werden → Benutzer/Entwickler kennt zulässige Instrumentarten → FT-001-Featurebook plus FT-006-Chart-Nachtrag → bestehende ETF-Entscheidung → dokumentierter Review ordnet ETF zum späteren Scope und erhält direkte Indizes außerhalb Wertpapierlistings. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-006

[Basiswerte, Listings und Identitäten im Backend](#pb-006-underlying)

<a id="pb-006-underlying"></a>
<details>
<summary>PB-006 — Basiswerte, Listings und Identitäten im Backend</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Released (historischer FT-001-Kern); Business Review (Abnahmenachweis späterer Eingabe-/ETF-Erweiterungen); Implementierung und Auslieferung abgeschlossen. |
| Abgeschlossener Teilumfang | Stammdatenservice inklusive Schutzregeln und integrierter Formularidentitätskorrektur abgeschlossen. |
| Soll / Nicht-Soll | **Soll:** Stabile Basiswert-/Listing-Identität, Änderungs- und Löschschutz; aktuelle Instrumentgrenzen beachten. **Nicht-Soll:** Indexreferenzen nicht als synthetische Wertpapierlistings anlegen; keine stille SHORT-Erweiterung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme (spätere Erweiterungen). |
| Implementierung / Consumer | [backend/app/features/market/service/service.py](../../backend/app/features/market/service/service.py): create/update/deactivate/reactivate/verify/delete/search mit atomarem Audit, Uniqueness, referenziertem Löschschutz und Optimistic Locking. [listing_service.py](../../backend/app/features/market/service/listing_service.py) separiert Listings. STOCK/ETF über bestehende Domainenum; keine synthetischen Indexlistings. |
| Test / Commit | [tests/unit/backend/features/market/test_service_layer.py](../../tests/unit/backend/features/market/test_service_layer.py), [tests/e2e/ft001-underlyings.spec.ts](../../tests/e2e/ft001-underlyings.spec.ts), [tests/e2e/underlying-form-isolation.spec.ts](../../tests/e2e/underlying-form-isolation.spec.ts), Watchlist-PostgreSQL-Tests. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer PB-006 Done/FT-001-Kern erhalten. Neuere Eingabe-/ETF-UX keine neu erfundene Fachabnahme. |
| Software-Auslieferung | [#249](https://github.com/burckhju/trading-workspace/pull/249) wurde als `79c5e0f4` integriert; heutiger v1.5.52 enthält es und ETF-Setup. Der alte offene-PR-Rest ist überholt. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Aktuelle menschliche Abnahme der STOCK-/ETF-Nutzerpfade fehlt → stabile Anlage/Bearbeitung ohne Identitätswechsel → vorhandener FT-001-Marketowner → synthetische STOCK-/ETF-Referenzfälle und fachlicher Prüfer → dokumentierte erfolgreiche Anlage/Änderung/Deaktivierung, Konflikt-/Löschschutz sowie Rückkehrnavigation mit unveränderter ID; kein erneuter [#249](https://github.com/burckhju/trading-workspace/pull/249)-Implementierungsauftrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-007

[Basiswertverwaltung in der Oberfläche](#pb-007-underlying-ui)

<a id="pb-007-underlying-ui"></a>
<details>
<summary>PB-007 — Basiswertverwaltung in der Oberfläche</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Released (historischer PB-007-Umfang); Business Review (aktuelle Nutzerabnahme der Folgekorrekturen); technische Qualifikation und Auslieferung abgeschlossen. |
| Abgeschlossener Teilumfang | Die früher offenen Formular-/Navigationseinträge sind integriert und technisch qualifiziert. |
| Soll / Nicht-Soll | **Soll:** Suchen, anlegen, ändern und deaktivieren über denselben fachlichen Owner. **Nicht-Soll:** Kein konkurrierender Stammdatenbestand in UI oder Workspace. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [frontend/src/features/market/pages/UnderlyingFormPage.tsx](../../frontend/src/features/market/pages/UnderlyingFormPage.tsx) ruft bestehenden create/update-Client mit Actor-/Identitätsschutz auf; UnderlyingDetailPage führt verify/deactivate/reactivate/delete über Marketowner aus. Listenrückkehr und Pending-/Aktivitätsguards sind vorhanden. |
| Test / Commit | [frontend/src/features/market/pages/UnderlyingFormIsolation.test.tsx](../../frontend/src/features/market/pages/UnderlyingFormIsolation.test.tsx), [UnderlyingNavigation.test.tsx](../../frontend/src/features/market/pages/UnderlyingNavigation.test.tsx); [tests/e2e/underlying-form-isolation.spec.ts](../../tests/e2e/underlying-form-isolation.spec.ts), [underlying-list-return.spec.ts](../../tests/e2e/underlying-list-return.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer PB-007 Done erhalten; keine menschliche Neuabnahme behauptet. |
| Software-Auslieferung | [#249](https://github.com/burckhju/trading-workspace/pull/249) `79c5e0f4` und [#204](https://github.com/burckhju/trading-workspace/pull/204) `5a18716f` auf Main; beide in v1.5.52 enthalten. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschlicher Bediennachweis der zusammengeführten Formular-/Rückkehrstrecke fehlt → Nutzer kehrt ohne verlorenen Listen-/Datensatzkontext zurück → vorhandene Market-Seiten/Navigation → konkrete geprüfte Version und fachlicher Prüfer → datierte Bedienabnahme von Anlegen/Bearbeiten/Abbrechen/Rückkehr und Wechsel bei ausstehender Antwort; [#204](https://github.com/burckhju/trading-workspace/pull/204)/#249 nicht erneut implementieren. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**A: Navigation — Nachweisfortschreibung 2026-10-25:** Der bestehende
[PR #204](https://github.com/burckhju/trading-workspace/pull/204) integriert Main
`fbd77fb94947a1fdbfc0aeb90811353fae655a59` / v1.5.14 konfliktfrei und erhält seine
veröffentlichte Historie. Die vorhandene URL-Navigation und der Formularschutz
bleiben unverändert; ergänzt werden gezielte Testverträge und aktuelle
Nachweise. Die [Navigationsqualifikation](../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md)
bindet A01–A14, die ausführbaren Quelltrees, 122 fokussierte Tests,
780 vollständige Frontendtests sowie 24 synthetische Browserfälle ohne Retry.
Die vollständigen aktuellen CI-Ergebnisse einschließlich beider Finanz- und
beider Lern-Ownerfälle werden im PR an den tatsächlichen Checkout/Tree gebunden.
Historische v1.5.11-Erfolge sind kein neuer Integrationsnachweis. Main-Merge,
Veröffentlichung, menschliche Abnahme und PC-Betrieb werden nicht vorweggenommen;
der neue Candidate-Governance-Auftrag B bleibt unberührt.

**Nachweisfortschreibung 2026-10-20:** Der ursprüngliche Formularschutz aus
[PR #249](https://github.com/burckhju/trading-workspace/pull/249) wurde am
18.10.2026 gemergt. Die Folgekorrektur auf Basis von
`254fe35b76027b72cd989715e17bd0ae55af55eb` behandelt zwei verbliebene Randfälle:
gleichwertige Querykodierungen dürfen bewusst bearbeitete Eingaben derselben
Formularinstanz nicht durch erneutes Laden überschreiben; alte Speicherantworten
dürfen bereits nach dem Commit der Zielansicht nicht mehr navigieren. Dazu gehören
ein stabiler Querysnapshot je Formularinstanz und eine Aktivitätsbereinigung in
der Layout-Phase, getrennt vom weiterhin passiven Ladeeffekt.

</details>

</details>

### PB-008

[FT-001 Integration und Abnahme](#pb-008-underlying-acceptance)

<a id="pb-008-underlying-acceptance"></a>
<details>
<summary>PB-008 — FT-001 Integration und Abnahme</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Accepted (historischer Abnahmekern); Business Review (neuere Erweiterungen) |
| Abgeschlossener Teilumfang | Historische Implementierungs-/Dokumentationsfertigstellung und heutige technische Suite belegt; alter fehlender Checkout/grundsätzlich unausführbare Tests kein aktueller Blocker. |
| Soll / Nicht-Soll | **Soll:** Integration und Abnahme haben einen datierten, versionsgenauen Beleg. **Nicht-Soll:** Ein grüner Lauf ersetzt keine menschliche Fachabnahme. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachabnahme neuer Umfänge. |
| Implementierung / Consumer | [docs/planning/SPRINT_2_CLOSEOUT.md](../../docs/planning/SPRINT_2_CLOSEOUT.md) belegt vertikale FT-001-Implementierung; [docs/planning/reviews/sprint-2/STEP15_REVIEW.md](../../docs/planning/reviews/sprint-2/STEP15_REVIEW.md) dokumentiert technischen/dokumentarischen Abschluss. Damals offener finaler Foundation-Compose/Playwrightlauf ist historisch; aktuelle Suite existiert und ist grün. |
| Test / Commit | [tests/e2e/foundation.spec.ts](../../tests/e2e/foundation.spec.ts), [tests/e2e/ft001-underlyings.spec.ts](../../tests/e2e/ft001-underlyings.spec.ts) plus Main-CI; keine historische Testzahl als neuer eigener Lauf. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer Accepted-Kern bleibt; Abschlussdokument selbst nennt produktiven finalen Lauf damals offen. Neuere ETF/Formular-UX nicht automatisch mitabgenommen. |
| Software-Auslieferung | Aktueller v1.5.52 enthält die Implementierung und erfolgreiche reguläre Suite. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Gesonderte Abnahme nachfolgender ETF-/UI-Erweiterungen fehlt → klarer akzeptierter Benutzerumfang → FT-001-Owner → PB-006/007-Prüffälle → datierter Abnahmebeleg nennt genaue Version, Fälle und Restpunkte; ursprüngliche Accepted-Aussage bleibt unverändert. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-009

[Börsen und Handelsplätze](#pb-009-venues)

<a id="pb-009-venues"></a>
<details>
<summary>PB-009 — Börsen und Handelsplätze</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Börsen und Handelsplätze. Bereich/Querschnitt: 1. Bestehender Bezug: FT-002. Lieferziel: A. |
| Arbeitsstatus | Released (bestehende FT-002-Verwaltung) |
| Abgeschlossener Teilumfang | Kontrollierte Börsen-/Handelsplatzverwaltung und Listingverwendung abgeschlossen; kein fehlender Verwaltungsservice. |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Daten (konkrete aktive Zuordnungen). |
| Implementierung / Consumer | [backend/app/features/market/service/trading_venue_administration.py](../../backend/app/features/market/service/trading_venue_administration.py): eindeutiger MIC, create/update/deactivate/reactivate, Versionguard, Audit in gemeinsamer UoW. [frontend/src/features/market/pages/TradingVenueAdminPage.tsx](../../frontend/src/features/market/pages/TradingVenueAdminPage.tsx) nutzt diesen Owner; Listings referenzieren stabile Venue-ID. |
| Test / Commit | [tests/e2e/ft002-trading-venues.spec.ts](../../tests/e2e/ft002-trading-venues.spec.ts), [tests/e2e/reference-data-consolidation.spec.ts](../../tests/e2e/reference-data-consolidation.spec.ts), Market-Admin-/Referenztests. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische Sprint-7A-Release-Evidence PR [#8](https://github.com/burckhju/trading-workspace/pull/8) / `7f39bc0` bleibt; neue menschliche Gesamtfreigabe nicht abgeleitet. |
| Software-Auslieferung | Historisch Released; enthalten und regressionsgeprüft in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Die tatsächliche Handelsplatz-/Kalenderzuordnung produktiver Instrumente ist separat zu prüfen → Benutzer erkennt richtige Identität/Handelssitzung → vorhandene Market-/TC-001-Owner → zugängliche Quelldokumente und lokale Readbacks → je betroffenem Instrument belegte Venue-/Währungs-/Kalenderbindung oder präzise Datenlücke. Allgemeine Verwaltung nicht neu bauen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-010

[Emittenten](#pb-010-issuers)

<a id="pb-010-issuers"></a>
<details>
<summary>PB-010 — Emittenten</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Emittenten. Bereich/Querschnitt: 1. Bestehender Bezug: FT-003. Lieferziel: A. |
| Arbeitsstatus | Released (bestehende FT-003-Verwaltung) |
| Abgeschlossener Teilumfang | Emittentenverwaltung und Verwendung in Optionsscheinstammdaten implementiert. |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Daten (reale Instrumentzuordnung). |
| Implementierung / Consumer | [backend/app/features/market/service/issuer_administration.py](../../backend/app/features/market/service/issuer_administration.py): globale Issuer-ID, LEI-Eindeutigkeit, create/update/deactivate/reactivate, optimistic Versionguard und atomarer Audit. IssuerAdminPage konsumiert denselben Owner; WarrantService prüft Issuerreferenz. |
| Test / Commit | [frontend/src/features/market/pages/IssuerAdminPage.test.tsx](../../frontend/src/features/market/pages/IssuerAdminPage.test.tsx); FT-004-/Reference-Data-Regressionen. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer Released-Stand bleibt, ursprüngliche RC-Notiz historisch. Keine aktuelle menschliche Liveabnahme. |
| Software-Auslieferung | Bestehende Verwaltung im veröffentlichten v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Reale Issuer-/Dokumentquellenzuordnung des betroffenen Bestands nicht vollständig belegt → nachvollziehbarer Emittent und Originalbedingungen → vorhandene Market-/Product-Owner → passende Originalproduktdokumente → bestätigte exakte Issuer-/Produktidentität oder ein konkret ausgewiesener Zuordnungskonflikt je Fall. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-011

[Instrumente und Optionsscheine](#pb-011-warrants)

<a id="pb-011-warrants"></a>
<details>
<summary>PB-011 — Instrumente und Optionsscheine</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Instrumente; Optionsscheine. Bereich/Querschnitt: 1. Bestehender Bezug: FT-004. Lieferziel: A. |
| Arbeitsstatus | Released (historischer FT-004-Kern); Business Review (neuere UI-/Datenabnahme); Implementierung und Auslieferung einschließlich [#285](https://github.com/burckhju/trading-workspace/pull/285) abgeschlossen. |
| Abgeschlossener Teilumfang | Instrument-/Terms-/Listingverwaltung und [#285](https://github.com/burckhju/trading-workspace/pull/285)-UI-Konsolidierung technisch abgeschlossen und ausgeliefert. |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Befundklasse / Lückenart | Vorhandene Funktion; reale Daten-/Entscheidungsblockade oder fehlender Betriebswirkungsnachweis einer ausgelieferten Korrektur; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Daten/Prüfung. |
| Implementierung / Consumer | [backend/app/features/product/service/application.py](../../backend/app/features/product/service/application.py): WarrantService erstellt/liest Instrument, historische TermsVersion und Listing getrennt, prüft Referenzen und eindeutige Kennungen. `frontend/src/features/product/` enthält den konsolidierten Verwaltungsweg; konkrete Produktbelege und Providerdaten bleiben eigene Owner. |
| Test / Commit | [tests/integration/backend/database/test_warrant_creation_listing_postgres.py](../../tests/integration/backend/database/test_warrant_creation_listing_postgres.py); [tests/e2e/warrant-admin-consolidation.spec.ts](../../tests/e2e/warrant-admin-consolidation.spec.ts), [warrant-listing-without-symbol.spec.ts](../../tests/e2e/warrant-listing-without-symbol.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. Zusätzliche v1.5.52-Nachweise: [Parserfälle](../../tests/unit/backend/providers/test_product_review_documents.py), [Originalupgrade](../../tests/unit/backend/features/product/test_product_document_reparse.py), [sequenzielle und konkurrierende PostgreSQL-Upgrades](../../tests/integration/backend/database/test_product_document_reparse_postgres.py), [Kalender-/Importfälle](../../tests/unit/backend/features/market_data/test_review_calendars.py); tatsächlich in der neuen [Main-CI](#nachweisregister) ausgeführt. |
| Fachliche Abnahme | Historischer FT-004-Scope und explizite Mergefolge [#284](https://github.com/burckhju/trading-workspace/pull/284)→[#285](https://github.com/burckhju/trading-workspace/pull/285) bleiben; keine neue gesamte Stammdaten-/Providerabnahme. |
| Software-Auslieferung | Historisch v0.9.0-warrants/#13; [#285](https://github.com/burckhju/trading-workspace/pull/285) als `f8f61a11` integriert und in v1.5.52 enthalten. Früher ausstehender Mergeauftrag ist historisch. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Produktive Originalbedingungen/Termine und deren exakte Zuordnung fehlen teils → Nutzer erhält gültige Produkt-/Terminbelege → bestehender Product-/Market-Data-Owner → lesende Positionsdiagnose und Originalquellen → je betroffenem Produkt Versions-/Identitäts-/Zeitnachweis oder konkrete Beschaffungs-/Konfliktbegründung; siehe einzigen nächsten Auftrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

#### Lokale Qualifikation der UI-Konsolidierung am 25.10.2026

Der Implementierungsstand `2a743463b381276baa291c27829709d74ae0b1e4` wurde
anschließend konfliktfrei mit dem zwischenzeitlich integrierten Main
`17d5891e0ff6e89ced73d587addb28589f5a292f` (#282) zusammengeführt. Produktcode
und zugehörige Browserfälle blieben dabei bytegleich. Die bereits auf Main
vorhandene Version 1.5.20 wurde unverändert übernommen; gegenüber Main gibt es
keine Änderung an Versionsdateien, Produkt-API oder Datenbankverträgen.

Die fokussierten und nativen lokalen Produktprüfungen unten wurden auf dem
unveränderten Implementierungsstand durchgeführt; der vollständige Frontend-Check
wurde nach der Main-Integration nochmals erfolgreich ausgeführt. Die abschließende
Diffprüfung war sauber. CI gehört zum tatsächlichen PR-Head und wird mit dessen
Workflow- und Artefaktlinks im PR ausgewiesen.

| Ebene | Ausgeführter Befehl / Umgebung | Ergebnis |
|---|---|---|
| Vollständiges Frontend | `bash scripts/check-frontend.sh`, Node 22.16.0 / npm 10.9.2 | Exit 0: Typecheck, ESLint, Prettier, 863 Tests in 126 Dateien, Coverage-Gates und Produktionsbuild erfolgreich. Statements/Lines 93,89 %, Branches 86,58 %, Functions 86,73 %. |
| Fokussierte simulierte UI | `npm run test -- src/features/product/pages --maxWorkers=1 --minWorkers=1`; zusätzlich Identifier-, Evidence- und NavigationGuard-Tests | 59 Seitentests und 26 Komponenten-/Guard-Tests erfolgreich; im vollständigen Frontendlauf enthalten, keine zusätzlichen nativen Persistenznachweise. |
| Backend-Verträge | `PYTHONPATH=backend:. python -m pytest -c backend/pyproject.toml tests/unit/backend/features/product -q`, Python 3.12.14 | 105 Tests erfolgreich; umfasst atomare Anlage, Bedingungen, Kennungskorrektur, Strike-Währung und geschützte Löschung. |
| Native PostgreSQL-Transaktion | Mit ausschließlich lokalem `TRADING_WORKSPACE_TEST_DATABASE_URL`: `PYTHONPATH=backend:. python -m pytest -c backend/pyproject.toml tests/integration/backend/database/test_warrant_creation_listing_postgres.py -q` | 2 Tests erfolgreich: gemeinsamer Commit und vollständiger Rollback nach Parent-Insert. Zufälliges isoliertes Testschema, anschließend entfernt. |
| Tatsächlicher Browser | Aus `frontend`: `npm run e2e -- warrant-admin-consolidation.spec.ts warrant-listing-without-symbol.spec.ts iv-data-evidence.spec.ts ft008-product-selection.spec.ts trade-plan-warrant-identity.spec.ts --workers=1 --reporter=list,html` | 10/10 Chromium-Tests, kein Skip/Retry/Flaky: sechs mit synthetischen API-Antworten, vier über echtes Backend und PostgreSQL. Desktop 1440 und schmal 390 Pixel; bestehender Belegtest zusätzlich 320/768. 18 Bildanhänge; repräsentative Ansichten visuell geprüft. |

Die native Browserprüfung verwendete eine eigens erzeugte lokale Datenbank mit
PostgreSQL 17.6 und den vorhandenen Alembic-Migrationen bis `20261017_0047`,
Playwright 1.55.0 / Chromium 140 unter Node 24.22.1 / npm 11.9.0 und
`TRADE_E2E_WRITES_ALLOWED=1`. Der vollständige Frontend-Check lief getrennt
unter der projektgepinnten Node-Version 22.16.0. Externe
Marktdaten-, Monitoring- und Benachrichtigungsjobs waren ausgeschaltet. Die
Datenbank und Dienste wurden ausschließlich für diese synthetische Prüfung
verwendet. Das ist kein Nachweis einer Installation auf dem Benutzer-PC.

Der erste vollständige Frontendlauf zeigte zwei Tests, die auf noch gesperrte
Ladebuttons klickten; die Tests warten jetzt ausdrücklich auf Bedienbereitschaft.
Der Browserlauf belegte zusätzlich eine Lücke im Tab-Umlauf des nativen
Verwerfungsdialogs; ein expliziter Fokusumlauf schließt sie. Die vollständigen
Prüfungen wurden anschließend erfolgreich wiederholt. Keine Fachassertion wurde
hierfür entfernt. Vorherige in der Prozess-Sandbox hängende Teststarts und der
Node-24/jsdom-Kompatibilitätsfehler werden nicht als bestandene Läufe gewertet.

#### Gemeinsame Vorabprüfung und Mergefreigabe

Die gemeinsame lokale Vorabprüfung von #284
(`a3e6e4450d0003c05eb181c65d377c48ec600ed6`) und #285
(`e58ac0e4d1448bbba9f296d77e98965e508d1366`), Tree
`ff8137ffaac87e2c7adf665f93707497ca5bb5ea`, bestand den vollständigen
Frontend-Check mit 952 Tests in 128 Dateien sowie elf Browserfälle ohne Skip,
Retry oder Flaky-Ergebnis: acht mit API-Fixtures, drei über echtes Backend und
PostgreSQL. Der gemeinsame Reparatur-/Rückkehr-/Neubewertungs-/Auswahl-/BUY-Ablauf
und der unabhängige Code-/Dokumentationsabgleich waren erfolgreich. Die genauen
Heads, Befehle und Nachweise stehen in
[PR #285](https://github.com/burckhju/trading-workspace/pull/285).

Der Nutzer hat am 26.10.2026 die Reihenfolge #284 mergen, #285 auf den neuen
Main bringen und nach erfolgreicher finaler CI ebenfalls mergen ausdrücklich
freigegeben. Der lokale Vorabnachweis ersetzt die CI auf diesem tatsächlichen
Integrationsstand nicht. Die übernommene Main-Version bleibt unverändert;
eine PC-Installation oder fachliche Gesamtfreigabe wird damit nicht behauptet.

</details>

</details>

### PB-012

[Watchlist](#pb-012-watchlist) · [Kandidatenqualifikation](#pb-012-candidate) · [Scanner und Scanner-Modell](#pb-012-scanner)

<a id="pb-012-watchlist"></a>
<details>
<summary>PB-012 — Watchlist</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Watchlist. Bereich/Querschnitt: 3. Bestehender Bezug: FT-005. Lieferziel: A. |
| Arbeitsstatus | Business Review (fachliche Nutzer-/Datenabnahme der festen Chart-Watchlist); Implementierung, technische Qualifikation und Auslieferung abgeschlossen. Analysis (generischer Watchlistumfang). |
| Abgeschlossener Teilumfang | Persistente feste 31er-Watchlist samt einmaliger Einrichtung, Schedulerintegration und Chartconsumer ist technisch abgeschlossen und ausgeliefert. Die frühere pauschale Aussage „Watchlist nicht verifiziert“ ist durch die getrennten Implementierungs-, Test- und Auslieferungsnachweise ersetzt. |
| Soll / Nicht-Soll | **Soll:** Benutzerverwaltete Beobachtungsliste mit nachvollziehbarer Zugehörigkeit, unabhängig vom Qualifikationsergebnis. **Nicht-Soll:** Kandidatenliste ist kein Nachweis eines generischen Watchlist-Aggregats. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Vorhanden, unvollständig: Entscheidung/Implementierung für generische Mitgliedschaft; Prüfung/Daten für feste Liste. |
| Implementierung / Consumer | [backend/app/features/market/service/chart_watchlist.py](../../backend/app/features/market/service/chart_watchlist.py) aktiviert genau versionierten Katalog nach confirmed=true, persistiert 31 Mitglieder samt Prüfsumme/Actor/Reihenfolge, wiederholt idempotent. [chart_watchlist_setup.py](../../backend/app/features/market/service/chart_watchlist_setup.py) nutzt bestehende Market-/Mappingowner; [market_data/service/refresh.py](../../backend/app/features/market_data/service/refresh.py) führt Setup/Import über bestehende Lane aus. [frontend/src/features/analysis/components/ChartWatchlistOverview.tsx](../../frontend/src/features/analysis/components/ChartWatchlistOverview.tsx) und MarketChartsPage zeigen direkte S&P-500-Referenz + 30 ETFs. GET ist passiv; kein Add/Remove/Reorder frei gewählter Watchlistmitglieder im API-/UI-Vertrag. |
| Test / Commit | [tests/unit/backend/features/market/test_chart_watchlist.py](../../tests/unit/backend/features/market/test_chart_watchlist.py); [tests/integration/backend/database/test_chart_watchlist_postgres.py](../../tests/integration/backend/database/test_chart_watchlist_postgres.py) (persistente Aktivierung, Wiederaufnahme, Eigentümerrevisionen, Workspacegrenzen); [tests/e2e/market-watchlist.spec.ts](../../tests/e2e/market-watchlist.spec.ts) (31 Karten, Aktivierung/Reload, lokale Interaktion, Reflow/Zoom); Watchlist-Frontendtests. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [market-watchlist.spec.ts](../../tests/e2e/market-watchlist.spec.ts) stubbt Browser-HTTP vollständig; die echte dauerhafte PostgreSQL-/Ownerprüfung liegt separat in [test_chart_watchlist_postgres.py](../../tests/integration/backend/database/test_chart_watchlist_postgres.py) (synthetische Providerantworten). Browser-Reload beweist alleine keine DB-Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Konkreter Nutzerauftrag 09.11.2026 im Implementierungs-/Releasebericht; menschliche UX-/Domain-, Screenreader-/Touchabnahme und reale 31-Reihen-Abdeckung ausdrücklich offen. |
| Software-Auslieferung | [docs/releases/V1.5.46-SP500-ETF-OVERVIEW.md](../../docs/releases/V1.5.46-SP500-ETF-OVERVIEW.md); [#340](https://github.com/burckhju/trading-workspace/pull/340) und Tag v1.5.46 auf `d01c259f4b79fdfbdcec8743ececda035b69f9d1`, Bestandteil v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Freie benutzerverwaltete Beobachtungsmitgliedschaft außerhalb des festen Katalogs fehlt → Benutzer kann gewünschte Instrumente unabhängig vom Candidate-Ergebnis beobachten → bestehender Market-/Chart-Watchlistowner und FT-005-Consumer → fachliche Entscheidung zu Instrumentarten, Add/Remove/Reorder, Katalogbindung und Datenrechten → freigegebener Mitgliedschaftsvertrag und persistente Bedienfälle über Reload/Neustart, ohne zweite Stammdaten-/Statuswahrheit. Separat: feste 31 Reihen auf PC je Instrument mit Quellen-/Historienstatus und datierter UX-Abnahme belegen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-012-candidate"></a>
<details>
<summary>PB-012 — Kandidatenqualifikation</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Kandidaten. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005; FT-019/FT-020 als vorhandene Kandidaten-Erweiterungen. Lieferziel: A, D. |
| Arbeitsstatus | Released (historisch abgenommener Kandidatenkern); Business Review (Abnahmenachweis der späteren Nutzer-/Governanceerweiterungen); technische Strecke und Auslieferung abgeschlossen. |
| Abgeschlossener Teilumfang | Versionierte Kandidatenevaluation, konkrete Planübergabe und technische Governancejourney vorhanden; keine neue Kandidatenstrecke bauen. |
| Soll / Nicht-Soll | **Soll:** Nachvollziehbare Top-down-Evaluation mit konkreter Analyse-/Modellversion und explizitem Handoff. **Nicht-Soll:** Kein aggregierter Candidate-Score und keine automatische Planfreigabe. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme/Daten. |
| Implementierung / Consumer | [backend/app/features/candidate/service/application.py](../../backend/app/features/candidate/service/application.py) create/evaluate_auto/evaluate_from_analyses/evaluate speichert immutable Evaluation, Kriterien und exakte MARKET/SECTOR/UNDERLYING-Referenzen. Runtime wird über TOP_DOWN_CANDIDATE/RuntimeActivationService aufgelöst. Frontend Candidate-Consumer und TradePlanService.create_from_candidate verwenden konkrete Evaluation; kein Score/Autotrade. |
| Test / Commit | [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts); [tests/integration/backend/test_candidate_trade_plan_handoff.py](../../tests/integration/backend/test_candidate_trade_plan_handoff.py); Candidate-Orchestration-/Domain-/Runtime-Tests. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische Sprint-5-Reviews plus spätere konkrete Governanceentscheidungen erhalten; keine globale FT-005-Endabnahme. |
| Software-Auslieferung | [docs/releases/V1.5.16-CANDIDATE-GOVERNANCE-JOURNEY.md](../../docs/releases/V1.5.16-CANDIDATE-GOVERNANCE-JOURNEY.md); [#278](https://github.com/burckhju/trading-workspace/pull/278)-Analysefix als `b49e87e8` auf Main; gesamte Strecke in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Endabnahme und reale Datenvollständigkeit der Kandidatenstrecke fehlen → nachvollziehbare Candidate-Begründung mit ursprünglicher Analyse-/Modellversion → bestehende FT-005/006/013-Consumer → qualifizierte Marktreferenzen und datierter Testfall → dokumentierte Nutzerabnahme inklusive qualifiziert/nicht auswertbar, Übergabe in Plan sowie historischer Reproduktion; allgemeiner Scanner bleibt separater Rest. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-012-scanner"></a>
<details>
<summary>PB-012 — Scanner und Scanner-Modell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Scanner; M9: Scanner. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005 / FT-006; FT-013 für Governance. Lieferziel: A, D. |
| Arbeitsstatus | Analysis (eigenständiger ursprünglicher Scannerumfang nicht umgesetzt/nicht definiert) |
| Abgeschlossener Teilumfang | Einzelkandidatenqualifikation ist Vorleistung, nicht Scannerabschluss. |
| Soll / Nicht-Soll | **Soll:** Der ursprüngliche Scanneranspruch bleibt als eigener Umfang mit explizitem Suchuniversum, Auslöser und Modellbezug sichtbar. **Nicht-Soll:** Einzelne Candidate-Evaluation oder eine Liste ist nicht automatisch ein vollständiger Scanner. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fehlende Funktion plus fachliche Entscheidung/Daten. |
| Implementierung / Consumer | CandidateService bewertet explizit angelegte einzelne Kandidaten/Underlying über vorhandene Top-down-Orchestrierung; die Chartübersicht liest einen festen Katalog. In diesen tatsächlichen API-/UI-/Servicepfaden gibt es keinen universumsweiten Scannerauftrag mit definierter Population, Auslöser und reproduzierbarem Ergebnislauf. |
| Test / Commit | Candidate-/Charttests belegen Nachbarfunktionen; kein eigenständiger Scannerlauf/-Consumer-Testnachweis. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Keine dokumentierte Entfernung des ursprünglichen M2/M9-Scanneranspruchs; fachlicher Umfangsentscheid fehlt. |
| Software-Auslieferung | Nachbarfunktionen in v1.5.52, kein eigener Scannerrelease belegt. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Definierter universumsweiter Scanner fehlt → Benutzer erhält nachvollziehbare Kandidaten aus expliziter Grundgesamtheit → vorhandene FT-005/006-Orchestrierung, FT-013 für Modellversion → Entscheidung über Universum, Trigger, Regeln, Datenabdeckung → freigegebener Vertrag und reproduzierbarer Lauf mit vollständiger Population, Fehlgründen und konkretem UI-Handoff; keine zweite Candidateengine. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-013

[Marktübersicht](#pb-013-overview) · [Marktbreite](#pb-013-breadth) · [Sektoren und Referenzen](#pb-013-sectors) · [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis)

<a id="pb-013-overview"></a>
<details>
<summary>PB-013 — Marktübersicht</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Marktübersicht. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Released (historischer Sprint-4-Umfang); Business Review (spätere Chart-/UX-/Watchlisterweiterung und gesamter M2-Nutzen); Implementierung und Auslieferung abgeschlossen. |
| Abgeschlossener Teilumfang | Bestehende Chart-/Datenübersicht technisch implementiert und ausgeliefert. |
| Soll / Nicht-Soll | **Soll:** Markt- und Datenzustände nachvollziehbar lesen. **Nicht-Soll:** Chartvergleich ist keine Depot-Performance. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Daten. |
| Implementierung / Consumer | [backend/app/features/analysis/service/charts.py](../../backend/app/features/analysis/service/charts.py) liest gespeicherte Daily-/Referenzdaten, erzeugt begrenzten Vergleich ohne FT-006-Runs. MarketChartsPage enthält 31er-Standardübersicht, Detailvergleich maximal vier Reihen, getrennte Preisachsen/Quellen/Lücken. Betriebs-/Datenzustände kommen vom vorhandenen Owner. |
| Test / Commit | [tests/unit/backend/features/analysis/test_chart_service.py](../../tests/unit/backend/features/analysis/test_chart_service.py), [tests/integration/backend/database/test_market_charts_postgres.py](../../tests/integration/backend/database/test_market_charts_postgres.py); [tests/e2e/market-charts.spec.ts](../../tests/e2e/market-charts.spec.ts), [market-watchlist.spec.ts](../../tests/e2e/market-watchlist.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [market-watchlist.spec.ts](../../tests/e2e/market-watchlist.spec.ts) stubbt Browser-HTTP vollständig; die echte dauerhafte PostgreSQL-/Ownerprüfung liegt separat in [test_chart_watchlist_postgres.py](../../tests/integration/backend/database/test_chart_watchlist_postgres.py) (synthetische Providerantworten). Browser-Reload beweist alleine keine DB-Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer Sprint-4-Abnahmekern erhalten; spätere Chart-/UX4-/31er-Erweiterung hat keine belegte menschliche Gesamtabnahme. |
| Software-Auslieferung | Charts v1.5.0; feste Übersicht v1.5.46, enthalten in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Abnahme und tatsächliche Historien-/Quellenabdeckung fehlen → Nutzer erkennt Markt- und Datenlage ohne scheinbare Live-/Performanceaussage → vorhandene Analysis-/Market-Charts-Consumer → freigegebene Quellen und lokale Readbacks → datierte Abnahme der 31 Karten/Detailvergleiche einschließlich fehlender, veralteter und unterschiedlicher Einheiten; weitergehender Übersichtsbedarf nur durch Produktentscheidung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-breadth"></a>
<details>
<summary>PB-013 — Marktbreite</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Marktbreite. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Analysis (ursprüngliche Marktbreite offen) |
| Abgeschlossener Teilumfang | Markt-/Sektoranalysen und Chartdarstellung sind Vorleistungen. |
| Soll / Nicht-Soll | **Soll:** Marktbreite besitzt eine definierte Grundgesamtheit, Berechnung und Datenqualität. **Nicht-Soll:** Marktbenchmark, Sektormatrix oder Relative Strength allein belegt keine Marktbreite. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fehlende Funktion plus fachliche Entscheidung/Daten. |
| Implementierung / Consumer | FT-006 berechnet SMA/Momentum/Volatilität/Handelsspanne und Top-down-Relative-Strength; [analysis/service/charts.py](../../backend/app/features/analysis/service/charts.py) zeigt Preisreihen. Diese verarbeiteten Größen bilden keine explizite Marktbreite einer definierten Grundgesamtheit ab. Kein passender Marktbreite-Service-/UI-Ergebnisvertrag im geprüften Pfad. |
| Test / Commit | Analyse-/Charttests sind keine Marktbreite-Tests; spezifische Referenzfälle fehlen. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Sprint-4-Freigabe betrifft dessen engeren Analyseumfang, nicht ursprüngliche vollständige Marktbreite. Umfangsentscheidung fehlt. |
| Software-Auslieferung | Kein eigenständiger Marktbreite-Liefernachweis. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Grundgesamtheit, Berechnung und Abdeckung für Marktbreite fehlen → Benutzer versteht Breite einer definierten Marktbewegung → vorhandener FT-006-Analyseowner/TC-001 → Entscheidung über Universum, Kennzahl, Zeit-/Ausfallsemantik und verfügbare Historien → versionierter Vertrag, synthetische Referenzfälle und API/UI mit transparentem Nenner, Ausfällen und Quellen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-sectors"></a>
<details>
<summary>PB-013 — Sektoren und Referenzen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Sektoren. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Released (Referenz-/Sektorstruktur und Darstellung); Business Review (reale Abdeckung) |
| Abgeschlossener Teilumfang | Administrierte Referenzzuordnungen, echte Analyseconsumer und dynamische Darstellung vorhanden. |
| Soll / Nicht-Soll | **Soll:** Administrierte Sektor-/Marktreferenzen und ihre Datenabdeckung bleiben erkennbar. **Nicht-Soll:** Keine erfundenen Index-Listings; ETF-Vorschläge sind keine zweite Stammdatenwahrheit. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Daten/Prüfung. |
| Implementierung / Consumer | [backend/app/features/market/service/top_down_administration.py](../../backend/app/features/market/service/top_down_administration.py) besitzt Referenzen/Zuordnungen, [analysis/service/reference_application.py](../../backend/app/features/analysis/service/reference_application.py) analysiert echte Referenzinstrumente, [analysis/service/charts.py](../../backend/app/features/analysis/service/charts.py) stellt Sektor-/Marktreihen dar; keine erfundenen Indexlistings. |
| Test / Commit | [tests/unit/backend/features/market/test_top_down_administration_service.py](../../tests/unit/backend/features/market/test_top_down_administration_service.py), [test_top_down_readiness_instrument_chain.py](../../tests/unit/backend/features/market/test_top_down_readiness_instrument_chain.py); [tests/integration/backend/database/test_candidate_native_reference_sources_postgres.py](../../tests/integration/backend/database/test_candidate_native_reference_sources_postgres.py); Market-Charts-E2E. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer Sprint-4-/5-Scope; aktuelle menschliche Abnahme produktiver Referenzzuordnungen nicht belegt. |
| Software-Auslieferung | Referenz-/Sektorerweiterungen und [#278](https://github.com/burckhju/trading-workspace/pull/278)-Qualitätsfix in v1.5.52; Charts seit v1.5.0. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Aktive Zuordnungen und tatsächliche Historie je Sektor/Markt noch nicht im Zielbetrieb nachgewiesen → Benutzer sieht belastbare Top-down-Referenzen → vorhandener Market-/TC-001-/FT-006-Owner → reale Provider-/Mapping-/Kalenderbelege → je verwendeter Referenz exakte Identität, Quellenzeit und nutzbare Historie oder konkret benannte Lücke; keine erneute technische Sektormatriximplementierung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-analysis"></a>
<details>
<summary>PB-013 — Reproduzierbare Analyse und Marktmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Analyse; M9: Marktmodell. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Released (historisch abgenommene Sprint-4-Analyse); Business Review (Abnahmenachweis der späteren Quellen-/Analyseerweiterung); EOD_TREND_MOMENTUM 1.0.1 und historische Reproduktion technisch abgeschlossen und ausgeliefert. |
| Abgeschlossener Teilumfang | Reproduzierbarer konkreter Analysemodellpfad einschließlich 1.0.1-Quellenqualität technisch abgeschlossen und ausgeliefert. |
| Soll / Nicht-Soll | **Soll:** Beschreibende Analyse speichert Eingaben, Parameter, Quellen und konkrete Modellversion. **Nicht-Soll:** Keine Handelsentscheidung; Charts erzeugen keine FT-006-Runs. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Daten; fachliche Entscheidung nur für weitergehende Modellansprüche. |
| Implementierung / Consumer | [backend/app/features/analysis/service/application.py](../../backend/app/features/analysis/service/application.py) speichert Snapshots, Parameter und Modellversion, führt run/retry/verify mit versioniertem Dispatch aus. [reference_application.py](../../backend/app/features/analysis/service/reference_application.py) verwendet denselben Qualitätsvertrag; CandidateService speichert die genauen Referenzen. 1.0.0 bleibt historisch reproduzierbar; neue Runs 1.0.1. Kein generischer Nachweis jeder Modellfamilie. |
| Test / Commit | [tests/integration/backend/database/test_ft006_versioned_quality_postgres.py](../../tests/integration/backend/database/test_ft006_versioned_quality_postgres.py), [test_candidate_native_reference_sources_postgres.py](../../tests/integration/backend/database/test_candidate_native_reference_sources_postgres.py); [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts); [docs/implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md](../../docs/implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Sprint-4-Analyse fachlich abgenommen mit damaliger RC-Grenze; spätere Version 1.0.1 technisch nachgewiesen, keine globale M9-Abnahme. |
| Software-Auslieferung | [#278](https://github.com/burckhju/trading-workspace/pull/278) als `b49e87e8` integriert; aktueller Tag v1.5.52 enthält den Fix. Alter Rest „Mergefreigabe/Integration [#278](https://github.com/burckhju/trading-workspace/pull/278) fehlt“ ist überholt. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Reale vollständige Quellenabdeckung und fachlicher Akzeptanzbeleg der neuen Analyseversion fehlen → Nutzer kann neue und historische Ergebnisse richtig interpretieren → vorhandene FT-006-/Candidate-Consumer → versionsgebundene Referenzfälle/Marktdaten → dokumentierte Abnahme von GOOD/LIMITED/NOT_EVALUABLE und 1.0.0-Reproduktion; weitere Marktmodellanforderungen ausdrücklich definieren, nicht aus Governance ableiten. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-014

[Einstieg planen](#pb-014-entry) · [Stopstrategie im TradePlan](#pb-014-stop) · [Kursziele im TradePlan](#pb-014-targets) · [Risikoannahmen im TradePlan](#pb-014-risk) · [Annahmen, Freigabe und Herkunft des Plans](#pb-014-assumptions)

**Begrenzter UI-Nachtrag 25.10.2026:** Der Nutzerauftrag konsolidiert einmalige
Basiswert-/CandidateEvaluation-Auswahl, zentrale versionsgenaue Planansicht und
den vorbefüllten Approved-Amendment-Weg bis zum prüfbaren Draft-PR.
[Vertrag, vollständiger TRIGGER-Referenzfall und Qualifikationsgrenzen](../implementation/TRADE_PLAN_SELECTION_CONTEXT.md).
Die historische Auslieferung unten bleibt historisch; neue Ergebnisse sind an
den aktuellen UI-Commit zu binden. **Offener Folgepunkt:** eigener fachlicher/API-
Vertrag für die Inhaltsrevision bereits gespeicherter DRAFT-Versionen; Rückkehr
von READY_FOR_REVIEW nach DRAFT ist nur eine Statusaktion. Keine Versions-, Merge-,
Release- oder PC-Freigabe aus diesem UI-Auftrag.

<a id="pb-014-entry"></a>
<details>
<summary>PB-014 — Einstieg planen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Einstieg. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (belegter FT-007-Teilscope und integriertes [#284](https://github.com/burckhju/trading-workspace/pull/284)) |
| Abgeschlossener Teilumfang | Einstieg als produktneutraler immutable Planinhalt samt TRIGGER-Fällen und APPROVED-Amendment implementiert. |
| Soll / Nicht-Soll | **Soll:** Produktneutralen Einstieg in einer konkreten TradePlanVersion dokumentieren. **Nicht-Soll:** Keine Order, keine automatische Einstiegsempfehlung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; DRAFT-Inhaltsrevision bei Einstieg zusätzlich Entscheidung/Implementierung. |
| Implementierung / Consumer | [backend/app/features/trade_plan/service/application.py](../../backend/app/features/trade_plan/service/application.py) erzeugt manuelle oder konkrete Candidate-Ursprünge, immutable Inhalte, explizite submit/return/approve-Transitions und Amendments ausschließlich von APPROVED; [frontend/src/features/trade_plan/pages/TradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx), [ExistingTradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx) und TradePlanVersionContent stellen exakte Versionen dar. ProductSelectionService verlangt genau APPROVED. |
| Test / Commit | [tests/unit/backend/features/trade_plan/test_application_service.py](../../tests/unit/backend/features/trade_plan/test_application_service.py), `test_domain.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft007-trade-plan.spec.ts](../../tests/e2e/ft007-trade-plan.spec.ts), [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Der native [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts) nutzt keine route mocks; er legt Stammdaten/Plan/Selection/BUY über echte Owner-APIs an und prüft TRIGGER-Amendment samt getrenntem Approval. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-007-Abnahmekern/S6 Architecture Review Accepted bleibt; neuer UI-Auftrag [#284](https://github.com/burckhju/trading-workspace/pull/284) kein zusätzlicher menschlicher Gesamtbeleg. |
| Software-Auslieferung | Historisch v0.6.0-trade-plan; [#284](https://github.com/burckhju/trading-workspace/pull/284) auf `059860ea` / v1.5.21 integriert; sämtliche Funktion in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Fachlicher/API-Vertrag zur Inhaltsrevision bereits gespeicherter DRAFTs fehlt → Benutzer kann einen gespeicherten Entwurf kontrolliert ändern → bestehender FT-007-Owner → Entscheidung über Versionierung/Lineage/Validierungen → definierter und getesteter DRAFT-Änderungsweg; Statusrückkehr READY_FOR_REVIEW→DRAFT bleibt kein Inhaltsedit. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-stop"></a>
<details>
<summary>PB-014 — Stopstrategie im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Stopstrategie. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (belegter FT-007-Teilscope und integriertes [#284](https://github.com/burckhju/trading-workspace/pull/284)) |
| Abgeschlossener Teilumfang | Invalidation-/Stopannahme wird in konkreter Planversion historisiert; Managementstop ist getrennt. |
| Soll / Nicht-Soll | **Soll:** Geplante Invalidation/Stopannahme bleibt unveränderlich referenzierbar. **Nicht-Soll:** Planparameter sind kein Nachweis eines eigenständigen Stopmodells. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; DRAFT-Inhaltsrevision bei Einstieg zusätzlich Entscheidung/Implementierung. |
| Implementierung / Consumer | [backend/app/features/trade_plan/service/application.py](../../backend/app/features/trade_plan/service/application.py) erzeugt manuelle oder konkrete Candidate-Ursprünge, immutable Inhalte, explizite submit/return/approve-Transitions und Amendments ausschließlich von APPROVED; [frontend/src/features/trade_plan/pages/TradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx), [ExistingTradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx) und TradePlanVersionContent stellen exakte Versionen dar. ProductSelectionService verlangt genau APPROVED. |
| Test / Commit | [tests/unit/backend/features/trade_plan/test_application_service.py](../../tests/unit/backend/features/trade_plan/test_application_service.py), `test_domain.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft007-trade-plan.spec.ts](../../tests/e2e/ft007-trade-plan.spec.ts), [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Der native [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts) nutzt keine route mocks; er legt Stammdaten/Plan/Selection/BUY über echte Owner-APIs an und prüft TRIGGER-Amendment samt getrenntem Approval. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-007-Abnahmekern/S6 Architecture Review Accepted bleibt; neuer UI-Auftrag [#284](https://github.com/burckhju/trading-workspace/pull/284) kein zusätzlicher menschlicher Gesamtbeleg. |
| Software-Auslieferung | Historisch v0.6.0-trade-plan; [#284](https://github.com/burckhju/trading-workspace/pull/284) auf `059860ea` / v1.5.21 integriert; sämtliche Funktion in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Eigenständiges Stopmodell ist kein Teil des manuell erfassten Plans → nachvollziehbare berechnete Stopregel nur nach eigenem Modellentscheid → bestehender FT-007-Consumer/FT-013 → PB-020-Stopmodellvertrag → dessen separate Abnahmekriterien erfüllt; keine erneute Implementierung der vorhandenen Planeingabe. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-targets"></a>
<details>
<summary>PB-014 — Kursziele im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Kursziele. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (belegter FT-007-Teilscope und integriertes [#284](https://github.com/burckhju/trading-workspace/pull/284)) |
| Abgeschlossener Teilumfang | Kursziele sind immutable Planinhalt; Approved-Amendment erhält frühere Version und historische Selection. |
| Soll / Nicht-Soll | **Soll:** Ursprüngliche Ziele in der konkreten Planversion erhalten. **Nicht-Soll:** Keine automatische Zielwahl; Managementänderungen überschreiben nicht den Plan. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; DRAFT-Inhaltsrevision bei Einstieg zusätzlich Entscheidung/Implementierung. |
| Implementierung / Consumer | [backend/app/features/trade_plan/service/application.py](../../backend/app/features/trade_plan/service/application.py) erzeugt manuelle oder konkrete Candidate-Ursprünge, immutable Inhalte, explizite submit/return/approve-Transitions und Amendments ausschließlich von APPROVED; [frontend/src/features/trade_plan/pages/TradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx), [ExistingTradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx) und TradePlanVersionContent stellen exakte Versionen dar. ProductSelectionService verlangt genau APPROVED. |
| Test / Commit | [tests/unit/backend/features/trade_plan/test_application_service.py](../../tests/unit/backend/features/trade_plan/test_application_service.py), `test_domain.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft007-trade-plan.spec.ts](../../tests/e2e/ft007-trade-plan.spec.ts), [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Der native [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts) nutzt keine route mocks; er legt Stammdaten/Plan/Selection/BUY über echte Owner-APIs an und prüft TRIGGER-Amendment samt getrenntem Approval. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-007-Abnahmekern/S6 Architecture Review Accepted bleibt; neuer UI-Auftrag [#284](https://github.com/burckhju/trading-workspace/pull/284) kein zusätzlicher menschlicher Gesamtbeleg. |
| Software-Auslieferung | Historisch v0.6.0-trade-plan; [#284](https://github.com/burckhju/trading-workspace/pull/284) auf `059860ea` / v1.5.21 integriert; sämtliche Funktion in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschlicher Abnahmebeleg der Ziel-/Versionsdarstellung fehlt → Benutzer erkennt ursprüngliche und später geänderte Ziele → bestehender FT-007-/FT-011-Consumer → konkreter Referenzplan mit Amendment → datierter UI-Abnahmefall bindet ursprüngliche und neue Version/Handoff; eigenständiges Zielmodell bleibt PB-020. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-risk"></a>
<details>
<summary>PB-014 — Risikoannahmen im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Risiko. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (belegter FT-007-Teilscope und integriertes [#284](https://github.com/burckhju/trading-workspace/pull/284)) |
| Abgeschlossener Teilumfang | Risikoannahmen und produktneutrale Validierungen sind im TradePlan gespeichert; keine Positionsgrößenautonomie. |
| Soll / Nicht-Soll | **Soll:** Risikoannahmen und Grenzen transparent dokumentieren. **Nicht-Soll:** Keine Positionsgrößenentscheidung; fehlende Eingaben sind nicht Nullrisiko. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; DRAFT-Inhaltsrevision bei Einstieg zusätzlich Entscheidung/Implementierung. |
| Implementierung / Consumer | [backend/app/features/trade_plan/service/application.py](../../backend/app/features/trade_plan/service/application.py) erzeugt manuelle oder konkrete Candidate-Ursprünge, immutable Inhalte, explizite submit/return/approve-Transitions und Amendments ausschließlich von APPROVED; [frontend/src/features/trade_plan/pages/TradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx), [ExistingTradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx) und TradePlanVersionContent stellen exakte Versionen dar. ProductSelectionService verlangt genau APPROVED. |
| Test / Commit | [tests/unit/backend/features/trade_plan/test_application_service.py](../../tests/unit/backend/features/trade_plan/test_application_service.py), `test_domain.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft007-trade-plan.spec.ts](../../tests/e2e/ft007-trade-plan.spec.ts), [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Der native [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts) nutzt keine route mocks; er legt Stammdaten/Plan/Selection/BUY über echte Owner-APIs an und prüft TRIGGER-Amendment samt getrenntem Approval. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-007-Abnahmekern/S6 Architecture Review Accepted bleibt; neuer UI-Auftrag [#284](https://github.com/burckhju/trading-workspace/pull/284) kein zusätzlicher menschlicher Gesamtbeleg. |
| Software-Auslieferung | Historisch v0.6.0-trade-plan; [#284](https://github.com/burckhju/trading-workspace/pull/284) auf `059860ea` / v1.5.21 integriert; sämtliche Funktion in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Prüfung der dargestellten Risikogrenzen fehlt → Nutzer verwechselt Planannahme nicht mit ausgeführter Positionsbewertung → bestehende FT-007-/FT-009-Consumer → repräsentativer Plan-/Kauffall → dokumentierter Abnahmefall weist Annahme, Ausführungsfakt und fehlende Daten getrennt aus. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-assumptions"></a>
<details>
<summary>PB-014 — Annahmen, Freigabe und Herkunft des Plans</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Annahmen. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (belegter FT-007-Teilscope und integriertes [#284](https://github.com/burckhju/trading-workspace/pull/284)) |
| Abgeschlossener Teilumfang | Thesis/Annahmen, exakter optionaler Candidate-Ursprung, Approval-Actor/-Zeit und Amendment-Lineage sind implementiert. |
| Soll / Nicht-Soll | **Soll:** Versionierte Annahmen, explizite Freigabe und gegebenenfalls genaue CandidateEvaluation referenzieren. **Nicht-Soll:** Keine Verwendung von latest statt des historischen Ursprungs. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; DRAFT-Inhaltsrevision bei Einstieg zusätzlich Entscheidung/Implementierung. |
| Implementierung / Consumer | [backend/app/features/trade_plan/service/application.py](../../backend/app/features/trade_plan/service/application.py) erzeugt manuelle oder konkrete Candidate-Ursprünge, immutable Inhalte, explizite submit/return/approve-Transitions und Amendments ausschließlich von APPROVED; [frontend/src/features/trade_plan/pages/TradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx), [ExistingTradePlanPage.tsx](../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx) und TradePlanVersionContent stellen exakte Versionen dar. ProductSelectionService verlangt genau APPROVED. |
| Test / Commit | [tests/unit/backend/features/trade_plan/test_application_service.py](../../tests/unit/backend/features/trade_plan/test_application_service.py), `test_domain.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft007-trade-plan.spec.ts](../../tests/e2e/ft007-trade-plan.spec.ts), [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Der native [ft007-plan-context-postgres.spec.ts](../../tests/e2e/ft007-plan-context-postgres.spec.ts) nutzt keine route mocks; er legt Stammdaten/Plan/Selection/BUY über echte Owner-APIs an und prüft TRIGGER-Amendment samt getrenntem Approval. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-007-Abnahmekern/S6 Architecture Review Accepted bleibt; neuer UI-Auftrag [#284](https://github.com/burckhju/trading-workspace/pull/284) kein zusätzlicher menschlicher Gesamtbeleg. |
| Software-Auslieferung | Historisch v0.6.0-trade-plan; [#284](https://github.com/burckhju/trading-workspace/pull/284) auf `059860ea` / v1.5.21 integriert; sämtliche Funktion in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Aktuelle menschliche Abnahme des versionsgenauen Gesamtwegs fehlt → Nutzer kann ursprüngliche Planfreigabe und Änderung nachvollziehen → bestehender FT-007-/FT-008-Consumer → fachlicher Prüfer und Referenzfall → datierte Abnahme von Create→Review→Approve→Amend mit unveränderter alter Selection/BUY; Draft-Inhaltsrevision nur nach Vertrag bei PB-014 Einstieg. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-015

[Produktsuche und Suchuniversum](#pb-015-search) · [Produktvergleich und bewusste Auswahl](#pb-015-comparison) · [Produktscore und fachliche Modellfamilie](#pb-015-score)

**Kontextnachtrag 25.10.2026:** Der begrenzte [FT-007-/FT-008-UI-Schnitt](../implementation/TRADE_PLAN_SELECTION_CONTEXT.md)
bindet eine ausdrücklich ausgewählte APPROVED-Version gemeinsam mit ihrem Plan.
Eine weiterhin freigegebene frühere Version bleibt auch bei neuestem DRAFT
wählbar. Gespeicherte Runs werden über ihre ursprünglichen Referenzen geöffnet;
Lesen und Reparaturrückkehr starten keine neue Bewertung oder Ausführung.
Produkteditor und Produkt-API bleiben beim parallelen Produktverwaltungsauftrag.
Die bestehenden Reparatur-/Rückkehrrouten sowie NOT_EVALUABLE-Bestätigung und
Erstkaufstrecke sind beim Zusammenführen beider Branches erneut zu prüfen.

<a id="pb-015-search"></a>
<details>
<summary>PB-015 — Produktsuche und Suchuniversum</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktsuche. Bereich/Querschnitt: 4. Bestehender Bezug: FT-008; FT-004 Stammdaten; TC-001. Lieferziel: A. |
| Arbeitsstatus | Released (persistiertes internes Produktuniversum); Analysis (weitergehende Beschaffungsabdeckung) |
| Abgeschlossener Teilumfang | Internes Such-/Bewertungsuniversum aus gespeicherten Produkten und aktuellen Terms/Listings implementiert. |
| Soll / Nicht-Soll | **Soll:** Produkte und gültige Terms/Listings für die konkrete freigegebene Planversion nachvollziehbar ermitteln. **Nicht-Soll:** Provider-Discovery ist keine stabile Produktidentität und keine Eignungsbestätigung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Daten/Entscheidung für weitergehende Suche, Prüfung. |
| Implementierung / Consumer | [backend/app/features/product_selection/service/application.py](../../backend/app/features/product_selection/service/application.py) start_run liest konkrete APPROVED-Version; `_load_universe` bindet FT-004-Warrants, effektive TermsVersion und WarrantListing; [service/universe.py](../../backend/app/features/product_selection/service/universe.py) erzeugt explizite Omission-Gründe. Es wird keine vollständige externe Emittenten-Produktsuche behauptet. |
| Test / Commit | [tests/unit/backend/features/product_selection/test_universe.py](../../tests/unit/backend/features/product_selection/test_universe.py), `test_application.py`; [tests/integration/backend/test_trade_plan_product_selection_handoff.py](../../tests/integration/backend/test_trade_plan_product_selection_handoff.py); [tests/e2e/ft008-product-selection.spec.ts](../../tests/e2e/ft008-product-selection.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft008-product-selection.spec.ts](../../tests/e2e/ft008-product-selection.spec.ts) ist Browser-UI mit abgefangenem HTTP; [product-selection-confirmation-capture.spec.ts](../../tests/e2e/product-selection-confirmation-capture.spec.ts) verwendet echte Owner-APIs auf dem Wegwerfstack und prüft persistierte Ausnahmeauswahl plus BUY. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer FT-008-Teilscope/Release bleibt; keine neue fachliche Liveuniversum-Abnahme. |
| Software-Auslieferung | v1.0.0-product-selection als historische Lieferung, fortgeschrieben in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Vollständige gewünschte externe Produktabdeckung ist nicht belegt → Benutzer findet die zulässigen Produkte für seinen konkreten Plan → vorhandene FT-004-/FT-008-/TC-001-Owner → Entscheidung zum Suchuniversum und verifizierte Quellen-/Mappingrechte → definierte Instrumentmenge wird mit exakten Terms/Listings gefunden, fehlende Produkte/Quellen explizit ausgewiesen; bestehendes internes Universum nicht neu bauen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-015-comparison"></a>
<details>
<summary>PB-015 — Produktvergleich und bewusste Auswahl</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktvergleich. Bereich/Querschnitt: 4. Bestehender Bezug: FT-008. Lieferziel: A. |
| Arbeitsstatus | Released (historischer FT-008-V1-Umfang); Business Review (menschlicher Abnahmenachweis der begründeten Ausnahmeauswahl); Implementierung, technische Qualifikation und Auslieferung abgeschlossen. |
| Abgeschlossener Teilumfang | Der alte technische Rest „Ausnahmeweg durch API/UI und Tests prüfen“ ist erledigt. Vergleich/Auswahl ist tatsächlich durchgängig implementiert. |
| Soll / Nicht-Soll | **Soll:** Inputs, Kriterien, Datenzustände und exakte Produktversionen erklären; Auswahl bleibt Benutzerentscheidung. **Nicht-Soll:** Vergleich ist kein numerischer Produktscore. Eine begründete Ausnahme bestätigt keine Eignung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachabnahme/Daten. |
| Implementierung / Consumer | `ProductSelectionService` berechnet Referenz-/Kurskriterien, Inputs/Metrics und Eligibility; `ProductSelectionCommandService.select_product` persistiert eine Nutzerwahl je gespeicherten Run. `ProductSelection.from_user_decision` verbietet INELIGIBLE, fordert für NOT_EVALUABLE Begründung. ProductSelectionPage.confirmSelection fordert bewussten Dialog und rationale, erhält konkrete historische Run-/Planversion. |
| Test / Commit | [tests/unit/backend/features/product_selection/test_commands.py](../../tests/unit/backend/features/product_selection/test_commands.py), `test_domain.py`; [tests/e2e/ft008-product-selection.spec.ts](../../tests/e2e/ft008-product-selection.spec.ts) prüft fehlende Quotes+Ausnahme, eligible Quote+Bestätigung und historische Planversion; [tests/e2e/product-selection-confirmation-capture.spec.ts](../../tests/e2e/product-selection-confirmation-capture.spec.ts) verbindet bestätigte Auswahl mit genau einem BUY. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft008-product-selection.spec.ts](../../tests/e2e/ft008-product-selection.spec.ts) ist Browser-UI mit abgefangenem HTTP; [product-selection-confirmation-capture.spec.ts](../../tests/e2e/product-selection-confirmation-capture.spec.ts) verwendet echte Owner-APIs auf dem Wegwerfstack und prüft persistierte Ausnahmeauswahl plus BUY. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische V1-ELIGIBLE-only-Aussage bleibt historisch; heutige begründete Ausnahme technisch nachgewiesen, keine nachträgliche Eignungsbestätigung durch Auswahl. Menschlicher Ausnahme-Abnahmebeleg nicht verifiziert. |
| Software-Auslieferung | Historisch v1.0.0-product-selection; spätere Ausnahme-/Bestätigungstrecke in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Abnahme der Ausnahmeinterpretation und reale Kursabdeckung fehlen → Benutzer versteht ausdrücklich nicht auswertbare Auswahl ohne behauptete Eignung → vorhandener FT-008-/TC-001-Owner → repräsentative Belegfälle/qualifizierte Quotes → datierter Abnahmebeleg für ELIGIBLE, NOT_EVALUABLE mit Begründung und verbotene INELIGIBLE-Auswahl, Quellenlücken unverändert sichtbar. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-015-score"></a>
<details>
<summary>PB-015 — Produktscore und fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktscore; M9: Produktscore. Bereich/Querschnitt: 4; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-008; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis (ursprünglicher Produktscore offen) |
| Abgeschlossener Teilumfang | Kriterienbasierte Eligibility/Comparison ist implementierte Vorleistung. |
| Soll / Nicht-Soll | **Soll:** Ein Produktscore benötigt definierte Bedeutung, Eingaben, Parameter, Modellversion und nachvollziehbare Validierung. **Nicht-Soll:** Allgemeine EvaluationMetric-Felder, Eligibility oder Sortierung sind kein fertiger Score. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fehlende Funktion plus fachliche Entscheidung/Daten. |
| Implementierung / Consumer | Der tatsächliche FT-008-Applicationpfad erzeugt CriterionResult/EvaluationMetric und EligibilityStatus; ProductEvaluation besitzt keinen numerischen Gesamtscore und kein Rankingmodell. ProductSelection ist eine Nutzerentscheidung; allgemeine Modellreferenzen sind kein implementierter Score. |
| Test / Commit | Eligibility-/Comparison-Tests vorhanden; kein Score-Referenzdatensatz oder getesteter fachlicher Scoreconsumer. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Keine belegte Produktscoredefinition/Freigabe und keine dauerhafte Entfernung des ursprünglichen M4/M9-Ziels. |
| Software-Auslieferung | Kein gesonderter Produktscore-Liefernachweis in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Bedeutung/Formel/Gewichte/Fehldatensemantik des Produktscores fehlen → Benutzer erhält nachvollziehbare vergleichbare Produktauswertung → bestehender FT-008-Owner, FT-013 als Governance → Modellverantwortlicher legt Inputs, Versionierung und Validierungsdaten fest → freigegebener Vertrag und reproduzierbare Referenzfälle inklusive fehlender Quotes, erklärbarer Ergebnisconsumer und separate Nutzerwahl. |
| Umfangsentscheidung | Im engeren S8-V1 nicht freigegeben; das ist keine belegte Entfernung aus dem ursprünglichen Zielbild. Originalanspruch bleibt offen. |

</details>

### PB-016

[Trade eröffnen und tatsächliche Käufe erfassen](#pb-016-opening) · [Depot und abgeleitete offene Positionen](#pb-016-positions)

<a id="pb-016-opening"></a>
<details>
<summary>PB-016 — Trade eröffnen und tatsächliche Käufe erfassen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Trade eröffnen. Bereich/Querschnitt: 5. Bestehender Bezug: FT-009. Lieferziel: A, B. |
| Arbeitsstatus | Released (Kauf-/Währungs-/UX1-A-Implementierung); Business Review (Nutzerabnahme) |
| Abgeschlossener Teilumfang | Bestätigte Erst-/Nachkäufe, exakte Herkunft, atomare Währungsbelege und UX1-A-Wiederverwendung technisch vorhanden. |
| Soll / Nicht-Soll | **Soll:** Bestätigte Erst-/Nachkäufe als immutable Ausführungsfakten erfassen, Herkunft exakt behalten. **Nicht-Soll:** Keine Brokerorder, autonome Produktauswahl oder Mengenempfehlung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme; begrenzter Nebenläufigkeitsbefund offen. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). [tests/integration/backend/test_product_selection_trade_position_handoff.py](../../tests/integration/backend/test_product_selection_trade_position_handoff.py), [tests/e2e/product-selection-confirmation-capture.spec.ts](../../tests/e2e/product-selection-confirmation-capture.spec.ts), [trade-capture-safety.spec.ts](../../tests/e2e/trade-capture-safety.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische FT-009-Freigaben und enger UX1-A-Auftrag erhalten; neue menschliche Abnahme nicht dokumentiert. |
| Software-Auslieferung | v1.1.0-trade-position; UX1-A [#318](https://github.com/burckhju/trading-workspace/pull/318)/v1.5.37 auf `bb49ffe781933270746b9f86f4aee99b6f8144c2`; enthalten in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Währungs-/Captureabnahme fehlt und paralleler erstmaliger Learning-execute-as-trade-Aufruf mit identischem Key ist nur statisch als möglicher generischer 422 statt Replay beschrieben → verlässliche einmalige Erfassung mit richtiger Währung → vorhandener FT-009-/Learning-Handoffowner → isolierter synthetischer Parallelfall sowie bestätigte Währungsquelle → datierte Abnahme und reproduzierter Paralleltest weist genau eine Anlage, atomare Währung und vertragliche Replay-/Fehlerantwort nach; keine Wiederimplementierung des sequentiellen Replay. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Abgegrenzter UX-1-Nachtrag 31.10.2026:** Der aktuelle Auftrag autorisiert Umsetzung,
isolierte Qualifikation und einen Draft-Integrations-PR, keinen Merge, Release oder
PC-Update. Die [Feldinventur und Prüfnachweise](../implementation/UX1_INPUT_REUSE_QUALIFICATION.md)
trennen vorhandene Wiederverwendung von der neuen lesenden Währungsvorschau vor
Erstkauf/Nachkauf/Verkauf. Automatische Herkunft wird niemals als manuelle Bestätigung
gespeichert. Unabhängige Folgechangesets betreffen den einzigen gespeicherten
Bewertungslauf einer Planversion und den Browserzonen-Vorschlag für Performance.
Journal-/Lessonquellen werden bereits übernommen; keine erfundenen Bewertungen.

**Technischer UX-1-Nachtrag 01.11.2026:** Der damalige Implementierungsauftrag oben
bleibt historisch. Der abgegrenzte UX1-A-Schnitt wurde inzwischen gemeinsam mit
UX2-A in [#318](https://github.com/burckhju/trading-workspace/pull/318) integriert
und als `v1.5.37` auf `bb49ffe781933270746b9f86f4aee99b6f8144c2` veröffentlicht.
Der [Auslieferungsnachweis](../implementation/UX1_INPUT_REUSE_QUALIFICATION.md#ux1-delivery-1-5-37)
belegt den behobenen Previewbefund sowie getrennte PR-, Main- und Publisherprüfungen.
Er erzeugt keine neue menschliche Abnahme und keinen PC-Betriebsnachweis.

</details>

</details>

<a id="pb-016-positions"></a>
<details>
<summary>PB-016 — Depot und abgeleitete offene Positionen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Depot. Bereich/Querschnitt: 5. Bestehender Bezug: FT-009, durch FT-010 weiterentwickelter gemeinsamer Execution-/Position-Vertrag. Lieferziel: A, C. |
| Arbeitsstatus | Released (Positionsprojektion und Währungsqualifikation); Business Review (reale Bestandsabnahme) |
| Abgeschlossener Teilumfang | Reproduzierbare offene Mengen/Kostenbasis und ausgelieferte Währungsqualifikation abgeschlossen; alter ausstehender Releaseauftrag v1.5.30 erledigt. |
| Soll / Nicht-Soll | **Soll:** Offene Mengen und Einstand aus effektiven Ausführungsfakten reproduzierbar darstellen. **Nicht-Soll:** Positionsübersicht ist weder Brokerdepot-Synchronisation noch vollständige Depot-Equity. |
| Befundklasse / Lückenart | Vorhandene Funktion; reale Daten-/Entscheidungsblockade oder fehlender Betriebswirkungsnachweis einer ausgelieferten Korrektur; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Daten/Prüfung. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. [service/valuation_basis.py](../../backend/app/features/trade_position/service/valuation_basis.py) qualifiziert beitragende Kaufwährungen; fehlend/gemischt/quoteabweichend ist nicht Null-PnL. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). [tests/unit/backend/features/trade_position/test_historical_position_valuation_basis.py](../../tests/unit/backend/features/trade_position/test_historical_position_valuation_basis.py), [tests/e2e/position-currency-qualification.spec.ts](../../tests/e2e/position-currency-qualification.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Enger Gleichwährungsvertrag 28.10. freigegeben; menschliche reale Bestandsabnahme weiterhin nicht belegt. |
| Software-Auslieferung | [#297](https://github.com/burckhju/trading-workspace/pull/297) `1f6ca802df25b2d508338ac837fdfb39ac79eca2`; Tag v1.5.30 tatsächlich `7a3a583d236be128957999a34ae0854911bc6a40`; enthalten in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Historische Kaufwährungs-/Preisquellen im realen Bestand teils unbelegt → nachvollziehbare bewertbare Position oder konkreter Nichtberechenbarkeitsgrund → vorhandener Execution-/Position-/TC-001-Owner → lesende Diagnose und unveränderte Originalbelege → je betroffener Position Kostenbasisbeiträge/Quotewährung/Quellenbindung nachvollziehbar, keine erfundene EUR- oder FX-Ergänzung; Bestandsänderung nur als gesonderter Auftrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**UI4-Fortschreibung vom 26.10.2026:** Die
[Konsolidierung von Tradeübersicht und Buchungen](../implementation/UI_TRADE_BOOKINGS_CONSOLIDATION.md)
führt Produktbezug, Trade-Status, offene Menge, Datumsangaben und bestehende
Backendpositionsergebnisse in einer Übersicht zusammen. Status und offene Menge
erscheinen im Überblick jeweils einmal; unbekannte Werte werden nicht zu Null.
Die Änderung arbeitet auf `f8f61a11f65e9b36735704a2fabc3e4e953d4a77` / 1.5.21
und erhält die Positionsrechnung des Owners. Der Draft-PR bindet den finalen
Implementierungscommit und die tatsächlich abgeschlossenen Prüfungen. Kein neuer
Depot-/Performanceumfang, keine Statushochsetzung oder Auslieferung durch UI4.

**Nachfolgende Freigabe vom 26.10.2026:** Der gemeinsame Stand nach UI3 soll bei
grünen Prüfungen integriert und als **1.5.22** für den PC bereitgestellt werden.
Der [Integrationsnachtrag](../implementation/UI_TRADE_BOOKINGS_CONSOLIDATION.md#nachtrag-26102026-freigegebene-integration-und-pc-bereitstellung)
bindet diesen Folgeauftrag getrennt von der ursprünglichen Draft-Übergabe.
Fachlicher Arbeitsstatus und ausstehender Zielbetriebsnachweis bleiben erhalten.

**Liefernachtrag 28.10.2026:** Die ursprüngliche Beschränkung auf einen überprüfbaren
PR bleibt historisch erhalten. Die neue ausdrückliche Nutzerfreigabe erlaubt
Integration bei grünen Prüfungen und versionierte PC-Bereitstellung.
Implementierungsmerge `1f6ca802df25b2d508338ac837fdfb39ac79eca2` und geprüfter
#297-Head haben denselben Tree `93de00ad0e5bd8e66c666e5cd4efcb3f23c59781`.
Bei Anlage dieses Nachtrags war v1.5.30 noch nicht veröffentlicht. Der
[Releasevertrag](../releases/V1.5.30-POSITION-PNL-CURRENCY.md) trennt neue
Releaseprüfungen, tatsächlichen Tag und spätere PC-Installation.

</details>

</details>

### PB-017

[Stop- und Zielmanagement](#pb-017-stop) · [Teilverkäufe](#pb-017-partial) · [Vollverkauf und Abschluss](#pb-017-close) · [Event-Historie und historische Korrekturen](#pb-017-history) · [Produktwechsel](#pb-017-product-change) · [Positionsbezogenes realisiertes Brutto-PnL](#pb-017-gross-pnl)

<a id="pb-017-stop"></a>
<details>
<summary>PB-017 — Stop- und Zielmanagement</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Stopmanagement. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Released (technisch ausgelieferter FT-010-Teilscope); Business Review (aktuelle Nutzerabnahme) |
| Abgeschlossener Teilumfang | Stop-/Ziel-/Thesis-/Notizevents mit unveränderlicher Historie, expliziter PriceBinding und getrenntem aktuellen Readmodel implementiert. |
| Soll / Nicht-Soll | **Soll:** Bestätigte Managemententscheidungen historisieren; für automatische Prüfung Instrument und Währung explizit binden. **Nicht-Soll:** Managementereignis ist kein SELL und überschreibt keine Planversion. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. [domain/management.py](../../backend/app/features/trade_position/domain/management.py) projiziert Stop/Target mit eigener PriceBinding. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). [tests/integration/backend/database/test_monitoring_price_binding_postgres.py](../../tests/integration/backend/database/test_monitoring_price_binding_postgres.py). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technischer Sprint-10-Closeout und historische Releasebelege erhalten; keine eigenständige neue menschliche Fachabnahme aus den technischen Gates. |
| Software-Auslieferung | Tag `v1.2.0-trade-management` zeigt auf `9be01b334e3a1134b412b157c7fd2f17e981f9d6`; aktuelle Implementierung in v1.5.52. Der historische Text READY FOR RELEASE TAG ist kein aktueller Lieferblocker. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Abnahme der Preisachsendarstellung fehlt → Nutzer erkennt gültigen Stop/Ziel einschließlich Instrument und Währung → vorhandener FT-010-Managementowner/Monitoringconsumer → gebundene und Legacy-ungebundene Referenzregeln → dokumentierter Abnahmefall zeigt bindende Achse und weist ungebundene Altregel als unprüfbar aus; keine Deutung durch Währungsgleichheit. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-partial"></a>
<details>
<summary>PB-017 — Teilverkäufe</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Teilverkauf. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Released (technisch ausgelieferter FT-010-Teilscope); Business Review (aktuelle Nutzerabnahme) |
| Abgeschlossener Teilumfang | SELL kleiner als offene Menge reduziert Position und Kostenbasis deterministisch; unveränderte BUY/SELL-Fakten bleiben erhalten. |
| Soll / Nicht-Soll | **Soll:** SELL kleiner als offene Menge erzeugt einen Teilverkauf und reproduzierbare Restposition. **Nicht-Soll:** Keine negative Position und kein impliziter SHORT. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technischer Sprint-10-Closeout und historische Releasebelege erhalten; keine eigenständige neue menschliche Fachabnahme aus den technischen Gates. |
| Software-Auslieferung | Tag `v1.2.0-trade-management` zeigt auf `9be01b334e3a1134b412b157c7fd2f17e981f9d6`; aktuelle Implementierung in v1.5.52. Der historische Text READY FOR RELEASE TAG ist kein aktueller Lieferblocker. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Bedienabnahme des aktuellen Teilverkaufs-/Korrekturwegs fehlt → korrekter Restbestand und verständliche Realisation → vorhandener Execution-/Positionowner → synthetischer Teilverkauf mit Preis-/Währungsbeleg → datierter Abnahmefall bestätigt Restmenge, Average Cost, Realisation und erhaltene Historie; technische Mengen-/Replay-/Korrekturtests sind vorhanden. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-close"></a>
<details>
<summary>PB-017 — Vollverkauf und Abschluss</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Trade schließen. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Released (technisch ausgelieferter FT-010-Teilscope); Business Review (aktuelle Nutzerabnahme) |
| Abgeschlossener Teilumfang | Vollverkauf führt aus effektiver Historie zu Menge null/CLOSED und FT-011-Eignung; kein separat editierbarer CLOSED-Status. |
| Soll / Nicht-Soll | **Soll:** Realer voller SELL schließt wirtschaftlich durch effektive Historie; FT-011 erst danach. **Nicht-Soll:** Kein unabhängig editierbarer CLOSED-Status und keine virtuelle Ausführung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technischer Sprint-10-Closeout und historische Releasebelege erhalten; keine eigenständige neue menschliche Fachabnahme aus den technischen Gates. |
| Software-Auslieferung | Tag `v1.2.0-trade-management` zeigt auf `9be01b334e3a1134b412b157c7fd2f17e981f9d6`; aktuelle Implementierung in v1.5.52. Der historische Text READY FOR RELEASE TAG ist kein aktueller Lieferblocker. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Menschliche Abnahme des Abschluss→Nachbeobachtung-Wechsels fehlt → Benutzer beginnt Lernen erst nach wirtschaftlich geschlossenem Trade → FT-009/010→FT-011-Consumer → synthetischer Vollverkauf plus Korrekturfall → dokumentierte Reise zeigt passenden geschlossenen Trade und verhindert FT-011 nach einer wieder offenen effektiven Historie; keine Neuimplementierung des Handoffs. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-history"></a>
<details>
<summary>PB-017 — Event-Historie und historische Korrekturen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Event-Historie. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Released (technisch ausgelieferter FT-010-Teilscope); Business Review (aktuelle Nutzerabnahme) |
| Abgeschlossener Teilumfang | Unveränderliche Execution-/Managementereignisse, Supersession und zusammengesetzte Timeline ohne doppelte SELL-Wahrheit implementiert. |
| Soll / Nicht-Soll | **Soll:** Ausführungen und Managementevents unveränderlich erhalten; Korrektur/Supersession leitet aktuellen Zustand neu ab. **Nicht-Soll:** Keine zweite Verkaufstatsache in der Timeline, kein Überschreiben historischer Fakten. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Fachabnahme. |
| Implementierung / Consumer | [backend/app/features/trade_position/service/application.py](../../backend/app/features/trade_position/service/application.py) steuert record_initial_purchase/record_external_purchase/record_additional_purchase/record_sale, Korrekturen und Managementevents über UoW. [domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) prüft effektive BUY/SELL-Reihenfolge, gleiche Produkt-ID, Mengen und Average Cost; [backend/app/features/trade_position/persistence/repositories.py](../../backend/app/features/trade_position/persistence/repositories.py) liefert effektive Historie. TradeManagementPage/ExecutionDatesPanel konsumieren bestehende API. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_application.py](../../tests/unit/backend/features/trade_position/test_application.py), [test_projector.py](../../tests/unit/backend/features/trade_position/test_projector.py), [test_corrections_timeline.py](../../tests/unit/backend/features/trade_position/test_corrections_timeline.py); [tests/e2e/ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts), [trade-execution-corrections.spec.ts](../../tests/e2e/trade-execution-corrections.spec.ts), [trade-timeline.spec.ts](../../tests/e2e/trade-timeline.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Prüfgrenze: [ft010-trade-management.spec.ts](../../tests/e2e/ft010-trade-management.spec.ts) ist Browser-UI mit abgefangenem HTTP; Domain-/Service- und native PostTrade-/Reportowner-Journeys sind getrennte Belege für echte Verarbeitung/Persistenz. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technischer Sprint-10-Closeout und historische Releasebelege erhalten; keine eigenständige neue menschliche Fachabnahme aus den technischen Gates. |
| Software-Auslieferung | Tag `v1.2.0-trade-management` zeigt auf `9be01b334e3a1134b412b157c7fd2f17e981f9d6`; aktuelle Implementierung in v1.5.52. Der historische Text READY FOR RELEASE TAG ist kein aktueller Lieferblocker. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Fachliche Abnahme der Auswirkungen historischer Korrekturen auf Review/Learning fehlt → Nutzer erkennt alte Fakten und heutigen wirksamen Stand → FT-010-Historienowner plus FT-011/012-Currentnessconsumer → geschlossener Referenztrade mit Review/Evidence und nachträglicher Korrektur → datierter Fall weist Original-/Folgeversionen und veraltete Ableitungen nach; Currentnessrest beim bestehenden PB-018-Anker führen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**UI4-Fortschreibung vom 26.10.2026:** Ein gemeinsamer Timeline-Read versorgt
„Aktuelle Buchungen“, die ersetzende schreibgeschützte Historie und genau einen
an die ausgewählte wirksame Execution gebundenen Datum-/Währungseditor.
Die bisherige zweite Timeline unter Alerts und der zusätzliche Stornierungszweig
entfallen. Originale, Korrekturverknüpfungen, Erfassungszeiten und Währungsquellen
bleiben erhalten. Der gemeinsame Navigationsschutz, die gesonderten Retry-/Replay-
Verträge und der Erhalt paralleler Managemententwürfe sind im
[UI4-Implementierungs- und Qualifikationsnachweis](../implementation/UI_TRADE_BOOKINGS_CONSOLIDATION.md)
mit Akzeptanzfällen und konkreten Tests dokumentiert. Abschließender Prüfstand im
Draft-PR mit Commit-/Treebezug; native PostgreSQL- und geroutete UI-Mockbelege werden
getrennt ausgewiesen. Die historischen Nachweise oben behalten ihren Codebezug.
Keine allgemeine Mengen-/Preis-/Seiten- oder historische Managementkorrektur-UI,
keine automatische Review-/Journal-/Lesson-Neubindung und kein Merge/Release
werden mit diesem begrenzten Schnitt behauptet.

**Nachfolgende Freigabe vom 26.10.2026:** Die Nutzeranweisung zur Integration bei
grünen Prüfungen und zur PC-Bereitstellung erweitert die ursprüngliche
Übergabegrenze. **1.5.22** erhält einen neuen Nachweis des gemeinsamen Stands mit
UI3, anschließend die regulären Main-Gates und den bestehenden Tag-Publisher.
Commit-, Tree- und Workflowbezüge werden in
[PR #287](https://github.com/burckhju/trading-workspace/pull/287) festgehalten;
Softwarebereitstellung, fachliche Abnahme und tatsächlich installierter PC-Stand
bleiben getrennt. Die ursprünglichen historischen Nachweise oben bleiben erhalten.

</details>

</details>

<a id="pb-017-product-change"></a>
<details>
<summary>PB-017 — Produktwechsel</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktwechsel. Bereich/Querschnitt: 4, 5. Bestehender Bezug: FT-008/FT-010; Umsetzungseigentum erst nach Entscheidung, keine neue Paketgrenze. Lieferziel: B. |
| Arbeitsstatus | Analysis (ursprünglicher Produktwechsel offen) |
| Abgeschlossener Teilumfang | Erfassung realer SELLs und BUYs ist vorhandene Vorleistung. |
| Soll / Nicht-Soll | **Soll:** Wechsel zwischen konkreten Produkten erhält wirtschaftliche SELL-/BUY-Fakten, Planherkunft und verständliche Trade-Identität. **Nicht-Soll:** Kein PRODUCT_CHANGED-Ereignis, das Ausführungen verdeckt; keine Mutation von Trade.product_id. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fehlende Funktion plus fachliche Entscheidung. |
| Implementierung / Consumer | [docs/features/FT-010_TRADE_MANAGEMENT.md](../../docs/features/FT-010_TRADE_MANAGEMENT.md), Abschnitt Product change boundary, schließt Produktwechsel im V1-Scope ausdrücklich aus. PositionProjector verlangt jede Execution.product_id == Trade.product_id; es gibt keine Wechselbeziehung und keinen PRODUCT_CHANGED-Managementtyp. Unabhängiger SELL/BUY ist keine vollständige Produktwechselreise. |
| Test / Commit | FT-010-Tests prüfen gleiche Produktidentität und wirtschaftliche Fakten; kein Test einer expliziten Wechselbeziehung. Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Gesonderter Trade-Identitäts-/Korrekturentscheid und ADR laut FT-010 erforderlich; keine dokumentierte Entfernung von M4. |
| Software-Auslieferung | Kein eigenständiger Produktwechselrelease. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Trade-Identität/Verknüpfung bei Produktwechsel fehlen → Benutzer kann Wechsel nachvollziehen, ohne Ausführungsfakten oder Planherkunft zu verlieren → vorhandener FT-009/010-Owner und FT-008-Consumer → Product Owner entscheidet getrennte Trades versus explizite Wechselbeziehung, Korrektur-/Lernsemantik → ADR, Akzeptanzfälle und implementierter Pfad erhalten beide realen SELL-/BUY-Fakten, exakte Produkt-/Planversionen und historische Korrekturen; keine Mutation von Trade.product_id. |
| Umfangsentscheidung | Belegt: nicht Teil von FT-010 V1. Nicht belegt: dauerhafte Verschiebung/Entfernung aus M4. Dieser Eintrag verantwortet die Restklärung; PB-015 verweist nur hierher. |

</details>

<a id="pb-017-gross-pnl"></a>
<details>
<summary>PB-017 — Positionsbezogenes realisiertes Brutto-PnL</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: abgeleitetes Positionsergebnis; Vorleistung für M8. Bereich/Querschnitt: 5, 8. Bestehender Bezug: FT-010 auf FT-009 Execution-/Position-Vertrag. Lieferziel: C. |
| Arbeitsstatus | Released (realisierte Brutto-/Währungsqualifikation); Business Review (reale Datenabnahme) |
| Abgeschlossener Teilumfang | Positions-Bruttorechnung, historische Währungsqualifikation und bereits veröffentlichte v1.5.30/31-Teile abgeschlossen. Alte Releasebereitstellungsreste nicht fortführen. |
| Soll / Nicht-Soll | **Soll:** Realisiertes Brutto-PnL und Einstand aus effektiven BUY-/SELL-Fakten nach bestehender Average-Cost-Semantik ableiten. **Nicht-Soll:** Keine Gebühren, Steuern, Nettoerträge, Depot-Equity oder tradeübergreifende Performance erfinden. |
| Befundklasse / Lückenart | Vorhandene Funktion; reale Daten-/Entscheidungsblockade oder fehlender Betriebswirkungsnachweis einer ausgelieferten Korrektur; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Daten/Prüfung. |
| Implementierung / Consumer | [backend/app/features/trade_position/domain/projector.py](../../backend/app/features/trade_position/domain/projector.py) verwendet Average Cost und SELL-Beiträge; [service/currency_evidence.py](../../backend/app/features/trade_position/service/currency_evidence.py), `currency_confirmations.py`, [valuation_basis.py](../../backend/app/features/trade_position/service/valuation_basis.py) und Domain-Währungsresolver qualifizieren historische Kaufwährungen statt sie aus heutiger Quote zu erfinden. Bereits bestätigte Quellen werden wiederverwendet; keine Netto-/FX-/Equityrechnung. |
| Test / Commit | [tests/unit/backend/features/trade_position/test_projector_trace.py](../../tests/unit/backend/features/trade_position/test_projector_trace.py), [test_currency_evidence_owner.py](../../tests/unit/backend/features/trade_position/test_currency_evidence_owner.py), [test_historical_position_valuation_basis.py](../../tests/unit/backend/features/trade_position/test_historical_position_valuation_basis.py), [test_historical_currency_resolution.py](../../tests/unit/backend/features/trade_position/test_historical_currency_resolution.py); [tests/e2e/realized-gross-report-postgres.spec.ts](../../tests/e2e/realized-gross-report-postgres.spec.ts), [execution-currency-reuse.spec.ts](../../tests/e2e/execution-currency-reuse.spec.ts). Wesentliche Assertion-/Guardpfade in der Erstprüfung gelesen; unveränderte Pfade durch den Main-Deltaabgleich bestätigt. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | V1-Währungs-/Periodenvertrag 17.10. und Wiederverwendung 20.10. sowie [#297](https://github.com/burckhju/trading-workspace/pull/297)/#298/Releasefreigaben erhalten; reale Quellen-/Fachabnahme separat. |
| Software-Auslieferung | v1.5.9 `254fe35b76027b72cd989715e17bd0ae55af55eb`; v1.5.30 `7a3a583d236be128957999a34ae0854911bc6a40`; v1.5.31 tatsächlich `5f1b675e09bd993da8e0576067e3e466c5b5bbdb`; sämtliche Teile in v1.5.52. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 auf dem PC am 19.11.2026; eine gesonderte Bedien-/Fachabnahme dieser Teilfähigkeit ist daraus nicht ableitbar. |
| Restarbeit / nächste Abhängigkeit | Historische Währungs-/Kostenbasisquellen des realen Bestands fehlen teils → Benutzer sieht belastbare Bruttowerte oder konkreten Nichtberechenbarkeitsgrund → vorhandener Execution-/Positionowner, FT-012-Performance als Leser → Originalausführungsbelege und lesender Bestandsnachweis → jede betroffene Kostenbasis ist quellengenau qualifiziert oder explizit unbekannt; Fachabnahme bestätigt Brutto-/Währungsgrenzen. Weitere Performanceanforderungen bei PB-019, keine erneute Bruttoimplementierung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Fortschreibung 28.10.2026:** Der [enge laufende Bewertungsvertrag samt tatsächlicher Qualifikation](../implementation/POSITION_VALUATION_CURRENCY_QUALIFICATION.md)
verwendet denselben Ownerprojektor und Resolver auf Basis Main `dc89dfa65758dfc1258a8fab657257f6598b0179`
/ 1.5.29. Marktwert und PnL sind getrennt qualifiziert; unbekannte, gemischte
oder abweichende Kaufkostenwährungen liefern fehlendes PnL mit Grund.
Der Vertrag wurde vor der Implementierung festgelegt; Rot-/Grünnachweise und
die lokalen regulären Gates sind inzwischen erbracht. Die Nachweisdokumentation
bindet die tatsächlich geprüften lokalen Commits und die identischen
veröffentlichten Trees. Aktuelle headgebundene CI-Ergebnisse und Reviewbereitschaft:
[PR #297](https://github.com/burckhju/trading-workspace/pull/297).
Historische Nachweise und Freigaben oben beziehen sich auf ihre früheren Schnitte;
der ursprüngliche PR-Auftrag erlaubte keine Integration, Veröffentlichung oder
Installation. Fachabnahme und reale Quellenabdeckung bleiben offen; Consumerstatus
in [PB-016](#pb-016-positions).

**Liefernachtrag 28.10.2026:** Mit **„wenn grün mergen und für den PC bereitstellen“**
liegt nun eine eigene Freigabe für diesen Währungsfix vor. [PR #297](https://github.com/burckhju/trading-workspace/pull/297)
ist auf `1f6ca802df25b2d508338ac837fdfb39ac79eca2` integriert.
[v1.5.30](../releases/V1.5.30-POSITION-PNL-CURRENCY.md) hält die neue
Veröffentlichungsqualifikation getrennt von den historischen Lieferbelegen oben.
Bei Anlage des Nachtrags noch kein veröffentlichter v1.5.30-Tag und kein
PC-Installationsnachweis; unveränderter Finanz-/Währungsvertrag.

**Liefernachtrag 28.10.2026 zu v1.5.31:** [PR #298](https://github.com/burckhju/trading-workspace/pull/298)
ist nach grüner CI auf `271d2abbad076c867352297b96e29b6aa4b19092` integriert.
Der [historische Quellenvertrag mit Integrations- und Prüfbelegen](../implementation/HISTORICAL_EXECUTION_CURRENCY.md)
ergänzt die automatische Wiederverwendung einmal geprüfter Quellen in
Performanceberichten und laufender Positionsbewertung. Heutige EUR-Listings
allein reichen weiterhin nicht. Der Auftrag **„Update für pc bereitstellen“**
autorisiert den [engen Release v1.5.31](../releases/V1.5.31-HISTORICAL-EXECUTION-CURRENCY.md).
Bei Anlage dieses Nachtrags steht dessen Veröffentlichung noch aus; Release-PR,
Main, Publisher und tatsächlicher Tag-/Commitbezug erhalten eigene Belege.
Keine PC-Installation, produktive Datenkorrektur oder vollständige M8-Abnahme.

</details>

</details>

### PB-018

[Zulässige Nachbeobachtung](#pb-018-observation) · [Virtuelle Weiterführung](#pb-018-virtual) · [Exit Review und Handoff](#pb-018-review) · [Vergleich tatsächlicher und virtueller Ausstiege](#pb-018-exit-comparison) · [Korrekturen, Review-Currentness und historische Herkunft](#pb-018-currentness)

<a id="pb-018-observation"></a>
<details>
<summary>PB-018 — Zulässige Nachbeobachtung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Nachbeobachtung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Released — implementierter FT-011-V1-Start technisch abgeschlossen; Business Review der fachlichen Nutzung offen. |
| Abgeschlossener Teilumfang | Wirtschaftliches Exitgate, Listingauflösung und persistierter Start; die alte allgemeine Aufforderung, echte Persistenz erst nachzuweisen, ist durch vorhandene PostgreSQL-/Owner-Browserfälle erledigt. |
| Soll / Nicht-Soll | **Soll:** Nachbeobachtung startet nur nach tatsächlichem vollständigem wirtschaftlichem Exit und mit historischem Produkt-/Listingkontext. **Nicht-Soll:** Kein Beobachtungsstart allein durch manuell gesetzten Abschlussstatus; keine neue reale Position. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; reale Datenversorgung. |
| Implementierung / Consumer | PostTradeObservationService.start in [backend/app/features/post_trade/application/observation_service.py](../../backend/app/features/post_trade/application/observation_service.py) prüft realen Vollabschluss und historischen Produktkontext, löst das Basiswertlisting und persistiert genau eine Observation pro Trade über bestehende UOW. [frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx](../../frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) bindet diesen Command an; externe Trades ohne Plan sind zulässig. |
| Test / Commit | [tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py](../../tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py); [test_post_trade_repositories_postgres.py](../../tests/integration/backend/post_trade/test_post_trade_repositories_postgres.py) (Unique-Observation, Persistenz, Rollback); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts) und [post-trade-evidence-history-postgres.spec.ts](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts) (echte BUY/SELL, verweigerter Frühstart). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Dokumentierter FT-011-V1-Vertrag und historische Acceptance-Matrizen gelten für ihren Umfang. Keine neue menschliche fachliche Nutzungsabnahme gefunden. Historische Baseline [docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md](../../docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md): Accepted after repository-first S11 review; [docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md](../../docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md): damalige 35/35 AT-S11, 107 Unit-/11 PostgreSQL-Fälle und vollständiges Backendgate PASS. Dieser damalige V1-Umfang bleibt anerkannt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende fachliche Betriebsabnahme für reale geschlossene Trades → Benutzer kann zulässige Beobachtung samt historischem Listing nachvollziehen → FT-011 post_trade, lesend FT-009/010 und FT-004 → freigegebener realer Vollabschluss und belegte Listingbindung → protokollierter Start-/Wiederholungs-/Nicht-zulässig-Fall mit unveränderten wirtschaftlichen Fakten; fehlende Kursversorgung ausdrücklich als Datenrest dokumentieren. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-virtual"></a>
<details>
<summary>PB-018 — Virtuelle Weiterführung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Virtuelle Weiterführung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Released — 20-EOD-Evidenzberechnung abgeschlossen; Business Review des breiteren ursprünglichen Vergleichsanspruchs offen. |
| Abgeschlossener Teilumfang | 20-EOD-Auswahl, Extremwerte, Schluss und Levelkreuzung mit ehrlicher Unvollständigkeit. |
| Soll / Nicht-Soll | **Soll:** Der definierte Nachbeobachtungshorizont verwendet nachvollziehbare gespeicherte Beobachtungsdaten. **Nicht-Soll:** Keine virtuellen Daten als reale Ausführung, keine erfundene historische Warrant-Equity. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung/Abnahme; Datenversorgung. |
| Implementierung / Consumer | [backend/app/features/post_trade/domain/observation_metrics.py](../../backend/app/features/post_trade/domain/observation_metrics.py) wählt 20 reale EOD-Beobachtungen streng nach dem Exitdatum, sortiert, weist doppelte Handelstage mit Fehler zurück und synthetisiert keine fehlenden Tage. Höchst-/Tiefstwert, letzter Schluss und erste Ziel-/Stopkreuzungen werden berechnet. observation_service.refresh liest gespeicherte DailyPrices und schließt erst bei vollständigem Horizont. PostTradeReviewPage zeigt Underlying-Nachbeobachtung neben tatsächlichem Exit. Kein hypothetisches Warrant-PnL. |
| Test / Commit | [tests/unit/backend/features/post_trade/test_observation_metrics.py](../../tests/unit/backend/features/post_trade/test_observation_metrics.py); [test_acceptance_contracts.py](../../tests/unit/backend/features/post_trade/test_acceptance_contracts.py) (Laufzeitende kürzt Underlying-Horizont nicht); [tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py](../../tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py); Owner-E2E 19→20. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Fester FT011_V1_OBSERVATION_COUNT=20 ist implementierter dokumentierter V1-Vertrag. Gesamtumfang von „virtueller Weiterführung“ bleibt gegen ursprüngliches M6 fachlich zu bestätigen; keine Warrant-Rendite aus Basiswertdaten ableiten. Historische Baseline [docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md](../../docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md): Accepted after repository-first S11 review; [docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md](../../docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md): damalige 35/35 AT-S11, 107 Unit-/11 PostgreSQL-Fälle und vollständiges Backendgate PASS. Dieser damalige V1-Umfang bleibt anerkannt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Ungeklärte Vollständigkeit des M6-Vergleichs über den bestehenden 20-EOD-Umfang hinaus → Benutzer versteht, welche hypothetische Aussage der Vergleich zulässt → FT-011 post_trade und TC-001 market_data → fachlich bestätigter Preis-/Horizontvertrag und tatsächliche Datenabdeckung → dokumentierte Annahme des vorhandenen Umfangs oder präziser Erweiterungsauftrag mit Referenzfällen; keine erneute Implementierung der bestehenden EOD-Logik. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-review"></a>
<details>
<summary>PB-018 — Exit Review und Handoff</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Exit Review. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Released — Review-/Finalisierungs-/Handoffpfad technisch abgeschlossen; Business Review offen. |
| Abgeschlossener Teilumfang | Persistierter Draft→Final, nichtleere Begründung, zulässiges NOT_ASSESSABLE und genaue Handoffversion; vollständiger Browser-/DB-Bedienweg vorhanden. |
| Soll / Nicht-Soll | **Soll:** Abgeschlossene Beobachtung und finalisierte aktuelle Reviewversion erlauben einen versionsgenauen Handoff. **Nicht-Soll:** Finalisierung erzeugt keine automatische Lesson oder Modellfreigabe. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung. |
| Implementierung / Consumer | [backend/app/features/post_trade/application/exit_review_service.py](../../backend/app/features/post_trade/application/exit_review_service.py) erstellt/ändert DRAFT, finalisiert nur nach COMPLETED und erneut vollständigen Eingängen und speichert vier explizite Bewertungen, Begründung und Input-Fingerprint. [handoff_service.py](../../backend/app/features/post_trade/application/handoff_service.py) verlangt COMPLETED/FINALIZED/CURRENT und genaue Version. PostTradeReviewPage bietet Folgeversion und getrennte Currentnessprüfung; PostTradeLearningPage den bewussten Übergang. |
| Test / Commit | [tests/unit/backend/features/post_trade/test_exit_review_service.py](../../tests/unit/backend/features/post_trade/test_exit_review_service.py), [test_acceptance_contracts.py](../../tests/unit/backend/features/post_trade/test_acceptance_contracts.py), [test_handoff_service.py](../../tests/unit/backend/features/post_trade/test_handoff_service.py); [tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py](../../tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts) (Reviewfinal, Folgeversion, Journalhandoff). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische Review-/Handoffverträge erhalten; technische Validierung ersetzt keine menschliche Angemessenheitsabnahme der Bewertungen. Historische Baseline [docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md](../../docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md): Accepted after repository-first S11 review; [docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md](../../docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md): damalige 35/35 AT-S11, 107 Unit-/11 PostgreSQL-Fälle und vollständiges Backendgate PASS. Dieser damalige V1-Umfang bleibt anerkannt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende menschliche Abnahme der Reviewbedienung → Benutzer kann Exit nachvollziehbar bewerten, unbewertbare Aspekte markieren und spätere Korrekturen erklären → FT-011 post_trade → vorhandene 20-EOD-Evidence und genaue Plan-/Exitquelle → dokumentierte Fachabnahme von finalem Review, NOT_ASSESSABLE und Folgeversion; automatische Lesson/Modellfreigabe bleibt ausgeschlossen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-exit-comparison"></a>
<details>
<summary>PB-018 — Vergleich tatsächlicher und virtueller Ausstiege</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Vergleich tatsächlicher und virtueller Ausstiege. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Released — Gegenüberstellung tatsächlicher Exitfakten und Basiswert-Evidenz abgeschlossen; Analysis des weitergehenden Vergleichsumfangs. |
| Abgeschlossener Teilumfang | Vorhandene Gegenüberstellung und deren echte Datenpfade, nicht nur Router. |
| Soll / Nicht-Soll | **Soll:** Tatsächliche Exitfakten und hypothetische Nachbeobachtung mit offengelegter Preis-/Datenbasis unterscheiden. **Nicht-Soll:** Underlying-Bewegung ist nicht automatisch hypothetische Warrant-Rendite oder Gebühren-/Netto-PnL. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung; gegebenenfalls Implementierung/Daten nach Entscheidung. |
| Implementierung / Consumer | [query_service.py](../../backend/app/features/post_trade/application/query_service.py) / `read_adapters.py` liefern tatsächliche SELLs, Vollabschluss und Brutto-PnL getrennt von Basiswert-EOD. [PostTradeReviewPage.tsx](../../frontend/src/features/post_trade/pages/PostTradeReviewPage.tsx) zeigt Actual (Full Exit, PnL, Executionliste) neben Counterfactual (Highest High, Lowest Low, Final Close), Originalplan und späteren Managementlevels. [observation_metrics.py](../../backend/app/features/post_trade/domain/observation_metrics.py) liefert zusätzlich Ziel-/Stopkreuzungen. Keine bewiesene hypothetische Optionsscheinertragsrechnung. |
| Test / Commit | [tests/unit/backend/features/post_trade/test_query_service.py](../../tests/unit/backend/features/post_trade/test_query_service.py), [test_observation_metrics.py](../../tests/unit/backend/features/post_trade/test_observation_metrics.py); [PostTradeReviewPage.test.tsx](../../frontend/src/features/post_trade/pages/PostTradeReviewPage.test.tsx); PostgreSQL-Lifecycle und Journal-Ownerstrecke. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Der begrenzte V1-Vergleich ist konkret. Ob er die ursprüngliche M6-Formulierung vollständig erfüllt, benötigt eine dokumentierte Produktabnahme; keine stillschweigende Erweiterung auf Netto-/Warrant-Renditen. Historische Baseline [docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md](../../docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md): Accepted after repository-first S11 review; [docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md](../../docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md): damalige 35/35 AT-S11, 107 Unit-/11 PostgreSQL-Fälle und vollständiges Backendgate PASS. Dieser damalige V1-Umfang bleibt anerkannt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende Entscheidung zur ausreichenden Vergleichsaussage → Benutzer erhält einen fachlich erklärten Vergleich ohne falsche Gleichsetzung von Underlying und Produkt → FT-011 post_trade → Produktentscheidung zu Messgröße, Preisachse, Horizont und Datenlücken → angenommene vorhandene V1-Grenze oder eigener präziser Restauftrag mit unabhängigen Referenzwerten und benötigter Originalhistorie. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-currentness"></a>
<details>
<summary>PB-018 — Korrekturen, Review-Currentness und historische Herkunft</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5/M6/M7: historische Korrekturen als durchgängiger Vertrag. Bereich/Querschnitt: 7; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-010 → FT-011 → FT-012. Lieferziel: B, D. |
| Arbeitsstatus | Released — technische Korrektur-/Currentness-/Historienkette abgeschlossen; Business Review offen. |
| Abgeschlossener Teilumfang | Die im alten Rest geforderte echte Korrektur→Review→Evidence→Lesson-Nachweiskette ist technisch vorhanden und auf aktuellen Owner-Journeys qualifizierbar. |
| Soll / Nicht-Soll | **Soll:** Korrekturen erhalten alte Fakten und Versionen; veraltete Review-/Evidence-Kontexte bleiben erkennbar. **Nicht-Soll:** Keine nachträgliche Umschreibung bereits materialisierter Evidence auf latest. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; Skalierungs-/Bediennachweis. |
| Implementierung / Consumer | exit_review_service.refresh_currentness vergleicht Fingerprint und markiert bisherigen Finalstand STALE; inspect_version_currentness prüft lesend konkrete Versionen. JournalService trennt unveränderlichen Inhalt von heutigem Quellenstatus, fordert explizites Rebind bei Drafts. FT011EvidenceHistory und JournalEvidenceOrigin zeigen exakte alte Review-/Journal-/Lessonversionen ohne latest-Ersatz. |
| Test / Commit | [tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py](../../tests/integration/backend/post_trade/test_post_trade_application_lifecycle_postgres.py)::test_changed_inputs_turn_finalized_review_stale_and_block_handoff; [test_ft011_materialization_command_postgres.py](../../tests/integration/backend/post_trade/test_ft011_materialization_command_postgres.py); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts) und [post-trade-evidence-history-postgres.spec.ts](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts) (reale Executionkorrektur, alte Evidence/Versionen unverändert, neue Review/Journal/Lessonversion). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische Quellen-/Supersessionverträge erhalten; keine behauptete neue menschliche Abnahme. Historische Baseline [docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md](../../docs/implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md): Accepted after repository-first S11 review; [docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md](../../docs/implementation/SPRINT_11_FT011_BACKEND_ACCEPTANCE_MATRIX.md): damalige 35/35 AT-S11, 107 Unit-/11 PostgreSQL-Fälle und vollständiges Backendgate PASS. Dieser damalige V1-Umfang bleibt anerkannt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende Fachabnahme der Currentnesserklärung und großvolumiger Historien → Benutzer versteht alte Inhalte und heutige Quellenprüfung getrennt → FT-011/FT-012 mit bestehenden Quellenreads → repräsentative Historie, Review/Journalkorrekturfall und explizite Testdaten → protokollierte Fach-/Bedienabnahme ohne automatische Retargetierung; Lastkriterien erst konkret festlegen statt Funktionsneubau. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

> Fortschreibung 21.10.2026: Die unabhängige [lesende Einzeltrade-Quellenansicht](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md) verbindet konkrete Review-/Journalversionen mit getrennt ausgewiesener heutiger Quellenprüfung. Veröffentlicht in Draft-PR #272; echte Quellenreise über Browser/API/PostgreSQL auf 8cc68f6 bestanden, einschließlich unveränderter historischer Inhalte bei separat berechnetem STALE. Vollständige finale CI-/Mobilnachweise sind checkoutgebunden im PR zu prüfen; die damalige Abschlussstatistik-Integration blieb offen. Der getrennt beauftragte [Integrationsschnitt](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md) verbindet jetzt Liste, qualifiziertes Ergebnis und genaue Quellen im Entwicklungsbranch; neue Vollgate-/Browsernachweise bleiben an seinen PR gebunden. Keine automatische Revalidierung, kein main-Merge und kein neuer Release.

</details>

</details>

### PB-019

[Exit-Review-Evidence bewusst materialisieren](#pb-019-materialization) · [Journalentwurf und Journalabschluss](#pb-019-journal) · [Regelabweichungen dokumentieren](#pb-019-deviations) · [Belegte Lessons Learned](#pb-019-lessons) · [Entscheidungsbewertung getrennt vom Ergebnis](#pb-019-decision-quality) · [Performancekennzahlen](#pb-019-performance-metrics) · [Tradeübergreifende Statistiken](#pb-019-performance-statistics) · [Performance-Dashboards](#pb-019-performance-dashboards) · [Perioden- und Tradeauswertungen](#pb-019-performance-evaluations)

<a id="pb-019-materialization"></a>
<details>
<summary>PB-019 — Exit-Review-Evidence bewusst materialisieren</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6→M7: Übergang zum Lernen. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012; FT-011 bleibt Quellowner. Lieferziel: B, D. |
| Arbeitsstatus | Business Review — fachlicher Abnahmenachweis offen; FT-011-Evidence-Materialisierung und Historieninventar technisch qualifiziert und ausgeliefert. |
| Abgeschlossener Teilumfang | Beide damaligen V1-Race-/Inventarlücken; Integration/Auslieferung sind am heutigen Main bereits erfolgt. Alte „PR-Prüfung/normaler Merge/Release als nächstes“ sind historisch. |
| Soll / Nicht-Soll | **Soll:** Ein expliziter idempotenter FT-012-Befehl materialisiert unveränderliche Evidence mit exakter Reviewversion. **Nicht-Soll:** Keine automatische Interpretation, keine zweite Readinesslogik in FT-012. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung. |
| Implementierung / Consumer | [backend/app/features/post_trade/application/materialization_handoff.py](../../backend/app/features/post_trade/application/materialization_handoff.py) schützt exakte Quelle im Owner; [learning/application/ft011_evidence_history_service.py](../../backend/app/features/learning/application/ft011_evidence_history_service.py) und [ft011_materialization_status_service.py](../../backend/app/features/learning/application/ft011_materialization_status_service.py) lesen unabhängiges historisches Inventar. Bestehender FT-012-Materialisierungscommand bindet unveränderliche Evidence an konkrete ExitReviewVersion. [Ft011EvidenceHistory.tsx](../../frontend/src/features/learning/components/Ft011EvidenceHistory.tsx) zeigt alte LessonVersion-Relationen und neue getrennte Evidence. |
| Test / Commit | [tests/integration/backend/post_trade/test_ft011_materialization_command_postgres.py](../../tests/integration/backend/post_trade/test_ft011_materialization_command_postgres.py) (Parallelität, gleicher/anderer Idempotenzschlüssel, STALE, falsche Version, Nachfolger); [tests/e2e/post-trade-evidence-history-postgres.spec.ts](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts); [docs/implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md](../../docs/implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md) (historischer eigener Commit 0863248b0c44e7c36d41b29acbef56b451d2592f). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | ADR-POST-FT012-007 definiert technischen Konsistenzumfang. Menschliche Fachabnahme und große Historien nicht belegt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende Fach-/Lastabnahme des vorhandenen Inventars → Benutzer materialisiert bewusst und findet exakt die damalige Evidence/Lesson wieder → FT-012 learning mit FT-011 materialization_handoff → repräsentative historische und konkurrierende Fälle → Fachabnahme von SOURCE_BUSY, alter STALE-Evidence und neuer idempotenter Materialisierung, definierte Antwortzeit bei vereinbarter Historiengröße. |
| Umfangsentscheidung | Kein paralleler Owner, keine geänderte 20-EOD- oder Journal-Schreibregel. Ältere offene Race-/Inventarhinweise gelten für deren damalige Baselines; der neue Nachweis ist kein pauschaler Abschluss von M6/M7 oder aller PB-019-Fähigkeiten. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

> Fortschreibung 2026-10-16: neuer abgegrenzter Konsistenz-/Inventarschnitt aus v1.5.7 (`3faf0f76…`). Bestehende Journal-/Lesson-Owner und 20-EOD-Semantik unverändert. Historische Prüfbezüge unten sind keine Qualifikation der neuen Änderungen.
> Qualifikationsfortschreibung: [eigener Nachweis auf gemeinsamem Commit](../implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md). Die folgende Tabelle beschreibt diesen technischen Schnitt; ältere Notizen bleiben als historische Belege erhalten.

> Nachweisfortschreibung 2026-10-14: [vollständige Repository-Integration und abgegrenzte Qualifikation](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md) in Draft-PR #259 auf v1.5.6. b40: 2600 Backendtests einschließlich drei unabhängiger PostgreSQL-Fälle; dort bezeichneter 8f-Testmerge: 456 Frontendtests und 51 Browserfälle. Drei neue Browserfälle verwenden abgefangenes HTTP, keine vollständige Journal-/DB-Nutzerreise.
> First-party-Review-Pin und UI-Readback sind ein technischer Teilschnitt, keine Abnahme des Journals oder des gesamten Lernprozesses. Arbeitsstatus und Betriebsfreigabe werden durch diese Notiz nicht hochgestuft.

</details>

</details>

<a id="pb-019-journal"></a>
<details>
<summary>PB-019 — Journalentwurf und Journalabschluss</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Journal. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012; bestehende Evaluation-Ownership. Lieferziel: B. |
| Arbeitsstatus | Business Review — fachliche Abnahme offen; Journal-V1 einschließlich Folgeversion, Quellenbindung und Evidence technisch abgeschlossen und ausgeliefert. |
| Abgeschlossener Teilumfang | Journalentwurf, Abschluss, Versionierung, exakte Herkunft, historischer Lesemodus, Evidence-Übergabe und UI6-Navigation; frühere Draft-/Release-/Installationsfreigabereste überholt. |
| Soll / Nicht-Soll | **Soll:** Ein eigenständiger Journalentwurf dokumentiert Reflexion und genaue Trade-/Review-Herkunft; Abschlussregeln sind testbar festgelegt. **Nicht-Soll:** Performance ist keine Voraussetzung für einen Entwurf. Exit Review, LearningEvidence und Lesson sind kein stiller Ersatz für Journal. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; Entscheidung/Implementierung für externe Journale. |
| Implementierung / Consumer | [learning/application/journal_service.py](../../backend/app/features/learning/application/journal_service.py) implementiert CREATE_DRAFT, SAVE_DRAFT, FINALIZE, REBIND_SOURCE, MATERIALIZE mit Idempotenz, tradebezogener Sperre und edit_revision. [journal_repository.py](../../backend/app/features/learning/persistence/journal_repository.py) persistiert echte TradeJournalVersionen. [journal_router.py](../../backend/app/features/learning/api/journal_router.py) / [journalClient.ts](../../frontend/src/features/learning/services/journalClient.ts) / [TradeJournalPanel.tsx](../../frontend/src/features/learning/components/TradeJournalPanel.tsx) / [useTradeJournal.ts](../../frontend/src/features/learning/components/useTradeJournal.ts) bilden den Benutzerweg. Finale Inhalte bleiben unverändert; bewusste neue Version kopiert Inhalt und pinnt genaue Reviewquelle. Leeres Final bleibt zulässig und sichtbar. |
| Test / Commit | [tests/integration/backend/learning/test_journal_write_postgres.py](../../tests/integration/backend/learning/test_journal_write_postgres.py); [tests/unit/backend/features/learning/test_journal_commands.py](../../tests/unit/backend/features/learning/test_journal_commands.py) und [test_journal_api.py](../../tests/unit/backend/features/learning/test_journal_api.py); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts) (BUY/SELL→19/20 EOD→Review→Journal→Evidence→Lesson→Korrektur→Folgeversion mit alten Pins); UI-Lokalsuiten TradeJournalPanel/journalViewState. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | ADR-POST-FT012-005 ist Implementierungsentscheidung für autorisierten V1-Schnitt, ausdrücklich keine menschliche Domainabnahme. Optionale drei Textfelder und leerer Final sind bereits entschieden, nicht als neu fehlende Implementierung planen. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende menschliche V1-Abnahme sowie nicht gelieferter ExternalObservationJournal-Editor → Benutzer kann eigene Reflexion samt leerem Final und alter Quelle bewusst nachvollziehen; externer Journalbedarf wird gesondert entschieden → FT-012 learning, FT-011 als Quellenowner → dokumentierte Fach-/Bedienfälle und Entscheidung zum externen Journalumfang → V1-Fachabnahme plus expliziter abgegrenzter Folgeauftrag oder dokumentierte Scopeentscheidung für externe Journale; bestehende Tradejournal-Funktion nicht neu bauen. |
| Umfangsentscheidung | M7 bleibt ursprüngliche Referenz. Journal-V1 ist kein pauschaler Abschluss von M7 oder des ganzen Lernbereichs; keine neuen Scores, Pflichtbewertungen, Importquellen oder Modellaktivierungen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

> Umsetzungsschnitt 2026-10-14: [Journal-Schreibvertrag und Abnahmekriterien](../implementation/FT012_JOURNAL_WRITE_DOR.md), [ADR zur Versionierung/Quellenbindung](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md). Auf getrenntem Entwicklungsbranch aus PR #259: vorhandenes Modell → Commands/UOW → API → Entwurf/Finalisierung/Folgeversion → explizite Journal-Evidence. Historienanzeige bleibt bei veralteter Quelle verfügbar; TradePlan-Hard-Delete erhält eine Final-Historien-Sperre.
> Fortschreibung 2026-10-15: [eigene Journal-Qualifikation](../implementation/FT012_JOURNAL_WRITE_QUALIFICATION.md) auf gemeinsamem Prüfcommit abgeschlossen. Die Tabelle führt den aktuellen begrenzten Arbeitsstand. Keine menschliche Fachabnahme, Veröffentlichungsversion oder Zielinstallation wird behauptet. Die folgenden Bestandsnotizen bleiben als Stand **vor** diesem Journal-Schnitt erhalten.


> Bestandsnotiz 2026-10-14: [vollständiger Checkout und Journal-Vertragsvorschlag](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md) bestätigen Journalmodelle und Evidence-Lesetypen, aber keinen Journal-Schreibservice, entsprechende UOW-Repositories, registrierte Schreibroute oder Editor im FT-012-Consumer. Die Domain erlaubt leere Finals und enthält dort keinen konkreten Review-Pin.
> Journal-Commands, API, UI, Finalisierung, Folgeversion und Datenbanknachweise sind durch den Handoff-Patch nicht geliefert. Keine automatische Verschärfung durch Performance und keine neue Freigabe für zusätzliche Pflichtbewertungen.

**UI6-Fortschreibung vom 27.10.2026:** Die
[Konsolidierung der Journalansicht und exakten Quellenaufrufe](../implementation/UI_JOURNAL_CONSOLIDATION.md)
baut auf Main `eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4` / `v1.5.23` mit den
integrierten UI1–UI5 auf. Unter `/post-trade?trade_id=…&journal_version_id=…`
bleibt die verlangte Journalversion exakt gebunden; fehlerhafte Quellenaufrufe
erhalten keinen neuesten Ersatzstand. Lesemodus, vollständig vorbefüllte
Bearbeitung und Bestätigung teilen sich einen Journaltextbereich. Gespeicherte
Revision und lokale Eingaben bleiben getrennt, ebenso Journalstatus und heutige
Quellenprüfung. Ein zentraler Navigationsschutz koordiniert Journal, beide
eingebetteten Lessonformulare sowie die begrenzten Review-/Materialisierungsadapter.
Die vorhandenen Journalcommands und ihre Idempotenz bleiben erhalten; der normale
Lesson-POST erhält keine Journal-Replaygarantie. Der eigene Bericht bindet die
tatsächlich ausgeführten Prüfungen, Commit/Tree und verbleibenden Grenzen und
dokumentiert die kleine Dateikollision mit PR #90. Übergabe als separater Draft-PR;
fachlicher Arbeitsstatus, historische Nachweise und offene Zielinstallation
bleiben erhalten. Merge, Versionserhöhung und Veröffentlichung gehören zu einem
eigenständigen Folgeauftrag.

</details>

</details>

<a id="pb-019-deviations"></a>
<details>
<summary>PB-019 — Regelabweichungen dokumentieren</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Regelabweichungen. Bereich/Querschnitt: 7; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-012; Reviewquelle FT-011. Lieferziel: B, D. |
| Arbeitsstatus | Analysis — vorhandene manuelle Review-/Journal-Dokumentation abgeschlossen, vollständiger Regelabweichungsvertrag offen. |
| Abgeschlossener Teilumfang | Freitext-/Prozesstreue-Dokumentation und genaue Review-/Journalherkunft. |
| Soll / Nicht-Soll | **Soll:** Abweichungen beziehen sich auf die tatsächlich verwendete Regel-/Planversion und belegte Fakten. **Nicht-Soll:** Keine nachträgliche Bewertung alter Entscheidungen mit latest-Regeln. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung nach bestätigtem Delta. |
| Implementierung / Consumer | ExitReviewVersion speichert process_adherence, timing, risk_decision, overall_exit_decision und rationale; JournalVersion speichert what_went_well, would_do_differently und additional_notes mit exakter Reviewversion. Diese Felder erlauben qualitative Reflexion. In den gelesenen aktiven Services/DTOs kein vollständiges strukturiertes regel-ID-/modellversionsbezogenes Abweichungsregister. |
| Test / Commit | [tests/unit/backend/features/post_trade/test_acceptance_contracts.py](../../tests/unit/backend/features/post_trade/test_acceptance_contracts.py) (NOT_ASSESSABLE); Journal-Commandtests und nativer Journal-/Lessonweg prüfen Persistenz, nicht Vollständigkeit einer Regelabweichungstaxonomie. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Keine angenommene Definition eines vollständigen Regelabweichungsumfangs nachgewiesen. Manuelle Qualitätsurteile sind bestehende Funktion. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Ungeklärter Umfang jenseits vorhandener Prozesstreue und Reflexion → Benutzer kann Abweichung auf damals gültige Regel/Planversion und Fakten zurückführen → FT-012 learning, Quellen FT-011/FT-007 → Definition erforderlicher Regelreferenzen, Abweichungstypen und nicht beurteilbarer Fälle → fachlich angenommene Kriterienmatrix samt positivem/negativem Beispiel; danach ausschließlich fehlende Felder/Consumer mit Versions- und Korrekturtests umsetzen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-019-lessons"></a>
<details>
<summary>PB-019 — Belegte Lessons Learned</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Lessons Learned. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012. Lieferziel: B, D. |
| Arbeitsstatus | Business Review — fachliche Abnahme offen; explizite Lesson-Erstellung, Prüfung und Folgeversion technisch abgeschlossen und ausgeliefert. Weitere Umfänge bleiben separat. |
| Abgeschlossener Teilumfang | Explizite Review- und Folgeversionsstrecke, UI3 und integrierte Erfolgsnavigation; kein weiterhin offener UI3-Draft. Die FT011-Konsistenzlücke nicht wieder aufmachen. |
| Soll / Nicht-Soll | **Soll:** Eine bewusste Interpretation referenziert konkrete LearningEvidence und eine unveränderliche LessonVersion. **Nicht-Soll:** Evidence-Transport erzeugt keine Lesson; Lesson erzeugt kein automatisches Modellapproval. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; Entscheidung/Implementierung für getrennte Komforterweiterungen. |
| Implementierung / Consumer | lesson_service.create_with_tags commitet Lesson, erste Version, Evidence und Tags atomar. [lesson_review_service.py](../../backend/app/features/learning/application/lesson_review_service.py) / [lesson_review_commands.py](../../backend/app/features/learning/application/lesson_review_commands.py) sperren Lesson, pinnen Version/Status/Signal und lösen Review unverändert, mit Folgeversion oder RETIRED. Neue Version braucht explizites SUPPORTS; Relationssnapshot und Supersedes bleiben erhalten. LessonDetailPage/LessonReviewPanel/JournalEvidenceOrigin zeigen genaue Version, vorbefüllten Editor und aktuelle Quellenprüfung. |
| Test / Commit | [tests/integration/backend/learning/test_explicit_lesson_review_postgres.py](../../tests/integration/backend/learning/test_explicit_lesson_review_postgres.py); [tests/unit/backend/features/learning/test_lesson_review_resolutions.py](../../tests/unit/backend/features/learning/test_lesson_review_resolutions.py); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts) prüft echte neue Journal-Evidence, SUPPORTS/QUALIFIES, persistierte Lesson V2 und unveränderte V1; [post-trade-evidence-history-postgres.spec.ts](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts) prüft exakte alte Lessonlinks. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | ADR-POST-FT012-006 und historische technische Qualifikation gelten; Menschliche Fachabnahme des Interpretations-/Reviewwegs weiterhin nicht belegt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende Fach-/Bedienabnahme und bewusst ausgeschlossene RETIRED-Reaktivierung/Titel-Tag-Bearbeitung → Benutzer interpretiert Evidenz nachvollziehbar und korrigiert versioniert → FT-012 learning → bestehende Evidenz-/Versionsverträge und priorisierte Entscheidung zu Erweiterungen → dokumentierte V1-Abnahme von Quellenalterung versus Widerspruch; Erweiterungen jeweils mit eigener Umfangsentscheidung und Tests, ohne bereits vorhandene Reviewstrecke neu zu planen. |
| Umfangsentscheidung | Vorhandene Lesson-/Review-Verträge konsolidiert; kein neuer Backend-Lifecycle oder automatischer Governance-Befehl. Produkt-/Plankonsolidierungen [#284](https://github.com/burckhju/trading-workspace/pull/284)/#285 sind bereits integriert und werden hier nicht erneut bearbeitet. Journal bleibt eigener ursprünglicher Anspruch. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Aktueller Integrationsabgleich 28.10.2026:** [PR #295](https://github.com/burckhju/trading-workspace/pull/295)
ist am 28.10.2026 mit Merge `13e8d5331abab32d4998118e83aaecbc231dea31`
integriert; dessen Head war `36e846cf9bcdaeb47981328597cb05335fe83d1f`.
Die gemeinsame Lesson-Erfolgsnavigation und der Erhalt bestätigter Ergebnisse
bei Verwerfen im gleichen Evidence-Kontext sind Bestandteil der aktuellen
Basis `dc89dfa65758dfc1258a8fab657257f6598b0179` / 1.5.29.
Der frühere Draft-/Übergabestand oben bleibt historischer Nachweis.
[Reviewbeleg](../reviews/REMAINING_WORK_INTEGRATION_2026-10-28.md) und
[PR #296](https://github.com/burckhju/trading-workspace/pull/296) trennen technische
Qualifikation und anschließende Softwarebereitstellung. Keine neue menschliche
Fachabnahme oder PC-Installation wird daraus abgeleitet. Diese Änderungen werden
im Währungsfix erhalten und nicht erneut implementiert; #90 bleibt als
historischer PR von diesem Auftrag unberührt.

</details>

</details>

<a id="pb-019-decision-quality"></a>
<details>
<summary>PB-019 — Entscheidungsbewertung getrennt vom Ergebnis</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Entscheidungsbewertung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011 Review / FT-012 Journal und Lessons. Lieferziel: B, D. |
| Arbeitsstatus | Analysis — gespeicherte qualitative Exitbewertung und Quellensicht abgeschlossen; allgemeiner M7-Bewertungsmaßstab offen. |
| Abgeschlossener Teilumfang | Qualitative Exitbewertung und exakte historische Quellensicht. |
| Soll / Nicht-Soll | **Soll:** Prozess-/Entscheidungsqualität und wirtschaftliches Ergebnis werden mit erklärten Kriterien getrennt bewertet. **Nicht-Soll:** Ein positiver Ertrag beweist keine gute Entscheidung; keine erfundenen Scorekriterien. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung/Abnahme; ggf. Implementierung nach Delta. |
| Implementierung / Consumer | exit_review_service.finalize speichert vom Benutzer bestätigte timing/process_adherence/risk_decision/overall_exit_decision plus rationale und Fingerprint. PostTradeReviewPage rendert/bearbeitet diese getrennt vom tatsächlichen Bruttoergebnis; Tradequellenansicht zeigt exakte Review-/Journal-/Evidence-/Lessonpins. Keine automatische Ableitung guter Entscheidungen aus Gewinn. |
| Test / Commit | [tests/unit/backend/features/post_trade/test_acceptance_contracts.py](../../tests/unit/backend/features/post_trade/test_acceptance_contracts.py); [tests/e2e/post-trade-journal-postgres.spec.ts](../../tests/e2e/post-trade-journal-postgres.spec.ts); [tests/e2e/closed-trades-report-postgres.spec.ts](../../tests/e2e/closed-trades-report-postgres.spec.ts) und [support/trade_source_journey.ts](../../tests/e2e/support/trade_source_journey.ts) für Quellenreise. Tests belegen Speicherung und Trennung, keine fachliche Güte des Urteils. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Vollständige Bewertung von Analyse, Einstieg, Risikomanagement, Ausstieg und Lernen gemäß PROJECT/M7 benötigt einen angenommenen Maßstab; keine neuen Scores erfinden. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende gemeinsame Kriterien für vollständige Entscheidungsqualität → Benutzer kann Prozessqualität und Geldresultat getrennt bewerten → FT-011 Review / FT-012 Journal und Lessons → bestätigte Kriterien für die ursprünglichen Entscheidungsaspekte und Nichtbeurteilbarkeit → angenommene Kriterienmatrix mit Beispielentscheidungen; vorhandene Exitfelder zuordnen, nur belegte fehlende Aspekte anschließend umsetzen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

> Fortschreibung 21.10.2026: [Quellenansicht und A1–A16-Prüfgrenzen](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md) ergänzen ausschließlich die Anzeige gespeicherter Exit-Bewertung, genauer Journal-/Evidence-/Lessonbeziehungen und Originalplanung. 598 Frontendtests und 680 betroffene Backend-Unitfälle bestanden; Quellen-Browserreise mit exakten L1-/Journalpins und Nichtmutation jetzt tatsächlich bestanden (Draft-PR #272). Der erste Backend-Volllauf fand zwei korrigierte Fixturefehler; sein Ergebnis wird nicht als grüner Abschluss gewertet. Finale Vollgate-/Mobilnachweise bleiben im PR getrennt gebunden. Gesamtergebnis/Abschlusslisten-Einstieg werden im gesonderten [Integrationsschnitt](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md) an den bestehenden Reportowner angebunden; exakte neue Prüfbindung im Integrations-PR. Menschliche Fachabnahme und Zielinstallation bleiben offen. Der allgemeine Bewertungsumfang bleibt **Analysis**, nicht durch reine Quellenanzeige erledigt.

</details>

</details>

<a id="pb-019-performance-metrics"></a>
<details>
<summary>PB-019 — Performancekennzahlen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Performancekennzahlen. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Business Review (fachliche Abnahme des begrenzten Umfangs); Brutto-SELL-/Abschlusskennzahlen und vier Basisstatistiken technisch abgeschlossen und ausgeliefert. Analysis (weitere Kennzahlen). |
| Abgeschlossener Teilumfang | Brutto-SELL- und vollständige Tradeergebnisse sowie vier benannte Basiskennzahlen; erneute Umsetzung von Trefferquote/Mittel/Median/Profit-Faktor entfällt. |
| Soll / Nicht-Soll | **Soll:** Kennzahlen besitzen explizite Bedeutung, Daten-/Währungsgrenzen, Nenner und Behandlung unbekannter Werte. **Nicht-Soll:** Keine erfundene Equity, Nullgebühren, FX-Historie oder Netto-Performance. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Prüfung/Daten; fachliche Entscheidung für Erweiterungen. |
| Implementierung / Consumer | [performance/domain/report.py](../../backend/app/features/performance/domain/report.py) und [closed_report.py](../../backend/app/features/performance/domain/closed_report.py) verwenden effektive Ausführungen, PositionProjector und historischen Währungsresolver. [closed_statistics.py](../../backend/app/features/performance/domain/closed_statistics.py) berechnet Trefferquote, Durchschnitt, Median und Brutto-Profit-Faktor allein aus vollständiger Abschlusskohorte und ungerundeten Ownerbeträgen; neutrale Trades bleiben im Nenner. PARTIAL/NOT_COMPUTABLE/EMPTY liefern Gründe statt künstlicher Werte. [ClosedTradeStatistics.tsx](../../frontend/src/features/performance/components/ClosedTradeStatistics.tsx) zeigt genaue Definition, Population, Einheit und Rohwert. |
| Test / Commit | [tests/unit/backend/features/performance/test_closed_statistics.py](../../tests/unit/backend/features/performance/test_closed_statistics.py) (unabhängiger Vier-Trade-Golden, kleine Vorzeichen, neutral, gerader/ungerader Median, Rundung, keine Verluste, unvollständige Quellen); [tests/e2e/closed-trades-report-postgres.spec.ts](../../tests/e2e/closed-trades-report-postgres.spec.ts) und [realized-gross-report-postgres.spec.ts](../../tests/e2e/realized-gross-report-postgres.spec.ts); [ux4-c-performance-visualization.spec.ts](../../tests/e2e/ux4-c-performance-visualization.spec.ts). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | ADR-S10-008/009 plus bestätigter Statistikauftrag 25.10.2026 und UX4-C-Releasefreigabe 07.11.2026 definieren begrenzte Teilumfänge; keine Gesamt-M8-Fachabnahme. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende tatsächliche Währungsquellenabdeckung und fachliche M8-Gesamtabgrenzung → Benutzer sieht belastbare Kennzahlen oder konkrete Datenlücken → FT-012 performance mit FT-009/010-Owner → geprüfte Ausführungs-/Währungsquellen und Entscheidung zu zusätzlichen Kennzahlen → reale Beispielkohorte gegen unabhängige Referenzwerte abgenommen; fehlende Währungen bleiben ungeklärt; weiterer Netto-/FX-/Equityumfang nur mit eigenem entschiedenem Vertrag. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

</details>

<a id="pb-019-performance-statistics"></a>
<details>
<summary>PB-019 — Tradeübergreifende Statistiken</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Statistiken. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Business Review — fachliche Gesamtabnahme offen; vollständige Abschlusskohorte und closed-trade-statistics-v1 technisch abgeschlossen und ausgeliefert; historische Vertragsfreigaben erhalten. |
| Abgeschlossener Teilumfang | Abschlusskohorte, Vorzeichenzähler und alle vier Statistikwerte sind im ausgelieferten Stand; historische Texte „neue Head-/Merge-/Releasequalifikation erst offen“ nicht mehr aktuelle Aufgabe. |
| Soll / Nicht-Soll | **Soll:** Aggregation erklärt Population, offene/geschlossene Trades, Korrekturen und Filter. **Nicht-Soll:** Keine undefinierte Grundgesamtheit oder aus Teildaten abgeleitete Erfolgsquote. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Prüfung; Datenversorgung; Entscheidung für breitere Statistik. |
| Implementierung / Consumer | [closed_report.py](../../backend/app/features/performance/domain/closed_report.py) trennt acht disjunkte Gruppen nach realem Vollabschluss/Periodenzuordnung/Währungsqualifikation, summiert gesamte wirksame Lebenszeitverkäufe je Trade. [closed_statistics.py](../../backend/app/features/performance/domain/closed_statistics.py) liest genau diese Antwort/Basis, verwendet COMPLETE und N>0, setzt keine Teildatenquote an. ClosedTradesReportView und ClosedTradeStatistics zeigen Backendzahlen, Populationsgrenzen und exakte Quellen. |
| Test / Commit | [tests/unit/backend/features/performance/test_closed_report.py](../../tests/unit/backend/features/performance/test_closed_report.py), [test_closed_statistics.py](../../tests/unit/backend/features/performance/test_closed_statistics.py); [tests/integration/backend/test_closed_trades_report_postgres.py](../../tests/integration/backend/test_closed_trades_report_postgres.py); [tests/e2e/closed-trades-report-postgres.spec.ts](../../tests/e2e/closed-trades-report-postgres.spec.ts); [tests/e2e/ux4-c-performance-visualization.spec.ts](../../tests/e2e/ux4-c-performance-visualization.spec.ts). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Kohorten-/Signum-/Abdeckungsentscheidung in ADR-S10-009, vier zusätzliche Kennzahlen im Vertrag [CLOSED_TRADE_STATISTICS_V1.md](../../docs/implementation/CLOSED_TRADE_STATISTICS_V1.md) vom 25.10.2026; menschliche Gesamtabnahme offen. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende fachliche Betriebsabnahme und Definition weiterer Statistikfragen → Benutzer erhält erklärbare vollständige Kohorten mit belastbaren Daten → FT-012 performance → reale Beleggrundlage und angenommene zusätzliche Statistikbedürfnisse → dokumentierter Abgleich COMPLETE/PARTIAL/EMPTY, neutralem Trade und fehlendem Verlustnenner; zusätzlicher Statistikumfang mit konkretem Nutzen und Referenzfällen entschieden. |
| Umfangsentscheidung | Die drei engen Kohortenregeln sind entschieden; ursprüngliches M8 bleibt sichtbar. Kein Netto-/FX-/Equity-Modell, keine Modellaktivierung und keine pauschale Erledigung weiterer Statistikanforderungen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Begrenzter Statistiknachtrag 25.10.2026:** Der neue Nutzerauftrag gibt
Trefferquote, durchschnittliches Bruttoergebnis, Median und Profit-Faktor brutto
als `closed-trade-statistics-v1` zur Umsetzung und Qualifikation bis zum
Draft-PR frei. Diese vier Kennzahlen waren im ursprünglichen ADR-S10-009 noch
ausgeschlossen. Sie verwenden ausschließlich vollständige Abschlussberichte
mit positiver Population, dieselben ungerundeten Ownerergebnisse und dieselbe
Berichtsbasis; Teilberichte liefern verständlich begründete Nullwerte.
[Neuer Vertrag, vorab bestimmte Referenzfälle und Qualifikation](../implementation/CLOSED_TRADE_STATISTICS_V1.md).
Die bisherigen Kohorten-/Quellennachweise bleiben erhalten. Dieser Auftrag
autorisiert keinen Merge, Release, Tag oder PC-Update; insbesondere wird die
frühere Freigabe für #278 nicht übertragen.

</details>

</details>

<a id="pb-019-performance-dashboards"></a>
<details>
<summary>PB-019 — Performance-Dashboards</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Dashboards. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Business Review — menschliche Fach-/Bedienabnahme offen; gemeinsamer Performancebereich und SELL-Beitragsgrafik technisch abgeschlossen und ausgeliefert. Weiterer Umfang bleibt zu klären. |
| Abgeschlossener Teilumfang | Einzel-SELL-Grafik, Originalwerttabelle, Kennzahlenkacheln und gemeinsamer Filterrahmen. Alte pauschale Aussage „Diagramme noch offen“ ist falsch. |
| Soll / Nicht-Soll | **Soll:** Lesende Auswertung zeigt Kennzahlen, Grenzen, Datenlücken und Herkunft verständlich. **Nicht-Soll:** Operational Workspace und Marktcharts sind kein Performance-Dashboard; keine Frontend-Zweitberechnung. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Prüfung; fachliche Entscheidung/Implementierung für darüber hinausgehende Dashboards. |
| Implementierung / Consumer | [PerformanceWorkspace.tsx](../../frontend/src/features/performance/pages/PerformanceWorkspace.tsx) verbindet bestehende SELL-/Abschlussberichte mit einem Zeitraum-/Zeitzonenfilter bei getrennten Antworten. [RealizedGrossVisualization.tsx](../../frontend/src/features/performance/components/RealizedGrossVisualization.tsx) / [RealizedGrossPlot.tsx](../../frontend/src/features/performance/components/RealizedGrossPlot.tsx) zeigen einzelne wirksame SELL-Beiträge aus derselben Antwort samt semantischer Originalwerttabelle, lokalen Seiten, Quellenaufruf und Diagrammfehler-Fallback. ClosedTradeStatistics zeigt vier Backendkennzahlen. Keine synthetische Zeit-/Equityachse und keine Frontend-Finanzrechnung. |
| Test / Commit | [tests/e2e/ux4-c-performance-visualization.spec.ts](../../tests/e2e/ux4-c-performance-visualization.spec.ts) (9 Fälle: 320/390/1280 px, Tastatur, native 200/400-Prozent-Zooms, Chart-Lade/Renderfehler, unverfügbare Werte); RealizedGrossVisualization*`.test.tsx`; [tests/e2e/performance-workspace-ui.spec.ts](../../tests/e2e/performance-workspace-ui.spec.ts). Historische vollständige Qualifikation in [V1.5.42-UX4-PERFORMANCE-QUALITY-LIFECYCLE.md](../../docs/releases/V1.5.42-UX4-PERFORMANCE-QUALITY-LIFECYCLE.md). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | UX4-C-Schnitt integriert und mit v1.5.42 bereitgestellt; automatisierte Responsiv-/Tastaturtests sind keine menschliche Screenreader-/Touch-/Domainabnahme. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende menschliche UX-/Fachabnahme und unentschiedener zusätzlicher Dashboardnutzen → Benutzer versteht SELL-Ereignisse, vollständige Trades und Datenlücken auch assistiv → FT-012 performance, vorhandene UI-Owner → vorhandene C/D-Artefakte und reale Nutzungsszenarien → protokollierte Tastatur-/Screenreader-/Touch-/Fachabnahme; nur zusätzliche konkret entschiedene Visualisierungen oder Export als neuer Rest, vorhandene Grafik nicht erneut bauen. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

</details>

<a id="pb-019-performance-evaluations"></a>
<details>
<summary>PB-019 — Perioden- und Tradeauswertungen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Auswertungen. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Business Review — Fach-/Datenabnahme offen; SELL-Zeitraum-/Vollabschlussauswertung, Quellenreise und gemeinsame Filter technisch abgeschlossen und ausgeliefert; historische Vertragsfreigaben erhalten. |
| Abgeschlossener Teilumfang | Bereits integrierte UI8-/historische Währungsquellen-/v1.5.31-Auslieferung nicht mehr als nächster Releaseauftrag führen; heutiger Softwarestand enthält sie. |
| Soll / Nicht-Soll | **Soll:** Explizite Zeit-/Tradeauswahl, Stichtag und nachvollziehbare Berechnungsgrenzen. **Nicht-Soll:** Keine stillen historischen Rekonstruktionen eines damals unbekannten Datenstands. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Datenversorgung; Prüfung; Entscheidung für Export/weitere Auswertungen. |
| Implementierung / Consumer | [performance/service/reader.py](../../backend/app/features/performance/service/reader.py) liest vollständigen begrenzten PostgreSQL-Snapshot in REPEATABLE READ READ ONLY mit Limits und Timeout. `application.py` erzeugt daraus getrennte SELL-/Abschlussberichte; historische Währungsevidence wird konsumiert. PerformanceWorkspace bewahrt getrennte Finanzdefinitionen bei gemeinsamer expliziter Filterauswahl; Quellenlinks und Rückkehr bleiben versions-/kontextgebunden. Kein historischer as-of-Enddatum-Replay. |
| Test / Commit | [tests/integration/backend/test_realized_gross_report_postgres.py](../../tests/integration/backend/test_realized_gross_report_postgres.py), [test_closed_trades_report_postgres.py](../../tests/integration/backend/test_closed_trades_report_postgres.py), [test_realized_gross_learning_independence_postgres.py](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py); beide nativen Report-E2E plus [PerformanceWorkspace.test.tsx](../../frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx) / [performance-workspace-ui.spec.ts](../../tests/e2e/performance-workspace-ui.spec.ts). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | ADR-S10-008/009, EUR-UI-Entscheidung vom 25.10.2026 und UI8-Vertrag erhalten. Reale Quellenabdeckung und vollständige M8-Fachabnahme getrennt. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Unbelegte historische Kaufwährungen und fehlende fachliche Abnahme repräsentativer Berichte → Benutzer kann Zeitraum und Vollabschlussquellen korrekt unterscheiden → FT-012 performance mit FT-009/010-Währungsowner → belegte wirtschaftliche Originalquellen und expliziter Auswertungsumfang → reale Referenzfälle samt Korrektur/Datum-ohne-Zeit/Quellenrückkehr abgenommen; unbekannte Werte bleiben sichtbar, Export/weiterer Umfang wird separat konkretisiert. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**UI-Nachtrag 27.10.2026 (UI8):** Die vorhandenen Verkaufs- und
Abschlussberichte verwenden einen gemeinsamen Performance-Einstieg, genau einen
Filterbereich und dieselbe ausdrücklich übernommene Zeitraum-/Zeitzonenauswahl.
Ihre Finanzdefinitionen, Quellenstände und Antworten bleiben getrennt; die
Abschlussstatistiken behalten ihre bestehende Bindung an den Abschlussbericht.
[Bedien-, URL-, Quellen- und Prüfnachweis](../implementation/UI_PERFORMANCE_CONSOLIDATION.md)
führt die neue Qualifikation einschließlich der beiden gezielt erweiterten
nativen Journeys mit unveränderten Testidentitäten. UI8 ist die Arbeitsbezeichnung
dieses Bedienumfangs, keine neue FT-/PB-Nummer oder Statusquelle. Übergabe als
geprüfter Draft-PR; Merge, Version, Veröffentlichung, PC-Installation und fachliche
Bedienabnahme bleiben eigenständige nachfolgende Schritte. UI6/Journal und
UI7/Ausführungskorrektur sind getrennte Umfänge.

**UI-Nachtrag 25.10.2026:** Auf ausdrücklichen Nutzerwunsch ist die
Berichtswährung in Verkaufs- und Abschlussübersicht fest EUR. Vorhandene
Nicht-EUR-Listenlinks werden ohne stillen Ersatzread erklärt; Buchungswährungen,
Quellen und Definitionen bleiben unverändert. [Umfang und neue
Qualifikation](../implementation/REPORT_EUR_UI_QUALIFICATION.md). Dies ist kein
Nachweis vollständiger realer Währungsabdeckung oder einer neuen Auslieferung.

</details>

</details>

### PB-020

[Modellinfrastruktur: Evidence bis Freigabe](#pb-020-governance) · [Gesonderte Runtime-Aktivierung und Rückkehr](#pb-020-activation) · [Stopmodell](#pb-020-stop-model) · [Zielmodell](#pb-020-target-model) · [Trade Assistant](#pb-020-assistant) · [Nachbeobachtungsmodell](#pb-020-observation-model) · [TOP_DOWN_CANDIDATE als konkrete Modellfamilie](#pb-020-candidate-family) · [MarketContext als fachliche Modellfamilie](#pb-020-market-context) · [Relative Strength als fachliche Modellfamilie](#pb-020-relative-strength)

<a id="pb-020-governance"></a>
<details>
<summary>PB-020 — Modellinfrastruktur: Evidence bis Freigabe</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: gemeinsame Governance der Modellfamilien. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013; FT-012 besitzt Evidence. Lieferziel: D. |
| Arbeitsstatus | Released (historischer FT-013-Vertragsumfang); Business Review (Fachabnahme der späteren konkreten Consumerreise); generische Governancekette und Kandidatenconsumer technisch abgeschlossen und ausgeliefert. Familienerweiterungen separat. |
| Abgeschlossener Teilumfang | Versionierte Governanceartefakte und konkrete gespeicherte Kandidatenreise; generische Infrastruktur nicht erneut planen. |
| Soll / Nicht-Soll | **Soll:** Explizite Hypothese, Proposal gegen konkrete genehmigte Basis, cutoffgebundene Validierung und Freigabe erzeugen eine neue immutable ModelVersion. **Nicht-Soll:** Freigabe ist weder Runtime-Aktivierung noch Handelsentscheidung; keine rückwirkende Evidence-Umschreibung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; Entscheidung/Implementierung je weiterer Modellfamilie. |
| Implementierung / Consumer | [model/service/application.py](../../backend/app/features/model/service/application.py) prüft Evidence/Workspace, erzeugt Hypothese, DRAFT-Proposal aus APPROVED-Basis, retrospektive Validation mit Cutoff, neue immutable APPROVED-Version und Approval-Audit. Aktive Version wird dabei nicht geändert. LessonHypothesisPanel/HypothesisProposalPanel/ProposalValidationPanel/ProposalApprovalPanel bieten explizite Benutzeraktionen; konkrete Runtimeanwendung im CandidateService. |
| Test / Commit | [tests/unit/backend/features/model/test_ft013_service.py](../../tests/unit/backend/features/model/test_ft013_service.py); [tests/unit/backend/features/model/test_governance_source_scope.py](../../tests/unit/backend/features/model/test_governance_source_scope.py); [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts) (exakte historische Lesson→Hypothese→Proposal→Validation→Approval, A bleibt bis Aktivierung aktiv); Model-Proposal-/Governance-Unit-/UI-Suiten; [CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md](../../docs/implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md). Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historische FT-013- und FT-019/020-Verträge bleiben gültig. Technisch valide Governance beweist keine wirtschaftliche Überlegenheit oder vollständige Fachabnahme aller Modellfamilien. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende fachliche Modellabnahme und weitere Consumerverträge → Benutzer kann Modelländerungen evidenzgebunden freigeben → FT-013 model, fachlicher Owner je Familie → exakte Evidence, angenommene Validationskriterien und Verbraucherdefinition → dokumentierte Fachabnahme der Kandidatenreise; pro weiterer Familie separat Input/Version/Anwendung/Rückkehr mit eigenen Tests belegt. |
| Umfangsentscheidung | Vorhandene Governance wiederverwenden; der alte PB-020-Status Not Started ist überholt. |

</details>

<a id="pb-020-activation"></a>
<details>
<summary>PB-020 — Gesonderte Runtime-Aktivierung und Rückkehr</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: reproduzierbare Anwendung freigegebener Modelle. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance; technische Qualität/Betrieb. Bestehender Bezug: FT-013; vorhandener Candidate-Consumer FT-005/FT-019/FT-020. Lieferziel: D. |
| Arbeitsstatus | Business Review — fachlicher und produktiver Abnahmenachweis offen; separate Aktivierung und A→B→A-Rückkehr für Kandidaten technisch abgeschlossen und ausgeliefert; historische Freigaben erhalten. |
| Abgeschlossener Teilumfang | Die alte Aufgabe „genau eine Regel samt Rückkehr belegen“ ist für TOP_DOWN_CANDIDATE erfüllt; Approval allein aktiviert nicht. |
| Soll / Nicht-Soll | **Soll:** Explizite Aktivierung einer kompatiblen freigegebenen Version, konkrete Aktivierungsherkunft und kontrollierte Rückkehr zu früherer Version. **Nicht-Soll:** Keine Aktivierung durch Installation, Migration, Review oder Modellfreigabe. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung/Betriebsnachweis; weitere Familien gesondert. |
| Implementierung / Consumer | RuntimeActivationService.activate verlangt APPROVED-Version, erzeugt append-only Aktivierungsrecord und weist bereits aktive Version ab. resolve_by_key liefert stabile Definition/Version; CandidateService verwendet sie für neue unveränderliche Evaluationen. RuntimeActivationPanel zeigt gespeicherte aktuelle Version, explizite Bestätigung und erneutes Lesen bei unklarem Ausgang. Rückkehr ist neue Aktivierung einer früheren APPROVED-Version. |
| Test / Commit | [tests/unit/backend/features/model/test_runtime_activation_service.py](../../tests/unit/backend/features/model/test_runtime_activation_service.py); [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts) belegt GOOD-Quellen und A/A/B/A→QUALIFIED/QUALIFIED/NOT_QUALIFIED/QUALIFIED, unveränderte historische Quellen/Evaluationen; [RuntimeActivationPanel.journey.test.tsx](../../frontend/src/features/model/components/RuntimeActivationPanel.journey.test.tsx); historische B07-Qualifikation an 18e3e1411b98d54812850ce006ce24c5ceab874d / Run 40182968277. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technischer A-B-A-Nachweis ist abgeschlossen, keine produktive Aktivierung oder bessere Handelsregel daraus folgern. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende menschliche Abnahme der Aktivierungsbedienung und produktiver Nutzungsnachweis → Benutzer versteht freigegeben versus aktiv und kann bewusst zurückkehren → FT-013 model und FT-005 candidate → fachlich freigegebene konkrete Kandidatenversion, bestehender Diagnose-/Readbackweg → protokollierte Bedienabnahme von Approval-ohne-Aktivierung, separater Aktivierung und Rückkehr mit unveränderter Historie; kein neuer Betriebsauftrag aus alten Freigaben. |
| Umfangsentscheidung | Die alte V1- und Golden-Path-Aussage ohne Runtime-Aktivierung ist historisch. Vorhandener Service schließt die Infrastruktur-Lücke, nicht jede Modellfamilien-/Betriebsabnahme. |

</details>

<a id="pb-020-stop-model"></a>
<details>
<summary>PB-020 — Stopmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Stopmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 Governance; FT-007/FT-010 fachliche Consumer. Lieferziel: D. |
| Arbeitsstatus | Analysis — benachbarte Plan-/Management-/Hilfsfunktionen vorhanden; eigenständige Modellfamilie offen. |
| Abgeschlossener Teilumfang | Benachbarte Plan-/Management-/Workspacefunktionen bleiben anerkannt, generische Governance vorhanden. |
| Soll / Nicht-Soll | **Soll:** Eine konkrete fachliche Stopmodellfamilie hat definierte Inputs, Versionen und Consumer. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung/Prüfung des spezifischen Consumers. |
| Implementierung / Consumer | Manuelle Stop-/Zielpläne, Managementevents und Regelprüfung sind vorhanden. Die tatsächlichen Modell- und Runtimeconsumer sind EOD_TREND_MOMENTUM, MARKET_CONTEXT/RELATIVE_STRENGTH und TOP_DOWN_CANDIDATE; die gelesenen aktiven Modell-/Plan-/PostTradeverträge liefern keinen eigenständigen vollständigen Stopmodell-Versions-/Anwendungs-/Aktivierungsvertrag. Kein Abwesenheitsschluss allein aus Suchtreffern. [docs/foundation/MODEL_BOOK.md](../../docs/foundation/MODEL_BOOK.md) grenzt FT-007 ausdrücklich von automatischen Handels-/Scoring-/Positionsgrößenmodellen ab; Entry/Stop/Targets sind manuelle Planparameter. |
| Test / Commit | Keine familienbezogene vollständige Runtime-/Rückkehr-/Abnahmeprüfung für Stopmodell nachgewiesen; Candidate-Journey ist kein Ersatz. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Fachlicher Familienumfang und Eingänge nicht hinreichend entschieden/nachgewiesen; keine Modellparameter oder Regeln erfinden. |
| Software-Auslieferung | Keine Auslieferung dieser vollständigen Modellfamilie belegt. Plan-/Management-/Governance-Nachbarfunktionen sind in v1.5.52 enthalten. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlender eigenständiger Stopmodell-Vertrag → Benutzer erhält erklärbare versionierte Unterstützung mit genauen Inputs und unveränderten alten Ergebnissen → FT-007 trade_plan / FT-010 trade_position und position_monitoring → dokumentierte Modellsemantik, erforderliche Quellen und Consumerentscheidung → angenommener Vertrag mit Referenz-/Negativfällen; anschließend Versionierung, tatsächliche Anwendung und erforderliche Aktivierungs-/Rückkehrstrecke derselben Familie nachgewiesen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-target-model"></a>
<details>
<summary>PB-020 — Zielmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Zielmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 Governance; FT-007/FT-010 fachliche Consumer. Lieferziel: D. |
| Arbeitsstatus | Analysis — benachbarte Plan-/Management-/Hilfsfunktionen vorhanden; eigenständige Modellfamilie offen. |
| Abgeschlossener Teilumfang | Benachbarte Plan-/Management-/Workspacefunktionen bleiben anerkannt, generische Governance vorhanden. |
| Soll / Nicht-Soll | **Soll:** Eine konkrete Zielmodellfamilie ist fachlich definiert und reproduzierbar anwendbar. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung/Prüfung des spezifischen Consumers. |
| Implementierung / Consumer | Manuelle Stop-/Zielpläne, Managementevents und Regelprüfung sind vorhanden. Die tatsächlichen Modell- und Runtimeconsumer sind EOD_TREND_MOMENTUM, MARKET_CONTEXT/RELATIVE_STRENGTH und TOP_DOWN_CANDIDATE; die gelesenen aktiven Modell-/Plan-/PostTradeverträge liefern keinen eigenständigen vollständigen Zielmodell-Versions-/Anwendungs-/Aktivierungsvertrag. Kein Abwesenheitsschluss allein aus Suchtreffern. [docs/foundation/MODEL_BOOK.md](../../docs/foundation/MODEL_BOOK.md) grenzt FT-007 ausdrücklich von automatischen Handels-/Scoring-/Positionsgrößenmodellen ab; Entry/Stop/Targets sind manuelle Planparameter. |
| Test / Commit | Keine familienbezogene vollständige Runtime-/Rückkehr-/Abnahmeprüfung für Zielmodell nachgewiesen; Candidate-Journey ist kein Ersatz. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Fachlicher Familienumfang und Eingänge nicht hinreichend entschieden/nachgewiesen; keine Modellparameter oder Regeln erfinden. |
| Software-Auslieferung | Keine Auslieferung dieser vollständigen Modellfamilie belegt. Plan-/Management-/Governance-Nachbarfunktionen sind in v1.5.52 enthalten. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlender eigenständiger Zielmodell-Vertrag → Benutzer erhält erklärbare versionierte Unterstützung mit genauen Inputs und unveränderten alten Ergebnissen → FT-007 trade_plan / FT-010 trade_position und position_monitoring → dokumentierte Modellsemantik, erforderliche Quellen und Consumerentscheidung → angenommener Vertrag mit Referenz-/Negativfällen; anschließend Versionierung, tatsächliche Anwendung und erforderliche Aktivierungs-/Rückkehrstrecke derselben Familie nachgewiesen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-assistant"></a>
<details>
<summary>PB-020 — Trade Assistant</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Trade Assistant. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 laut ursprünglichem Modellplan; konkrete fachliche Consumer-/Ownershipentscheidung offen. Lieferziel: D. |
| Arbeitsstatus | Analysis — benachbarte Plan-/Management-/Hilfsfunktionen vorhanden; eigenständige Modellfamilie offen. |
| Abgeschlossener Teilumfang | Benachbarte Plan-/Management-/Workspacefunktionen bleiben anerkannt, generische Governance vorhanden. |
| Soll / Nicht-Soll | **Soll:** Eine begrenzte, nachvollziehbare Entscheidungsunterstützung mit explizitem Versionsbezug. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Befundklasse / Lückenart | Eigenständige ursprüngliche Funktion im geprüften Pfad nachweislich fehlend; vorhandene Bausteine unten erhalten. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung/Prüfung des spezifischen Consumers. |
| Implementierung / Consumer | Manuelle Stop-/Zielpläne, Managementevents und Regelprüfung sind vorhanden. Die tatsächlichen Modell- und Runtimeconsumer sind EOD_TREND_MOMENTUM, MARKET_CONTEXT/RELATIVE_STRENGTH und TOP_DOWN_CANDIDATE; die gelesenen aktiven Modell-/Plan-/PostTradeverträge liefern keinen eigenständigen vollständigen Trade Assistant-Versions-/Anwendungs-/Aktivierungsvertrag. Kein Abwesenheitsschluss allein aus Suchtreffern. [docs/foundation/MODEL_BOOK.md](../../docs/foundation/MODEL_BOOK.md) grenzt FT-007 ausdrücklich von automatischen Handels-/Scoring-/Positionsgrößenmodellen ab; Entry/Stop/Targets sind manuelle Planparameter. |
| Test / Commit | Keine familienbezogene vollständige Runtime-/Rückkehr-/Abnahmeprüfung für Trade Assistant nachgewiesen; Candidate-Journey ist kein Ersatz. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Fachlicher Familienumfang und Eingänge nicht hinreichend entschieden/nachgewiesen; keine Modellparameter oder Regeln erfinden. |
| Software-Auslieferung | Keine Auslieferung dieser vollständigen Modellfamilie belegt. Plan-/Management-/Governance-Nachbarfunktionen sind in v1.5.52 enthalten. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlender eigenständiger Trade Assistant-Vertrag → Benutzer erhält erklärbare versionierte Unterstützung mit genauen Inputs und unveränderten alten Ergebnissen → bestehende FT-013-Governance und vom Product Owner zu präzisierender fachlicher Consumer → dokumentierte Modellsemantik, erforderliche Quellen und Consumerentscheidung → angenommener Vertrag mit Referenz-/Negativfällen; anschließend Versionierung, tatsächliche Anwendung und erforderliche Aktivierungs-/Rückkehrstrecke derselben Familie nachgewiesen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-observation-model"></a>
<details>
<summary>PB-020 — Nachbeobachtungsmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Nachbeobachtungsmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-011 fachlicher Consumer; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis — fest definierte FT-011-V1-Logik abgeschlossen; eigenständig governte Nachbeobachtungsfamilie offen. |
| Abgeschlossener Teilumfang | Feste deterministische 20-EOD-Nachbeobachtung und Consumer vorhanden. |
| Soll / Nicht-Soll | **Soll:** Definierte Nachbeobachtungslogik mit konkretem historischen Modellbezug. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung spezifischer Modellprovenienz/Governance nach Entscheidung. |
| Implementierung / Consumer | [post_trade/domain/models.py](../../backend/app/features/post_trade/domain/models.py) erzwingt FT011_V1_OBSERVATION_COUNT=20; [observation_metrics.py](../../backend/app/features/post_trade/domain/observation_metrics.py) berechnet deterministische EOD-Evidence, [observation_service.py](../../backend/app/features/post_trade/application/observation_service.py) und PostTradeReviewPage konsumieren sie. Die Berechnungslogik ist tatsächlich vorhanden. Keine eigenständige FT-013-ModelVersion-/Aktivierungsverbindung für die Nachbeobachtungsfamilie im gelesenen Runtimepfad. |
| Test / Commit | FT-011-Domain-, PostgreSQL-Lifecycle- und Journal-E2E-Nachweise belegen V1. Kein eigener familienbezogener Aktivierungs-/Versionswechseltest belegt. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Ob der bestehende feste V1-Vertrag die ursprüngliche Versionierungszusage ausreichend erfüllt oder eine separat governte Familie nötig ist, muss dokumentiert entschieden werden. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlender klarer historischer Modellversionsvertrag jenseits fester V1-Logik → Benutzer reproduziert Beobachtungen mit damals gültiger Methode → FT-011 post_trade, FT-013 model → akzeptierter Umfang von Versionierung und Wechsel sowie Datenvertrag → dokumentierter reproduzierbarer Versionsbezug mit Referenzfall; falls Governance gefordert, separater Wechsel-/Rückkehrnachweis ohne alte Evidence umzuschreiben. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-candidate-family"></a>
<details>
<summary>PB-020 — TOP_DOWN_CANDIDATE als konkrete Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Präzisierung, FT-019/FT-020. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005, FT-013, FT-019, FT-020. Lieferziel: D. |
| Arbeitsstatus | Business Review — fachlicher Abnahmenachweis offen; TOP_DOWN_CANDIDATE/1.0 und /2.0 sowie GOOD-A→B→A technisch abgeschlossen und ausgeliefert; historische LIMITED-Qualifikation erhalten. |
| Abgeschlossener Teilumfang | Konkrete Kandidatenmodellstrecke inklusive exakter Quellen, beider V2-Policies, A→B→A und unveränderter früherer Ergebnisse. Die widersprüchliche alte „B07 bleibt offen“-Passage ist historisch überholt. |
| Soll / Nicht-Soll | **Soll:** Die bestehende konkrete Kandidatenregel über Hypothese, Proposal, Validation, Approval, separate Aktivierung und Anwendung nachvollziehen. **Nicht-Soll:** Keine neue Candidate-Strecke oder automatische Auswahl/Aktivierung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung; Daten/Evaluationsbedarf bei fachlicher Modellverbesserung. |
| Implementierung / Consumer | [candidate/domain/runtime_definition.py](../../backend/app/features/candidate/domain/runtime_definition.py) akzeptiert exakte bekannte V1-/V2-Schemas und Policies, [candidate/domain/qualification.py](../../backend/app/features/candidate/domain/qualification.py) wendet sie an. CandidateService löst aktive Governanceversion auf und speichert Ergebnis/Kriterien plus drei konkrete Analysequellen. TopDownEvaluationOrchestrator liest echte FT-006-Analysen einschließlich nativer Markt-/Sektorreferenzen. Ganze Hypothese→Approval→separate Aktivierung→Anwendung→Rückkehr im gerouteten UI. |
| Test / Commit | [tests/unit/backend/features/candidate/test_candidate_runtime_execution.py](../../tests/unit/backend/features/candidate/test_candidate_runtime_execution.py); [tests/unit/backend/features/candidate/test_runtime_definition.py](../../tests/unit/backend/features/candidate/test_runtime_definition.py); [tests/unit/backend/features/candidate/test_orchestration.py](../../tests/unit/backend/features/candidate/test_orchestration.py); [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts); [tests/e2e/support/candidate-governance-setup.ts](../../tests/e2e/support/candidate-governance-setup.ts); Candidate-Unit-/Runtime-Definitionstests; historical GOOD-B07 an 18e3e141 / Run 40182968277, heutiger Ownerjob erneut auf Main. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | GOOD-Referenznachweis B07 ist technisch erledigt. Historische LIMITED-Qualifikation behält ihren Geltungsumfang; kein Backtest- oder wirtschaftlicher Überlegenheitsbeweis. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Fehlende menschliche Fach-/Bedienabnahme und wirtschaftliche Validierung der konkreten Änderung → Benutzer versteht Wirkungsänderung bei gleicher Evidence → FT-005 candidate und FT-013 model → akzeptierte fachliche Policy und ausreichend qualifizierte unveränderte Quellen → protokollierte Fachabnahme des bereits implementierten A-B-A-Wegs; wirtschaftliche Modellverbesserung nur nach gesondertem Daten-/Validationsauftrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-market-context"></a>
<details>
<summary>PB-020 — MarketContext als fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Top-down-Präzisierung. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006 / FT-005; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Released — fachliche MARKET_CONTEXT/1.0.0-Berechnung und Candidate-Verwendung vorhanden; Analysis eigenständiger Governance. |
| Abgeschlossener Teilumfang | MARKET_CONTEXT-Berechnung mit fester Modell-ID/Version und echtem Consumer. |
| Soll / Nicht-Soll | **Soll:** Fachliche Berechnung, historische Version und tatsächlicher Runtime-Consumer bleiben genau referenzierbar. **Nicht-Soll:** Governance der Kandidatenregel beweist nicht automatisch eine eigenständig governte Aktivierung dieser Familie. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung/Prüfung nur für zusätzliche Governance. |
| Implementierung / Consumer | [analysis/domain/top_down.py](../../backend/app/features/analysis/domain/top_down.py) definiert MARKET_CONTEXT/1.0.0: Long-/Medium-Trend bestimmen Struktur, Short-Trend kann auf CAUTIOUS abwerten; INSUFFICIENT/NOT_EVALUABLE bleiben explizit. [candidate/service/orchestration.py](../../backend/app/features/candidate/service/orchestration.py) ruft calculate_market_context aus konkreter persistierter Marktanalyse auf. Das ist tatsächliche versionierte fachliche Berechnung; kein eigener FT-013-Runtime-Activation-Consumer. |
| Test / Commit | [tests/unit/backend/features/candidate/test_top_down_domain.py](../../tests/unit/backend/features/candidate/test_top_down_domain.py); [tests/unit/backend/features/candidate/test_orchestration.py](../../tests/unit/backend/features/candidate/test_orchestration.py); [tests/integration/backend/test_top_down_fixture_e2e.py](../../tests/integration/backend/test_top_down_fixture_e2e.py); Top-down-Domain-/Candidate-Orchestrationtests sowie GOOD-Candidate-E2E prüfen tatsächliche Verwendung; kein eigenständiger MARKET_CONTEXT-Aktivierungsnachweis. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Dokumentierte V1-Berechnung nicht mit Kandidatenpolicy verwechseln. Eigener Governance-/Parametrisierungsumfang muss fachlich entschieden sein. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Unentschiedene unabhängige Änderbarkeit/Runtimegovernance → Benutzer kann Herkunft der Marktklassifikation und Änderungen nachvollziehen → FT-006 analysis / FT-005 candidate, Governance FT-013 → Entscheidung, ob feste versionierte Methode genügt oder separat freigebare Familie erforderlich ist → angenommener Provenienz-/Wechselvertrag samt Reproduktionsfall; nur bestätigten zusätzlichen Governanceumfang implementieren. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-relative-strength"></a>
<details>
<summary>PB-020 — Relative Strength als fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Top-down-Präzisierung. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006 / FT-005; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Released — RELATIVE_STRENGTH/1.0.0-Berechnung und Candidate-Verwendung vorhanden; Analysis eigenständiger Governance. |
| Abgeschlossener Teilumfang | Deterministische Berechnung, explizite ID/Version und tatsächlicher Candidate-Consumer. |
| Soll / Nicht-Soll | **Soll:** Fachliche Berechnung, historische Version und tatsächlicher Runtime-Consumer bleiben genau referenzierbar. **Nicht-Soll:** Governance der Kandidatenregel beweist nicht automatisch eine eigenständig governte Aktivierung dieser Familie. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Entscheidung; Implementierung/Prüfung nur für zusätzliche Governance. |
| Implementierung / Consumer | [analysis/domain/top_down.py](../../backend/app/features/analysis/domain/top_down.py) definiert RELATIVE_STRENGTH/1.0.0 als Renditedifferenz über 60 Intervalle mit ±2-Prozentpunkten Neutralzone und definierter Decimalrundung; mindestens 61 abgestimmte Beobachtungen, sonst INSUFFICIENT. [candidate/service/orchestration.py](../../backend/app/features/candidate/service/orchestration.py) richtet Datenreihen aufeinander aus und konsumiert Ergebnis. Kein eigenständiger FT-013-Runtime-Activation-Consumer. |
| Test / Commit | [tests/unit/backend/features/candidate/test_top_down_domain.py](../../tests/unit/backend/features/candidate/test_top_down_domain.py); [tests/unit/backend/features/candidate/test_orchestration.py](../../tests/unit/backend/features/candidate/test_orchestration.py); [tests/integration/backend/test_top_down_fixture_e2e.py](../../tests/integration/backend/test_top_down_fixture_e2e.py); Top-down-Domain-/Orchestrationtests und GOOD-Candidate-E2E; kein eigenständiger Relative-Strength-Aktivierungs-/Rückkehrbeleg. Quellen und Assertionen am geprüften Main gelesen. Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Bestehende V1-Parameter sind dokumentierte Implementierung, keine neu zu erfindenden Schwellen. Separater Governanceumfang offen. |
| Software-Auslieferung | Im geprüften Main c7db441de36297a98d47cdf28c64b4e5d9994692 und veröffentlichten Tag v1.5.52 enthalten. Der historische Draft-/Bereitstellungsstand ist überholt; Veröffentlichung belegt keine vollständige fachliche Abnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt die Installation des Gesamtstands v1.5.51 am 19.11.2026; keine gesonderte beobachtete Nutzung oder Fachabnahme dieser Fähigkeit in den geprüften Quellen. Historische enger begrenzte Nutzungsbelege bleiben erhalten. |
| Restarbeit / nächste Abhängigkeit | Unentschiedener unabhängiger Änderungs-/Versionsconsumervertrag → Benutzer kann historische relative Stärke korrekt reproduzieren → FT-006 analysis / FT-005 candidate, Governance FT-013 → Entscheidung zum hinreichenden festen Versionsumfang oder eigenständiger Freigabe/Aktivierung → akzeptierter Provenienz-/Reproduktionsvertrag mit Datenlückenfällen; bei Erweiterung eigene Aktivierungs-/Rückkehrprüfung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### Bestehende unnummerierte Fähigkeiten und Querschnittsarbeit

[Datenprovider und benutzerverwaltete Konfiguration](#provider-configuration) · [Marktdatenbereitschaft, Qualität und Herkunft](#market-data-quality) · [Datenaktualisierung und Schedulerzustände](#market-data-refresh) · [Kursprotokoll und versionierte Produktbelege](#market-data-evidence) · [IV-Datenbereitschaft und hypothetisches Modelllabor](#iv-risk-lab) · [Regelüberwachung und fachliche Alerts](#monitoring-rules) · [Benachrichtigungen und Zustellzustände](#notification-delivery) · [Erinnerungen](#reminders) · [Modellüberwachung](#model-monitoring) · [Täglicher Operational Workspace](#operational-workspace) · [Performanceoptimierung](#operations-optimization) · [Stabilität und sichere Betriebsgrenzen](#operations-stability) · [Regressionstests](#operations-regression) · [Releasevorbereitung und Softwarestand](#operations-release) · [Betriebsnachweis der identifizierten Zielinstallation](#operations-installation)

<a id="provider-configuration"></a>
<details>
<summary>unnummeriert — Datenprovider und benutzerverwaltete Konfiguration</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Datenprovider. Bereich/Querschnitt: 1, 2. Bestehender Bezug: separates Providerfeature; TC-001 nur technische Dateninfrastruktur. Lieferziel: A. |
| Arbeitsstatus | Released — technische Mapping-/Berechtigungsgrenzen; Analysis — vollständiges benutzerverwaltetes Providerfeature |
| Abgeschlossener Teilumfang | Vorhandene Mapping-/Validierungs-/Status- und Allowed-Provider-Anbindung nicht erneut implementieren. |
| Soll / Nicht-Soll | **Soll:** Provider-/Quellenidentität, Rechte und bewusste Einrichtung haben eindeutige Ownership. **Nicht-Soll:** TC-001 wird nicht zum erfundenen fachlichen Stammdatenowner; keine neue Zustimmung oder kostenpflichtiger Abruf. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung und Prüfung; danach ggf. Implementierung des abgegrenzten Restes. |
| Implementierung / Consumer | Vorhanden: Provider-Mapping-Administration mit Anlegen/Prüfen/Aktivieren, Providerstatus ohne Secrets und zentrale Providereligibilität. Konfiguration/Consent in core/config, CLI und Provideradaptern; kein generisches eigenständiges Provider-Verwaltungsfeature aus dem Routing ableiten. Quellen: [backend/app/features/market_data/api/router.py](../../backend/app/features/market_data/api/router.py); [service/administration.py](../../backend/app/features/market_data/service/administration.py); [service/provider_eligibility.py](../../backend/app/features/market_data/service/provider_eligibility.py); [backend/app/core/config/settings.py](../../backend/app/core/config/settings.py). |
| Test / Commit | [tests/unit/backend/features/market_data/test_mapping_administration.py](../../tests/unit/backend/features/market_data/test_mapping_administration.py); [tests/unit/backend/features/market_data/test_provider_capabilities.py](../../tests/unit/backend/features/market_data/test_provider_capabilities.py); [tests/unit/backend/test_settings.py](../../tests/unit/backend/test_settings.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Bestehende quellspezifische Zustimmungen/Entscheidungen behalten ihren Umfang. Vollständiger M1-Vertrag für benutzerverwaltete Providerkonfiguration nicht belegt. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Installation des damaligen v1.5.51-Codes durch PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; Nutzung und fachliche Abnahme genau dieses Teilpfads nicht separat nachgewiesen. |
| Restarbeit / nächste Abhängigkeit | Unbestimmter Restumfang einer benutzerverwalteten Providerverwaltung → Benutzer kann unterstützte Quellen und zulässige Konfiguration bewusst einrichten → bestehende Administration/Market-Data-Providergrenze → Zuständigkeit und unterstützte Einstellungen/Rechte entscheiden → dokumentierter Vertrag mit eindeutigem Owner; jeder vereinbarte Einrichtungs-/Fehler-/Deaktivierungsweg ist durch UI/API/Tests oder klaren Folgeauftrag abgedeckt. |
| Umfangsentscheidung | Original M1 bleibt offen, soweit nicht belegt. Vorhandener Katalog sieht ein separates später zu spezifizierendes Providerfeature vor; keine neue FT-Nummer. |

</details>

<a id="market-data-quality"></a>
<details>
<summary>unnummeriert — Marktdatenbereitschaft, Qualität und Herkunft</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Datenprovider; M2: Datenbasis; spätere TC-001-Fähigkeit. Bereich/Querschnitt: 2. Bestehender Bezug: TC-001; fachliche Consumer bleiben Eigentümer ihrer Ergebnisse. Lieferziel: A. |
| Arbeitsstatus | Released — Qualitäts-/Provenienzverträge; Observed — Gesamtread vom 22.11. und gebundene P02-V2-Teilabdeckung vom 24.11.; weitere Datenversorgung und strenge Regelabdeckung offen. Observed — archivgebundene Quellenkandidaten-Ergänzung vom 24.11., 20:33 Uhr ausgewertet; konkrete P01-Originaldateideckung separat geprüft, produktive P01-Verarbeitung offen. |
| Abgeschlossener Teilumfang | Technische Qualitäts-/Zeittrennung, V2-Verarbeitung und Datenproblemepisoden sind ausgeliefert. Zusätzlich ist der falsche Produktende-/Zahlungstagvergleich beim Product-Owner in v1.5.52 korrigiert, qualifiziert und veröffentlicht; diese technische Ursache ist keine offene Implementierungsaufgabe mehr. Die zusätzliche [Collector-Ergänzung](../reviews/DEPOT_SOURCE_COVERAGE_COLLECTOR_2026-11-24.md) erschließt aktuelle gespeicherte Coverage und bislang nicht exportierte Auswahl-/Produkt-/Bewertungsfakten; dies ist noch keine neue Positionsabnahme. |
| Soll / Nicht-Soll | **Soll:** Fehlende, veraltete, indikative und nicht anwendbare Daten sowie Kurs-, Abruf- und Erfassungszeiten unterscheiden. **Nicht-Soll:** Erfolgreicher Abruf ersetzt keine aktuelle verwertbare Quote; unbekannt ist nicht Null oder geringes Risiko. |
| Befundklasse / Lückenart | Vorhandene Funktion mit offener realer Datenversorgung und Betriebswirkungsprüfung. **Art der Restarbeit:** Quellen-/Einheiten-/Identitätsqualifikation, persönliche Entscheidungen und Nachweis am privaten Bestand; Datumsfix technisch abgeschlossen. |
| Implementierung / Consumer | Backend unterscheidet gespeicherte Originalquote, Empfangszeit, Retention/Refreshfehler, Identitätswechsel und Kursverwendbarkeit. refresh_quality.quote_evidence bewertet tatsächliche Quote separat von Jobstatus. V2 qualifiziert eigene Original-BID-, Emittenten- und verzögerte Quellenmodi; eingehende Zeitpunkte bleiben verschieden. Quellen: [market_data/service/refresh_quality.py](../../backend/app/features/market_data/service/refresh_quality.py), [risk_read.py](../../backend/app/features/market_data/service/risk_read.py); [position_monitoring/domain/indicative_entry.py](../../backend/app/features/position_monitoring/domain/indicative_entry.py) und [service/indicative_entry_inputs.py](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py). Seit v1.5.52 trennt [current-product-document-v2](../../backend/app/providers/product_review_documents.py) Produktende und Zahlungstag samt Rollen und Qualifiern. [review_evidence](../../backend/app/features/product/service/review_evidence.py) vergleicht das Termsdatum mit einem exakt belegten Originalfeld; echte Widersprüche bleiben Sperren. [ProductReviewReadiness](../../backend/app/features/product/service/review_acquisition.py) führt den lokalen Originalupgrade vor dem Netzwerk-Backoff aus; passive GETs lösen ihn nicht aus. [ReviewCalendar](../../backend/app/features/market_data/service/review_calendars.py) und die [Import-CLI](../../backend/app/tools/import_review_calendar_original.py) erlauben ausschließlich das qualifizierte XSTU-2026-Original mit lesender Vorschau, lokaler Herkunft und DAY_ONLY-Grenze. |
| Test / Commit | [tests/unit/backend/features/market_data/test_refresh_quality_diagnostics.py](../../tests/unit/backend/features/market_data/test_refresh_quality_diagnostics.py); [tests/unit/backend/features/market_data/test_saved_quote_evidence.py](../../tests/unit/backend/features/market_data/test_saved_quote_evidence.py); [tests/integration/backend/database/test_indicative_entry_v2_postgres.py](../../tests/integration/backend/database/test_indicative_entry_v2_postgres.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. Zusätzliche v1.5.52-Nachweise: [Parserfälle](../../tests/unit/backend/providers/test_product_review_documents.py), [Originalupgrade](../../tests/unit/backend/features/product/test_product_document_reparse.py), [sequenzielle und konkurrierende PostgreSQL-Upgrades](../../tests/integration/backend/database/test_product_document_reparse_postgres.py), [Kalender-/Importfälle](../../tests/unit/backend/features/market_data/test_review_calendars.py); tatsächlich in der neuen [Main-CI](#nachweisregister) ausgeführt. |
| Fachliche Abnahme | Quellenmoduspacing Variante 2 war ausdrücklich entschieden; V2 ist eine ausdrücklich beauftragte indikative Alternative. Das ist keine B58- oder vollständige Depotqualifikation. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367), Nutzerbeleg 19.11.2026: v1.5.51/254f0bbd… installiert, vier Dienste healthy, Readiness 200/ready, Schema 20261118_0060. Audit 18:13:12 MEZ: V2-Zyklus 18:06:42–18:07:17 MEZ, 35,307 s, running=true, last_error=null; Review und Deadline je 6 bewertet/6 Datenprobleme/0 technische Positionsfehler. Kein eigener PC-Zugriff dieser Prüfung. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. Späterer [P02-Read vom 24.11.2026](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060 und vier gesunde Dienste; historischer Timeout konkret, jüngeres `BELOW_ENTRY` mit Bid um 18:21:41 Uhr MEZ. Kein neuer Gesamtzyklus-/Inventar-/Fristnachweis. |
| Restarbeit / nächste Abhängigkeit | Die Vierer-Matrix vom 22.11. belegt damalige Käufe/Kaufwährungen sowie Quellen-/Einheits-/Basiswert-/Kalender-/Fristlücken. Der P02-Gap ist seit 24.11. konkretisiert, eine jüngere gespeicherte V2-Bewertung mit Bid beobachtet. **Einzige nächste Abhängigkeit:** [eine weitere tatsächlich offene Position versorgen](#naechster-schnitt), jetzt konkret P01 nach abgeschlossener Archiv-/Quellenbindung und positivem gettex-Originaldateitreffer: belegte Einheit, Listing/Mapping und frischer Verbraucherpreis. Die [Quellen-/Kostenprüfung](../reviews/ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md) bleibt datiertes Beschaffungsangebot; tatsächliche Listingdeckung, Rechte und Originalstatus werden nicht daraus abgeleitet. Weitere Abnahme bleibt getrennte Regelabdeckung am Verbraucher, kein Runnerzähler. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>



<a id="market-data-refresh"></a>
<details>
<summary>unnummeriert — Datenaktualisierung und Schedulerzustände</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Datenaktualisierung. Bereich/Querschnitt: 2, 6; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: TC-001; bestehender Scheduler, keine neue FT-Nummer. Lieferziel: A. |
| Arbeitsstatus | Released — Scheduler-/Lane-/Pacing-Schnitte; Observed — Refresh im v1.5.52-Read und späterer gespeicherter P02-Bid unter v1.5.54; kontinuierliche Versorgung und Gesamtdeckung nicht belegt. |
| Abgeschlossener Teilumfang | Pacing-/Lane-/Discovery-Korrekturen integriert und in v1.5.51 ausgeliefert; technische Umsetzung/Integration abgeschlossen. |
| Soll / Nicht-Soll | **Soll:** Abrufzustände und Datenbereitschaft nachvollziehbar zeigen; vorhandene Providergrenzen erhalten. **Nicht-Soll:** Kein Diagnoselauf mit unbeabsichtigtem Schreiben/Versand; neue Planung ist keine Providerzustimmung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Betriebsprüfung und Datenversorgung. |
| Implementierung / Consumer | Fünf bestehende Lanes, Same-Cycle-Discovery-Retry, Public-Website-Pacing, Quote-Lane-Guard und passive /refresh/status-Diagnose sind im Main enthalten. refresh_runner bindet Lauf in lifespan ein. Quellen: [market_data/service/refresh.py](../../backend/app/features/market_data/service/refresh.py), [refresh_runner.py](../../backend/app/features/market_data/service/refresh_runner.py), [refresh_catalog.py](../../backend/app/features/market_data/service/refresh_catalog.py); [market_data/api/router.py](../../backend/app/features/market_data/api/router.py); [app/main.py](../../backend/app/main.py). Snapshot-Pacing-[#271](https://github.com/burckhju/trading-workspace/pull/271) und Guard-[#295](https://github.com/burckhju/trading-workspace/pull/295) dürfen nicht erneut als Integrationsauftrag stehen. Der XSTU-Owner kann seit v1.5.52 eine korrekt gespeicherte lokale Originalrevision mit verstärkter Integritätsprüfung wiederverwenden; dies belegt weder einen ausgeführten Import noch die Behebung des HTTP-403-Netzabrufs. |
| Test / Commit | [tests/unit/backend/features/market_data/test_refresh_lanes.py](../../tests/unit/backend/features/market_data/test_refresh_lanes.py); [tests/unit/backend/features/market_data/test_refresh_source_modes.py](../../tests/unit/backend/features/market_data/test_refresh_source_modes.py); [tests/unit/backend/features/market_data/test_refresh_backlog.py](../../tests/unit/backend/features/market_data/test_refresh_backlog.py); [tests/integration/backend/test_refresh_diagnostics_api.py](../../tests/integration/backend/test_refresh_diagnostics_api.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Begrenzte Pacing-Entscheidung vom 21.10. erhalten; Vollabdeckung aller Quellen kein Testschluss. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt Monitoring-Hintergrundlauf; Audit besitzt separate Quote-Refresh-Statistik. Diese qualifiziert keine V2-Eingänge; vollständige Scheduler-/Datenabdeckung weiter nicht nachgewiesen. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. Späterer [P02-Read vom 24.11.2026](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060 und vier gesunde Dienste; historischer Timeout konkret, jüngeres `BELOW_ENTRY` mit Bid um 18:21:41 Uhr MEZ. Kein neuer Gesamtzyklus-/Inventar-/Fristnachweis. |
| Restarbeit / nächste Abhängigkeit | Am 22.11. endeten drei Positionen ohne bestätigte Route; P02 hatte einen bidlosen Bestand und einen später erfassten `JPMORGAN_SNAPSHOT_TIMEOUT`. Am 24.11. ist ein jüngerer Bid mit V2-Verbraucherwirkung gespeichert. Weder ursprüngliche Netzwerkursache noch erster Wiederherstellungszeitpunkt sind belegt. **Einzige nächste Abhängigkeit:** [eine weitere offene Position über bestehende Quellenauswahl versorgen](#naechster-schnitt). Scheduler/Pacing/Backoff beibehalten; konkrete Kandidaten-/Ausschlussgründe klären. Keine unbelegte Intervallverkürzung oder neue Transportreparatur aus dem historischen Timeout ableiten. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Aktueller Integrationsabgleich 28.10.2026:** [PR #295](https://github.com/burckhju/trading-workspace/pull/295)
ist mit `13e8d5331abab32d4998118e83aaecbc231dea31` in Main integriert.
Der Guard gegen erneuten Quote-Lane-Start während des laufenden Discovery-Retry
ist in der aktuellen Basis `dc89dfa65758dfc1258a8fab657257f6598b0179` / 1.5.29
enthalten. [Reviewnachweis](../reviews/REMAINING_WORK_INTEGRATION_2026-10-28.md)
und [anschließender Release-PR #296](https://github.com/burckhju/trading-workspace/pull/296)
bleiben getrennt von einer beobachteten Scheduler-/PC-Abnahme. Der Währungsfix
übernimmt keine historischen #225/#235-Änderungen erneut und verändert diese
Schedulerkorrektur nicht. Die früheren Übergabegrenzen oben bleiben datierte
historische Nachweise, keine erneute Implementierungsabhängigkeit.

</details>

</details>



<a id="market-data-evidence"></a>
<details>
<summary>unnummeriert — Kursprotokoll und versionierte Produktbelege</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Nach ursprünglicher Baseline: 1.5.4-Ergänzung zu M1/M10. Bereich/Querschnitt: 1, 2. Bestehender Bezug: bestehende TC-001-/Produktbelegfähigkeit; keine neue FT-Zuordnung. Lieferziel: A, C. |
| Arbeitsstatus | Released — dauerhafte Quote-/Original-/Kalender-/Produktbelegpfade; Daten-/Betriebsprüfung offen |
| Abgeschlossener Teilumfang | Persistenz, Versionierung, Ownerbindung und passive Reads sind vorhanden. Zusätzlich sind Parser current-product-document-v2, idempotenter gespeicherter v1→v2-Originalupgrade vor dem Netzwerk-Backoff sowie der enge lokale XSTU-2026-Originalimport implementiert, technisch qualifiziert und in v1.5.52 veröffentlicht. Der sequenzielle und konkurrierende Originalupgrade ist mit echter PostgreSQL-Persistenz nachgewiesen; die neuen Kalenderimportfälle verwenden SQLite und gemockte CLI-Grenzen. |
| Soll / Nicht-Soll | **Soll:** Erlaubte Abrufe nachvollziehbar protokollieren und manuell geprüfte Belege an Produktidentität/TermsVersion binden. **Nicht-Soll:** Kein Backfill erfundener Historie; Empfangszeit ersetzt keine Originalkurszeit. |
| Befundklasse / Lückenart | Beleginfrastruktur einschließlich Datumsfix und Importweg technisch abgeschlossen; tatsächliche Anwendung auf private Originale und weitere Datenversorgung offen. **Art der Restarbeit:** Betriebsnachweis, Original-/Identitäts-/Einheitenqualifikation und gegebenenfalls konkret beauftragte Datenhandlung. |
| Implementierung / Consumer | Vorhanden sind Warrant-Quote-Samples, gespeicherte Quoteprovenienz, ursprüngliche Marktstatusmeldungen auch ohne Preis, Originalkalender, unveränderliche Produktmaßstabsrevisionen, KID-Originalbytes/Hash/Parser sowie Original-Listingtermine und Exitwahl. Quellen: [market_data/service/risk_read.py](../../backend/app/features/market_data/service/risk_read.py), `session_evidence.py`, `status_observations.py`; [product/service/review_evidence.py](../../backend/app/features/product/service/review_evidence.py), `price_scale_evidence.py`, `deadline_listing_terms.py`, `deadline_choice.py`. ProductReviewReadiness beschafft unterstützte KIDs/Kalender außerhalb wirtschaftlicher Transaktion; passive Reader beschaffen nichts. Seit v1.5.52 trennt [current-product-document-v2](../../backend/app/providers/product_review_documents.py) Produktende und Zahlungstag samt Rollen und Qualifiern. [review_evidence](../../backend/app/features/product/service/review_evidence.py) vergleicht das Termsdatum mit einem exakt belegten Originalfeld; echte Widersprüche bleiben Sperren. [ProductReviewReadiness](../../backend/app/features/product/service/review_acquisition.py) führt den lokalen Originalupgrade vor dem Netzwerk-Backoff aus; passive GETs lösen ihn nicht aus. [ReviewCalendar](../../backend/app/features/market_data/service/review_calendars.py) und die [Import-CLI](../../backend/app/tools/import_review_calendar_original.py) erlauben ausschließlich das qualifizierte XSTU-2026-Original mit lesender Vorschau, lokaler Herkunft und DAY_ONLY-Grenze. Der neue gezielte Collectormodus nutzt diese vorhandenen passiven Owner für ursprüngliche/aktuelle Auswahl, Assessmentinputs, Product-Evidenz und KID-Metadaten; keine aktive Neubeschaffung im Diagnosepfad. |
| Test / Commit | [tests/integration/backend/database/test_market_status_observations_postgres.py](../../tests/integration/backend/database/test_market_status_observations_postgres.py); [tests/integration/backend/database/test_session_evidence_postgres.py](../../tests/integration/backend/database/test_session_evidence_postgres.py); [tests/integration/backend/database/test_product_price_scale_evidence_postgres.py](../../tests/integration/backend/database/test_product_price_scale_evidence_postgres.py); [tests/integration/backend/database/test_review_readiness_postgres.py](../../tests/integration/backend/database/test_review_readiness_postgres.py); [tests/integration/backend/database/test_product_deadline_choice_postgres.py](../../tests/integration/backend/database/test_product_deadline_choice_postgres.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. Zusätzliche v1.5.52-Nachweise: [Parserfälle](../../tests/unit/backend/providers/test_product_review_documents.py), [Originalupgrade](../../tests/unit/backend/features/product/test_product_document_reparse.py), [sequenzielle und konkurrierende PostgreSQL-Upgrades](../../tests/integration/backend/database/test_product_document_reparse_postgres.py), [Kalender-/Importfälle](../../tests/unit/backend/features/market_data/test_review_calendars.py); tatsächlich in der neuen [Main-CI](#nachweisregister) ausgeführt. |
| Fachliche Abnahme | V2-Original-/Referenzmarkt-/Historienannahmen ausdrücklich als begrenzt beauftragt; Annahme historischer Kontinuität und Nutzeroriginal sind keine unabhängige Quellenprüfung. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Installation des damaligen v1.5.51-Codes durch PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; Nutzung und fachliche Abnahme genau dieses Teilpfads nicht separat nachgewiesen. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. Späterer [P02-Read vom 24.11.2026](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060 und vier gesunde Dienste; historischer Timeout konkret, jüngeres `BELOW_ENTRY` mit Bid um 18:21:41 Uhr MEZ. Kein neuer Gesamtzyklus-/Inventar-/Fristnachweis. |
| Restarbeit / nächste Abhängigkeit | Getrennte Produktende-/Zahlungsrollen waren am 22.11. bei 4/4 beobachtet; der falsche Datumswiderspruch fehlte. Der aktuelle KID-Parserhead ist für P01/P03/P04 am 24.11. als current-product-document-v2 beobachtet. Genau eine Originalupgrade-Folgerevision und konkrete Kalenderimportherkunft bleiben gezielt zu belegen. Der P02-Journal-/Assessmentread ist am 24.11. abgeschlossen. Produktmaßstäbe, der damalige Produkt-/Basiswertkonflikt, Originalstatus/-zeit und B06-Grundevidenz bleiben offen; vorhandene Käufe/Währungen nicht neu erfassen. **Einzige nächste Abhängigkeit:** [Quellen- und erforderliche Produktbelege für eine weitere offene Position](#naechster-schnitt). Erhaltene Originalupgrade-/Importabnahmegrenzen gelten weiter. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>


<a id="iv-risk-lab"></a>
<details>
<summary>unnummeriert — IV-Datenbereitschaft und hypothetisches Modelllabor</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Nach ursprünglicher Baseline: 1.5.4-Ergänzung. Bereich/Querschnitt: 4, 6; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: bestehende Risiko-/Modelllaborfähigkeit; genaue Code-Ownership hier nicht neu bestimmt. Lieferziel: A, D. |
| Arbeitsstatus | Released — hypothetisches Vanilla-Labor und ehrliche Readiness; reale IV-Fähigkeit blockiert |
| Abgeschlossener Teilumfang | Hypothetischer Rechner und Datenlückenanzeige implementiert/ausgeliefert. |
| Soll / Nicht-Soll | **Soll:** Reale Positionsdaten von eigenen hypothetischen Modellannahmen und deren Modellgrenzen unterscheiden. **Nicht-Soll:** Modelllabor ist kein Beleg echter Positions-IV, historischer IV-Ranks oder belastbarer realer Sensitivität. |
| Befundklasse / Lückenart | Vorhandene Funktion; reale Daten-/Entscheidungsblockade oder fehlender Betriebswirkungsnachweis einer ausgelieferten Korrektur; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Datenversorgung plus fachlicher Modell-/Nutzungsvertrag. |
| Implementierung / Consumer | POST /risk/iv/model-preview ruft solve_iv/revalue für europäische Vanilla Calls/Puts mit explizitem HYPOTHETICAL_ASSUMPTIONS auf, ohne DB/Provider/Positionsmutation. IvRiskPanel zeigt reale IV/Rank/Vega als nicht verfügbar und getrennt IvModelCalculator. assess_iv_readiness liefert ausdrücklich NOT_EVALUABLE; Provider-IV/Greeks, synchrone Underlyingquote, Zins-/Dividendenannahmen sowie qualifizierte Historie fehlen. Quellen: [position_monitoring/api/iv.py](../../backend/app/features/position_monitoring/api/iv.py), [service/iv_readiness.py](../../backend/app/features/position_monitoring/service/iv_readiness.py); [analysis/domain/vanilla_iv.py](../../backend/app/features/analysis/domain/vanilla_iv.py); [frontend/src/features/alert/components/IvRiskPanel.tsx](../../frontend/src/features/alert/components/IvRiskPanel.tsx), [IvModelCalculator.tsx](../../frontend/src/features/alert/components/IvModelCalculator.tsx). |
| Test / Commit | [tests/unit/backend/features/analysis/test_vanilla_iv.py](../../tests/unit/backend/features/analysis/test_vanilla_iv.py); [tests/unit/backend/features/position_monitoring/test_iv_readiness.py](../../tests/unit/backend/features/position_monitoring/test_iv_readiness.py); [frontend/src/features/alert/components/IvRiskPanel.test.tsx](../../frontend/src/features/alert/components/IvRiskPanel.test.tsx); [frontend/src/features/alert/services/iv.test.ts](../../frontend/src/features/alert/services/iv.test.ts) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historischer 1.5.4-Laborscope erhalten; keine Abnahme realer Positions-IV. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Installation des damaligen v1.5.51-Codes durch PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; Nutzung und fachliche Abnahme genau dieses Teilpfads nicht separat nachgewiesen. |
| Restarbeit / nächste Abhängigkeit | Keine qualifizierten realen IV-/Greeks-/synchronen Kurs-/Ereignisdaten → Benutzer erhält belegbare aktuelle Sensitivität mit Modellgrenzen → bestehende Market-Data-/Product-Reader und IV-Readiness/Vanilla-Modell → Quellenrechte, Originalzeit-/Währungs-/Produktqualifikation und Bewertungsvertrag → definierter Realdatensatz erzeugt reproduzierbares Ergebnis; fehlende Eingänge bleiben NOT_EVALUABLE; hypothetisches Labor wird nicht als realer Risikonachweis verwendet. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="monitoring-rules"></a>
<details>
<summary>unnummeriert — Regelüberwachung und fachliche Alerts</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Regelüberwachung. Bereich/Querschnitt: 6. Bestehender Bezug: Position Monitoring & Alert Capability; FT noch offen. Lieferziel: A. |
| Arbeitsstatus | Observed — Gesamtzyklus mit Datenproblemen auf v1.5.52 und gespeicherte P02-V2-Teilabdeckung auf v1.5.54 am 24.11.; Released — technische Teilpfade einschließlich Datumsfix; Business Review — übrige reale Regelabdeckung und Gesamtumfang. |
| Abgeschlossener Teilumfang | Ausgelieferte Reader, B04/B57-Rechenkern, indikative V2 und Produktfristreview bleiben abgeschlossen. Neu: tatsächliche v1.5.52-Installation und regulärer V2-Zyklus, vollständige Vierer-Ursachenmatrix und getrennte Produktende-/Zahlungsrollen am Verbraucher belegt. Vollständige Originalupgrade-/fachliche Depotabnahme ist dadurch nicht erteilt. Am 24.11. zusätzlich: archivgebundener P02-Gapgrund und jüngerer tatsächlicher V2-Entscheid `BELOW_ENTRY` mit Bid auf v1.5.54; keine aktuelle Gesamtquote. |
| Soll / Nicht-Soll | **Soll:** Effektive Positions-/Managementregeln mit richtiger Instrument-/Währungsbasis auswerten; deduplizierte fachliche Alerts erhalten. **Nicht-Soll:** Alert ist keine Notification, kein SELL und keine automatische Stop-/Zieländerung. |
| Befundklasse / Lückenart | Vorhandene Funktion mit konkret belegten Daten-/Zuordnungs-/Entscheidungslücken. Datumsfix wirkt am Verbraucher; P02 ist am 24.11. indikativ beurteilbar gespeichert; P01/P03/P04 sind später neu gelesen und konkret quellen-/produktblockiert. **Art der Restarbeit:** gezielte Versorgung beim bestehenden Owner und Umsetzung der erhaltenen übrigen F207-Reste. |
| Implementierung / Consumer | Runner komponiert getrennt alte Stop-/Ziel-Cycle, Risiko, B04/B57, indikative V1/V2 und kursfreie Produkttermine. V2 hat persistente Bewertungen/Episoden/Alerts, gemeinsame Familie über V1/V2, qualitätsgebundene Erholung und Vollverkaufsbehandlung. ProductDeadline hat eigene Bewertungen/Episoden/Outbox. B04/B57 streng implementiert; QUALIFIED_B58_PATHS=() und Hebeltrader-Scope getrennt. Passive Indicative/Deadline-Reads mit READ ONLY, beide explizit full_baseline_activated=false; Deadline qualified_b05=false und product_cutoff_status=UNVERIFIED. Quellen: [position_monitoring/service/runtime.py](../../backend/app/features/position_monitoring/service/runtime.py), [runner.py](../../backend/app/features/position_monitoring/service/runner.py), indicative_entry*.py, product_deadline_review*.py, [hebeltrader_b58_sources.py](../../backend/app/features/position_monitoring/service/hebeltrader_b58_sources.py); API `__init__.py`; [PositionDetails.tsx](../../frontend/src/features/operational_workspace/components/PositionDetails.tsx) / [IndicativeEntryObservation.tsx](../../frontend/src/features/operational_workspace/components/IndicativeEntryObservation.tsx) / [TradeAlertsPanel.tsx](../../frontend/src/features/alert/components/TradeAlertsPanel.tsx). Seit v1.5.52 liefert der bestehende Product-Owner getrennte Datumsrollen; ProductDeadlineInputs übernimmt sie in das gespeicherte product_evidence. maturity_on bleibt Produktende. Die Monitoringrouter und der Entry-DTO wurden dafür nicht erweitert; Original-/Parserbelege werden zusätzlich beim Product-Owner gelesen. |
| Test / Commit | [tests/integration/backend/database/test_indicative_entry_v2_postgres.py](../../tests/integration/backend/database/test_indicative_entry_v2_postgres.py); [tests/integration/backend/database/test_indicative_entry_postgres.py](../../tests/integration/backend/database/test_indicative_entry_postgres.py); [tests/integration/backend/database/test_product_deadline_review_postgres.py](../../tests/integration/backend/database/test_product_deadline_review_postgres.py); [tests/unit/backend/features/position_monitoring/test_indicative_entry_read_migration.py](../../tests/unit/backend/features/position_monitoring/test_indicative_entry_read_migration.py); [frontend/src/features/operational_workspace/components/IndicativeEntryObservation.test.tsx](../../frontend/src/features/operational_workspace/components/IndicativeEntryObservation.test.tsx) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | V2 als ausdrückliche Alternative beauftragt; volle B01–B58-Baseline bleibt unverändert, B08 ausgeschlossen, B07 eigenständig. Technische Durchläufe ersetzen keine vollständige fachliche Depotabnahme. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367), Nutzerbeleg 19.11.2026: v1.5.51/254f0bbd… installiert, vier Dienste healthy, Readiness 200/ready, Schema 20261118_0060. Audit 18:13:12 MEZ: V2-Zyklus 18:06:42–18:07:17 MEZ, 35,307 s, running=true, last_error=null; Review und Deadline je 6 bewertet/6 Datenprobleme/0 technische Positionsfehler. Kein eigener PC-Zugriff dieser Prüfung. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. Späterer [P02-Read vom 24.11.2026](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060 und vier gesunde Dienste; historischer Timeout konkret, jüngeres `BELOW_ENTRY` mit Bid um 18:21:41 Uhr MEZ. Kein neuer Gesamtzyklus-/Inventar-/Fristnachweis. |
| Restarbeit / nächste Abhängigkeit | **Aktuell 24.11.2026:** Gesamt-, P02- und Quellenkandidatenreads ausgewertet; tatsächliches v1.5.54, P02-`BELOW_ENTRY` und drei weitere offene quellen-/produktblockierte Positionen belegt. [P01 für V2 versorgen](#naechster-schnitt) ist der einzige nächste Auftrag; isolierter passender gettex-Dateitreffer vorhanden. Historische Kaufwährungen waren am 22.11. bei allen vier vorhanden; heutige Bindung der übrigen Archivpositionen ist bestätigt; konkrete Einheits-/Mapping- sowie weitere Produkt-/Kalender-/Fristlücken bleiben beim zuständigen Owner. **B04/B57/B58:** Produktionsregistry leer; eigener Original-BID und Statuszeit/-geltung samt realer Listinglieferung und Recovery sind nicht qualifiziert belegt. Ein neuer Feed braucht außerdem qualifizierten Adapter-/Zeitsemantikanschluss. **B05/B20:** V2 liefert nur getrennten begrenzten Fristreview; Exitlisting, letzter Handelstag, Folgekalender und individueller Produktschluss bleiben erforderliche Belege. **F207-2/B06:** historische Basiswerttrades zu beitragenden Käufen, ursprüngliche Ziele/Zieltreffer, vergleichbarer höchster Schutzboden, Bekanntgabe, Z1-Zählung, weitere Überwachung und Korrekturklärung bleiben offen. **F207-5:** vollständige gemeinsame Meldungsdarstellung, Zustands-/Versions-/Betriebsabnahme gesondert; Teilpfade ersetzen Gesamtumfang nicht. B07 separat, B08 ausgeschlossen. V1/V2 bleiben ausdrücklich freigegebene Alternativen mit eigener begrenzter Aussage, keine Lockerung der strengen Regeln. [Versorgungsnachweis vom 20.11.2026](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md) bindet sämtliche Datenanforderungen und Beschaffungsszenarien; keine neue Providerfreigabe oder Produktivänderung. Die weitere [Restabnahme](#monitoring-restabnahme) erhält die Abschlussgrenzen für diese Teilumfänge. |
| Umfangsentscheidung | Bestehende unnummerierte Fähigkeit behalten; keine FT-Nummer erfinden. Frühere reine Underlying-EOD-Aussage nicht auf sämtliche spätere Regeln verallgemeinern. |





<a id="monitoring-restabnahme"></a>
#### Erhaltene Monitoringreste und ihre Abschlussgrenzen

Diese Reste gehören zum selben Arbeitsstatusfeld; sie sind keine zweite Aufgabenliste und keine zusätzlichen aktuell priorisierten Aufträge. Die ursprünglichen B-/F207-Kennungen und Ausschlüsse bleiben im [Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md) erhalten.

| Verbleibender Teilumfang | Lücke → Benutzerergebnis → bestehender Owner → Voraussetzung → Abschluss |
|---|---|
| Restliches F207-2: Ziel-/Schutzhistorie | Historische dokumentierte Stops, höherer vergleichbarer Schutzboden, Bekanntgabe und spätere Überwachung sind nicht vollständig geschlossen → nachvollziehbarer Schutzvorschlag mit unveränderter historischer Herkunft → vorhandenes Position Monitoring, FT-010 und Executionowner → belegte Z1-/Z2-Ereignisse, persönlicher Basiswerteinstieg, dokumentierte Stop-/Preisachsen und geklärte Korrekturfälle → höhere vorhandene Schutzgrenze bleibt erhalten, Rückgang löscht keinen früheren Treffer, Korrektur erzeugt explizite neue Evidenz; Vorschlag verändert weder Brokerstop noch Ausführungen |
| B06 / Z1-Sitzungen | Vollständige 20-Sitzungen-/80%-Z1-Regel und historischer Z1-Startbezug fehlen → zeitlich erklärbarer Folgestopvorschlag → bestehender Monitoring-/Kalenderowner → dauerhaft belegter Z1-Zeitpunkt, damaliger Einstieg, ursprüngliches Z1 und höherer Schutzboden → Grenzfälle vor/bei 20 abgeschlossenen Sitzungen und max(Schutzboden, Einstieg, 0,8 × ursprünglichem Z1) auf belegter Basiswertachse geprüft; bestehende ATR-Policy nicht still umgedeutet |
| Strenger B04/B57/B58-Betrieb | Technischer Verlust-/Episodenkern vorhanden; geeignete reale Originalstatusversorgung und gegebenenfalls historische Anpassungs-/Bindungsevidenz fehlen → belastbare strenge Verlustbeurteilung → bestehender Market-Data-/Product-/Monitoringowner → erlaubte exakte Original-BID-Quelle, Statusfortgeltung, verifizierte Sitzung, Währung/Skala, 20 abgeschlossene Sitzungen bereits zur Kurszeit → reale Quellenqualifikation einschließlich Zukunft/900-Sekunden-Grenze, negativer/preisloser Meldung, Lücke und Erholung; Datenlücke beendet keine Verlustepisode. V2 ist kein Ersatzbeleg |
| Vollständiges B05/B19/B20 | Rechenkern und begrenzte Produktfristerinnerung vorhanden; feste persönliche Exitbindung, vollständige Termin-/Kalenderbelege und individueller Produktschluss teils offen → nachvollziehbare kursunabhängige vollständige Fristbeurteilung → Product, TC-001, bestehendes Monitoring → verifiziertes Produktende/letzter Handelstag, benötigte Originalkalender und konkreter Cutoff → früheres relevantes Datum; der gesamte Produktterminstag zählt nicht mit; die 20. vorherige Produktsitzung ist der Fristtag, die erste Öffnung der davorliegenden Sitzung ist die B19-Vorwarnung. Verkürzte/ausgefallene Sitzung und Cutoff-/Zeitzonengrenze sind belegt; Tagesstatus `B05_PARTIAL_B20_UNVERIFIED`, `qualified_b05=false` und `product_cutoff_status=UNVERIFIED` erst nach passendem Nachweis ändern |
| Historische Daten- und Skalenabdeckung | Tatsächliche Beschaffung, damalige Listingbindung und gegebenenfalls Anpassungsfaktoren nicht für alle benötigten Historien belegt → reproduzierbarer Vergleich ohne erfundene Preise → Market Data/Product mit FT-009/010-Executionfakten → erlaubte Originalhistorie, Buy-Zeit-/Währungsbelege und dokumentierte Anpassungen → jeder beitragende Kauf und Vergleichspunkt ist zeitlich/skalengenau qualifiziert oder gezielt ausgeschlossen; keine rückwirkend erfundene Coverage |
| Vollständiges F207-5 | Gemeinsame Darstellung, gesehen/abgelehnt/ausgeführt, globale Versionierung und Gesamtbetriebsvertrag bleiben über vorhandene Episode/Delivery hinaus offen → nachvollziehbare gemeinsame Meldungsbearbeitung → vorhandene Alert-/Notification-/Monitoring-/Workspaceowner → bestätigter gemeinsamer Status-/Versionsvertrag und Ergebnisse der jeweiligen Regeln → gleichzeitige Ursachen/Priorität, Wiederanlauf/Deduplizierung und historische Zustände in API/UI/E2E sowie anschließendem Zielbetrieb abgenommen; keine zweite Zustands- oder Ausführungswahrheit |

B07 bleibt die separate Einstiegsprüfung aus #187 mit eigenem Grenzfallnachweis; B08 bleibt ausgeschlossen. Der gleich benannte Candidate-Governance-Testfall B07 ist keine Hebeltrader-Regelfreigabe.

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Quellen-/Implementierungsnachtrag 17.11.2026 nach Installation 1.5.47:**
Main und Tag `v1.5.47` wurden auf
`2d0c7b06476864d68deae67cbb7db41ad1b7376f` zurückgelesen. Der Nutzer meldete
denselben installierten Commit, vier gesunde Container und `Bereitschaft: ready`;
dies ist ein Nutzerbericht zur Installation, kein unabhängig beobachteter
B58-Depotbetrieb. Die fortgesetzte [reale Quellenprüfung](../reviews/B58_ARIVA_ACQUISITION_2026-11-17.md)
bestimmt das tatsächliche Frankfurt-Echtzeitprodukt über ARIVA; frei erreichbare
Last-/Emittenten-/Aussetzungsdaten schließen die Statuszeitlücke weiterhin nicht.
Der eigene, auf diesem Main aufbauende
[Beschaffungsprüfer](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b58-ariva-acquisition-probe-v1)
übernimmt gespeicherte ISINs automatisch, verwendet dokumentierte
Client-Credentials-/Quellen-/Marketstate-/Listingrequests und erfasst echte
Originalantworten, sobald ein berechtigter Evaluationszugang vorliegt. Keine
zusätzliche UI, Migration, Daten-Neuerfassung oder produktive Providerfreigabe.
Tests bleiben synthetisch mit abgefangenen externen Aufrufen; aktuelle
Head-/Integrationsstand- und reguläre Gatebelege stehen im zugehörigen PR.
Der Schnitt ist mit [#355](https://github.com/burckhju/trading-workspace/pull/355)
am grün geprüften unveränderten Head integriert: Main-Merge
`ae554532269b2ac215ea80e93373fe806b73050e`, Tree
`0badca1f6de01ee6cf24b0a041c377eb84d605d4`, identisch zum tatsächlichen
PR-Testmerge. Der anschließende schmale [Versionsschnitt v1.5.48](../releases/V1.5.48-B58-ACQUISITION.md)
bereitet den bestehenden kontrollierten PC-Updateweg vor. Seine eigenen PR-
und Main-Push-Gates sowie Tag/Commit werden separat nachgewiesen; der gemeldete
PC-Stand bleibt v1.5.47. **Nächste externe Abhängigkeit:** geeigneter erlaubter
ARIVA-Evaluationszugang zu `XSC / REALTIME` **und** belegte Lieferung eigener
Originalstatuszeit/-semantik, negativer/preisloser Ereignisse, Lücken/Recovery
und Nutzungsrecht. Ein konkreter unverbindlicher Anfrageentwurf ist vorbereitet,
aber nicht versendet. API-Zugang allein genügt nicht. `QUALIFIED_B58_PATHS=()`
und `HEBELTRADER_SCOPE=DISABLED` bleiben bestehen; B05, B06 und F207-5 behalten
ihre oben genannten Restarbeiten. Arbeitsstatus des Gesamtumfangs unverändert.

</details>

</details>



<a id="notification-delivery"></a>
<details>
<summary>unnummeriert — Benachrichtigungen und Zustellzustände</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Benachrichtigungen. Bereich/Querschnitt: 6. Bestehender Bezug: Notification Capability / austauschbarer Outbound-Adapter; FT noch offen. Lieferziel: A. |
| Arbeitsstatus | Released — dauerhafte Outbox/Retry/Zustellzustände; reale Zustellabnahme offen |
| Abgeschlossener Teilumfang | Deduplizierung, dauerhafte Versuche, Retry/Recovery/Pause/Suppression implementiert und synthetisch qualifiziert; nicht erneut bauen. |
| Soll / Nicht-Soll | **Soll:** Notification und DeliveryAttempts getrennt vom Alert führen; Fehler, Retry und erfolgreiche Zustellung sichtbar halten. **Nicht-Soll:** Keine echten Testnachrichten; Telegram ist kein Trading-Eingabekanal. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung und ggf. ausdrückliche fachliche Zustellentscheidung. |
| Implementierung / Consumer | AlertNotificationService persistiert getrennte Notification; DurableNotificationDeliveryService speichert Attempt vor Adapteraufruf, setzt beschränkte Retries/Recovery und Keyset-Paginierung um. Neue Review-/Deadline-Notifications prüfen Scope und aktuelle Ereignisgrundlage; Datenlücken pausieren, Vollverkauf unterdrückt alte Zustellungen. Workspace und TradeAlertsPanel zeigen autoritative Zustellzustände. Quellen: [notification/service/creation.py](../../backend/app/features/notification/service/creation.py), `durable_delivery.py`, [persistence/durable_delivery.py](../../backend/app/features/notification/persistence/durable_delivery.py); [position_monitoring/service/runtime.py](../../backend/app/features/position_monitoring/service/runtime.py), [product_deadline_review_delivery.py](../../backend/app/features/position_monitoring/service/product_deadline_review_delivery.py). |
| Test / Commit | [tests/integration/backend/test_position_monitoring_notification_e2e.py](../../tests/integration/backend/test_position_monitoring_notification_e2e.py); [tests/unit/backend/features/notification/test_durable_delivery.py](../../tests/unit/backend/features/notification/test_durable_delivery.py); [tests/unit/backend/features/notification/test_durable_delivery_pagination.py](../../tests/unit/backend/features/notification/test_durable_delivery_pagination.py); [tests/unit/backend/features/notification/test_product_deadline_delivery.py](../../tests/unit/backend/features/notification/test_product_deadline_delivery.py); [tests/integration/backend/database/test_position_review_notification_postgres.py](../../tests/integration/backend/database/test_position_review_notification_postgres.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Vorhandene Provider-/Zustellfreigaben behalten ihren Umfang; keine neue Versandfreigabe. Externe V2-Reviewzustellung laut PR [#367](https://github.com/burckhju/trading-workspace/pull/367) ausgeschaltet. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | V2-Zustellung in beobachteter Installation deaktiviert; kein tatsächlicher externer Nachrichtenerfolg daraus. Alte zulässige Telegram-Konfiguration unverändert übernommen. |
| Restarbeit / nächste Abhängigkeit | Kein aktueller realer Zustellnachweis im beauftragten Scope → Benutzer versteht zugestellt/fehlgeschlagen/pausiert → bestehender Notification-/Delivery-Owner → lesende vorhandene Attemptbelege und geklärter gewünschter Scope → Zustände mit Alert/Episode/Attempt und Zeitpunkt konsistent nachgewiesen; Versandtest nur als gesondert beauftragte Folgearbeit. |
| Umfangsentscheidung | Vorhandene Capability, Nummerierungsentscheidung weiterhin separat offen; keine neue Plattform oder neuer Kanal. |

</details>

<a id="reminders"></a>
<details>
<summary>unnummeriert — Erinnerungen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Erinnerungen. Bereich/Querschnitt: 6. Bestehender Bezug: konkrete Erinnerungen im bestehenden Monitoring; weiterer ursprünglicher M10-Erinnerungsumfang fachlich zu klären. Lieferziel: A. |
| Arbeitsstatus | Business Review (fachliche Abnahme konkreter 20-Sitzungen-/Produkttermin-Erinnerungen); Implementierung und Auslieferung abgeschlossen. Analysis (weitergehender ursprünglicher M10-Umfang). |
| Abgeschlossener Teilumfang | Begrenzter Erinnerungsowner/-vertrag und Consumer sind technisch nachgewiesen und ausgeliefert. Seit v1.5.52 liefert der bestehende Product-Owner getrennte Datumsrollen an die Produktfrist-Eingangsstrecke; der Zahlungstag ersetzt weder Produktende noch letzten Handelstag. |
| Soll / Nicht-Soll | **Soll:** Erinnerungsanlass, Fälligkeit, Benutzeraktion und Herkunft sind ausdrücklich definiert. **Nicht-Soll:** Ein Alert, Schedulerjob oder Workspace-Hinweis ist nicht automatisch ein vollständiger Reminder-Contract. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Datenversorgung/Prüfung; Entscheidung über weiteren ursprünglichen Umfang. |
| Implementierung / Consumer | REVIEW_DUE nach 20 belegten Sitzungen und PRODUCT_DEADLINE_REVIEW besitzen konkrete Anlass-/Fälligkeits-/Episode-/Quellenverträge. Produktterminrechnung ist kursunabhängig, nimmt früheres Produktdatum und dokumentierte vorherige Sitzungen/Tage; DAY-only erzeugt keine erfundenen Öffnungs-/Schlusszeiten. Einmalig später erkannte Stufen erfinden keine frühere Zustellung. Quellen: [domain/indicative_entry.py](../../backend/app/features/position_monitoring/domain/indicative_entry.py), `product_deadline_review.py`, [product_deadline_days.py](../../backend/app/features/position_monitoring/domain/product_deadline_days.py); [service/product_deadline_review.py](../../backend/app/features/position_monitoring/service/product_deadline_review.py); frontend TradeAlertsPanel. Seit v1.5.52 liefert der bestehende Product-Owner getrennte Datumsrollen; ProductDeadlineInputs übernimmt sie in das gespeicherte product_evidence. maturity_on bleibt Produktende. Die Monitoringrouter und der Entry-DTO wurden dafür nicht erweitert; Original-/Parserbelege werden zusätzlich beim Product-Owner gelesen. |
| Test / Commit | [tests/unit/backend/features/position_monitoring/test_product_deadline_review.py](../../tests/unit/backend/features/position_monitoring/test_product_deadline_review.py); [tests/integration/backend/database/test_product_deadline_review_postgres.py](../../tests/integration/backend/database/test_product_deadline_review_postgres.py); [tests/integration/backend/database/test_indicative_entry_postgres.py](../../tests/integration/backend/database/test_indicative_entry_postgres.py); [frontend/src/features/alert/components/TradeAlertsPanel.test.tsx](../../frontend/src/features/alert/components/TradeAlertsPanel.test.tsx) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | V2-Produkttermine ausdrücklich beauftragt; nicht vollständiges B05/B20 und keine Entscheidung, dass sämtliche ursprünglichen Erinnerungsansprüche entfallen. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Produktterminpfad im echten V2-Lauf ausgewertet, aber 6/6 Datenprobleme. Sechs neue Hinweise sind Datenwarnungen, keine sechs belegten Fristauslöser. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. |
| Restarbeit / nächste Abhängigkeit | Reale Fristbeurteilung nach dem ausgelieferten Datumsfix sowie übrige Terminfakten sind unbelegt → nachvollziehbare fällige Produkttermine → vorhandener Product-/Calendar-/Monitoring-/Notification-Pfad → bestätigter installierter Stand mit Fix, regulärer Zyklus, persönliche Exitwahl, Original des letzten Handelstags und benötigte Kalenderreichweite → je Referenzposition belegtes Produktende getrennt vom Zahlungstag, zulässiger Erinnerungstag und passende Episode oder konkret begründete Sperre. Allgemeine zusätzliche M10-Erinnerungsanlässe fachlich konkretisieren; keine erneute Qualifikation/Integration/Veröffentlichung von [#368](https://github.com/burckhju/trading-workspace/pull/368) einplanen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="model-monitoring"></a>
<details>
<summary>unnummeriert — Modellüberwachung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Modellüberwachung. Bereich/Querschnitt: 6; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 und jeweilige fachliche Modellconsumer; keine neue Capability-ID. Lieferziel: A, D. |
| Arbeitsstatus | Business Review (konkrete Candidate-Version/Readiness technisch abgeschlossen und ausgeliefert); Analysis (vollständige Modellüberwachung). |
| Abgeschlossener Teilumfang | Versions-/Kompatibilitäts-/Readiness-Transparenz der vorhandenen Kandidatenfamilie nicht erneut implementieren. |
| Soll / Nicht-Soll | **Soll:** Aktive/angewendete Version, Kompatibilität und Datenbereitschaft bleiben überprüfbar. **Nicht-Soll:** Runtime-Auflösung ist nicht automatisch Modellgüte-/Driftüberwachung oder automatische Modelländerung. |
| Befundklasse / Lückenart | Vorhandene, gegenüber dem ursprünglichen Gesamtanspruch unvollständige Funktion; benannter Teilumfang abgeschlossen. **Art der Restarbeit:** Fachliche Entscheidung, danach abgegrenzte Implementierung/Prüfung. |
| Implementierung / Consumer | RuntimeActivationService und CandidateRuntimeReadiness verbinden aktive Version, Familien-/Consumerkompatibilität und Datenbereitschaft; keine allgemeine Modellgüte-/Driftüberwachung dadurch. Quellen: [model/service/runtime_activation_service.py](../../backend/app/features/model/service/runtime_activation_service.py); [candidate/service/runtime_readiness.py](../../backend/app/features/candidate/service/runtime_readiness.py); [frontend/src/features/model/components/RuntimeActivationPanel.tsx](../../frontend/src/features/model/components/RuntimeActivationPanel.tsx). |
| Test / Commit | [tests/e2e/candidate-governance-journey-postgres.spec.ts](../../tests/e2e/candidate-governance-journey-postgres.spec.ts); [frontend/src/features/model/components/RuntimeActivationPanel.test.tsx](../../frontend/src/features/model/components/RuntimeActivationPanel.test.tsx) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Konkrete Kandidatenfamilie und getrennte Aktivierung dokumentiert; allgemeine Monitoringmetriken/Schwellen nicht entschieden. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Installation des damaligen v1.5.51-Codes durch PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; Nutzung und fachliche Abnahme genau dieses Teilpfads nicht separat nachgewiesen. |
| Restarbeit / nächste Abhängigkeit | Unbestimmter M10-Überwachungsumfang jenseits Candidate-Readiness → Benutzer erkennt definierte Modellprobleme → FT-013 und vorhandener fachlicher Modellconsumer → Anlässe/Metriken/Referenzdaten/Schwellen ausdrücklich beschließen → jede beschlossene Überwachungsregel mit genauer Modellversion, positivem/negativem Referenzfall und nachvollziehbarer Reaktion geprüft; keine autonome Modelländerung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operational-workspace"></a>
<details>
<summary>unnummeriert — Täglicher Operational Workspace</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Spätere Querschnittsfähigkeit zu M2–M10. Bereich/Querschnitt: Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: Operational Workspace; nur lesend. Lieferziel: A. |
| Arbeitsstatus | Fachstruktur A technisch qualifiziert und mit [PR #372](https://github.com/burckhju/trading-workspace/pull/372) am 21.11.2026 integriert; Business Review (menschliche Abnahme der täglichen Nutzerreise); lesende Arbeitsbereich-/Währungs-/V2-Consumer technisch abgeschlossen und ausgeliefert; historische begrenzte Freigaben erhalten. |
| Abgeschlossener Teilumfang | Integrierte Währungsqualifikation und V2-Reader/Anzeige released; historische v1.5.30-Bereitstellung nicht als nächster Auftrag führen. Die ausgewählte Fachstruktur A mit fünf Hauptgruppen, konsolidierten Depotdetails und erhaltener Rückkehrnavigation ist auf Main `febeb922c0f337029baa7f9d792c37f9f72ba02b` integriert. |
| Soll / Nicht-Soll | **Soll:** Nächste Aufgaben, Datenbereitschaft, offene Positionen, Monitoring und Zustellung aus autoritativen Quellen verständlich zusammenführen. **Nicht-Soll:** Keine eigenen Done-/Acknowledge-/Assignment-Zustände und keine konkurrierende fachliche Schreibwahrheit. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Fachliche Nutzerabnahme und reale Datenabdeckung. |
| Implementierung / Consumer | OperationalWorkspaceReadModel bildet Ownerzustände auf Aktionen ab; PositionSnapshotService verbindet Position/Bewertung; kein eigener Done-Owner. Fachstruktur A trennt Aktuelles, Depot, Marktanalyse, Lessons Learned und Basisdaten; kanonische Trade-/Run-/Lernbereiche erhalten ihre bisherigen Owner. Die vollständige Zuordnung steht im [UX-Masterplan](../coordination/UX_MASTER_PLAN.md#gewählte-fachstruktur-a--21112026). PositionMonitoring lädt IndicativeEntryObservation; TradeAlertsPanel zeigt Produkt-/Einstands-/Datenhinweise und Quellen. Währungsqualifikation bleibt Backend-basiert. ACHTUNG: /operational-workspace/positions ist fachlich lesend, ruft aber valuation_reader/QuoteResolver auf; nicht als garantiert refreshfreie Diagnose verwenden. |
| Test / Commit | [tests/unit/backend/features/operational_workspace/test_read_model.py](../../tests/unit/backend/features/operational_workspace/test_read_model.py); [tests/unit/backend/features/operational_workspace/test_position_snapshot.py](../../tests/unit/backend/features/operational_workspace/test_position_snapshot.py); [frontend/src/features/trade/pages/TradeManagementMonitoring.test.tsx](../../frontend/src/features/trade/pages/TradeManagementMonitoring.test.tsx); [frontend/src/features/operational_workspace/components/IndicativeEntryObservation.test.tsx](../../frontend/src/features/operational_workspace/components/IndicativeEntryObservation.test.tsx); [tests/e2e/purchase-workspace-handoff.spec.ts](../../tests/e2e/purchase-workspace-handoff.spec.ts) Historische Auslieferung: [Main-CI im Nachweisregister](#nachweisregister). Fachstruktur A: vollständige grüne PR-CI in [#372](https://github.com/burckhju/trading-workspace/pull/372), anschließend [2.838 Frontend-Tests auf Main](https://github.com/burckhju/trading-workspace/actions/runs/44943371791) und [213 Browserfälle in Smoke-/Owner-Umgebungen](https://github.com/burckhju/trading-workspace/actions/runs/44943371718); Zuordnung und Grenzen im [Integrationsprotokoll](../coordination/UX_INTEGRATION_STATUS.md#fachstruktur-a-20261121). Die neuen v1.5.54-Releasegates werden separat im Release-PR gebunden. |
| Fachliche Abnahme | UX-Hinweisvertrag und begrenzte Währungsschnitte historisch freigegeben; kein vollständiger menschlicher UX-/Tagesablaufnachweis. |
| Software-Auslieferung | Historischer Währungs-/V2-Umfang im veröffentlichten Tag v1.5.52 enthalten. Die in Main integrierte Fachstruktur A wird mit dem beauftragten [PC-Lieferumfang v1.5.54](../releases/V1.5.54-UI-FACHSTRUKTUR-PC-DELIVERY.md) über den vorhandenen Launcher bereitgestellt; Veröffentlichung erst nach grünen PR- und Main-Prüfungen, endgültiger Tag-Commit im Release-PR. Keine dadurch erteilte Gesamtfachabnahme oder nachgewiesene PC-Installation. |
| Betriebsnachweis | Installation des damaligen v1.5.51-Codes durch PR [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; Nutzung und fachliche Abnahme genau dieses Teilpfads nicht separat nachgewiesen. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. |
| Restarbeit / nächste Abhängigkeit | Vollständige Lesbarkeit täglicher Aufgaben mit echten begrenzten Datenzuständen unbelegt → Benutzer erkennt Priorität, Ursache und zulässigen Folgeschritt → bestehender Workspace/Positions-/Alertconsumer → datierte identifizierte Installation und aktuelle Ownerbelege → repräsentative Handlungs-/Leer-/Fehler-/Datenwarnungsfälle mit Quellenrückkehr fachlich abgenommen, ohne neue Zustandswahrheit. |
| Umfangsentscheidung | Nutzerwahl A am 21.11.2026 autorisiert die dokumentierte UI-Konsolidierung nach Auswahl aus drei Varianten; anschließende ausdrückliche Freigabe des grünen Merges und Auftrag zur PC-Bereitstellung am 22.11.2026. Bestehender fachlicher Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Abgegrenzter UX3-K-Vertragsnachtrag, 01.11.2026:** Der
[kanonische Hinweisvertrag](../ui/ux-3/README.md) führt die Bestandsinventuren und
fachlichen Ergänzungen aus #314/#315 gemäß der integrierten UX-Koordination zusammen.
[Inventur](../ui/ux-3/inventory.md), [Detailnachweise](../ui/ux-3/detail-inventory.md)
und [Abnahmefälle](../ui/ux-3/test-and-acceptance.md) erhalten die bestehenden
Domainowner, Quellen-, Schreib-, Readback- und Recoverygrenzen. Die
[getrennten Folgeaufträge](../ui/ux-3/integration-and-rollout.md) beginnen später
mit genau einem lesenden Pilot. Der Nutzerauftrag erlaubt Merge bei grünen
erforderlichen Prüfungen und PC-Bereitstellung des konsolidierten Vertrags;
dieser Nachtrag ändert weder den fachlichen Arbeits-/Abnahmestatus noch eine
Produktoberfläche, Finanzberechnung, Handelsregel oder Planfreigabe.

</details>

</details>

<a id="operations-optimization"></a>
<details>
<summary>unnummeriert — Performanceoptimierung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Performanceoptimierung. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Released — einzelne Scheduler-/Build-Verbesserungen; Analysis — messbarer Gesamtleistungsumfang |
| Abgeschlossener Teilumfang | Vorhandene Pacing-/Lane-/Build-Reparaturen abgeschlossen; Performanceoptimierung nicht pauschal ohne Implementierung. |
| Soll / Nicht-Soll | **Soll:** Technische Leistung mit explizitem Szenario und messbarem Ausgangswert verbessern. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung und fachlich/betriebliche Zielentscheidung. |
| Implementierung / Consumer | Public-Pacing statt zusätzlicher Snapshotpause, Lane-/Discovery-Konkurrenzkorrektur und wiederverwendbare Paketschicht in Backend-Dockerfile vorhanden. audit_monitoring_performance liefert Zyklus-/Preisrequest-/Refreshzeiten; keine allgemeine Last-/Ladezeitqualifikation. |
| Test / Commit | [tests/unit/backend/features/market_data/test_refresh_source_modes.py](../../tests/unit/backend/features/market_data/test_refresh_source_modes.py); [tests/unit/backend/features/market_data/test_refresh_lanes.py](../../tests/unit/backend/features/market_data/test_refresh_lanes.py); [tests/unit/backend/tools/test_audit_monitoring_performance.py](../../tests/unit/backend/tools/test_audit_monitoring_performance.py); [tests/unit/backend/test_backend_dependency_install.py](../../tests/unit/backend/test_backend_dependency_install.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Begrenzte Pacing-/Recovery-Aufträge entschieden; allgemeine Zielwerte/Lastprofile nicht festgelegt. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | Ein V2-Zyklus von 35,307 s am 19.11.2026 belegt, ohne vorher/nachher Benchmark und ohne allgemeines Leistungs-SLA. |
| Restarbeit / nächste Abhängigkeit | Kein definierter allgemeiner Engpass-/Last-/Zielnachweis → Benutzer erhält messbar ausreichende Reaktions-/Aktualisierungszeit → bestehende Laufzeit-/Frontend-/CI-Owner → repräsentative Last und Ausgangswert festlegen → wiederholbarer Vorher/Nachher-Beleg samt Zielwert und unveränderten Qualitätsgates; Abfragebündelung/Bundleaufteilung nur bei nachgewiesenem Engpass. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Begrenzung zum Währungsfix vom 28.10.2026:** Abfragebündelung der
Positions-/Quote-Leser und eine mögliche Bundleaufteilung bleiben begründete
Folgearbeiten, weil sie keine Voraussetzung für die fachliche Währungsqualifikation
sind und einen eigenen Last-/Ladezeitnachweis benötigen. Neue Performancefunktionen
und zusätzliche Modellfamilien verbleiben in ihren vorhandenen PB-019-/PB-020-
Einträgen; ihre Fachverträge werden nicht durch diesen Integritätsfix erweitert.

</details>

</details>

<a id="operations-stability"></a>
<details>
<summary>unnummeriert — Stabilität und sichere Betriebsgrenzen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Stabilität. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Observed — kontrollierter Ersatzrelease/gesunde Installation; Released — technische Recovery/Sandbox; Gesamtbetrieb offen |
| Abgeschlossener Teilumfang | Beobachteten Prepare-Abbruch/SQLAlchemy-Buildblocker durch qualifizierten Ersatzrelease und erfolgreichen PC-Übergang geschlossen. Ursprüngliche Indexantwortursache bleibt unbewiesen. |
| Soll / Nicht-Soll | **Soll:** Wiederholbarkeit, Erhalt privater Konfiguration/Daten und nachvollziehbare Fehlerzustände. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Befundklasse / Lückenart | Vorhandene Fähigkeit mit ausdrücklich begrenztem Abschluss und noch fehlender fachlicher/Betriebs-/Umfangsprüfung. **Art der Restarbeit:** Prüfung des weiteren Betriebs-/Wiederherstellungsumfangs. |
| Implementierung / Consumer | Gebundener Python-OCI-Index/SQLAlchemy-Wheel, begrenzte Installerwiederholung, Retry/Replace mit Prüfung von Tag/SHA/Abstammung/Deploymentverträgen, bewahrte Altbelege und unveränderter Launcher. Nichtroot-/Sandbox-/Migration-/Readiness-Gates bleiben. Quellen: backend/Dockerfile, [install_dependencies.py](../../backend/install_dependencies.py); [scripts/retry-linux-update.py](../../scripts/retry-linux-update.py), [trading-workspace.sh](../../scripts/trading-workspace.sh); [.github/workflows/backend.yml](../../.github/workflows/backend.yml). |
| Test / Commit | [tests/unit/backend/test_backend_dependency_install.py](../../tests/unit/backend/test_backend_dependency_install.py); [tests/unit/backend/test_linux_update_recovery.py](../../tests/unit/backend/test_linux_update_recovery.py); [tests/unit/backend/test_linux_launcher.py](../../tests/unit/backend/test_linux_launcher.py); [.github/workflows/backend.yml](../../.github/workflows/backend.yml) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Konkreter Build-/Ersatzauftrag in [#367](https://github.com/burckhju/trading-workspace/pull/367) belegt; keine neu erteilte allgemeine Betriebsfreigabe. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367), Nutzerbeleg 19.11.2026: v1.5.51/254f0bbd… installiert, vier Dienste healthy, Readiness 200/ready, Schema 20261118_0060. Audit 18:13:12 MEZ: V2-Zyklus 18:06:42–18:07:17 MEZ, 35,307 s, running=true, last_error=null; Review und Deadline je 6 bewertet/6 Datenprobleme/0 technische Positionsfehler. Kein eigener PC-Zugriff dieser Prüfung. |
| Restarbeit / nächste Abhängigkeit | Kein umfassender längerer Betriebs-/Restore-Nachweis → Benutzer kann private Konfiguration, Daten und Belege zuverlässig erhalten/wiederherstellen → bestehender Launcher/Recovery/Backup-Owner → identifizierte Sicherung und isoliert beauftragte Restoreumgebung → Restore mit Daten-/Consent-/Belegerhalt und datierten Health-/Schema-/Versionsbelegen qualifiziert; reale Depot-Datenprobleme bleiben separater Datenrest. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-regression"></a>
<details>
<summary>unnummeriert — Regressionstests</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Regressionstests. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Released — etablierte Regressionsgates auf geprüftem Main erfüllt |
| Abgeschlossener Teilumfang | Reguläre Main-Gates auf c7db441… / v1.5.52 einschließlich neuer Original-/Datums-/Kalender-/PostgreSQL-Fälle erfolgreich; frühere Produkt- und Docs-CI behalten ihre historischen Commit-/Testmergebindungen. |
| Soll / Nicht-Soll | **Soll:** Etablierte Backend-, Frontend-, PostgreSQL- und Browser-Gates bleiben unverändert. **Nicht-Soll:** Keine Mutation realer Betriebsdaten durch Tests, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Befundklasse / Lückenart | Belegbar abgeschlossener enger Teilumfang; kein pauschaler Meilensteinabschluss. **Art der Restarbeit:** Laufende Änderungspflege, kein nachweisbarer fehlender Regressionsaufbau. |
| Implementierung / Consumer | Backend-/Frontend-/PostgreSQL-/vier E2E-Jobs, Produktionsimage, Sandbox und echte Docker-PostgreSQL-Recovery sind reguläre Gates. Sources [.github/workflows/backend.yml](../../.github/workflows/backend.yml), [frontend.yml](../../.github/workflows/frontend.yml), [e2e.yml](../../.github/workflows/e2e.yml) und `scripts/check-*.sh` / [run-e2e.sh](../../scripts/run-e2e.sh); kein alter TC-001-Integrationsschritt mehr offen. Der neue frühe Backend-Schritt für gespeicherte Originale, Datumssemantik und Kalender umfasst 88 Fälle inklusive echter PostgreSQL-Upgrades; sie sind Teilmengen der vollständigen Suite. |
| Test / Commit | [.github/workflows/backend.yml](../../.github/workflows/backend.yml); [.github/workflows/frontend.yml](../../.github/workflows/frontend.yml); [.github/workflows/e2e.yml](../../.github/workflows/e2e.yml); .github/tests/version-tag.test.cjs Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Technische qualifizierte Auslieferung, keine fachliche Abnahme des gesamten M0–M11-Zielbilds. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | CI-Wegwerfqualifikation ist echter technischer Nachweis; keine dadurch erzeugte Liveprovider- oder menschliche Abnahme. |
| Restarbeit / nächste Abhängigkeit | Kein offener Regressionsnachweis für den geprüften Produkt-Main c7db441…; dieser Teilumfang und die bisherige #368-Qualifikationsabhängigkeit sind abgeschlossen. Neue Änderungen → weiterhin verlässlich geschützte Integration → bestehende CI-/Ownerjobs → tatsächlicher neuer Head und Testmerge → eigene reguläre Gates genau auf diesem Stand. Die frühere grüne #369-CI auf 84451218…/483e468… gilt nicht für den fortgeschriebenen Dokumentations-Head. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-release"></a>
<details>
<summary>unnummeriert — Releasevorbereitung und Softwarestand</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Releasevorbereitung. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Released — v1.5.52 am geprüften Main; kein Gesamt-M11-Abschluss. |
| Abgeschlossener Teilumfang | Versionsschnitt, geschützte Integration und automatische Veröffentlichung v1.5.52 abgeschlossen: [#368](https://github.com/burckhju/trading-workspace/pull/368) gemergt am 19.11.2026, 20:16:54 Uhr MEZ; Publisherlog 20:45:01 Uhr MEZ. Die frühere offene Lieferaufgabe dieses Fixes ist erledigt; v1.5.51 und ältere Lieferstände bleiben historisch. |
| Soll / Nicht-Soll | **Soll:** Versionierte Software und nachvollziehbare Release-/CI-Bindung. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Befundklasse / Lückenart | Belegbar abgeschlossener enger Teilumfang; kein pauschaler Meilensteinabschluss. **Art der Restarbeit:** Kein offener Lieferrest des v1.5.52-Schnitts; private Betriebswirkung und spätere Änderungen benötigen eigene Nachweise. |
| Implementierung / Consumer | Fünf Versionswerte synchron 1.5.52; bestehender Publisher bindet den Tag an abgeschlossene reguläre Main-Push-Gates. [.github/workflows/version-tag.yml](../../.github/workflows/version-tag.yml), [VERSION](../../VERSION) und Backend-/Frontendmanifeste; Tag v1.5.52 auf c7db441… im [Nachweisregister](#nachweisregister) erneut geprüft. Der ältere GitHub-Latest-Release-Datensatz bleibt vom Softwaretag getrennt. |
| Test / Commit | .github/tests/version-tag.test.cjs; [.github/workflows/version-tag.yml](../../.github/workflows/version-tag.yml) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Begrenzter Datums-/Originalupgrade-/Kalenderimportumfang und konkrete Lieferfreigabe aus [#368](https://github.com/burckhju/trading-workspace/pull/368) sind belegt; keine neue fachliche Gesamt- oder PC-Betriebsabnahme aus Tag/CI ableiten. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367), Nutzerbeleg 19.11.2026: v1.5.51/254f0bbd… installiert, vier Dienste healthy, Readiness 200/ready, Schema 20261118_0060. Audit 18:13:12 MEZ: V2-Zyklus 18:06:42–18:07:17 MEZ, 35,307 s, running=true, last_error=null; Review und Deadline je 6 bewertet/6 Datenprobleme/0 technische Positionsfehler. Kein eigener PC-Zugriff dieser Prüfung. |
| Restarbeit / nächste Abhängigkeit | Kein offener Integrations- oder Lieferrest für v1.5.52/[#368](https://github.com/burckhju/trading-workspace/pull/368); die Tagveröffentlichung ist abgeschlossen. Separat fehlt die reale Wirkung → nachvollziehbare private Teilabdeckung → bestehender Launcher-/Product-/Monitoringowner → bestätigter PC-Commit und normaler V2-Zyklus → datierter Wirkungsnachweis gemäß [Betriebsabnahme](#operations-installation). Dies ist keine erneute Veröffentlichung desselben Fixes und kein neuer Produktrelease durch den Dokumentationsdiff. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

<details>
<summary>Historische Nachträge – damaliger Umfang, keine aktuelle Handlungsanweisung</summary>

Die nachstehenden Vorbereitungs-, Prüf- und Lieferangaben bleiben als datierte Belege erhalten. Aktuell gelten ausschließlich die Felder oben; zwischenzeitlich erledigte Aufgaben werden nicht erneut beauftragt.

**Liefernachtrag 28.10.2026 — laufende Positionsbewertung:** Die obigen 1.5.5-Angaben
sind historische Basisnachweise. Die neue ausdrückliche Freigabe
**„wenn grün mergen und für den PC bereitstellen“** betrifft den Währungsfix
in [PR #297](https://github.com/burckhju/trading-workspace/pull/297), integriert
als `1f6ca802df25b2d508338ac837fdfb39ac79eca2`. Der unmittelbar vorherige
veröffentlichte Tag `v1.5.29` wurde auf `dc89dfa65758dfc1258a8fab657257f6598b0179`
zurückgelesen. [v1.5.30](../releases/V1.5.30-POSITION-PNL-CURRENCY.md) wird mit
fünf gemeinsam fortgeschriebenen Versionswerten vorbereitet. Bei Anlage dieses
Nachtrags noch kein Veröffentlichungsbeleg für v1.5.30; der zugehörige Release-PR
bindet die neuen PR-/Main-Prüfungen, den Publisher und den tatsächlichen Tag-SHA.
Der bestehende Publisher und gepinnte PC-Updateweg bleiben unverändert.
Reale PC-Installation und menschliche Fachabnahme sind davon getrennt.


**Liefernachtrag 17.11.2026 — Hebeltrader-Teilumfang:** Die ausdrückliche Freigabe
umfasst die Integration der grün geprüften Draftkette und die versionierte
Bereitstellung für den bestehenden kontrollierten PC-Updateweg. #348 bis #353
sind geordnet auf Main `02eb6e1ca87dd8470ff8f17bf59dbfa6f98fc715` integriert.
Der gemeinsame Release-PR bereitet [v1.5.47](../releases/V1.5.47-HEBELTRADER-LOSS-PATH.md)
vor und synchronisiert alle fünf Versionswerte. PR-, Main-, Publisher- und
Tagbelege werden am tatsächlichen Quellstand geführt. Die Softwarebereitstellung
bleibt von der offenen B58-Quellenqualifikation, einer zentralen Regelaktivierung
und dem tatsächlichen Betrieb auf JMBbot getrennt. Bei Anlage dieses Nachtrags
ist noch kein Veröffentlichungs- oder PC-Installationsbeleg behauptet.

</details>

</details>

<a id="operations-installation"></a>
<details>
<summary>unnummeriert — Betriebsnachweis der identifizierten Zielinstallation</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Betrieb; Ziel A. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: bestehende Betriebs-/Releaseverantwortung. Lieferziel: A. |
| Arbeitsstatus | Observed — tatsächliches v1.5.54, Schema, gesunde Dienste und enger P02-Verbraucherread am 24.11.; letzte Gesamtinventur/Zyklusdiagnose am 22.11. auf v1.5.52; Business Review — weitere Regelabdeckung und vollständige Originalupgrade-/Importabnahme. |
| Abgeschlossener Teilumfang | Vollständiger privater Readback vom 22.11.2026: c7db441…/v1.5.52, Schema0060, vier gesunde Dienste, 30/30 GETs und vollständiges Vierer-Inventar. V2-Ausführung mit 4/4 Datenproblemen in beiden Prüfpfaden belegt. Die frühere fehlende PC-Installationsbestätigung ist geschlossen. Am 24.11. ist v1.5.54/9a5e59d… separat verifiziert; der enge P02-Collector liefert historischen Gap und aktuellen gespeicherten V2-Entscheid mit Bid. Kein erneuter P02-Export erforderlich. |
| Soll / Nicht-Soll | **Soll:** JMBbot mit tatsächlich installierter Version/Commit, Schema, Compose-Provenienz, Daten-/Monitoring-/Zustellzuständen und Nachweiszeitpunkt identifizieren. **Nicht-Soll:** Keine Diagnoseanleitung als erfolgreichen Lauf ausgeben; kein Monitoring-Einmallauf, Deployment oder Nachricht. |
| Befundklasse / Lückenart | Installation und datierte Verbraucherbefunde beobachtet; P02-Journalergänzung abgeschlossen. **Art der Restarbeit:** weitere Datenversorgung und gezielte Quellen-/Produktbindung, keine Wiederholung des pauschalen Betriebsnachweises. |
| Implementierung / Consumer | Bestehender Launcher und [activate-indicative-monitoring.py](../../scripts/activate-indicative-monitoring.py) (prepare/apply) liefern zentralen kontrollierten Übergang. Passiver Runtime-Status und die beiden READ ONLY-Statusreader sind vorhanden; Diagnoseanleitung ist kein eigener Lauf. |
| Test / Commit | [tests/unit/backend/test_linux_update_recovery.py](../../tests/unit/backend/test_linux_update_recovery.py); [tests/unit/backend/test_indicative_monitoring_activation.py](../../tests/unit/backend/test_indicative_monitoring_activation.py); [tests/unit/backend/features/position_monitoring/test_indicative_entry_read_migration.py](../../tests/unit/backend/features/position_monitoring/test_indicative_entry_read_migration.py); [tests/integration/backend/database/test_product_deadline_review_postgres.py](../../tests/integration/backend/database/test_product_deadline_review_postgres.py) Aktuelle Ausführung/Commitbindung: [Main-CI im Nachweisregister](#nachweisregister); kein neuer lokaler Anwendungstest. |
| Fachliche Abnahme | Historisch freigegebener PC-Übergang ist laut Nutzerbeleg ausgeführt. Fachliche Depotabdeckung nicht abgenommen. |
| Software-Auslieferung | Im geprüften Main und veröffentlichten Tag v1.5.52 enthalten; konkrete Softwareauslieferung, keine dadurch erteilte Gesamtfachabnahme. |
| Betriebsnachweis | PR [#367](https://github.com/burckhju/trading-workspace/pull/367), Nutzerbeleg 19.11.2026: v1.5.51/254f0bbd… installiert, vier Dienste healthy, Readiness 200/ready, Schema 20261118_0060. Audit 18:13:12 MEZ: V2-Zyklus 18:06:42–18:07:17 MEZ, 35,307 s, running=true, last_error=null; Review und Deadline je 6 bewertet/6 Datenprobleme/0 technische Positionsfehler. Kein eigener PC-Zugriff dieser Prüfung. Historische Ursache-/Liefernachweise aus [#368](https://github.com/burckhju/trading-workspace/pull/368) bleiben erhalten. Neuer [PC-Readback vom 22.11.2026](../reviews/DEPOT_DATA_READBACK_2026-11-22.md): v1.5.52/c7db441…, Schema0060, vier offene Positionen, regulärer V2-Zyklus mit 4/4 Einstands- und 4/4 Fristdatenproblemen bei jeweils null technischen Positionsfehlern. Getrennte Produktende-/Zahlungsrollen beobachtet; exakter Parserhead/Originalupgrade und konkreter Kalenderimport dadurch nicht vollständig nachgewiesen. Frühere Sechser-/Viererbefunde werden nicht über Kennungen hinweg gleichgesetzt. Späterer [P02-Read vom 24.11.2026](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md): tatsächliches v1.5.54/9a5e59d…, Schema0060 und vier gesunde Dienste; historischer Timeout konkret, jüngeres `BELOW_ENTRY` mit Bid um 18:21:41 Uhr MEZ. Kein neuer Gesamtzyklus-/Inventar-/Fristnachweis. |
| Restarbeit / nächste Abhängigkeit | Gesamt-, P02- und Quellenkandidatenread sind ausgeführt und ausgewertet. **Einzige nächste Abhängigkeit:** [P01 für V2 versorgen](#naechster-schnitt). Ein historischer gettex-EUR/MUND-Bid ist isoliert belegt; konkrete Listing-/Mapping-/Importvorschau und frischer tatsächlicher PC-Verbraucherpreis fehlen. Kein erneuter unveränderter Diagnoseexport. P01-KID-Prüfung abgeschlossen: Einheit fehlt im Original, kein Parserfix. Product-/V2-Anschluss implementiert; alle vier Regeloriginale am 25.11. tatsächlich qualifiziert und fest hinterlegt. Lieferung und P01-Verbraucherabnahme bleiben offen; bestehende gettex-Konfiguration erhalten. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>





<a id="naechster-schnitt"></a>
## Einziger nächster Arbeitsauftrag — P01 für V2 versorgen

**Ziel und erwartete Verbesserung:** Die weiterhin offene, archivgebundene
P01 über den vorhandenen gettex-Pfad und eine belegte Preiseinheit bis zu
einem tatsächlich verwendbaren V2-Input führen. Ein passender positiver
EUR/MUND-Bid ist in einer offiziellen Datei bereits konkret nachgewiesen.
Das Ziel ist eine zusätzliche beurteilbare Position; eine aktuelle
Gesamtquote wird ohne passende Gesamtinventur nicht zugesichert.

**Abgeschlossener Fortschritt:** P01/P03/P04 sind aktuell gelesen und
zugeordnet. Fehlende Routen und Auswahlkandidaten sind belegt; KID-Beschaffung
ist erfolgreich. P01/P03 haben einen nutzbaren V2-Referenzkalenderpfad, aber
keine vom Verbraucher verwendbare Preiseinheit. P04 hat zusätzliche
Identitäts-/Kalenderlücken. Die isolierte gettex-Dateiprobe enthält P01,
P03/P04 nicht in diesem Fenster. Das freigegebene P01-KID ist bytegleich zum
PC-Original geprüft: Es enthält die Einheit tatsächlich nicht, deshalb kein
Parserfix. Das aktuelle gettex-Regelwerk liefert einen geeigneten ergänzenden
Belegweg für eine ausdrücklich listinggebundene aktuelle Einheit.
[Belege und exakte Grenzen](../reviews/DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md).
Keine erneute unveränderte Sammlung gehört zum nächsten Schritt.

**Betroffene Daten und Regeln:** P01-Produkt-/MUND-Listing-/EUR-Bindung,
validiertes Mapping und Quellenauswahl, positiver Bid mit unveränderter
Originalquellenzeit und Empfangszeit, dokumentierte aktuelle Preiseinheit,
vorhandene Ausführungs-/Restmengenbasis und Sitzungszählung. Verbraucher
ist `indicative-entry-review-v2`, Quellenmodus `DELAYED_SOURCE_BID`.
B04/B57/B58, Produktfristen und B06 bleiben getrennte Anforderungen.

**Vorhandene Komponenten und konkrete Arbeit in diesem einen Schnitt:**

1. **Originalpaket am 25.11. qualifiziert:** Das
   [implementierte aktuelle Listing-Einheitenpaket](../reviews/P01_LISTING_UNIT_IMPLEMENTATION_2026-11-24.md)
   ist mit den drei Nutzer-PDFs und dem BSW-Original vervollständigt.
   Originalbytes, Hashes, Fassungen und Fundstellen sind geprüft; die
   feste Regelpaketversion ist [hinterlegt](../reviews/GETTEX_LISTING_UNIT_ORIGINALS_2026-11-25.md).
   Der bestehende neue lokale
   Import prüft die vollständige gzip-Datei und gewinnt daraus den begrenzten
   Zielnachweis; ein frei behaupteter Hash ist ausgeschlossen. Migration0061
   verwendet eine eigene Product-Tabelle mit Listing-Revisionskette statt
   zusätzlicher KID-Dokumentart. Product-Reader und V2 übergeben getrennte
   KID-/Einheitenprovenienz und die tatsächliche `saved.route` bereits.
   Die [Lieferung v1.5.55 ist konkret vorbereitet](#p01-lieferung-20261125):
   vorhandener Launcher, fünf Versionswerte und eigene Release-Head-/Main-Gates.
   Quellenstand, Datenbankmigration und reguläre CI vor Lieferung qualifizieren;
   Parser v2, KID-Fakten, Frischegrenzen und historische Kontinuitätsannahme
   bleiben unverändert.
2. Beim vorhandenen Product-Owner das konkrete MUND-Listing lesen
   (`GET /api/v1/warrants/{warrant_id}/listings`). Ein fehlendes Listing nur
   mit passendem Produkt-/MIC-/Währungsbeleg über `WarrantService.add_listing`
   ergänzen. `configure_gettex_warrant` zunächst ohne `--apply` verwenden;
   es verlangt genau ein aktives Listing und legt selbst keines an.
   Die feste Workspace-/Produktbindung vor jeder Anwendung gegen das
   private P01-Archiv prüfen. Die produktive Zuordnung erst mit konkreter
   überprüfter Vorschau und erforderlicher Datenfreigabe durchführen.
3. Die bestätigte Route über bestehende Mappingadministration und
   `PositionQuoteSourceSelector` anbinden; regulären Refresh, gemeinsamen
   Dateicache, Backoff und gespeicherte Quoteweitergabe weiterverwenden.
   Die beobachtete Datei umfasst rund 657 MB. Der regelmäßige Abruf muss
   mit Bandbreite, Zeit- und Speichergrenzen des PCs vereinbar sein;
   keine eigene tägliche technische Handarbeit als Dauerlösung.
4. Nach regulärer Verarbeitung den gespeicherten P01-V2-Input und Entscheid
   lesen: gleiche Identität, positiver Bid, passende Einheit, Quellenalter
   und Sitzungen. Eine erreichbare Datei oder ein laufender Runner allein
   erfüllt die Abnahme nicht.

**Benötigter Zugang / konkrete Entscheidung:** Der P01-KID-Lesezugang ist
freigegeben und genutzt; alle vier Regeloriginale sind vorhanden und geprüft.
Das bezeichnet den ursprünglichen Nachweisstand. Im neuen Arbeitsraum ist
BSW wieder bytegleich vorhanden; die drei Börsen-Dateikopien, das private
P01-Referenzarchiv, die vollständige gettex-Datei und der tatsächliche
PC-/DB-Zugang fehlen weiterhin, wie im [Liefernachtrag](#p01-lieferung-20261125)
konkret abgegrenzt. Fehlende Kopien sind keine neue fachliche Quellenlücke.
Nach geprüfter Lieferung werden nur aktuelle P01-Produkt-/Listing-/KID-Bindungen
für die echte Vorschau sowie die vollständige lokale gettex-Datei benötigt.
Der [vorbereitete Ablauf](../reviews/GETTEX_LISTING_UNIT_ORIGINALS_2026-11-25.md#5-vorbereitete-p01-import--und-mappingvorschau)
verwendet vorhandene Owner und Commands; ohne echte Datenbankbindung wird
kein Previewfingerprint behauptet. Eine gegebenenfalls fehlende MUND/EUR-
Listinganlage und die konkrete Mapping-/Importanwendung sind überprüfbar
vorzubereiten. Bestehende gettex-Aktivierung und technische Privatnutzungs-
bestätigung sind datiert belegt; aktuelle Einstellungen, Downloadgrenzen,
Cache und Taktung erhalten und eng prüfen. Keine pauschale neue Providerfreigabe,
kein bezahlter Ersatzanbieter und kein unveränderter Gesamtdiagnoseexport
sind aus der jetzt geschlossenen Dokumentlücke abzuleiten.

**Überprüfbare Abnahmekriterien:**

- Product-Evidenz für P01 enthält eine aus den gebundenen Originalen belegte
  Einheit `CURRENCY_PER_WARRANT`, passende EUR-/Produkt-/Basiswert-/Terms-
  und Listingbindung sowie `AVAILABLE`. Ergänzende Einheitenrevision und
  KID-Revision sind getrennt nachvollziehbar und gemeinsam fingerprintgebunden.
  Die Qualität bleibt `CURRENT_UNIT_HISTORY_ASSUMED`; das KID bleibt bytegleich
  und weiterhin ohne extrahierte Einheit. Fremdlisting, Währungs-/Termswechsel,
  beschädigte Originale oder widersprüchliche Belege bleiben gesperrt.
- Genau eine passende aktive P01-MUND-Route ist belegt, validiert und ausgewählt.
  Vorhandene widersprüchliche oder mehrdeutige Listings werden nicht geraten
  beziehungsweise automatisch überschrieben.
- Der tatsächliche V2-Verbraucher erhält einen positiven Bid und
  `source_quote_at` mit **0 bis einschließlich 1800 s** Alter, nicht künftig;
  Empfang bleibt separat. Produktmaßstab und mindestens 20 abgeschlossene
  Basiswertsitzungen passen zum Quellenereignis im freigegebenen V2-Modus.
- Eine neue gespeicherte Bewertung ist fachlich auswertbar, oder jedes noch
  sperrende Pflichtfeld mit konkretem Quellen-/Zugangsgrund dokumentiert.
  Alte Probedaten, technische Transporterfolge oder pauschale Erfolgsflags
  ersetzen diesen Nachweis nicht. Die heutige historische Datei wird nicht
  als aktuelle Quote importiert.
- Automatischer Wiederanlauf und Ausfall-/Alterserkennung bleiben beim
  vorhandenen Owner; keine dauerhafte tägliche manuelle technische Pflege.
  B58-Original-BID-Zeit/Status, historische Strenge, Fristen und B06 werden
  durch diesen begrenzten V2-Schritt nicht als erfüllt ausgegeben.
- Öffentliche Belege enthalten nur erforderliche technische Zusammenfassungen;
  Depotwerte, Kennungen, individuelle Produkt-URLs und Originaldaten bleiben privat.

**Arbeitsstatus:** Observed — Quellenkandidatenread, konkrete historische
P01-gettex-Quellendeckung und abgeschlossene P01-KID-Ursachenprüfung;
Implemented — ergänzender aktueller Listing-Einheitenbeleg mit Product-Import,
passivem Reader, Migration0061 und V2-Routenanschluss; am 25.11. alle vier
echten Regeloriginale qualifiziert und fest hinterlegt. Verbleibend sind die
Veröffentlichung und PC-Installation der inzwischen konkret vorbereiteten
Lieferung v1.5.55, konkrete P01-Listing-/Mapping-/Importvorschau und tatsächliche
Verbraucherabnahme. Originalqualifikation allein erhöht keine Depotabdeckung.
Die reine Collectorfertigstellung ist abgeschlossen. Zuständige Owner bleiben
Product, Market Data und Position Monitoring; kein neuer Regelumfang wird freigegeben.

<details>
<summary>Abgeschlossener enger P02-Auftrag vom 22.–24.11.2026</summary>

<a id="p02-auftrag-20261122"></a>
### Historischer Auftrag — P02-Versorgungsunterbrechung auflösen

**Abschlussstand 24.11.:** Gebundener Journal-/Assessmentread liegt vor;
`JPMORGAN_SNAPSHOT_TIMEOUT` und der davon zu trennende ältere fehlende Bid
sind konkret dokumentiert. Ein jüngerer gespeicherter V2-Entscheid mit Bid
ist auf v1.5.54 beobachtet. Der Resolver-/Diagnosefix ist im offenen PR
implementiert und auf 41a0cf80… durch die vier regulären CI-Läufe qualifiziert,
aber nicht auf dem PC installiert. Die ursprüngliche Rohpreisleere und die
unterliegende Netzwerk-/Streamursache bleiben aus dem Paket nicht weiter
auflösbar; daraus folgt kein belegter zusätzlicher Adapterfix. Die folgende
Auftragsfassung bewahrt den damaligen Stand, keine erneute Exportaufforderung.

**Ziel und erwartete Verbesserung:** Die tatsächliche Ursache hinter
`REVIEW_BID_MISSING` und `REVIEW_PRICE_SUPPLY_INTERRUPTED` für die einzige
bestätigte Kursroute eindeutig feststellen und den spezifischen Fehler
bis zum Verbraucher erhalten. Damit verbessert sich mindestens die
Ursachenklärung für eine der vier Positionen. Eine V2-Abdeckung von 1/4
ist zusätzlich möglich, wenn ein tatsächlich passender neuer Bid ankommt;
sie wird nicht durch eine reine Codeänderung zugesichert.

**Betroffene Daten/Regeln:** die vorhandene bestätigte P02-/JPMorgan-Route,
aktuelle gespeicherte Quote, `latest_gap`/`latest_capture`, die ursprünglichen
`IndicativeEntryAssessmentModel.inputs.status_observations`, spezifischer
Abruffehler, Retention und Zeitqualität. Verbraucher ist die freigegebene
indikative Einstandsprüfung V2; B58-Originalzeit/Instrumentstatus und
B06-/Produktfristlücken bleiben eigenständige Voraussetzungen.

**Bestehende Zuständigkeit:** Market Data / Position Monitoring. Vorhandene
`RiskMarketDataReader.saved_quote`, `MarketStatusReader.read`,
`latest_indicative_assessment`, `RetainedWarrantQuoteProvider`,
`position_monitoring/service/quote_sources.py` und JPMorgan-Adapter nutzen.
Der [Readbacknachweis](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#3-p02-vollständige-vorhandene-kette-und-verbleibende-informationslücke)
belegt die vollständige Kette und die konkrete Informationslücke.

**Konkrete Arbeit in diesem einen Schnitt:**

1. Einmalig nur die bestehende P02-Bindung in einer ausdrücklich
   `REPEATABLE READ READ ONLY`-Transaktion mit `autoflush=False` lesen:
   gespeicherter Quote, aktueller Gap/Capture und damalige Assessmentinputs.
   Grund, Identitätsübereinstimmung, Ereignis-/Empfangs-/Erfassungs- und
   Bewertungszeit privat sichern; Rollback. Es erfolgt kein Provider-I/O
   und kein Regellauf. Ein Wiederholen des unveränderten Gesamtcollectors
   reicht nicht, weil dessen GETs das Journalfeld nicht exponieren.
2. Den Resolverzweig für `INSUFFICIENT` so korrigieren, dass ein fehlender
   Bid und ein spezifischer `refresh_error`/Retentionkontext erhalten bleiben
   und nicht durch `QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY`
   verdeckt werden. Zeitqualität bleibt ein gesonderter Befund. Keine
   Originalzeit aus Empfang ableiten, keine Qualitätsgrenze lockern.
3. Nur eine durch den Original-/Journalbefund belegte technische Ursache
   auf derselben vorhandenen Route beheben. Ist stattdessen kein Preis
   angeboten oder ein anderer Zugang erforderlich, genau diesen Befund
   und den begrenzten Beschaffungs-/Entscheidungsbedarf ausweisen.
   Eine spätere reguläre Beobachtung am vorhandenen Verbraucher nachlesen;
   keine automatische Provider-/Scope-Aktivierung daraus ableiten.

**Bereitgestellter Fortschritt:** Schritt2 ist als enger Resolver-/API-Fix
implementiert und durch Fail-before-Regression sowie lokale Prüfungen
qualifiziert. Für Schritt1 steht derselbe eigenständige
[Collector](../../scripts/collect-depot-data-supply.py) im
[gezielten Modus](../technical/ISSUER_MONITORING_OPERATIONS.md#gezielter-p02-journalread)
bereit. Das alte vollständige Archiv wird als Identitätsreferenz gelesen;
der neue Export enthält keine erneute Gesamtsammlung. Aktuelle und damals
verwendete Fakten werden getrennt geliefert. Die Einzelbelege und
Prüfgrenzen stehen im [Nachtrag](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#p02-fortsetzung-20261122).

**Benötigter Zugang / Entscheidung:** Für Schritt1 genügt der vorhandene
lokale Backend-/DB-Lesezugang, derselbe Installationsbenutzer und die private
Bindung aus dem gelieferten Paket. Hier besteht kein interaktiver PC-Zugang;
deshalb ist genau dieser enge einmalige Ownerexport noch erforderlich.
Keine neue Quelle und keine kostenpflichtige Beschaffung sind dafür nötig.
Ein zusätzlicher Direktstream oder Ersatzprovider benötigt nur dann eine
konkret vorbereitete Zugangs-/Nutzungsentscheidung, wenn die gespeicherten
Fakten ihn erforderlich machen; bestehende Freigaben bleiben erhalten.

**Überprüfbare Abnahmekriterien:**

- P02 hat einen exakt gebundenen konkreten Fehler-/Quellleerebefund samt
  Zeitbezug; aktueller Journalstand und frühere Assessmentgrundlage werden
  nicht vermischt. Andere Produkte/Jobs dienen nicht als Ersatzbeleg.
- Ein gezielter synthetischer Test für fehlenden Bid plus Retentionfehler
  zeigt die erhaltene spezifische Ursache und separat unbekannte
  Originalzeit; vorhandene Provider-/V2-Verträge bleiben unverändert.
- Die folgende normale Verbraucherbeobachtung belegt entweder einen
  positiven identitäts-/einheits-/währungsgleichen Bid mit tatsächlichem
  Empfangsalter **≤300 s**, ohne wirksame neue Versorgungslücke und mit
  passendem V2-Ergebnis, oder den eindeutigen verbleibenden Quell-/
  Zugangsfehler. Ein Runnerstart, HTTP200, neue Receiptzeit oder pauschaler
  Timestampcode genügt nicht. Strenge B58-Abdeckung wird separat bewertet.
- Öffentlicher Befund bleibt technisch/pseudonymisiert; private Preise,
  Holdings, Identitäten, Originale und Zugangsdaten bleiben geschützt.

**Arbeitsstatus:** Analysis für die tatsächliche Versorgungsursache —
Gesamtreadback ausgewertet; Resolverkorrektur und enger Lesehelfer
implementiert und lokal qualifiziert. **Jetzt genau erforderlich:** den
gezielten Modus einmal auf dem bestehenden PC gegen das bereits gelieferte
Archiv ausführen und sein privates Ergebnis auswerten. Der konkrete
Journalgrund, eine daraus begründete Quellenkorrektur und die tatsächliche
Verbraucherwirkung sind weiterhin nicht beobachtet. Keine zusätzliche
Regel- oder Providerfreigabe aus dem Codefortschritt ableiten.

</details>

<details>
<summary>Erledigter Gesamtreadback: damaliger Auftrag und Abnahmekriterien</summary>

Die folgende Fassung erhält den am 20./21.11. vorbereiteten Diagnoseschnitt.
Der private Verbraucherexport und seine vierteilige Ursachenmatrix liegen
seit dem 22.11. vor. Originalupgrade-/Kalenderimport-Detailabnahme und der
konkrete P02-Gap sind als verbleibende Teilbelege ausdrücklich abgegrenzt;
daraus entsteht kein zweiter paralleler aktueller Auftrag.

<a id="depotdiagnose-auftrag-20261121"></a>
### Historischer Diagnoseschnitt vom 20./21.11.2026 — am 22.11. ausgewertet

**Ziel:** Einen vollständigen privaten, ausschließlich lesenden
Verbraucherbefund des tatsächlich installierten PC-Stands erstellen.
Die erwartete Verbesserung ist die eindeutige Ursachenklärung für jede
aktuelle offene Position und Regel, einschließlich der noch unbelegten
v1.5.52-Wirkung. Es wird keine erfundene Zahl künftig auswertbarer Positionen
versprochen.

**Betroffene Daten/Regeln:** effektive Ausführungs-/Währungsbasis,
Produkt-/Basiswert-/Listingbindung, gespeicherter Bid mit Zeitqualität,
historischer Maßstab, Kalender, Produktende/letzter Handelstag/Exitwahl,
Ziel-/Basiswerteinstiegsevidenz sowie persistierte Episoden.
V2-Einstand und V2-Frist, B04/B57/B58 und B06-Eingänge getrennt auswerten.

**Vorhandene Komponenten und konkrete Arbeit:** Die
[Betriebsanleitung mit einzelnem Collector](../technical/ISSUER_MONITORING_OPERATIONS.md#lesende-depot-datenversorgungsdiagnose)
verwendet `market-data/positions/quote-coverage` als vollständiges
Inventar und die bestehenden passiven Monitoring-/Trade-Position-Reader.
Runtime und Inventar vor/nach der Sammlung lesen; persönliche Werte im
privaten Diagnoseverzeichnis belassen. Gespeicherte Bewertungen,
`latest_assessment.reasons`, Erwerbsversuche und aktive Episoden
mit der jeweiligen wirtschaftlichen/Quellenbasis verbinden. Für jede
Blockade den zuständigen bestehenden Owner und die konkrete Korrektur
oder fehlende Beschaffung eintragen. Anschließend nur aggregierte
technische Befunde im Versorgungsnachweis und diese Statusfelder
aktualisieren. Kein neuer Runner, API-Endpunkt, Provideradapter oder
Produktivimport ist für diesen Diagnoseschnitt nötig.

**Benötigter Zugang / gebündelte fehlende Information:** einmalige
Ausführung von `collect-depot-data-supply.py` auf der bestehenden Installation
und Bereitstellung seines privaten `.tar.gz`-Pakets beziehungsweise ein
bereits vorhandener gleichwertiger lesender Befund. Kein neues
Providerkonto und keine Geheimnisse erforderlich. Für die nachfolgende
Brokerbewertung genügt ergänzend der tatsächliche Brokername und die
Angabe eines bereits erlaubten Lesezugangs. Fehlende persönliche
Exitentscheidungen und kostenpflichtige Quellen werden anhand der
Matrix konkret vorbereitet, nicht automatisch aktiviert.

### Ausgangsstand und Priorität

Der Produktdatums-Fix aus [PR #368](https://github.com/burckhju/trading-workspace/pull/368) ist qualifiziert, integriert und als [v1.5.52](https://github.com/burckhju/trading-workspace/tree/v1.5.52) auf `c7db441de36297a98d47cdf28c64b4e5d9994692` veröffentlicht. Merge: **19.11.2026, 20:16:54 Uhr MEZ**; Veröffentlichung: **20:45 Uhr MEZ**. Die [Liefernotiz](../releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md) beschreibt die getrennten Datumsrollen, die Wiederverwendung gespeicherter Originale und den engen lokalen Kalenderimport. Implementierung, technische Qualifikation, Integration und Veröffentlichung dieses Schnitts sind abgeschlossen.

Der letzte öffentlich belegte PC-Betrieb bleibt dagegen **v1.5.51 / `254f0bbd52ab42e0120d381e915dc96c1118796c`**. Der Zyklus aus [#367](https://github.com/burckhju/trading-workspace/pull/367), **19.11.2026, 18:06:42–18:07:17 Uhr MEZ**, meldete in beiden Prüfpfaden sechs bewertete Positionen, sechs Datenprobleme und null technische Positionsfehler. Der spätere vollständige private Readback, öffentlich in #368 zusammengefasst, betrifft **vier damals offene Positionen**, jeweils mit Einstands- und Fristdatenproblemen. Sein Rohdiagnosezeitpunkt und die private Einzelmatrix sind hier nicht zugänglich. Diese vier Positionen bilden einen historischen Referenzbestand. Maßgeblich ist die aktuelle vollständige offene Grundgesamtheit; abweichende Bestände werden erklärt und nicht auf vier oder sechs Positionen begrenzt.

Ein PC-Update auf v1.5.52 und ein anschließender regulärer V2-Zyklus sind bislang nicht öffentlich bestätigt. Daraus folgt keine Aussage, dass das Update tatsächlich unterblieben ist. Zunächst ist der installierte Stand lesend festzustellen. Die bekannten Datenprobleme bleiben belegte A-Blockaden und haben gemäß bestehender Prioritätsregel Vorrang vor dem B-/C-Fokus. Der falsche Produktende-/Zahlungstagvergleich ist nun eine **offene Betriebswirkungsprüfung der ausgelieferten Korrektur**; Kalender-HTTP-403 und weitere Beleglücken sind davon getrennt.

### Bestehende Diagnosewege und betroffene Komponenten

| Zweck | Vorhandener Weg / Owner | Grenze |
|---|---|---|
| Vollständige offene Grundgesamtheit im vorbereiteten GET-Ablauf | `GET /api/v1/market-data/positions/quote-coverage`; [kopierbare lesende Betriebsanleitung](../technical/ISSUER_MONITORING_OPERATIONS.md#lesende-depot-datenversorgungsdiagnose) | Alle offenen, nicht stornierten Positionen einschließlich fehlender Quellen. Inventar vor und nach den Detailreads vergleichen; `monitoring_usable` ist keine Regelqualifikation |
| Strenge B04/B57/B58-Eingänge und B06-Belege | Bestehende passive Reads `hebeltrader-original-bid`, `hebeltrader-loss`, `hebeltrader-targets` beim Monitoring sowie `hebeltrader-evidence` beim Trade-Position-Owner; alle sechs Pflichtreads stehen in der Betriebsanleitung | Für B06 beide Zielhistorien- und Trade-Evidenzreads verwenden. Belegabdeckung und wirtschaftliche Beitragsbasis sind kein vollständig ausgeführter Folgestop; Original-Einzeltrades bei konkretem Bedarf über vorhandenen History-Read ergänzen |
| Prozess-/Zyklussnapshot | `GET /api/v1/position-monitoring/runtime/status`; [API-Komposition](../../backend/app/features/position_monitoring/api/__init__.py), bestehender Runner | Passiver Read. `last_rule_checks` stammt aus der alten Stop-/Zielprüfung und ist allein **kein vollständiges V2-Positionsverzeichnis**. Installierte Version und Commit zusätzlich aus dem vorhandenen Betriebsnachweis binden |
| Direkter Ownerread als gezielte lesende Ergänzung | [OpenPositionReader.list_open()](../../backend/app/features/trade_position/service/open_position_reader.py) beim FT-009/010-Owner | In `AsyncSession(autoflush=False)` mit ausdrücklich gesetztem `REPEATABLE READ READ ONLY` und abschließendem Rollback verwenden; Workspacebindung erhalten. Bestehende Owner-SELECTs für aktive Episoden erklären gegebenenfalls historische Laufpositionen |
| Gespeicherter Einstandsbefund | `GET /api/v1/position-monitoring/trades/{trade_id}/indicative-entry?position_id={position_id}` | `IndicativeEntryReader` verwendet eine eigene `REPEATABLE READ READ ONLY`-Transaktion. Er liefert `latest_assessment` einschließlich `rule_version`, `document_readiness`, Episoden und Lesezeit. Der DTO enthält nicht sämtliche neuen Datums-/Parser-/Originalfelder; kein Reparse oder Providerabruf |
| Gespeicherter Produktfristbefund | `GET /api/v1/position-monitoring/trades/{trade_id}/product-deadline-review?position_id={position_id}` | `ProductDeadlineReviewReader` liest in eigener lesender Transaktion. Regelversion: Top-Level `definition_version`. Neue Datumsrollen können nach entsprechender Bewertung in `latest_assessment.product_evidence` stehen; `calculation`, Gründe, Episoden und Lesezeit bleiben getrennt. Ein älteres gespeichertes Assessment wird durch den GET nicht aktualisiert |
| Originalrevision, Datumsrollen und Bindung | [ProductReviewEvidenceReader und latest_document](../../backend/app/features/product/service/review_evidence.py); bestehender Product-Owner | In ausdrücklich lesender Transaktion zum benannten `known_at` verwenden. `latest_document` liefert unter anderem Parserstand, Originalhash, ursprüngliche Abruf- und neue Speicherzeit; `current_for_review` beziehungsweise `deadline_for_review` liefern die qualifizierten Fakten. Den Originalstand zeitlich dem jeweiligen Assessment zuordnen |
| Lokaler Parserupgrade | [ProductReviewReadiness](../../backend/app/features/product/service/review_acquisition.py) mit `reparse_saved_original_kid` | Bereits ausgelieferter **aktiver** Bestandteil des normalen V2-Laufs, kein Diagnose-GET. Intakte bekannte v1-Originale werden vor dem Netzwerk-Backoff neu ausgewertet. Eine neue Revision bleibt von späteren Netzwerkfehlern, unverändertem Beschaffungsstatus und Wiederholungsbudget unterscheidbar |
| Einheit, Listing und persönliche Exitwahl | Bestehende Product-Services `price_scale_evidence`, `deadline_listing_terms`, `deadline_choice` | Product bleibt Beleg-/Identitätsowner. Bestehende Terms, Ausführungen und historische Originale werden durch den Datumsfix nicht umgeschrieben |
| BID, Mapping, Kalender und Provenienz | Bestehende TC-001-/Market-Data-Reader, [risk_read](../../backend/app/features/market_data/service/risk_read.py), [review_calendars](../../backend/app/features/market_data/service/review_calendars.py), Sitzungsevidenz und Provideradapter | Qualifikation beim vorhandenen Owner. Der Workspace-Positions-GET kann Valuation-/Quoteresolver aufrufen und ersetzt keine garantiert passive Enumeration |
| Prüfung eines vorhandenen lokalen Kalenderoriginals | `python -m app.tools.import_review_calendar_original --file DATEI`; [ausgelieferte CLI](../../backend/app/tools/import_review_calendar_original.py) | Ohne `--apply` echte lesende Vorschau; `--file -` liest Originalbytes aus stdin. Nur das fest gebundene XSTU-2026-Original ist zulässig. `--apply` ist ein gesonderter Schreibschritt; ein Vorschauergebnis belegt keinen Import |

`monitoring-once`, Refresh-/Readiness-Commands, Update-`prepare/apply` und ein Kalenderimport mit `--apply` sind keine passiven Diagnoseaufrufe. Diese Dokumentationsfortschreibung führt sie nicht aus und erteilt keinen automatischen Update-, Import-, Provider-, Korrektur- oder Versandauftrag. Bereits vorhandene konkrete Freigaben behalten ihren damaligen Umfang.

### Quellen, Originale, Kalender und Entscheidungen gezielt zuordnen

Die folgenden Kriterien konkretisieren die Prüfung vorhandener Belege und den späteren Abschluss gesondert beauftragter Ownermaßnahmen; sie erweitern den aktuellen Auftrag nicht um Schreiboperationen. Die Kategorien stammen aus dem dokumentierten Readback und dem ausgelieferten Reparaturumfang. Ohne private Matrix wird keine Ursache einer erfundenen Position zugewiesen. Die technische Lieferung des Datumsfixes ist abgeschlossen; die erste Zeile betrifft ausschließlich seinen Nachweis am tatsächlichen Bestand.

| Lücke / bekannter Befund | Erwartetes Benutzerergebnis und bestehender Owner | Benötigte Voraussetzung | Überprüfbarer Abschluss |
|---|---|---|---|
| Betriebswirkung der korrigierten Produktende-/Zahlungstagsprüfung noch unbelegt | Product liefert getrennte belegte Datumsrollen; Monitoring verwendet das relevante Produktende | Bestätigter PC-Stand v1.5.52 oder begründet neuerer Stand mit diesem Fix; vorhandene Originalbytes, Hash und unveränderte Termsbindung; regulärer V2-Lauf | Im betroffenen Originalfall ist genau eine passende v2-Folgerevision mit unveränderten Bytes, Hash, Quelle und ursprünglicher Abrufzeit belegt; Wiederholung erzeugt keine zusätzliche identische Upgradeversion. Der falsche Widerspruch entfällt im nachfolgenden Assessment. `EXPECTED_LATEST` bleibt eingeschränkt; echte Datums-/Produkt-/Basiswertkonflikte bleiben Sperren. Ein Zahlungstag ersetzt kein fehlendes Produktende |
| Gespeicherter Kalenderabruf HTTP 403; tatsächlicher lokaler Import ungeklärt | TC-001 liefert eine nachvollziehbar belegte Kalenderrevision | Exaktes vorhandenes privates XSTU-2026-Original, fest gebundene URL, SHA256 und Quellenversion; vorhandener Importnachweis oder konkret beauftragter Import | Lesend bestätigte passende Revision beziehungsweise ausgeführter beauftragter Import mit `USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION` und `FILE_RECEIVED_AT`; keine Umdeutung zu erfolgreichem Netzabruf. Umfang bleibt XSTU, 2026 und `DAY_ONLY`; fehlende Datei oder Importfreigabe präzise benennen |
| Fehlende/ungeeignete BID-Route oder Kurszeit | Market Data liefert einen verwendbaren indikativen BID oder erklärt die konkrete Unverwendbarkeit | Exakte Produkt-/Listing-/Providerbindung, erlaubte Quelle und zeitlich qualifizierter Kurs gemäß bestehendem V2-Quellenmodus | Quote, Quelle, Originalzeit beziehungsweise ausdrücklich unbekannte Originalzeit, Empfang, Währung und Qualitätsgrenze sind belegt; eine zulässige verzögerte Indikation wird nicht als Echtzeit oder strenge B58-Eignung ausgegeben |
| Fehlender Stückmaßstab / echte Anpassung | Product und Execution liefern vergleichbare Einstands-/Kurseinheiten | Originalbedingungen, belegte Einheit, bei Konflikt Anpassungsbeleg und historische Kaufwährung | Vergleich ist nachvollziehbar möglich oder konkret blockiert; V2-Kontinuitätsannahme bleibt sichtbar und überstimmt keine bekannte Anpassung. Vorhandene Ausführungen bleiben die wirtschaftliche Quelle |
| Tatsächlich falsche Basiswertidentität | Product/Market-Owner bindet das richtige Instrument und dessen Referenzmarkt | Produktoriginal, stabile Identitätsbelege und konkret beauftragte Korrektur, falls erforderlich | Exakte Identität stimmt; alter Konflikt und Korrekturhistorie bleiben nachvollziehbar. Eine passende Datumsrolle oder bloße Namensähnlichkeit behebt keinen Identitätskonflikt |
| Fehlende persönliche Exitwahl / letzter Handelstag | Product liefert ausdrücklich gewähltes Ausstiegslisting und ursprünglichen Terminbeleg | Persönliche Listingentscheidung und Originalprodukt-/Listingseite mit letztem Handelstag | Listing, Revision, Produktende und letzter Handelstag bleiben exakt gebunden. Die Frist verwendet das frühere relevante Datum; der Zahlungstag ersetzt keines der erforderlichen Daten |
| Weitere Kalenderreichweite / individueller Produktschluss | TC-001/Product liefern passende Sitzungen und tatsächlich belegte Zeitpräzision | Konkrete benötigte Kalenderjahre, feste Börsenzuordnung und Originalbeleg zum individuellen Cutoff | Erforderlicher Vor-/Rückwärtsbereich ist vollständig belegt oder fehlende Tage/Jahre sind genau benannt. Ein Tageskalender erzeugt keinen Schlusszeitpunkt; B20 bleibt ohne Cutoffnachweis unbestätigt |

### Zugangslücke

Erforderlich sind der vollständige aktuelle lesende Verbraucherbefund und ein datierter Nachweis des tatsächlich installierten PC-Stands. Die vorhandene private Vier-Positionen-Diagnose und ihre Original-/Revisionsbelege werden als historische Vergleichsbasis übernommen, soweit sie zugänglich sind. Sie können als lokaler Readback bereitgestellt oder über einen zulässigen lesenden Zugang zum identifizierten Backend samt bestehenden Datenbankreadern gewonnen werden. Dieser Dokumentationsauftrag hat keinen solchen privaten Zugriff. Dadurch bleiben die aktuelle Installation, die positionsgenaue Ursachenbindung, der Originaldateivergleich und die reale Abdeckung nach v1.5.52 hier unabhängig unbestätigt.

Liegt nur der ältere Betriebsbeleg vor, bleiben ein geeigneter installierter Stand und die nachfolgende normale Auswertung Voraussetzungen des Wirkungsnachweises, keine Voraussetzung für die jetzige Ursachenklärung. Liegt bereits ein neuerer bestätigter Stand vor, wird dessen konkreter Commit und Verbindung zum ausgelieferten Fix verwendet. Ein fehlender Zugang oder ausstehender Betriebsnachweis wird mit dem genau blockierten Schritt dokumentiert; er setzt die abgeschlossene Implementierung und Veröffentlichung nicht zurück. Private Depotkennungen, wirtschaftliche Einzelwerte und Originaldateien bleiben im privaten Arbeitsnachweis. Im öffentlichen Repository genügen aggregierte Ergebnisse, Quellenklassen und technische Nachweisidentitäten.

### Überprüfbare Abnahmekriterien

1. Tatsächlichen Release-/Containerstand, Commit, Schema, Scope und datierte
   letzte reguläre Auswertung festhalten. v1.5.52 weder aus Main noch aus
   einem gestarteten Runner als installiert voraussetzen.
2. Beide Inventarreads erfolgreich; Zahl, eindeutige IDs und alle offenen
   Positionen einschließlich fehlender Quellen erfasst. Jede Position
   erhält sämtliche vorgesehenen Readergebnisse oder einen ausdrücklich
   ausgewiesenen Diagnosefehler. Kein fester Vierer-/Sechsernenner.
3. Je Position und Regel `vollständig / teilweise / nicht auswertbar`
   mit Assessment-ID, Regelversion, Bewertungs-/Aufzeichnungs-/Lesezeiten,
   unveränderten Reason-Codes, Episoden, Quellenbezug und Ursache
   `Quelle / Mapping / Import / Verarbeitung / Konfiguration /
   Fachentscheidung`. Unzugänglicher Read bleibt gesondert
   `Diagnose nicht verfügbar`. `monitoring_usable` ist keine
   Regelqualifikation.
4. Verschiedene Zyklus-, Bestands- oder Basisstände sichtbar halten und
   bei Bedarf gezielt lesend wiederholen. Keine globale Atomarität
   über mehrere GETs behaupten. Bereits vorhandene Rohlogs nur für
   einen konkret ungeklärten Beschaffungsfehler ergänzen.
5. Die Datumsreparatur am betroffenen Verbraucher nachweisen oder
   präzise als fehlenden Installationsnachweis, belegten älteren Stand,
   fehlende nachfolgende Auswertung oder weiterhin wirksamen echten
   Konflikt ausweisen. GETs allein beweisen
   keine aktuelle Parserrevision; nötige Originalrevisionsprüfung
   ausdrücklich als gezielte lesende Ergänzung benennen.
6. Für jede wesentliche Restlücke Beschaffungsweg, Owner, mögliche
   Regelverbesserung und erforderliche Entscheidung festhalten.
   Geeignete öffentliche Webrouten, mehrdeutige Auswahl und fehlende
   Abrufrechte ausdrücklich getrennt prüfen; Mehrquellenvergleich nicht
   als Ersatz für Originalzeit oder Status qualifizieren.
   Öffentlich nur aggregierte technische Ergebnisse; private
   Positionen, Beträge, Originale und Zugangsdaten bleiben geschützt.

Ein abgeschlossener Zyklus oder ein unveränderter Warnungszähler genügt
nicht. Abgenommen wird die lückenlose Ursachenmatrix beziehungsweise
konkret nachgewiesene bessere Regelabdeckung. Damals dokumentierter Arbeitsstatus: **Analysis — PC-Verbraucherbeleg fehlt;
lesender Ablauf ist vorbereitet.** Der tatsächliche Readback und die
Verbraucher-Ursachenmatrix sind seit dem 22.11. abgeschlossen; offene
Teilbelege sind im neuen Nachtrag und Folgeauftrag präzise benannt.

### Ergebnis und danach verfügbare Folgearbeit

Ergebnis ist die vollständige private Ursachen-/Belegmatrix mit öffentlicher aggregierter Nachweisfortschreibung. Bereits nachweisbare Teilabdeckung wird je Regel ausgewiesen; unbelegte Wirkung bleibt offen. Die Matrix bereitet genau abgegrenzte Quellen-, Identitäts-, Import- oder Betriebsmaßnahmen vor. Der bereits veröffentlichte #368-Schnitt wird weder neu gebaut noch nochmals zur Integration oder Veröffentlichung eingeplant.

Sobald kein vorrangiger A-Blocker verbleibt, wird der bestehende B-/C-Fokus anhand der dann offenen Fach-/Nutzungsabnahmen fortgesetzt. Daraus entsteht keine zweite parallele aktuelle Arbeitsanweisung und keine automatische Modell-, Baseline- oder Zustellaktivierung.

</details>

<a id="historische-planungsstaende"></a>
## Historische Planungs-, Freigabe- und Betriebsstände

Die folgenden Texte dokumentieren ihren damaligen Erkenntnisstand und historische Autorisierungen. Sie sind ausdrücklich **keine aktuelle Aufgabenstatusquelle und kein neuer Betriebs-, Merge-, Veröffentlichungs- oder Änderungsauftrag**. Die inzwischen belegten Fortschritte stehen in der aktuellen Abnahmematrix; der einzige aktuelle nächste Auftrag steht [oben](#naechster-schnitt). Frühere Datums-/Commit-/CI-/Scopebezüge bleiben erhalten.


<a id="historischer-audit-20261119"></a>
<details>
<summary>Erstprüfung vom 19.11.2026 auf v1.5.51 – damalige Main- und Liefernachweise</summary>

Der Audit begann am 19.11.2026 um 19:31:38 Uhr MEZ; sein letzter Main-/Tag-/PR-Abgleich erfolgte um 19:50 Uhr MEZ. Geprüft waren `254f0bbd52ab42e0120d381e915dc96c1118796c` und `v1.5.51`. Die folgende damalige Nachweistabelle bleibt erhalten. Insbesondere die Aussage, #368 sei noch offen, galt nur zu diesem Zeitpunkt; seine spätere Integration und Veröffentlichung sowie die aktuelle Betriebsgrenze stehen im heutigen Nachweisregister. Die damaligen CI-Zahlen werden nicht nachträglich dem neuen Produktcommit zugerechnet.

| Aktueller Nachweis | Erneut gelesener Befund | Aussagegrenze |
|---|---|---|
| [Main-Commit](https://github.com/burckhju/trading-workspace/commit/254f0bbd52ab42e0120d381e915dc96c1118796c) / [Softwaretag v1.5.51](https://github.com/burckhju/trading-workspace/tree/v1.5.51) | Main und Tag identisch; Tree `a353b22a025ab507320b648b5dac024eeac6045c`; VERSION `1.5.51` | Geprüfte Produktbasis; der spätere Dokumentationscommit ist kein neuer Produktrelease |
| [Backend 44538810458](https://github.com/burckhju/trading-workspace/actions/runs/44538810458) / [Qualityjob](https://github.com/burckhju/trading-workspace/actions/runs/44538810458/job/135611332370) | Push auf genau diesen Commit, Versuch 1, erfolgreich: Ruff, Black, mypy, Migration, 6.242 Tests, 1 Warnung; 89,90 % Coverage bei 85-%-Gate. Früher separater Schritt: 90 Installer-/Recoverytests erfolgreich | Logs einschließlich tatsächlichem Checkout direkt gelesen. Die 90 Fälle nicht zur Gesamttestzahl addieren; vorhandene Starlette-/AnyIO-Warnung erhalten |
| [Produktionsimage](https://github.com/burckhju/trading-workspace/actions/runs/44538810458/job/135611332059), [Docker-/PostgreSQL-Recovery und Renderer](https://github.com/burckhju/trading-workspace/actions/runs/44538810458/job/135611332638) | Beide Jobs/Schritte erfolgreich, Logs direkt gelesen: tatsächliches Wheel/Hash, Python 3.12.16, Nicht-Root-Rechte, Migration bis 0060; reale synthetische Retry-/Replace-Prüfungen und Sandbox | Synthetischer CI-Betrieb ersetzt weder private Bestandsprüfung noch PC-Wiederherstellungsabnahme |
| [Frontend 44538810455](https://github.com/burckhju/trading-workspace/actions/runs/44538810455/job/135611333257) | Versuch 1, erfolgreich: 205 Dateien / 2.713 Tests, TypeScript, ESLint, Prettier und Produktionsbuild; Abschlusslog/Checkout gelesen | Automatisierte Tests ersetzen keine menschliche fachliche/assistive Bedienabnahme |
| [End-to-End 44538810474](https://github.com/burckhju/trading-workspace/actions/runs/44538810474) | Alle vier Jobs erfolgreich, finale Logs direkt gelesen: 206 allgemeine Browserfälle; fünf vorgesehene Smoke-Skips sind zwei Reports, zwei Journal/Evidence-Journeys und eine Candidate-Governance-Journey in separaten Ownerjobs | Echte Owner-/PostgreSQL-Reisen und Browserfälle mit abgefangenem HTTP sind in den Teilfähigkeiten unterschieden; kein privater Liveprovider-End-to-End-Nachweis |
| [Publisher 44546805171](https://github.com/burckhju/trading-workspace/actions/runs/44546805171) | Neun Guards erfolgreich; Tagjoblog: `Published v1.5.51 at fully tested main 254f0bbd…`, 19.11.2026 15:43:29 Uhr MEZ | Tag ist veröffentlicht. [GitHub Latest Release](https://api.github.com/repos/burckhju/trading-workspace/releases/latest) liefert noch den datierten Release-Datensatz `v1.0.0-product-selection` vom 16.08.2026; kein Widerspruch zur Taglieferung |
| [PR #367](https://github.com/burckhju/trading-workspace/pull/367), Body zuletzt geändert 19.11.2026 18:30:33 Uhr MEZ | Nachträglich ergänzte Nutzer-Rückmeldungen zu Installation, Aktivierung und abgeschlossenem V2-Zyklus; öffentliche aggregierte Betriebsevidenz | Keine eigene PC-Ausführung dieser Prüfung; sechs Datenwarnungen sind keine sechs fachlichen Fristauslöser |
| [PR #368](https://github.com/burckhju/trading-workspace/pull/368), neu angelegt 19.11.2026 19:31:56 Uhr MEZ | Neuere Zusammenfassung des vollständigen privaten Readbacks mit vier offenen Positionen und bereits isolierten Ursachen; Body und relevante Dokument-/Implementierungsdiffs gelesen | Öffentlicher Bericht über privaten Befund; Originalmatrix/Originaldateien hier nicht zugänglich. Code am Auditstand nur im offenen PR, keine nachträgliche Zurechnung zu Main |

</details>

<details>
<summary>Konsolidierungs- und Zugriffsstand vom 13.–18.10.2026</summary>

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Revision | Konsolidierung 2026-10-13; zur fachlichen Prüfung |
| Quellenstand | `main` / `a78288ad38610656480d0363abe657b567c7ba94` / Softwaretag `v1.5.5` |
| Funktion | Einzige maßgebliche Quelle des aktuellen Arbeitsstatus |
| Prüfgrenze | Statische Quellen- und CI-Prüfung; kein vollständiger lokaler Checkout, keine neue Fach- oder Liveabnahme |

> Fortschreibung 17.10.2026 auf `e9aac2bfaadeb9133a6ed07e42d1dec39836b156` / 1.5.8: Vollständiger Checkout für PB-017 Brutto-PnL und PB-019 Performance geprüft; [Quellenvertrag und V1-Entscheidungsvorschlag](../implementation/PERIOD_REALIZED_GROSS_READINESS.md) und [Owner-Trace-Qualifikation](../implementation/PERIOD_REALIZED_GROSS_QUALIFICATION.md). Die darunter erhaltene Konsolidierungsbasis beschreibt ihren damaligen Prüfstand. Die anschließende Nutzeranweisung „Ok, umsetzen“ gibt den konkreten Währungs-/Periodenvertrag zur Umsetzung frei ([ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)); die [Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) dokumentiert die Fortsetzung. Nur ausdrücklich ergänzte Teilfähigkeiten werden fortgeschrieben; keine fertige Fachabnahme, Veröffentlichung oder PC-Abnahme.

> Fortschreibung 18.10.2026: Der Nutzer hat mit „wenn prüfungen grün mergen und für den pc verfügbar machen“ die geschützte Integration und PC-Bereitstellung des konkret gelieferten Schnitts ausdrücklich autorisiert. [Version 1.5.9 und Updateweg](../releases/V1.5.9-REALIZED-GROSS-REPORT.md) verbinden diese Freigabe mit erneuter aktueller PR-/main-CI, dem getrennt vorgezogenen Integritätsfix #249 und dem tatsächlich veröffentlichten Tag. Die Aussagen vom 17.10. über fehlende Veröffentlichungsfreigabe sind damit historisch; eine PC-Installation oder vollständige M8-Abnahme wird weiterhin nicht behauptet.

## Nachweisregister und erreichbare Prüfungen

Alle unten verlinkten Quellbelege sind auf den Basiscommit gepinnt. Historische Dateien können frühere Commitstände beschreiben; deren Zahlen und Freigaben sind keine heutigen Vollnachweise.

| Aktueller Basisnachweis | Erreichbares Ergebnis | Aussagegrenze |
|---|---|---|
| [Backend Run 38433996217](https://github.com/burckhju/trading-workspace/actions/runs/38433996217) | 2026-10-13, success; quality inkl. Ruff, Black, mypy, PostgreSQL-Migration, Tests/Coverage; restrictive-umask image; issuer renderer sandbox/isolierte Migrations- und Compose-Prüfung | Run-/Job-/Step-Ergebnisse gelesen; Rohlogs, Assertions und komplette Testreports nicht vollständig geprüft |
| [Frontend Run 38433996560](https://github.com/burckhju/trading-workspace/actions/runs/38433996560) | 2026-10-13, success; TypeScript, ESLint, Prettier, Unit/Coverage, Build | Kein lokaler neuer Lauf und keine menschliche Benutzerabnahme |
| [End-to-End Run 38433996404](https://github.com/burckhju/trading-workspace/actions/runs/38433996404) | 2026-10-13, success; Stackstart, Migration der Wegwerfdatenbank und Playwright smoke erfolgreich; fehlerabhängige Container-Log-Schritte skipped | Kein Liveprovider-/JMBbot-Nachweis; kein Beleg jedes ursprünglich versprochenen Features |
| [Git-Tag v1.5.5](https://github.com/burckhju/trading-workspace/tree/v1.5.5) | Ref zeigt auf a78288ad38610656480d0363abe657b567c7ba94; VERSION und Backend-/Frontend-Manifeste nennen 1.5.5 | Software-Auslieferung ist nicht Installation; vollständige Lock-/Versionsdateikonsistenz nicht erneut geprüft |

Die dokumentierten 2.567/445/48 Tests der Release-Notiz betreffen deren Nachweisstand und werden hier nicht als eigenständig nachgezählte Ergebnisse ausgegeben. Ebenso bleiben ältere 839-/274-/89-Testzahlen historische Belege.

**Zielinstallation:** JMBbot ist durch die 1.5.5-Release-Notiz identifiziert. Ihr dort genannter früher bestätigter PC-Stand ist v1.5.4 / `ab4730885b91fd954f3494434ff3d1f4734397db`. Aktuell installierte Revision, Schema, Compose-Kette, Providerrechte, Datenhistorie, reale Regeln und Zustellung wurden hier nicht beobachtet. Der in Release-Dokumenten genannte Schema-Head `20261012_0045` ist ein Dokument-/CI-Kontext, kein hier ausgeführtes `alembic heads/current` auf JMBbot.

**Nicht lokal ausgeführt:** `bash scripts/check-backend.sh`, `bash scripts/check-frontend.sh`, `bash scripts/run-e2e.sh`, gezielte Anwendungs-/DB-/Browserprüfungen. Ursache: nur eine hashgeprüfte Dokument-Arbeitskopie, kein vollständiger Checkout bzw. identifizierter lokaler Anwendungs-Teststack. Die drei Skripte wurden gelesen. Insbesondere löscht der E2E-Cleanup seine Testvolumes; er wurde nicht gegen unbekannte Ressourcen gestartet. Keine Provideraufrufe, echten Nachrichten oder Nutzerbestandsänderungen.

**Quellenzugriffsgrenzen:** Git-Klon/Archivzugriff im lokalen Laufzeitraum nicht verfügbar; GitHub-Datei-/Tree-/CI-Lesezugriff verfügbar. Code-Suche lieferte unvollständige Ergebnisse und wurde nicht als Abwesenheitsbeleg genutzt. Root/docs/foundation/docs/planning wurden auf anwendbare Anweisungsdateien geprüft; keine dortige AGENTS.md gefunden. Kein Zugriff auf nicht veröffentlichte Nutzer-Arbeitsbäume. Nicht sämtliche ADR-Volltexte, Feature Books, Backendservices, Migrationen, Lockdateien, Workflowdefinitionen, CI-Rohlogs und historischen Abnahmedokumente wurden vollständig neu geprüft. Diese Grenzen sind kein Grund, belegte Funktionen als Not Started zu führen.

## Statusdrift und Auflösung

| Konflikt am Basisstand | Geltende Einordnung und maßgeblicher Eintrag |
|---|---|
| Alte Sammelstatus PB-017–PB-020: Not Started, obwohl spätere Anbindungen/Nachweise vorhanden | Keine pauschale Freigabe; vorhandene Teilfähigkeiten einzeln unter PB-017–PB-020 mit Code-/Consumerbelegen führen |
| Alter FT-007-Hinweis Architecture Review Pending versus historische Traceability Accepted / PB-014 Released | Alten nächsten Sprintschritt nicht weiterführen; vorhandene Planfähigkeit erhalten, konkrete aktuelle Nachweise getrennt |
| Golden-Path-Closeout: Materialisierung/Runtime-Aktivierung offen | Extension 09, PostTradeLearningPage und RuntimeActivationService schließen spätere Teile; ursprüngliche Aussage bleibt historischer Stand |
| FT-013 V1: kein Aktivierungsendpoint; spätere FT-020-Strecke verlangt getrennte Aktivierung | V1-Nicht-Soll nicht als heutige Infrastruktur-Lücke verallgemeinern; Modellfamilien weiterhin separat prüfen |
| Alter Katalog nennt Produktwechsel; FT-010 V1 schließt ihn ausdrücklich aus | M4-Anspruch bleibt unter Produktwechsel offen; keine dauerhafte Verschiebung/Entfernung ohne Entscheidung |
| STOCK-only in alten Baselines; FT-006-/Chart-Nachtrag vom 2026-10-04 erlaubt ETF-Stammdaten | Historische Regel nur für ihren Umfang; aktuelle ETF-Stammdaten berücksichtigen, Indizes bleiben semantische Referenzen ohne erfundene Listings |
| Alter S8-Selektionshinweis versus begründeter NOT_EVALUABLE-Ausnahmeweg im aktuellen Domainvertrag | Ausnahme nicht als bestätigte Eignung darstellen; tatsächlichen aktuellen API-/UI-Vertrag vor fachlicher Behauptung prüfen |
| Alter Monitoringtext: unbedingte Underlying-Preisbasis | FT-010-Nachtrag 2026-09-14 verlangt explizite Instrument-/Währungsbindung; Legacy-ungebundene Regeln nicht als gültig behaupten |
| Alte README-Version/Checklisten versus aktuelle Manifeste/Tag | README führt zu VERSION, Release-Notiz und diesem Backlog; keine zweite vollständige Statusliste |
| Softwaretag 1.5.5 versus historisch genannter PC-Stand 1.5.4 | Aktueller JMBbot-Betriebsbeleg fehlt; kein erfundener Installationsstatus |

Offene PRs werden nicht dem Basiscommit zugerechnet: #249 Formularintegrität, #235/#225 Scheduler, #90 Learning-Navigation und die bereits gelesenen weiteren offenen Recherche-/Regel-/Historienentwürfe (#220/#207/#205/#204/#197/#187). Sie sind fremde/offene Änderungen; kein Merge, keine Übernahme und keine daraus abgeleitete neue Freigabe in diesem Auftrag.


</details>

<details>
<summary>Frühere nächste Schritte und Betriebsnachträge bis v1.5.52</summary>

Die späteren PC-Nachweise in #367 und die Ursachenfeststellung in #368 überholen die folgenden damaligen Aussagen über fehlende Installation, Aktivierung oder unbekannte Ursachen. Historische Releasevorbereitung ist kein offener aktueller Lieferauftrag. Die am Ende früher geplanten vier Statistiken und Diagramme sind im beschriebenen heutigen Teilumfang bereits geliefert.


<a id="indikative-freigabe-20261117"></a>
### Freigegebene indikative Positionsprüfung — 17.11.2026

Die ausdrücklich freigegebene Alternative ergänzt einen eigenen automatischen
Prüfumfang, ohne B04/B57, B58 oder bestehende Stop-/Zielachsen umzudeuten. Der
[gemeinsame Meldungsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-alert-contract-v1)
bereitet drei getrennte Alerttypen, nichtpreisliche Werteform und bestehende
Workspace-/Notification-Consumer vor. Dieser Grundlage folgt die eigene
regelmäßige Einstandsbeobachtung mit Prüferinnerung und Datenproblemepisode.
Der Meldungsgrundlagenschnitt [#357](https://github.com/burckhju/trading-workspace/pull/357)
allein ist keine laufende Überwachung. Der darauf aufbauende
[Regel-PR #358](https://github.com/burckhju/trading-workspace/pull/358) mit dem
[versionierte Regel-/Betriebsschnitt](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-entry-review-v1)
implementiert die eigene automatische Einstandsbeobachtung, deduplizierte
20-Sitzungen-Erinnerung und Datenproblemepisode auf vorhandenen Ownern.
Eigene Migration 0057, tatsächlicher Runneranschluss, passiver Statusread und
getrennte zentrale Scope-/Zustellfreigabe; B04/B57 und B58 bleiben unverändert.
Die Freigabe des Nutzers umfasst diesen alternativen Umfang sowie Merge nach
grünen Prüfungen und versionierte PC-Bereitstellung. Der kontrollierte
[einmalige Aktivierungsweg](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-linux-operation-v1)
ist als eigener Folgeschnitt vorbereitet. Die Prüfung von v1.5.47/48 auf den
neuen Stand fand eine erforderliche eng begrenzte Erweiterung der bisherigen
Deploymentqualifikation: genau zwei bisher fehlende Konfigurationsfelder dürfen
mit ausgeschalteten Werten ergänzt werden. Ein neu gepinnter Launcher und
Alt-Konfigurationsnachweise gehören deshalb zum PC-Lieferumfang. Integration,
reguläre Gates, Veröffentlichung und tatsächlicher PC-Betrieb bleiben getrennte
Nachweise; die PRs binden ihre Tests an Head und Integrationsstand.

Der [Versionsschnitt v1.5.49](../releases/V1.5.49-INDICATIVE-POSITION-REVIEW.md)
führt Meldungsgrundlage #357, Regelpfad #358 und
[PC-Betriebsübergang #359](https://github.com/burckhju/trading-workspace/pull/359)
in einer kontrolliert bereitstellbaren Version zusammen. Die Mergefolge bleibt
an vollständig grüne reguläre Prüfungen und unveränderte gemeinsame Trees
gebunden. Die Release-PR dokumentiert tatsächliche Heads, Integration und
Veröffentlichung; erst die neuesten erfolgreichen Main-Push-Gates am selben
Commit erlauben den unveränderten Publisher. v1.5.47 und v1.5.48 bleiben
unverändert getaggt. Letzter vom Nutzer gemeldeter PC-Nachweis ist weiterhin
v1.5.47 mit vier gesunden Diensten und Readiness; Installation, zentrale
Aktivierung, reale Positionsabdeckung und tatsächlich abgeschlossene Zyklen
dieser neuen Version sind damit noch nicht belegt.

B05 bleibt von aktuellen Kursen unabhängig. Die dokumentierten Originalkalender
sind verfügbar; eine aktuelle persönliche Produkttermin-/letzter-Handelstag-/
Ausstiegslistingbindung einschließlich produktspezifischem Schluss ist im
zugänglichen Quellenstand nicht belegt. Daraus folgt keine Aussage über unbekannte
lokale Belege auf dem Nutzer-PC. Der vorhandene Rechenkern bleibt erhalten;
produktive Fristmeldungen werden ohne diese erforderlichen Fakten nicht aktiviert.
Die übrigen offenen F207-2/B06-/F207-5-Arbeiten bleiben unverändert.

### Beauftragte Erweiterung der indikativen Überwachung — 18.11.2026

**Ausgangsstand:** Main und Tag v1.5.49 zeigen auf
`ce767a0dbee9254756024346a817baf7cdf77797`; die bisherigen Monitoring-PRs sind
integriert. Der Nutzer meldet v1.5.49 mit vier gesunden Diensten, Readiness und
aktiviertem `INDICATIVE_ENTRY_V1`. Der abgeschlossene PC-Durchlauf bewertet sechs
Positionen, erzeugt sechs Hinweise und meldet sechs Datenprobleme bei null
Positionsfehlern. Das ist ein beobachteter Runnerbetrieb, keine geeignete
Kurs-/Einstandsabdeckung. Externe Zustellung dieses Teilumfangs ist ausgeschaltet.

**V2-Lieferumfang dieses Versionsschnitts (1.5.50):**
Die beauftragte Implementierung ist als zusammenhängende Kette
[Originalbelege #361](https://github.com/burckhju/trading-workspace/pull/361) →
[Regelpfad #362](https://github.com/burckhju/trading-workspace/pull/362) →
[Produktfristen #363](https://github.com/burckhju/trading-workspace/pull/363) →
[Arbeitsbereich/PC #364](https://github.com/burckhju/trading-workspace/pull/364)
reviewfähig bereitgestellt. V2 ergänzt ursprüngliche Produktdokumente,
wiederverwendbare veröffentlichte Kalender, ausdrücklich indikative Verarbeitung
verzögerter Quellen, Qualitätsgrenzen für Erholungen, zusammenhängende Episoden
über den Versionswechsel und kursunabhängige begrenzte Produktfrist-Erinnerungen.
Der [V2-Belegvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-readiness-v2)
trennt aktuelle dokumentierte Einheit, angenommene historische Kontinuität und
den weiterhin unveränderten strengen B04/B57/B58-Pfad.

**Abnahme und Auslieferung:** Die Integration dieser Kette und des
[Versionsschnitts](../releases/V1.5.50-INDICATIVE-V2-AND-PRODUCT-DEADLINES.md)
ist ausschließlich nach erfolgreichen regulären PR-Gates und Abgleich der
jeweiligen tatsächlichen Integrationstrees freigegeben. Die unveränderte
Commitkette wird durch [Integrations-PR #365](https://github.com/burckhju/trading-workspace/pull/365)
gemeinsam gegen Main übernommen, nachdem alle vier eigenen Implementierungs-Heads
und der abschließende Release-Head grün geprüft sind. Dieser normale PR-Merge
erhält die bestehende Pflicht zu aktuellen Statusprüfungen; keine Schutzregel
wird gelockert und kein grüner Status auf einen neuen Head übertragen.
Der unveränderte Publisher
veröffentlicht `v1.5.50` erst nach erfolgreichen Backend-/Frontend-/E2E-Push-Läufen
am identischen aktuellen Main-Commit. Die konkreten Heads, Testmerge-Trees,
CI-Läufe und der danach zurückgelesene Tag stehen in der zugehörigen
Releaseübergabe; ein vorbereiteter Versionsschnitt allein ist keine bereits
erfolgte Veröffentlichung. Damit bleiben Implementierung, geprüfte Integration
und veröffentlichtes Artefakt getrennte Nachweise.

**Weiterhin offen: neuer beobachteter PC-Betrieb und reale Abdeckung.**
Die kontrollierte Übernahme von DISABLED oder V1 nach V2, Originaldateiimport und
explizite Exitwahl sind vorbereitet. Es gab hier keine PC-Installation,
Produktimport-/Auswahlaktion, neue produktive Providerzustimmung oder echte
externe Nachricht. Der letzte vom Nutzer belegte Betrieb bleibt v1.5.49 mit
sechs Datenproblemen. Ein dortiger neuer V2-Durchlauf muss die tatsächlich
brauchbaren Positionen und verbleibenden Lücken getrennt ausweisen.

**Reale Abdeckungsgrenzen:** Aktuelle KIDs zweier untersuchter Emittentenpfade
belegen EUR und Stücknotiz. Andere untersuchte Dokumente nennen die Währung,
belegen jedoch keinen eindeutig extrahierbaren Preismaßstab. Fünf untersuchte
Produkte nennen NYSE als Basiswertreferenz; die Originalkalender 2025–2027 sind
einschließlich besonderer Schließung und verkürzter Sitzungen verfügbar. Die
neue Referenzmarktannahme ist kein historischer persönlicher Listingnachweis.
Ein geprüftes einzelnes Stuttgarter Verzögerungsarchiv enthielt die untersuchten
Depotinstrumente nicht und keinen nichtleeren Instrumentstatus; daraus folgt
keine Aussage über sämtliche anderen Archivintervalle. Geeignete B58-Versorgung
bleibt unbelegt. Vier zugängliche Original-Produktseiten enthalten einen
expliziten letzten Handelstag; ihr einmaliger kontrollierter Dateiimport ist
vorbereitet, bestätigt aber keine unabhängig verifizierte Herkunft. Persönliche
Ausstiegslistingwahl, die am PC tatsächlich importierten Originale, fehlende
weitere Kalenderabdeckung und individueller Produktschluss bleiben gezielte
Ausnahmen. Der kalenderbasierte Fristteil bleibt B05_PARTIAL/B20_UNVERIFIED. B06, restliches F207-2 und F207-5 bleiben offen; B08 bleibt
ausgeschlossen.

### Betriebsnachtrag 19.11.2026 — Prepare-Abbruch beim PC-Update

Die Kette #361–#365 ist nach erfolgreichen regulären PR-Prüfungen integriert.
Main und veröffentlichter Tag `v1.5.50` wurden auf
`e335a42fd8380d494eb7a0639f57bc6ee2ff476e` zurückgelesen; die erfolgreichen
Main-Push-Prüfungen und automatische Veröffentlichung sind in
[#365](https://github.com/burckhju/trading-workspace/pull/365) nachgewiesen.

Der neue Nutzerbeleg vom PC zeigt einen davon getrennten Installationsabbruch:
Beim Backend-Imagebuild lief der Paketdownload von `files.pythonhosted.org` in
einen `ReadTimeoutError`; der parallele Frontend-Build wurde abgebrochen.
Die vier bisherigen v1.5.49-Container waren danach weiterhin gesund.
`prepared`, `apply-started`, `backups-verified`, `migration-started` und
`deployed` des neuen Versuchs fehlten. Der Checkout stand bereits auf dem
Zielrelease, während der vorherige Installationszustand und `pending` erhalten
blieben. Die anschließende V2-Vorbereitung wurde deshalb gesperrt; ein
erfolgreicher v1.5.50-PC-Betrieb oder eine V2-Depotabdeckung ist weiterhin nicht
belegt.

Der begrenzte [Wiederaufnahmeweg](../technical/LINUX_UPDATE_RECOVERY.md) schließt
diese operative Lücke mit einem separat zu qualifizierenden Supporthelfer:
vollständige Prüfung des unveränderten alten Zustands, reine Rückkehr des
Quellcheckouts, nachvollziehbarer Abschluss des vor Apply gescheiterten Versuchs
und erneuter Aufruf des unveränderten Launchers. Alte Belege bleiben erhalten;
Deploymentverträge, Runtimeversion, Regeln und Providerfreigaben werden dadurch
nicht geändert. Konkrete Tool-/CI-Qualifikation und tatsächliche PC-Ausführung
bleiben getrennte Nachweise. Der Gesamtarbeitsstatus und die fachlichen
Abdeckungsgrenzen oben bleiben bestehen.

### Zweiter Betriebsnachtrag 19.11.2026 — SQLAlchemy-Auflösung und Ersatzrelease

Der in [PR #366](https://github.com/burckhju/trading-workspace/pull/366)
qualifizierte Wiederanlauf wurde auf dem PC ausgeführt: Der ursprüngliche
Fehlversuch wurde kontrolliert abgeschlossen und der reguläre Launcher erneut
aufgerufen. Im neuen Versuch `20261119T115817Z-AJUxxu` scheiterte jedoch der
Backend-Build mit `No matching distribution found for SQLAlchemy==2.0.50`
und `from versions: none`. Die vier bisherigen v1.5.49-Dienste waren erneut
gesund; alle fünf Prepare-/Apply-/Migrationsmarker des neuen Versuchs fehlten.
Eine V2-Aktivierung oder erfolgreiche v1.5.50-Installation ist weiterhin nicht
beobachtet.

Die neun direkten Paketversionen existieren; die Anforderungen sind gegenüber
dem installierten v1.5.49 unverändert. Der erfolgreiche Main-Build von #366
installierte sie tatsächlich. Der PC verwendete einen anderen offiziellen
Python-3.12-Basisindex als CI. Weder diese Abweichung noch die leere
Kandidatenliste belegt einen inkompatiblen SQLAlchemy-Pin; die konkrete Ursache
der verworfenen Indexantwort bleibt unbelegt.

Der [Reparaturschnitt v1.5.51](../releases/V1.5.51-RELIABLE-BACKEND-BUILD.md)
bindet den Backend-Build an die geprüfte CI-Basis und SQLAlchemy 2.0.50 als
exaktes offizielles universelles Wheel mit SHA256. Begrenzte längere Abrufversuche
und eine vor den Anwendungsquellen liegende Abhängigkeitsschicht adressieren
die beiden beobachteten Beschaffungsfehler. Der neue Recovery-Einstieg prüft
den veröffentlichten Ersatzrelease vor dem unveränderten Abschluss des
fehlgeschlagenen alten Zielversuchs. Der normale Launcher bleibt für Build,
Sicherung, Migration und Zustandsabschluss zuständig.

Dieser Nachtrag erweitert keine fachliche Abdeckung. Regeln, gespeicherte
Käufe/Verkäufe, Providerfreigaben und Aktivierungsentscheidungen bleiben beim
bestehenden Owner. Die Liefernotiz bindet Quellen, Prüfgrenzen und den PC-Weg;
konkrete PR-/Main-/Publisherbelege sowie Tag/SHA werden im Release-PR geführt.
Die tatsächliche V2-Depotabdeckung bleibt bis zum beobachteten PC-Lauf offen.

### Dritter Betriebsnachtrag 19.11.2026 — belegte V2-Datumsursache und v1.5.52

Der neue Nutzerbeleg bestätigt eine erfolgreiche v1.5.51-Installation, aktive
V2 und abgeschlossene Prüfläufe ohne Laufzeitfehler. Die jüngste vollständige,
lesende Diagnose umfasst vier offene Positionen; alle vier melden weiterhin
Einstands- und Fristdatenprobleme. Der Readback erfasst alle offenen Positionen
und die unveränderte Zyklus-/Quellenlage vollständig. Eine tatsächliche
fachliche Vollabdeckung ist damit weiterhin nicht belegt.

Der Abgleich der bereits gespeicherten Originalbytes mit aktuellen und daran
gebundenen Produktbedingungen isoliert einen konkreten Implementierungsfehler:
Das vorhandene Fälligkeitsdatum entspricht dem Original-Zahlungstag, wurde aber
mit dem früheren Bewertungs-/Ausübungsende verglichen. Die
[Produkttermin-Reparatur v1.5.52](../releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md)
trennt die belegten Rollen und erhält erwartete beziehungsweise späteste
Zahlungstermine als eingeschränkt qualifizierte Fakten. Der lokale bekannte
Parserwechsel verwendet vorhandene Originale vor dem Netzwerk-Backoff und
bewahrt Quelle, ursprüngliche Abrufzeit und append-only Historie. Echte
Widersprüche bleiben Sperren; B17 verwendet weiterhin ausschließlich das
frühere belegte Produktende beziehungsweise den letzten Handelstag.

Die gespeicherten Kalenderfehler sind als HTTP 403 eingegrenzt. Ein kontrollierter
privater Import des exakten bereits qualifizierten 2026-Originals ergänzt den
vorhandenen Kalenderowner, ohne einen erfolgreichen Netzabruf oder zusätzliche
Kalenderjahre zu behaupten. Fremde Original-PDFs werden nicht veröffentlicht.

Implementierung, gezielte Regression, reguläre PR-Prüfungen, geschützte
Integration und automatische Veröffentlichung sind die eigenständigen
Liefernachweise dieses Schnitts. Deren konkrete Heads, Prüfläufe und Tag/SHA
werden im zugehörigen Release-PR geführt. Die anschließende PC-Ausführung muss
die tatsächlich wieder auswertbaren Positionen zeigen.

**Verbleibender fachlicher Auftrag:** Fehlende Kursrouten und Stückmaßstäbe,
eine tatsächlich falsche Basiswertidentität, persönliche Ausstiegswahl,
Originalbeleg des letzten Handelstags, weitere Kalenderabdeckung und
individueller Produktschluss bleiben gezielte Restarbeiten. Vorhandene
Buchungen werden wiederverwendet; technische Reparaturen dürfen diese offenen
Belege nicht durch Annahmen ersetzen. Geeignete Positionen werden unabhängig
von den übrigen Lücken ausgewertet. B58, restliches F207-2/B06 und vollständiges
F207-5 bleiben offen; B08 bleibt ausgeschlossen.


## Historischer nächster Umsetzungsschritt vom Oktober 2026

**Damals aktueller Liefernachtrag 28.10.2026 zu v1.5.31:** Nach dem freigegebenen und
erfolgten Merge von [PR #298](https://github.com/burckhju/trading-workspace/pull/298)
auf `271d2abbad076c867352297b96e29b6aa4b19092` ist die
[versionierte PC-Bereitstellung der historischen Währungsquellen](../releases/V1.5.31-HISTORICAL-EXECUTION-CURRENCY.md)
der nächste beauftragte Lieferschritt. Der Release ist bei Anlage dieses
Nachtrags noch nicht veröffentlicht; aktuelle Release-PR-, Main- und
Publisherprüfungen sowie der veröffentlichte Tag-/Commitbezug werden im
Release-PR belegt. Schema `20261028_0048` stammt bereits aus dem Feature und
führt keinen historischen Backfill aus. PC-Zugriff, Installation und produktive
Datenänderungen sind nicht beauftragt; reale Quellenabdeckung und vollständige
M8-Abnahme werden nicht aus dem Release abgeleitet.

**Historischer Liefernachtrag 28.10.2026 zu v1.5.30:** Der tatsächliche Abschluss des ausdrücklich
freigegebenen [v1.5.30-Releases des integrierten Währungsfixes](../releases/V1.5.30-POSITION-PNL-CURRENCY.md)
wird am zugehörigen Release-PR mit neuen PR-/Main-/Publisherbelegen und dem
veröffentlichten Tag-/Commitbezug geführt. Eine PC-Installation wird in diesem
Auftrag nicht ausgeführt. Anschließend bleiben reale Kaufbelege und beobachteter
Nutzerbetrieb gesondert zu belegen. Der folgende frühere 1.5.9-Schritt bleibt
als historischer Nachweis erhalten.

### Historischer nächster Schnitt für 1.5.9

**Nach der freigegebenen Bereitstellung Version 1.5.9 über den vorhandenen
PC-Launcher aktualisieren und den installierten Zustand lesend prüfen.**
Die [Release-Notiz](../releases/V1.5.9-REALIZED-GROSS-REPORT.md) beschreibt den
gepinnten Updateweg mit dem tatsächlich veröffentlichten Tag-Commit und Migration
0047. Die [Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
verbindet Quellen, Referenz/Korrektur, PostgreSQL-Rennen und den echten Browserweg.

Die Nutzeranweisungen „Ok, umsetzen“ und „wenn prüfungen grün mergen und für den pc
verfügbar machen“ liegen vor. Aktuelle PR-Prüfungen, normale geschützte Integration
und erfolgreiche main-Prüfungen vor der Tag-Erzeugung setzen diese Bedingung um.
PR #249 wird als eigener Integritätsfix vorgezogen; der Performance-Diff ändert
kein Basiswertformular. Die neue obligatorische Owner-Browserqualifikation liegt
zusätzlich im bestehenden End-to-End-Workflow und akzeptiert keinen Skip oder Retry.

Reale Nutzerbestände und ihre Währungsabdeckung wurden dabei nicht geprüft oder
verändert. Deren bewusste Bestätigung und die fachliche Beobachtung des installierten
Ergebnisses bleiben getrennt. Die durch #260/#261/#263 vorhandene Journal-/Lesson-/
Evidence-Strecke und sämtliche ursprünglichen M8-Restanforderungen bleiben in
ihren maßgeblichen Einträgen erhalten.

### Definition of Ready der ausgeführten Fortsetzung

[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
hält die ausdrückliche Umsetzungsfreigabe des konkreten Währungs-/Periodenvertrags
fest. Der vorhandene Average-Cost-Owner wurde wiederverwendet; der additive
Execution-Währungsowner wurde auf PostgreSQL separat qualifiziert. API und UI
verwenden ausschließlich bestätigte Quellen für monetäre Beiträge. Synthetische
EUR-Fixtures und Berichtswährung belegen weiterhin keine Währung alter Nutzerdaten.

### Definition of Done und erhaltene Restanforderungen

Der enge technische Lieferumfang umfasst vollständige SELL-Beiträge, belegte
Kostenbasis, explizite Berichtswährung, Summe/Teilsumme, Datenabdeckung und dieselbe
Quellenbasis innerhalb einer Antwort. Testbefunde und verbleibende Gate-/
Betriebsgrenzen sind im [Qualifikationsnachweis](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
konkret bezeichnet. Fertige Fachabnahme, Veröffentlichung und beobachteter Betrieb
bleiben eigenständig. Gewinner-/Verliererkohorten, Trefferquote, Durchschnitt/
Median, Profit-Faktor, Prozessbewertung, Diagramme und Export bleiben geplant;
Netto/FX/Equity/Drawdown und weitere Methoden benötigen eigene Verträge. Der
vorliegende Schnitt erklärt weder ursprüngliches M8 noch Bereich 7/8 als erledigt.

</details>
