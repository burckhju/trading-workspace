# Hebeltrader-Positionsmeldungen: Integrationsvertrag zu #207

## Zweck und Dokumentgrenze

Dieser Dokumentationsschnitt **F207-1** sichert die historischen Anforderungen aus
[#207](https://github.com/burckhju/trading-workspace/pull/207), ordnet sie dem
tatsächlichen Main-Code zu und trennt die verbleibenden Entwicklungsaufgaben.
Der Nutzer hat am 30.10.2026 die Erstellung dieses Dokumentations-Draft-PRs
beauftragt. Das ist der Umfang dieses Schnitts.

Die Arbeitsstatus-Felder im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#monitoring-rules) bleiben
maßgeblich. Die nachfolgenden Einordnungen sind commitgebundene Codebefunde und
Integrationsanforderungen zum Prüfdatum. F207-1 bis F207-5 sind lokale
Arbeitsreferenzen dieses Vertrags, keine neuen FT-/PB-Nummern und keine schon
angelegten GitHub-Issues.

Der Schnitt ändert Dokumentation und den zugehörigen Backlog-Verweis. Er führt
keine Regel aus, aktiviert keine Policy und ändert keine bestehenden
Phase-/Score-/Risiko-/Stopverträge. Die dokumentierten historischen Bestätigungen
bleiben erhalten; eine neue Handelsregel, ein produktiver Geltungsbeginn oder
eine Merge-, Installations- oder Providerfreigabe entsteht hieraus nicht.

## 1. Prüfstand und Herkunft

| Gegenstand | Gebundener Nachweis | Aussagegrenze |
| --- | --- | --- |
| Main am 30.10.2026 | `46cb2693e38751ca330074e8606142d0c5e9d24b`, Tree `4594723482e24b81d4abb55107bced0f1f3af429` | Quellstand dieses Abgleichs; kein Nachweis einer Installation auf dem Nutzer-PC. |
| Veröffentlichung | `VERSION` 1.5.34, Tag `v1.5.34` auf demselben Commit | Softwareveröffentlichung ist von fachlicher und betrieblicher Abnahme getrennt. |
| Tatsächlicher #207-Head | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Vollständiger Diff: eine neue `.github/workflows/hebeltrader-baseline.yml` mit 40 Zeilen, ausschließlich ein Entwicklungs-Exportworkflow. |
| Historischer Katalog | Git-Blob `2df37e7ba2a2aa4734412aebec9dee419002da73` im vorbereiteten Tree `33ab5cea93e2da2466a20050b59d23e2c087a153` | Vollständig lesbare Anforderungsquelle; kein Implementierungscommit im PR oder Main. |
| Historische Datenverträge | Git-Blob `a6b272e06a7fbda58262b149559835ec8dea0984` aus demselben Teilbaum | Hilfreicher Entwurf für Evidenz-/Kalendersemantik; keine heute implementierte oder unverändert zu übernehmende API. |
| Später beschriebenes Gesamtpaket | Lokaler Baum `033f825831ae3d4fde0c2e3482cb0fe294d30f2f` laut PR-Berichten | Beim Abgleich nicht als Commit/Tree lesbar. Ein vollständiges 62-Dateien-Paket oder dessen Qualifikation wird hier nicht behauptet. |
| #187 | `bad00a420f56994216ad1def6a580b00b0f5772f`, offener Draft | Eigenständige Einstiegsvorschau/Rekonstruktion; kein Main-Bestandteil. |
| #197 | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8`, offener Draft | Eigenständige historische Datenerhebung/Forschung; keine Live-Regelfreigabe. |

Der [historische Quellenkommentar][historical-comment], der
[Katalogblob][historical-catalog], der [Vertragsblob][historical-contracts] und
der [tatsächliche Helper am #207-Head][pr207-helper] sind getrennte Quellen.
Der Katalog nennt `HEBELTRADER_CONFIRMED_BASELINE`, Version `1.0.0`, und
`approved_at = 2026-09-14T04:53:07+00:00`. Diese Angaben werden als historische
Metadaten übernommen. Die 58 Originaleinträge bestehen aus **57 als CONFIRMED
gekennzeichneten Regeln und dem ausdrücklich ausgeschlossenen B08**.

Die Solltexte in Abschnitt 4 sind vollständig aus dem Katalog übernommen. Titel,
Regeltext und Status wurden gegen den gelesenen Git-Blob geprüft. Eigene heutige
Einordnung und Restarbeit stehen in getrennten Spalten; sie ersetzen den
historischen Wortlaut nicht. Private Forschungsdateien, Depotdaten und frühere
Gesprächsanhänge sind keine Quellen dieses Dokuments.

Die historische Herkunftskategorie lautet für B01–B08
`USER_CONFIRMED_PUBLISHER_DERIVED`, für B09–B58
`USER_CONFIRMED_IMPLEMENTATION`. Das Quellenlabel lautet „Individuelle
Nutzerbestätigungen 13./14. September 2026; jüngste Änderungen maßgeblich“.
Der Katalog dokumentiert außerdem `scope = ALL_POSITIONS`,
`mode = NOTIFICATIONS_ONLY`, `automatic_orders = false`,
`automatic_quantities = false`, `historical_entry_max_age_seconds = null`
und `held_bid_max_age_seconds = 900`. Diese Metadaten beschreiben den
historischen Sollvertrag, keine aktuelle technische Unterstützung jeder
Instrumentart oder neue Aktivierung.

## 2. Vorhandene Funktionen und zuständige Owner

### Operative Diagnose bleibt eigenständig

#303/#307 haben im geprüften Main Fehlerfolgen, Quellenidentität, qualifizierten
letzten Erfolg, Recovery, laufenden Versuch und Schedulerzustände integriert.
[Refreshdiagnostik][refresh-diagnostics] und
[Kursqualifikation][refresh-quality] unterscheiden Schedulerabschluss, erhaltenen
Altkurs, unklare Originalzeit, lokale Wartephase und tatsächlichen Providerfehler.
Die Fehlerzähler sind ausdrücklich prozesslokal; gespeicherte Kurse und
Historienbelege haben einen anderen Lebenszyklus.

Diese Diagnose ist keine Umsetzung der Hebeltrader-Positionsregeln. Der
Historienlesepfad aus #302/#306 und die gettex-Korrekturen aus #305 werden
ebenfalls weiterverwendet; F207-1 erzeugt dafür keine zweite Implementierung.

### Bestehende fachliche Bausteine

| Owner / vorhandener Vertrag | Wiederzuverwenden | Zusätzlicher Baseline-Bezug |
| --- | --- | --- |
| Trade Position / FT-009/010 | Effektive Ausführungen, Korrekturketten, Restmenge, Gross-Kostenbasis, gewichteter Einstand, frühester Kaufbeginn und Positionsschluss; [Projektor][position-projector], [Bewertungsbasis][valuation-basis] | Ursprünglicher Einstiegsauftrag, belegter Basiswertkurs zum Optionsscheinkauf, ursprüngliche Z1-Bezugsmenge und ausdrücklich zugeordnete Z1-Verkäufe. Diese Bezüge ändern die Ausführungen nicht. |
| Trade Management | Historische Stop-/Zieländerungen mit Gültigkeit und ausdrücklicher [Instrument-/Währungsbindung][price-binding] | Baseline-Schutzvorschlag mit Bekanntgabezeit und eigener Überwachung; keine automatische Management- oder Brokerstopänderung. |
| Market Data / Product | Qualifizierte Datenreader, getrennte Produkt-/Basiswertidentität, versionierte Produktbedingungen, vorhandene Laufzeit- und Risikoevidenz | Regelabhängige Eignung, verifizierter letzter Handelstag, Kalenderabdeckung und originale Kurszeit; ein vorhandener Wert ist nicht für jede Regel geeignet. |
| Position Monitoring | Gebundene STOP/TARGET-Auswertung, persistierter Regelzustand, Versions-/Provenienzprüfungen | Dauerhafte Z1/Z2-Ereignisse, dokumentierte Schutzmarken, Verlust-/Fristepisoden und vollständiger Baseline-Nachweis. |
| Alert / Notification | Bestehende Alert-Persistenz, Deduplizierung, getrennte Outbox und Zustellversuche mit Wiederanlauf | Mehrregelmeldung sowie gesehen/abgelehnt/ausgeführt als unterschiedliche Tatsachen; Schließungsgrenze und typgerechte Legacy-Behandlung. |

Der wirtschaftliche Rechenkern bleibt beim vorhandenen Trade-Owner. B10, B13,
B26 sowie Teile von B27 und B51–B53 begründen keinen neuen Bestands- oder
Einstandsrechner. Eine Regelmeldung, ein Zieltreffer oder ein quittierter Vorschlag
ist keine tatsächliche Ausführung.

Die [Phase][phase-policy], der [Score][score-policy] und der
[dynamische Stop][stop-policy] sind eigene lesende V1-Projektionen.
`DYNAMIC_STOP_V1` berechnet einen ATR-basierten Kandidaten neu. Das ist kein
persistierter, seit Bekanntgabe monotoner Baseline-Schutzstop. Der Unterschied
ist kein Defekt dieses bestehenden Vertrags. Eine spätere Kombination benötigt
einen ausdrücklichen Policybezug, Datenvertrag und bei geänderter Semantik eine
eigene Version; bestehende Schwellen werden nicht still verändert.

## 3. Abgrenzung zu #187, #197 und bestehenden Preisregeln

### #187: Einstiegsvorschau und Meldungsbaseline

Die neuere [Eingabepolicy von #187][pr187-input] ersetzt dessen alten manuellen
Band-/Puffer-Workflow. Bestätigte Import-/Quellenversionen liefern die Marken;
unbekannte B-Formeln, IV, Kalender oder Kursdaten werden nicht durch versteckte
Annahmen oder zusätzliche Schätzfelder ersetzt. Eine spätere Wiederverwendung
behält diese Grenze bei.

**B07** ist eine Einstiegsprüfung und bleibt dem separaten #187 zugeordnet.
Genau 2 % besteht nur diese Teilprüfung. Daraus folgt weder eine allgemeine
Einstiegsfreigabe noch eine laufende Ausstiegsregel.

**B08 bleibt ausgeschlossen.** Die späte 0,5-Allokation in
[`assess_entry()` von #187][pr187-entry] gehört zur unabhängigen rekonstruierten
Einstiegsvorschau. Sie wird nicht unter der Baseline-ID übernommen und in diesem
Dokumentationsschnitt nicht geändert. Aus dem Ausschluss entsteht auch kein
zusätzliches Einstiegsverbot oder Freigabesignal. Das ist eine ausdrücklich zu
erhaltende Scopegrenze, kein aktueller Konflikt zweier laufender Main-Regeln.

**B11 unterscheidet Treffer und Ausführung.** Ein belegter Z1-Treffer löst die
Prüfung einer Einstandsschutzmeldung aus; eine spätere Verkaufsausführung ist
dafür keine Voraussetzung. Der [Management-Preview von #187][pr187-management]
verwendet dagegen `target1_completed_on` und `stop_after_confirmed_fill`.
Diese Preview-Semantik bleibt eigenständig. Bei späterer Wiederverwendung dürfen
Trefferzeit, Bekanntgabezeit und Ausführungszeit nicht gleichgesetzt werden.
Beide Bereiche lassen reale Restmengen und Brokerstopps bis zu ihren eigenen
belegten Nutzer-/Ausführungsereignissen unangetastet.

### #197: historische Forschung

Der [Collector][pr197-collector] und der
[isolierte Forschungsworkflow][pr197-workflow] liefern historische Rohdaten mit
expliziten Vollständigkeits- und Qualitätsgrenzen. Sie sind kein produktiver
Kalender-, Historien- oder Regelprovider. Die
[Forschungsannahmen][pr197-research], unter anderem 25%-Z1-Realisierung und
Peak-Protection, werden nicht als bestätigte Baseline übernommen. Forschung kann
eine spätere versionierte Entscheidung begründen; sie aktiviert keine Policy.
#187 und #197 bleiben als eigenständige PRs erhalten.

### Instrument, Zeit und Sitzung sind regelabhängige Belege

Die bestehende [Preisbindung][price-binding] und der
[Regelpreisresolver][rule-prices] bleiben maßgeblich. Ein Optionsscheinpreis ist
kein Basiswert-Einstieg; gleiche Währung allein beweist keine gleiche Preisachse.
Ein abgeschlossenes Tageshoch/-tief beweist keine Intraday-Reihenfolge.

Die heute zulässigen markierten Emittentenindikationen können unter ihrem
bestehenden Vertrag eine frische Empfangszeit bei unbekannter Originalzeit
besitzen. Für B04/B58 reicht das nicht: benötigt werden ein geeigneter Geldkurs
des gehaltenen Instruments, belegte Originalzeit, Alter höchstens 900 Sekunden,
verifizierte offene Sitzung und die bereits zum Kurszeitpunkt erreichte
20-Sitzungsgrenze. Last, Close, Brief oder Mittelwert ersetzen keinen Geldkurs.
Ein gespeicherter BID kann geeignet sein, wenn er alle Originalzeit-, Alters-,
Sitzungs- und Qualitätsanforderungen erfüllt. Retention allein beweist diese
Eignung nicht; eine aktuelle Abrufzeit verjüngt keinen gespeicherten Kurs.
Vorhandene generische Indikationsregeln behalten ihren bisherigen Vertrag.

Die historische Nennung von Aktien und Optionsscheinen beweist keinen
vollständigen aktuellen Ownervertrag für jede Instrumentart. Unterstützt wird
eine Regel nur innerhalb des tatsächlich belegten Instrument-/Ownerpfads;
fehlende Unterstützung bleibt explizit und begründet.

## 4. Vollständige Anforderungszuordnung B01–B58

**Leseschlüssel:** „Vorhandener Baustein“ bezeichnet Code, der wiederverwendet
werden muss; „Teillücke“ den zusätzlich zu belegenden oder zu implementierenden
Baseline-Vertrag. „Fachlich extern“ bleibt im genannten unabhängigen Vorhaben.
„Ausgeschlossen“ ist keine Implementierungsaufgabe. Die Einordnung sagt nichts
über eine neue Fachabnahme oder die Installation auf dem Nutzer-PC aus.

Die Originalspalte enthält Titel, vollständigen Solltext und historischen Status.
Die Belegverweise zeigen auf die jeweils ausdrücklich gebundene Main-/PR-Version
oder auf das historische Git-Objekt. Ein Testpfad bezeichnet vorhandene
Regressionsevidenz, keinen in diesem Dokumentationsschnitt neu ausgeführten Test.

### B01–B13 — Kernregeln, Grenzen und Ausführungswahrheit

| Regel / historischer Status | Vollständiger Original-Solltext | Vorhandener Main-Baustein / Scope | Restarbeit und Folgeschnitt | Belege |
| --- | --- | --- | --- | --- |
| **B01 — 50%-Orientierung an Z1**<br>CONFIRMED | Teilverkaufsmeldung mit 50 % der ursprünglichen Einstiegsmenge; keine automatische Verkaufsmenge. | Teillücke: allgemeine TARGET-Erkennung und echte Ausführungsmenge vorhanden; spezifische einmalige Z1-Orientierung nicht im betrachteten Main-Monitoringpfad. | Belegten Z1-Treffer mit unveränderlicher ursprünglicher Einstiegsmenge verknüpfen; 50 % nur als Orientierung melden, ausgeführte zugeordnete Z1-Verkäufe anrechnen, niemals eine Verkaufsbuchung oder gerundete Ordermenge erzeugen.<br>[F207-2](#f207-2); [F207-4](#f207-4) | [M01][M01], [M02][M02], [M08][M08], [M09][M09] |
| **B02 — Einstandsschutz nach Z1**<br>CONFIRMED | Stopanhebung auf persönlichen Basiswert-Einstieg melden; höheres dokumentiertes Stopniveau erhalten. | Teillücke: gebundene Managementstopps und lesende dynamische Stoppprojektion vorhanden; diese implementieren nicht automatisch den persönlichen Basiswert-Einstandsschutz. | Ab belegtem Z1-Treffer einen gekennzeichneten Schutzvorschlag auf korrekter Basiswertachse ableiten; höheres dokumentiertes Schutzniveau erhalten. Vorschlag und tatsächlichen Brokerstop getrennt halten.<br>[F207-2](#f207-2); [F207-4](#f207-4) | [M02][M02], [M04][M04], [M14][M14], [M07][M07], [M10][M10] |
| **B03 — Z2-Restausstiegsprüfung**<br>CONFIRMED | Vollständigen Restausstieg an Z2 prüfen; kein zwingender Verkauf. | Teillücke: CURRENT_TARGET ist vorhanden; Planfallback liest sequence == 1. Vollständige eigenständige Z2-Restausstiegsprüfung ist dadurch nicht belegt. | Z2 auf derselben belegten Preisachse aus versionierter Quelle lesen und als Restausstiegsprüfung melden; tatsächliche Restmenge aus Ausführungsowner lesen. Keine verpflichtende Ausführung.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M01][M01], [M08][M08], [M09][M09] |
| **B04 — Verlust ab 20 Handelstagen**<br>CONFIRMED | Ab mindestens 20 abgeschlossenen Basiswertsitzungen vollständigen Restausstieg bei Kurs unter Einstieg melden; nicht auf Vor-Z1 beschränkt. | Teillücke: Preisbindung, gross-Einstand und Kursqualifikation vorhanden; die Kombination aus 20 verifizierten Basiswertsitzungen, gehaltenem Geldkurs und Verlustmeldung ist im betrachteten Main-Regelpfad nicht implementiert. | Frist anhand verifiziertem Basiswertkalender und Ausführungsbeginn bewerten; geeigneten Geldkurs des gehaltenen Instruments gegen qualifizierten persönlichen Einstand prüfen, unabhängig von Z1. B25/B57/B58 mitführen.<br>[F207-3](#f207-3); [F207-4](#f207-4) | [M03][M03], [M04][M04], [M06][M06], [M08][M08], [M10][M10] |
| **B05 — Laufzeitpuffer**<br>CONFIRMED | Bei befristeten Derivaten vollständigen Restausstieg spätestens 20 Produkthandelstage vor dem maßgeblichen Produkttermin vorsehen. | Teillücke: versionierte Produktbedingungen, maturity und evidenzbasiertes expiry_at vorhanden. Ein daran gebundener 20-Produktsitzungen-Ausstiegsvertrag fehlt im betrachteten Monitoringpfad. | Verifizierten Produktausstiegshandelsplatz, Kalender und maßgeblichen Termin nach B16–B20 verbinden; Fristmeldung unabhängig von aktueller Kurserreichbarkeit berechnen. Fehlende Belege als nicht beurteilbar ausweisen.<br>[F207-3](#f207-3) | [M12][M12], [M13][M13], [M01][M01] |
| **B06 — 80%-Z1-Folgestop**<br>CONFIRMED | Spätestens 20 Basiswertsitzungen nach Z1 max(bisherigem Schutzniveau, persönlichem Basiswert-Einstieg, 0,8 × ursprünglichem Z1) vorschlagen. | Teillücke: DYNAMIC_STOP_V1 existiert als eigene ATR-/Phase-/Score-Projektion; es ist nicht die 20-Sitzungen-/80%-Z1-Regel. | Ab dauerhaft belegtem Z1-Ereignis die Basiswertsitzungen zählen; max aus bisherigem Schutzniveau, persönlichem Basiswert-Einstieg und 0,8 × ursprünglichem Z1 als Vorschlag bilden. Eigene bestehende ATR-Policy nicht still ersetzen.<br>[F207-2](#f207-2); [F207-3](#f207-3); [F207-4](#f207-4) | [M06][M06], [M14][M14], [M07][M07], [M04][M04] |
| **B07 — 2%-Einstiegsabstand**<br>CONFIRMED | Bei weniger als 2 % Basiswert-Stopdistanz keinen Neueinstieg vorsehen; genau 2 % besteht nur diese Prüfung. Kein Ausstiegssignal. | Fachlich extern: Einstiegsprüfung gehört #187. Dessen aktueller Entwurf enthält MIN_STOCK_STOP_DISTANCE = 0.02 und eine < -Prüfung; nicht als in Main integriertes #207-Feature ausweisen. | Im separaten #187 die Quell-/Preisachse und Grenzfälle < 2 %, = 2 %, > 2 % erhalten/qualifizieren. Genau 2 % besteht ausschließlich diese Teilprüfung, keine pauschale Einstiegsfreigabe; kein Positionsausstieg daraus.<br>[#187](https://github.com/burckhju/trading-workspace/pull/187); [F207-1](#f207-1) | [P187E][P187E] |
| **B08 — Nicht aufgenommen**<br>EXCLUDED | Keine Halbierung eines späten Neueinstiegs nach erreichtem Z1; daraus kein zusätzliches Verbot oder Freigabesignal ableiten. | Ausgeschlossen: historischer Katalogstatus EXCLUDED, auch definition().excluded nennt B08. #187 enthält gleichzeitig eine gesonderte late-entry-Halbierungslogik; unterschiedliche Policies nicht vereinheitlichen. | Ausschluss unverändert dokumentieren. Vor gemeinsamer fachlicher Abnahme den Geltungsbereich gegenüber #187 ausdrücklich klären. Keine Halbierung, kein zusätzliches Verbot und keine Freigabe aus B08 in F207-2–5 übernehmen.<br>[F207-1](#f207-1); [#187](https://github.com/burckhju/trading-workspace/pull/187) | [H01][H01], [P187E][P187E] |
| **B09 — Zielhistorie**<br>CONFIRMED | Belegte Z1-/Z2-Treffer und Ereigniszeiten erhalten; Kursrückgänge löschen sie nicht. | Teillücke: persistierter generischer Regel-/Alertzustand vorhanden; ein unterschrittener Zielschwellwert kann den aktuellen Alarm auflösen. Das ist kein Nachweis einer dauerhaften Z1-/Z2-Ereigniswahrheit. | Belegte Zieltreffer mit Ereignis-/Feststellungszeit und Quellenversion dauerhaft halten; spätere Rückgänge dürfen die Trefferhistorie nicht löschen. Korrektur als neue Evidenz behandeln.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M02][M02], [M01][M01], [M11][M11] |
| **B10 — Ausführung bleibt Wahrheit**<br>CONFIRMED | Nur tatsächlich belegte Ausführungen verändern die echte Restmenge. | Vorhandener Baustein / bestehende Autorität: PositionProjector bildet offene Menge ausschließlich aus effektiven BUY-/SELL-Ausführungen. Monitoringservice schreibt Regelzustand/Alerts, keine PositionProjector-Ausführung. | Bestehenden Ausführungsowner unverändert verwenden. Baseline-Meldung, Quittierung oder Vorschlag dürfen keine echte Restmenge verändern; diese Nichtmutation später mit Integrationsregression absichern. Kein zweiter Bestandsrechner.<br>[F207-4](#f207-4); [F207-5](#f207-5) | [M08][M08], [M09][M09], [M16][M16], [M02][M02], [T02][T02] |
| **B11 — Stopmeldung beim Z1-Treffer**<br>CONFIRMED | Einstandsschutz bereits beim belegten Zieltreffer prüfen, nicht erst nach Teilverkauf. | Teillücke: Target-Alert bereits beim passenden Kurs vorhanden, aber keine gekoppelte persönliche Einstandsschutzmeldung. Separater #187-Managemententwurf koppelt `proposed_stop` an `target1_completed_on` (bestätigter Halbverkauf oder dokumentierter später Einstieg); `stop_after_confirmed_fill` ist separat. Dies ist fachlich abzugrenzen. | Schutzprüfung an belegten Z1-Treffer knüpfen, nicht an die SELL-Buchung. Meldung bleibt ein Vorschlag; weder Brokerstop noch verpflichtende Stopübernahme. Unterschied zu #187 vor gemeinsamer Abnahme explizit festhalten.<br>[F207-2](#f207-2); [F207-1](#f207-1); [#187](https://github.com/burckhju/trading-workspace/pull/187) | [M01][M01], [M02][M02], [M07][M07], [P187M][P187M] |
| **B12 — Persönlicher Einstiegsbezug**<br>CONFIRMED | Aktien-Ausführungspreis bzw. gesondert belegter Basiswertkurs zum Optionsscheinkauf; niemals Optionsscheinpreis als Basiswert-Stop. | Vorhandener Baustein plus Evidenzlücke: PriceBinding/Resolver unterscheiden WARRANT und UNDERLYING samt Instrument und Währung; Ausführungsowner enthält den Preis des tatsächlich gehaltenen Produkts. Ein gesondert belegter Basiswertkurs zum Optionsscheinkauf ist dadurch nicht geliefert. | Für Basiswertmarken nur passende persönliche Basiswertevidenz verwenden; beim Optionsschein nicht dessen Kaufpreis umdeuten. Historischen Basiswertbezug an effektive Ausführungen binden. Nicht pauschal behaupten, Main unterstütze bereits alle Aktienpositionsfälle.<br>[F207-4](#f207-4) | [M03][M03], [M04][M04], [T01][T01], [M09][M09], [M10][M10] |
| **B13 — Tatsächlicher Beginn**<br>CONFIRMED | Früheste gültige BUY-Ausführung bestimmt den Beginn, nicht Erfassung oder Freigabe; Teilverkauf startet nicht neu. | Vorhandener Baustein: PositionProjector setzt opened_at beim ersten BUY und ändert es beim SELL nicht; PositionAwareAnalyticsService sucht früheste nicht supersedierte BUY-Ausführung. | Dieselben effektiven Ownerfakten für Baselinebeginn wiederverwenden, nicht Erfassungs-/Freigabezeit. Datum-ohne-Uhrzeit-Präzision erhalten; spätere Teilverkäufe und Nachkäufe dürfen den Beginn nicht neu setzen.<br>[F207-4](#f207-4); [F207-3](#f207-3) | [M08][M08], [M09][M09], [M06][M06], [T02][T02] |

### B14–B26 — Sitzungen, Fristen und Preisnachweise

| Regel / historischer Status | Vollständiger Original-Solltext | Vorhandener Main-Baustein / Scope | Restarbeit und Folgeschnitt | Belege |
| --- | --- | --- | --- | --- |
| **B14 — Starttag null**<br>CONFIRMED | Kauf-/Z1-Tag = 0; nur danach vollständig abgeschlossene Sitzungen zählen. | Teilweise vorhanden: highest_high_since_entry schließt Kaufdatum und Auswertungsdatum konservativ aus. Es zählt aber geeignete vorhandene Tageszeilen, nicht alle verifizierten abgeschlossenen Sitzungen; Z1-Zeitbasis fehlt dort. | Starttag null für Kauf und Z1 explizit anwenden; Abschlusszeit und Zeitzone des zugeordneten Kalenders beachten. Nicht len(OHLC-Zeilen) als bewiesene Sitzungszahl übernehmen.<br>[F207-3](#f207-3) | [M06][M06], [H02][H02] |
| **B15 — Basiswertkalender**<br>CONFIRMED | B04/B06 verwenden den fest zugeordneten Basiswertkalender einschließlich Zeitzone; fehlende Kerzen sind keine Feiertage. | Teillücke: primäres Basiswertlisting und Tagesdaten sind vorhanden; der betrachtete Analytics-Reader liefert keinen vollständigen verifizierten Sitzungskalender. | Festes Basiswertlisting, Handelsplatz und Zeitzone samt explizitem Kalenderdeckungsbereich binden; Kurslücke von Nicht-Handelstag unterscheiden. Ungeklärte Kalenderabdeckung blockiert nur B04/B06.<br>[F207-3](#f207-3) | [M01][M01], [M06][M06], [H02][H02] |
| **B16 — Produktkalender**<br>CONFIRMED | B05 verwendet den verifizierten Kalender des fest zugeordneten Produkt-Ausstiegs-Handelsplatzes. | Teillücke: WarrantListing besitzt trading_venue_id und Währung; das allein belegt keinen vollständigen Produkt-Ausstiegskalender und keine dauerhafte Zuordnung für B05. | Verifizierten Kalender des ausdrücklich zugeordneten Produktausstiegshandelsplatzes lesen; Zuordnung und Versions-/Quellenevidenz erhalten. Basiswertkalender nicht ersatzweise für Produktfrist verwenden.<br>[F207-3](#f207-3) | [M13][M13], [H02][H02] |
| **B17 — Früherer Produkttermin**<br>CONFIRMED | min(verifiziertem Laufzeitende, letztem Handelstag); keinen Auszahlungstag substituieren. | Vorhandene Produktbausteine plus Teillücke: WarrantTermsVersion.maturity_date und RiskProductReference.maturity/expiry_at samt Evidenz existieren; im geprüften RiskProductReference fehlt ein verifizierter letzter Handelstag. | Bestehende versionierte Produktbelege wiederverwenden und benötigten Nachweis zum letzten Handelstag ergänzen; den früheren relevanten Termin wählen. Unbekanntes nicht durch Auszahlungstag oder bloße Annahmen auffüllen.<br>[F207-3](#f207-3) | [M12][M12], [M13][M13], [M18][M18] |
| **B18 — Rückwärtszählung**<br>CONFIRMED | Produkttermin ausschließen; 20. vorherige Produkthandelssitzung ist letzter vorgesehener Ausstiegstag. | Teillücke: Produkttermine existieren; eine geprüfte rückwärtszählende B05-Sitzungsfrist ist im betrachteten aktuellen Monitoringpfad nicht belegt. | Den Produkttermin aus der Zählung ausschließen und die 20. vorherige verifizierte Produktsitzung als Fristtag bestimmen; explizite Kalenderabdeckung und Nicht-Sitzungstage testen.<br>[F207-3](#f207-3) | [M12][M12], [M13][M13], [H02][H02], [M01][M01] |
| **B19 — Vorwarnung**<br>CONFIRMED | Spätestens beim Beginn der Sitzung vor dem Ausstiegstag melden; verspätete Feststellung verschiebt die Frist nicht. | Teillücke: Scheduler- und Monitoringlaufzeiten sind vorhanden, aber kein Beweis einer fachlichen Vorwarnung beim Beginn der Sitzung vor dem ermittelten Produktfristtag. | Vorwarnzeitpunkt aus demselben verifizierten Produktkalender ableiten; bei verspätetem Wiederanlauf Ereignis-/Feststellungszeit trennen und ursprüngliche Frist unverändert lassen.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [H02][H02], [M19][M19] |
| **B20 — Handelsschlussgrenze**<br>CONFIRMED | Vollständige Ausführung vor verifiziertem instrumentbezogenem Schluss am Fristtag vorsehen; offene Order ist keine Ausführung. | Vorhandener Ausführungsbaustein plus Fristlücke: echte Ausführungen bestimmen den Restbestand; eine Order ist keine ExecutionRecord. Ein verifizierter instrumentbezogener Handelsschluss für B05 ist damit nicht vorhanden. | Schlusszeit des relevanten Produkts am Fristtag nachweisen und verbleibende echte Restmenge dagegen prüfen; offene Order/Bestätigung nicht als Ausführung werten. Nur Meldung, keine Ordererzeugung.<br>[F207-3](#f207-3); [F207-4](#f207-4) | [M08][M08], [M09][M09], [M16][M16], [M13][M13], [H02][H02] |
| **B21 — Zielnachweis**<br>CONFIRMED | Abgeschlossene Hoch-Kursdaten nach eigenem Einstieg genügen; bei unklarer Kauf-Tagesreihenfolge keinen Treffer erfinden. | Vorhandener Baustein plus Teillücke: rule_prices nutzt abgeschlossene Tageshochs für gebundene Basiswertziele; position_analytics schließt den gesamten Kauftag konservativ aus. Das beweist keine vollständige Z1-/Z2-Zielhistorie nach persönlichem Einstieg. | Nur belegte vollständig abgeschlossene Intervalle nach persönlichem Einstieg für Zielnachweise nutzen; bei unklarer Reihenfolge am Kauftag keinen Treffer erfinden. Grobe Tagesdaten nicht in künstliche Intradayzeiten auflösen.<br>[F207-2](#f207-2); [F207-4](#f207-4) | [M04][M04], [T01][T01], [M06][M06], [M02][M02] |
| **B22 — Stopnachweis**<br>CONFIRMED | Tief ≤ zeitlich gültigem dokumentiertem Basiswert-Stop löst Prüfung aus; Erholung hebt Berührung nicht auf; keine Rückwirkung. | Vorhandener Baustein plus Teillücke: gebundene STOP-Regeln verwenden Basiswert-Tief und Managementevents haben effective_at. Dauerhafte Berührungswahrheit und vollständige Intervall-/Gültigkeitsabgrenzung sind dadurch nicht belegt. | Historische Tiefintervalle gegen den damals gültigen dokumentierten Basiswertstop prüfen, Berührung trotz späterer Erholung erhalten und keine jüngere Stopmarke rückwirkend anwenden. Bestehenden generischen Stopppfad nicht still umdeuten.<br>[F207-2](#f207-2) | [M03][M03], [M04][M04], [T01][T01], [M07][M07], [M09][M09], [M02][M02] |
| **B23 — Reihenfolge ungeklärt**<br>CONFIRMED | Stop-/Zielkonflikt ohne feine Daten nicht zeitlich auflösen; Restausstiegsprüfung priorisieren. | Teillücke: heutiger Preisregelpfad kann STOP und TARGET separat prüfen; sein Daily-Low/High-Vertrag beweist keine Intradayreihenfolge und keine Baseline-Konfliktpriorisierung. | Gleichzeitige belegte Stop-/Zielbefunde gemeinsam halten; bei fehlenden feineren Daten Reihenfolge als ungeklärt kennzeichnen und Restausstiegsprüfung priorisiert darstellen, ohne Ausführung zu erfinden.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M01][M01], [M03][M03], [M04][M04], [M15][M15] |
| **B24 — Gehaltenes Instrument**<br>CONFIRMED | Verlustregel vergleicht gehaltenen Aktien-/Optionsscheinpreis mit dessen persönlichem Kaufkurs. | Vorhandener Baustein plus Regelteillücke: Instrument-/Währungsbindung und qualifizierter Einstand des gehaltenen Produkts existieren. Das ersetzt keine eigenständige B04-Verlustprüfung. | Geeigneten Kurs des tatsächlich gehaltenen Instruments gegen dessen persönlichen, währungsqualifizierten Einstand vergleichen; Basiswertkurse nicht gegen Optionsschein-Einstand rechnen. Andere Instrumentarten nur innerhalb ihres belegten Ownervertrags bewerten.<br>[F207-3](#f207-3); [F207-4](#f207-4) | [M04][M04], [T01][T01], [M08][M08], [M10][M10] |
| **B25 — Geldkurs**<br>CONFIRMED | Nur geeigneten Geldkurs für B04; keine Brief-/Mittel-/Letzter-Kurs-Substitution. | Teillücke für B04: aktuelle generische Monitoringregeln erlauben ausdrücklich gekennzeichnete Referenz-/Indikationskurse; der existierende LAST_TRADE-Test belegt diese beabsichtigte andere Semantik. | Für die neue B04-Prüfung zusätzlich strikt einen geeigneten BID verlangen; vorhandene andersartige Referenzen nicht als Geldkurs umetikettieren. Echte Originalzeit, Sitzung und Alter nach B58 prüfen; aktuelle allgemeine Indikationsregeln erhalten.<br>[F207-3](#f207-3) | [M04][M04], [T01][T01] |
| **B26 — Ohne Gebühren**<br>CONFIRMED | Kursverlustschwelle ohne Gebühren; Netto-Ergebnis getrennt. | Vorhandener Baustein: ExecutionRecord.gross_amount und PositionProjector rechnen Kurskosten/-ergebnis ohne Gebühren. Das ist ausdrücklich keine Behauptung, ein vollständiges Nettoergebnis sei damit implementiert. | Gross-Preis-/Einstandsbasis für B04 verwenden und Gebühren/Nettoauswertung semantisch getrennt halten; keine zusätzliche Gebühren-Schwelle oder Neuberechnung des bestehenden Projektors.<br>[F207-4](#f207-4); [F207-3](#f207-3) | [M08][M08], [M09][M09], [M10][M10], [T02][T02] |

### B27–B39 — Evidenz, Meldungen und Geltung

| Regel / historischer Status | Vollständiger Original-Solltext | Vorhandener Main-Baustein / Scope | Restarbeit und Folgeschnitt | Belege |
| --- | --- | --- | --- | --- |
| **B27 — Teilausführungen**<br>CONFIRMED | Kaufkurs desselben Einstiegsauftrags mit tatsächlich ausgeführten Stückzahlen gewichten. | Vorhandener Rechenkern plus Zuordnungslücke: PositionProjector gewichtet echte BUYs mit Stückzahlen. ExecutionRecord besitzt in diesem Vertrag keine eigene ursprüngliche Einstiegsauftragsgruppe; Gewichtung aller offenen Käufe beweist deshalb nicht die B27-Gruppierung. | Bestehende Mengen-/Preisfakten und Gewichtungsarithmetik verwenden; zusätzlich den belegten Umfang desselben ursprünglichen Einstiegsauftrags identifizieren. Keine künstliche Ordergruppierung aus Uhrzeitnähe oder kompletter Tradehistorie ableiten.<br>[F207-4](#f207-4) | [M08][M08], [M09][M09], [M10][M10], [T02][T02] |
| **B28 — Basiswertgewichtung**<br>CONFIRMED | Basiswert-Einstieg bei Optionsschein-Teilausführungen mit Produktstückzahlen gewichten; fehlende Werte nicht auslassen. | Teillücke: Produkt-Ausführungsmengen und Währungsevidenz vorhanden; ein historischer Basiswertkurs je Optionsschein-Teilausführung ist im Ausführungsvertrag nicht mit enthalten. | Passende belegte Basiswertbeobachtung je effektiver Produkteinstandsausführung verknüpfen und mit Produktstückzahl gewichten; fehlenden Teilbeleg als unvollständige Gesamtevidenz anzeigen, nicht aus dem Nenner entfernen.<br>[F207-4](#f207-4) | [M09][M09], [M10][M10], [M04][M04], [H02][H02] |
| **B29 — Historischer Kursbezug**<br>CONFIRMED | Letzter geeigneter Basiswert-Trade zum oder vor dem Kauf; kein späterer Kurs als Ersatz. | Teillücke: heutiger rule_prices-Reader liest aktuell geeignete Produktbewertung bzw. neueste abgeschlossene Tagesdaten; daraus folgt kein Trade-genauer historischer Basiswertkurs vor einem Kauf. | Vorhandene historische Datenreader nur bei belegter Eignung für den letzten Basiswert-Trade zum oder vor der Ausführung einsetzen; Zeitpräzision/Quelle/Listing erhalten. Ohne solchen Nachweis nicht durch späteren Kurs, Close oder aktuellen Feed ersetzen.<br>[F207-4](#f207-4) | [M04][M04], [M09][M09], [M11][M11], [H02][H02] |
| **B30 — Nachtragung möglich**<br>CONFIRMED | Historischen Basiswert-Einstieg nachtragen; historische und Erfassungszeit trennen; keine feste 60-Sekunden-Grenze. | Vorhandener Zeitbaustein plus Evidenzlücke: ExecutionRecord und TradeTimeline trennen Ereignis-/Erfassungszeit; dies ist noch kein spezieller Nachtrag des persönlichen Basiswertkurses. | Nachtrag als eigenständige nachvollziehbare Basiswertevidenz an Ausführungsreferenz binden; historische Beobachtungszeit und spätere Erfassungszeit getrennt erhalten. Keine pauschale 60-Sekunden-Frist ergänzen und keine Execution-Zeit dafür verändern.<br>[F207-4](#f207-4) | [M09][M09], [M11][M11], [H02][H02] |
| **B31 — Einmalige Z1-Orientierung**<br>CONFIRMED | Bereits ausdrücklich zugeordnete Z1-Verkäufe anrechnen; keine erneute Halbierung der Restmenge. | Teillücke: echte SELLs und Restkosten sind vorhanden; sie besitzen in ExecutionRecord keine explizite Z1-Zweckzuordnung. Generische Alertdeduplizierung allein beweist keine einmalige Z1-Mengenorientierung. | Z1-Verkäufe nur über explizite belegte Zuordnung anrechnen; tatsächliche SELL-Ausführung bleibt unverändert beim Owner. Ursprünglichen Z1-Mengenbezug erhalten und keine neue Halbierung aus aktueller Restmenge ableiten.<br>[F207-2](#f207-2); [F207-4](#f207-4) | [M08][M08], [M09][M09], [M02][M02] |
| **B32 — Manuelle Stückzahlen**<br>CONFIRMED | Nutzer gibt konkrete Verkaufsmengen ein; keine automatische Rundung oder Ordermengenvorgabe. | Vorhandener Baustein: Ausführungs-API und Service verlangen eine konkrete positive quantity; Monitoringregeln erzeugen keine ExecutionRecord. Z1-Orientierung ist davon getrennt. | Bestehenden manuellen Ausführungsweg verwenden; neue Baselinehinweise geben weder gerundete konkrete Ordermenge noch automatische SELL-Buchung vor. 50%-Orientierung und tatsächlich eingegebene Stückzahl getrennt anzeigen.<br>[F207-4](#f207-4); [F207-5](#f207-5) | [M17][M17], [M16][M16], [M02][M02] |
| **B33 — Nur Meldungen**<br>CONFIRMED | Keine Orders, Stop-/Zielmutationen oder Kauf-/Verkaufsbuchungen aus Regelauslösern. | Die aktuelle Monitoringanwendung schreibt Regelzustände und Alerts; der getrennte Ausführungsowner bucht BUY/SELL. DYNAMIC_STOP_V1 und die Alertprojektion sind ausdrücklich lesende Projektionen. Damit besteht eine passende Nichtmutationsgrenze. | Diese Grenze für jede neue Baselineregel, Meldung und Nutzerreaktion verbindlich erhalten: keine Orders, STOP_CHANGED-/TARGET_CHANGED-Managementevents oder BUY/SELL aus einem Regelauslöser. Bestehende manuelle Order-/Ausführungsvorschauen sind keine Autorisierung für Baseline-Automation.<br>[F207-2](#f207-2); [F207-3](#f207-3); [F207-4](#f207-4); [F207-5](#f207-5) | [M02][M02], [M14][M14], [M05][M05], [M16][M16], [T03][T03] |
| **B34 — Keine Dubletten**<br>CONFIRMED | Unveränderten Handlungsbedarf sichtbar halten, nicht erneut benachrichtigen. | CURRENT_STOP/CURRENT_TARGET besitzen persistierten Übergangszustand; STAYED_TRIGGERED erzeugt keinen zweiten Alert. NotificationCreationService dedupliziert je Alert/Kanal/Ziel. Die Durable-Delivery-Infrastruktur speichert Zustellversuche. | Diese Bausteine wiederverwenden, aber für unveränderten Baseline-Handlungsbedarf stabile fachliche Schlüssel je Position/Version/Ereignis oder Episode definieren. Ein zurückgesetzter generischer TARGET-Alarm ist keine dauerhafte Z1-Wahrheit. Gesehen/Ablehnung oder Neustart dürfen keinen neuen logischen Hinweis erzeugen; Zustellwiederholung ist getrennt von fachlicher Neubenachrichtigung.<br>[F207-5](#f207-5) | [M02][M02], [M20][M20], [M21][M21], [M22][M22], [T03][T03], [T04][T04], [T05][T05] |
| **B35 — Quittierung**<br>CONFIRMED | Gesehen ist weder ausgeführt noch erledigt. | Alert besitzt OPEN, RESOLVED und INVALIDATED als Systemzustände; das bestehende Alert-API liest Alerts. Eine eigenständige fachliche Reaktion 'gesehen' oder 'abgelehnt' ist in diesem Vertrag nicht vorhanden. | Additiv 'gesehen', 'nicht umsetzen' und durch Ownerausführung belegten Vollzug getrennt modellieren. Quittierung darf weder Auflösung noch Ausführung oder Erfüllung bedeuten. Bei einer Empfehlung dürfen tatsächliche Teil-/Vollausführungen nur aus zugeordneter Ausführungsevidenz folgen.<br>[F207-5](#f207-5) | [M15][M15], [M23][M23], [M09][M09], [M16][M16] |
| **B36 — Nicht beurteilbar**<br>CONFIRMED | Fehlende, widersprüchliche oder ungeeignete Daten je Regel kennzeichnen; unabhängig mögliche Regeln weiter prüfen. | Der Monitoringzyklus behandelt Regeln getrennt, protokolliert rule_checks und überspringt fehlende/veraltete/ungeeignete Eingaben. Preisresolver und Bindungstests prüfen Instrument, Währung und geeigneten Beobachtungskontext. Einzelne ungeeignete Eingaben verhindern nicht grundsätzlich andere Regeln. | Die vorhandene Regelisolation für die Baseline als dauerhaft lesbares Ergebnis je Regel ausprägen: auswertbar/ausgelöst/nicht beurteilbar mit konkretem Grund und Datenstand. Eine fehlende Kursbeobachtung darf etwa eine allein aus belegtem Produktkalender auswertbare Fristregel nicht blockieren. Keine leeren Ergebnisse als Entwarnung.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [M24][M24], [M04][M04], [T06][T06], [T01][T01] |
| **B37 — Begründung**<br>CONFIRMED | Position, Regel-ID, Version, Datenstand, entscheidende Werte/Fristen und Einschränkungen anzeigen. | Alert und PriceObservation enthalten Position/Trade, Regelbezug, Schwelle, beobachteten Wert, Quell-/Feststellungszeit und Preis-/Herkunftskontext. Risikosnapshots liefern zusätzlich versionierte Policy-/Konfigurations- und Eingabebezüge. | Für die Baseline alle entscheidungsrelevanten Werte explizit zusammenführen: Regel-ID und Version, Ereignis-/Feststellungszeit, Instrumentachse/Währung/Skala, Einstands-/Mengenbezug, Kalender-/Fristevidenz und Einschränkungen. Vorhandene Felder nutzen; allgemeine Alerttexte oder ein aktueller Wert ersetzen nicht den nachvollziehbaren historischen Entscheidungsstand.<br>[F207-4](#f207-4); [F207-5](#f207-5) | [M15][M15], [M25][M25], [M24][M24], [M26][M26], [M27][M27] |
| **B38 — Version und Historie**<br>CONFIRMED | Frühere Prüfungen nicht umschreiben; Korrekturen als neue nachvollziehbare Evidenz/Prüfung. | Risikokonfigurationen und -snapshots bieten append-only bzw. unveränderliche, per Eingabefingerprint deduplizierte Evidenz. Trade Position verfügt über tatsächliche Ausführungs- und Korrekturhistorie. Der aktuelle generische Monitoringzustand ist dagegen ein fortgeschriebener Zustand. | Die Baseline darf vorhandene frühere Prüfungen/Eingaben nicht überschreiben. Korrigierte Ausführung, Zielquelle oder Preismaßstab erzeugt neue referenzierte Evidenz und Neubewertung, mit Zusammenhang zur vorherigen Bewertung. Bestehende Ownerhistorie referenzieren, keine zweite Ausführungshistorie erzeugen.<br>[F207-4](#f207-4); [F207-5](#f207-5) | [M27][M27], [M28][M28], [M09][M09], [M16][M16], [T07][T07] |
| **B39 — Globaler Geltungsbeginn**<br>CONFIRMED | Eine zentral geltende Version für alle offenen und künftigen Positionen ab dokumentiertem Zeitpunkt; keine individuelle Migration. | POSITION_RISK_V1 besitzt versionierte, ausdrücklich je Position konfigurierte Aktivierung und Revisionsprüfung. Das ist ein vorhandener anderer Geltungsvertrag, keine zentral ab einem Zeitpunkt geltende Baseline für alle offenen und künftigen Positionen. | Zentralen Baseline-Regelsatz mit dokumentiertem Geltungsbeginn und unveränderlicher Versionsreferenz vorsehen. Kein individueller Migrations-/Bestätigungsworkflow pro Position. Bestehende Opt-in-Risikokonfiguration nicht still umdeuten oder dadurch die Baseline aktivieren; F207-1 dokumentiert nur den künftigen Vertrag.<br>[F207-5](#f207-5) | [M26][M26], [M27][M27], [M29][M29] |

### B40–B58 — Lebenszyklus, Anpassungen und Restmengen

| Regel / historischer Status | Vollständiger Original-Solltext | Vorhandener Main-Baustein / Scope | Restarbeit und Folgeschnitt | Belege |
| --- | --- | --- | --- | --- |
| **B40 — Prüfanlässe**<br>CONFIRMED | Abgeschlossene Tagesdaten, relevante neue Daten/Ausführungen oder Nutzeranfrage prüfen; Produktfristen unabhängig. | MonitoringRunner und Runtime führen wiederkehrende Auswertungen aus; der Preisresolver liest unter anderem abgeschlossene Tageswerte. Der bestehende Zyklus verarbeitet aktuelle verfügbare Inputs und enthält operative Lauf-/Recoverydaten. | Relevante abgeschlossene Tagesdaten, neue qualifizierte Daten, effektive Ausführungsänderungen und explizite Nutzeranfrage als Auswertungsanlässe anbinden. Produktfristprüfung muss ohne aktuellen Kurs fortschreiten können. Bestehenden Runner wiederverwenden, aber Polling allein nicht als Beweis aller fachlichen Auslöseanlässe ausweisen.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [M19][M19], [M29][M29], [M24][M24], [M04][M04] |
| **B41 — Wiederanlauf**<br>CONFIRMED | Versäumte Sitzungen nachholen, Ereignis- und Feststellungszeit trennen; keine erfundenen vergangenen Meldungen/Ausführungen. | Monitoring speichert first/last seen und Quell-/Feststellungszeiten. Durable Delivery kann bestehende ausstehende Benachrichtigungen nach Wiederanlauf fortsetzen. Das ist keine fachliche Nachholung jeder versäumten Börsensitzung. | Aus verifizierter Kalender-/Evidenzhistorie nach Wiederanlauf relevante verpasste Sitzungen und Friststufen nachholen; tatsächlichen Ereigniszeitpunkt und spätere Feststellung trennen. Keine angeblich damals versandten Meldungen oder ausgeführten Trades erzeugen. Bereits gespeicherte logische Ereignisse/deliveries nicht duplizieren.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [M02][M02], [M25][M25], [M19][M19], [M22][M22], [M30][M30], [T05][T05] |
| **B42 — Geschlossene Position**<br>CONFIRMED | Handlungsmeldungen beenden, Historie erhalten; keine künstliche Erfüllung jeder Empfehlung. | Der Subject-Reader schließt Positionen mit Restmenge 0/closed_at aus. Der allgemeine Alert-Reader erhält Tradehistorie. Die ausstehende Zustellung prüft annullierten Trade und INVALIDATED-Alert; eine generelle Sperre durch normalen Vollverkauf ist darin nicht vorhanden. Die Risikohistorie verwendet zudem einen OpenPositionReader. | Für neue Baseline-Handlungsmeldungen den belegten Positionsschluss ausdrücklich in aktiven/pending Meldungen berücksichtigen und eine weiterhin lesbare geschlossene Historie vorsehen. Schluss beendet Handlungsbedarf, ohne jede frühere Empfehlung als umgesetzt zu markieren. Die Schließungsprüfung ist typbezogen; bestehende andersartige Alerts nicht pauschal unterdrücken.<br>[F207-5](#f207-5) | [M01][M01], [M31][M31], [M30][M30], [M26][M26], [T08][T08] |
| **B43 — Ablehnung**<br>CONFIRMED | Handlung nicht umsetzen separat dokumentieren; keine Änderung von Regeln/Bestand/Ereignissen. | Die vorhandenen Systemzustände OPEN/RESOLVED/INVALIDATED bilden keine eigenständige Nutzerentscheidung 'nicht umsetzen' ab. Ausführungen und Stop-/Zieländerungen sind getrennte, tatsächlich dokumentierte Ownerevents. | Ablehnung als zeitlich nachvollziehbare Reaktion auf einen konkreten Hinweis ergänzen. Sie verändert weder Regelversion noch Bestand, Zieltreffer, Schutzvorschlag oder tatsächliche Ausführung. Ablehnung unterdrückt keine später eigenständig fällige Friststufe und ist von Gesehen zu unterscheiden.<br>[F207-5](#f207-5) | [M15][M15], [M23][M23], [M07][M07], [M09][M09] |
| **B44 — Stopmeldung genügt**<br>CONFIRMED | Keine verpflichtende Stopübernahme oder Geltungsbeginn-Eingabe; Vorschlag ist kein Brokerstop. | DYNAMIC_STOP_V1 liefert ausdrücklich nur einen lesenden ATR-Kandidaten. Tatsächliche dokumentierte Stopänderungen laufen separat über Managementevents und effective_at. Diese saubere Trennung ist bereits vorhanden. | Baselineschutz als gekennzeichneten Vorschlag führen, ohne verpflichtende Stopübernahme oder manuell einzugebenden Geltungsbeginn. Den Bekanntgabezeitpunkt des Vorschlags systemseitig dokumentieren. Vorschlag nie automatisch in STOP_CHANGED, Brokerstop oder Ausführung übersetzen.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M32][M32], [M14][M14], [M07][M07], [T09][T09] |
| **B45 — Vorschlag überwachen**<br>CONFIRMED | Gemeldete höhere Stopmarke ab Bekanntgabe weiter überwachen, entsprechend gekennzeichnete Restausstiegsprüfung bei Berührung. | CURRENT_STOP überwacht den wirksam dokumentierten Managementstop. DYNAMIC_STOP_V1 und alert_projection berechnen nur einen aktuellen Kandidaten bzw. Aufmerksamkeit; sie persistieren keine bekanntgegebenen Schutzvorschläge. | Eine höhere bekanntgegebene Baselineschutzmarke samt Achse/Skala/Version/Bekanntgabe dauerhaft halten und ab Bekanntgabe eigenständig beobachten. Berührung erzeugt eine ausdrücklich auf den überwachten Vorschlag bezogene Restausstiegsprüfung, ohne einen realen Brokerstop zu behaupten.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M01][M01], [M07][M07], [M32][M32], [M14][M14], [M05][M05], [T10][T10] |
| **B46 — Vorschlag nicht senken**<br>CONFIRMED | Reguläre Folgevorschläge dürfen höhere Überwachungsmarken nicht lockern; bestätigte Korrektur/Split getrennt. | Der dynamische ATR-Kandidat wird bei jedem Aufruf neu berechnet und garantiert vertraglich keinen gespeicherten Mindeststop. Das ist kein Defekt dieses zustandslosen Analysevertrags. Managementevents halten explizite Stopänderungen. | Für die eigene Baseline den höchsten gültigen, vergleichbaren überwachten Vorschlag als Untergrenze regulärer Folgevorschläge erhalten. Eine bestätigte Korrektur oder verifizierte Skalierung ist ein gesonderter nachvollziehbarer Vorgang; unterschiedliche Preisachsen/Skalen nicht ungeprüft maximieren. Bestehende ATR-Policy unverändert lassen.<br>[F207-2](#f207-2); [F207-4](#f207-4) | [M32][M32], [M14][M14], [M07][M07], [M33][M33], [T11][T11] |
| **B47 — Friststufen**<br>CONFIRMED | Vorwarnung, Fälligkeit und Überschreitung je einmal melden, auch nach Quittierung/Ablehnung. | Der vorhandene Triggerübergang vermeidet unveränderte Wiederholungen. Er besitzt keine eigenständige Baseline-Sequenz aus Vorwarnung, Fälligkeit und Überschreitung; Durable Delivery liefert nur Zustellmechanik. | Jede fachliche Friststufe separat mit unveränderlichem Fristbezug und stabilem Deduplizierungsschlüssel halten. Jede Stufe darf einmal logisch neu gemeldet werden, selbst wenn die vorherige gesehen oder abgelehnt wurde. Wiederanlauf und verspätete Feststellung verändern die Frist nicht.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [M20][M20], [M02][M02], [M21][M21], [M22][M22] |
| **B48 — Bereits verletzter Vorschlag**<br>CONFIRMED | Bei geeigneter aktueller Beobachtung auf/unter neuem Niveau sofort Risikohinweis, keine rückwirkende Stopgültigkeit behaupten. | DYNAMIC_STOP_V1 kann einen berechneten Kandidaten bereits mit current_price <= candidate_stop als verletzt kennzeichnen; die Alertprojektion kann daraus hohe Aufmerksamkeit ableiten. Das ist noch kein persistierter Bekanntgabe-/Hinweisvertrag. | Bei Bekanntgabe einer neuen Baselineschutzmarke einen geeigneten aktuellen Punkt auf/unter der Marke sofort als gegenwärtigen Risikohinweis dokumentieren. Keine Rückwirkung auf frühere Kursintervalle oder Brokerstopgültigkeit. Ein Tagestief mit unklarer Reihenfolge vor Bekanntgabe belegt keine spätere Berührung.<br>[F207-2](#f207-2); [F207-5](#f207-5) | [M32][M32], [M05][M05], [M04][M04], [T11][T11], [T01][T01] |
| **B49 — Basiswertsplit**<br>CONFIRMED | Nur verifizierte Anpassungen; alle Vergleichswerte einheitlich skalieren, Originale erhalten, nicht doppelt anpassen. | Risikoanalytik verwendet adjustierte Schlusskurse und sperrt unpassende Roh-ATR-Vergleiche bei erkannter Corporate-Action-/Adjustierungsänderung. Produktvergleich prüft Identität, terms und adjustment_basis; passende Split-/Skalenregressionen sind vorhanden. | Für Baselinevergleiche zusätzlich verifizierte Anpassungsfaktoren und eindeutige Evidenzreferenzen über persönliche Basiswerteinstiege, Originalziele, gültige Schutzmarken und Beobachtungen verbinden. Originale erhalten, einheitlich skalieren, jede Anpassung nur einmal anwenden. Vorhandenes Erkennen einer Skalenänderung ist noch keine vollständige Baseline-Normalisierung.<br>[F207-4](#f207-4) | [M33][M33], [M34][M34], [T12][T12] |
| **B50 — Produktanpassung**<br>CONFIRMED | Kein Rückschluss auf Optionsscheinmenge/-kosten/-bedingungen allein aus Aktiensplit; produktspezifische Nachweise verlangen. | WarrantTermsVersion modelliert versionierte Produktbedingungen einschließlich ratio, strike, maturity und Gültigkeitsintervall. Produktvergleich verlangt identische/verifizierte Bedingungen und lehnt unpassende Anpassungsbasis ab. Echte Menge/Kosten stammen aus Trade-Position-Ausführungen. | Produktspezifische Anpassungen ausschließlich durch Produktbelege qualifizieren und referenzieren. Ein Basiswertsplit allein darf keine Optionsscheinmenge, Kostenbasis oder Bedingungen ändern. Baseline übernimmt diese Ownergrenze; keine zusätzliche Depot-/Produktanpassungsbuchhaltung implementieren.<br>[F207-4](#f207-4) | [M13][M13], [M34][M34], [M08][M08], [M09][M09], [T12][T12] |
| **B51 — Neuer Trade nach Schließung**<br>CONFIRMED | Wiedereinstieg als neue Position mit eigenem Beginn; frühere Historie erhalten; B08 nicht wieder einführen. | Bereits wirtschaftlich umgesetzt: PositionProjector verbietet BUY nach geschlossenem Trade. Ein neuer initialer/externer Kauf erzeugt neue Trade-/Position-IDs; Repositoryschutz verbietet nur parallele offene Doppelpositionen. Die alte Historie bleibt an der alten Identität. Tests prüfen das Wiederöffnungsverbot. | Kein neuer Trade-/Bestandsmechanismus nötig. Baselinezustand und Meldungshistorie an die vorhandene neue Position binden; früheres Ziel-/Verlust-/Stopereignis nicht auf den Wiedereinstieg übertragen. B08 bleibt ausgeschlossen; aus dem Wiedereinstieg keine alte Halbierungsregel importieren.<br>[F207-4](#f207-4); [F207-5](#f207-5) | [M08][M08], [M16][M16], [M35][M35], [T02][T02], [T07][T07], [T08][T08] |
| **B52 — Nachkauf**<br>CONFIRMED | Bei offener Position Bestand erweitern, Beginn/Zielhistorie/Verkäufe nicht zurücksetzen. | Bereits wirtschaftlich umgesetzt: record_additional_purchase ergänzt eine reale BUY-Ausführung zur offenen Position und reprojiziert dieselbe ID. PositionProjector setzt opened_at nur beim ersten BUY; frühere SELLs bleiben in der effektiven Ausführungskette. | Vorhandenen Nachkaufpfad und unveränderten Positionsbeginn übernehmen. Die neu hinzukommende Baseline-Zieltreffer-/Schutz-/Meldungshistorie darf beim Nachkauf nicht zurückgesetzt werden. Tatsächlichen Nachkauf nicht als neue Position oder Rücknahme früherer Verkäufe behandeln.<br>[F207-4](#f207-4); [F207-2](#f207-2) | [M16][M16], [M08][M08], [M09][M09], [T02][T02], [T07][T07], [T08][T08] |
| **B53 — Gehaltenen Einstand neu gewichten**<br>CONFIRMED | Nachkäufe mit noch offener Menge gewichten, verkaufte Stücke nicht erneut einbeziehen; ohne Gebühren, keine steuerliche FIFO-Aussage. | Bereits im Rechenkern umgesetzt: Bei SELL reduziert PositionProjector die Kostenbasis um Menge × vorherigen Durchschnitt; ein BUY addiert neue Gross-Kosten zur verbleibenden Kostenbasis und teilt durch neue offene Menge. Verkäufe gehen nicht nochmals in die Nachkaufgewichtung ein. project_with_trace zeigt Mengen-/Kostenbeiträge nachvollziehbar. | Keinen zweiten Durchschnitts-/Depotkostenrechner bauen. Qualifizierten vorhandenen Gross-Einstand samt effektiver Ausführungs-, Währungs- und Mengenbasis lesen. Baselineverbindung nach Teilverkauf/Nachkauf regressionssichern; diese Durchschnittsrechnung ist keine Netto-/Gebührenrechnung und keine steuerliche FIFO-Aussage.<br>[F207-4](#f207-4) | [M08][M08], [M09][M09], [T02][T02], [T13][T13] |
| **B54 — Basiswert-Einstand neu gewichten**<br>CONFIRMED | Optionsschein-Nachkäufe mit Restmenge und belegten Basiswertkursen gewichten; höhere Stopmarken erhalten. | Vorhandene Owner liefern tatsächliche Restmengen, Nachkäufe und Kostenbeiträge; PriceBinding trennt Produkt und Basiswert. Ein gesonderter belegter Basiswertkurs je historischer Optionsscheinkauf-Ausführung ist dadurch noch nicht gegeben. | Persönlichen Basiswerteinstieg aus belegten Basiswertkursen mit den tatsächlich noch offenen Mengen und neuen Produktkaufmengen qualifizieren. Fehlende Teilbelege nicht aus dem Nenner entfernen. Keine Optionsscheinpreise als Basiswertpreise verwenden; höhere gültige Schutzmarken nach Nachkauf erhalten. Die Mengen-/Ausführungsauswahl kommt weiterhin vom bestehenden Owner.<br>[F207-4](#f207-4); [F207-2](#f207-2) | [M08][M08], [M09][M09], [M04][M04], [M07][M07], [T13][T13], [T01][T01] |
| **B55 — Z1-Menge bleibt ursprünglich**<br>CONFIRMED | Nachkauf erhöht ursprüngliche Z1-Bezugsmenge nicht und löst keinen zusätzlichen Z1-Teilverkaufshinweis aus. | Die echte Ausführungshistorie und aktuelle Restmenge existieren. CURRENT_TARGET kennt aber weder eine unveränderliche ursprüngliche Z1-Bezugsmenge noch die Zuordnung tatsächlicher Verkäufe zur einmaligen Z1-Orientierung. | Originale Einstiegsbezugsmenge aus nachvollziehbar identifizierter erster Einstiegsgruppe bewahren; Nachkäufe dürfen sie nicht erhöhen. Belegte zugeordnete Verkäufe berücksichtigen, aber weder aus einem Zieltreffer einen Verkauf erzeugen noch wegen Nachkauf erneut Z1-Teilverkauf melden. Keine zweite Bestandsrechnung.<br>[F207-4](#f207-4); [F207-2](#f207-2) | [M09][M09], [M08][M08], [M01][M01], [M02][M02], [T02][T02] |
| **B56 — Gebündelte Meldung**<br>CONFIRMED | Alle gleichzeitigen Auslöser dokumentieren; vollständigen Restausstieg vor Teilverkauf/Stopanhebung anzeigen; keine Ausführung. | Der aktuelle Zyklus prüft einzelne Stop-/Zielregeln; Risikosignale und lesende Alertprojektion sind getrennte Ausgaben. Ein gemeinsames Baseline-Ergebnis mit allen gleichzeitigen Ursachen und fachlicher Handlungspriorität ist damit nicht bewiesen. | Alle belegten gleichzeitigen Auslöser im Ergebnis erhalten; die Darstellung einer vollständigen Restausstiegsprüfung vor Teilverkauf/Stopanhebung priorisieren. Niedriger priorisierte Evidenz nicht löschen und keine künstliche zeitliche Reihenfolge aus Tagesdaten erfinden. Bündelung erzeugt keine Order oder Ausführung.<br>[F207-2](#f207-2); [F207-3](#f207-3); [F207-5](#f207-5) | [M24][M24], [M02][M02], [M05][M05], [M15][M15] |
| **B57 — Verlustzustandswechsel**<br>CONFIRMED | Nur verlässlicher Geldkurs ≥ Einstand beendet aktuelle Verlustbedingung; erneuter Eintritt neue Episode; Datenlücke ist keine Erholung. | Generische Triggerübergänge können einen aktuellen Zustand beenden und nach neuem Eintritt erneut melden. Die Risikoengine hält Warnungen durch Datenlücken und fordert geeignete neue Bestätigung zur Erholung. Das sind nützliche Muster, keine implementierte B04-/B57-Verlustepisode. | Eine B04-Verlustepisode ausschließlich durch einen nach B58 geeigneten Originalgeldkurs >= qualifiziertem gehaltenem Einstand beenden. Datenlücke, ungeeigneter Ersatzkurs oder fehlender Kalender bedeutet unbekannt und keine Erholung. Erst erneuter verlässlich qualifizierter Verlust nach tatsächlicher Entwarnung eröffnet eine neue Episode mit neuer Meldung.<br>[F207-3](#f207-3); [F207-5](#f207-5) | [M20][M20], [M02][M02], [M04][M04], [T12][T12], [T03][T03] |
| **B58 — 15-Minuten-Geldkurs**<br>CONFIRMED | Laufende verifizierte Handelssitzung, Markt offen, Kurszeit nicht zukünftig und höchstens 15 Minuten alt; 20 Sitzungen bereits zum Kurszeitpunkt erreicht. | Vorhandene Preisqualifikation prüft Identität/Währung sowie Originalzeit, Retention und Qualität. Allgemeine Monitoringregeln dürfen jedoch ausdrücklich Last/Referenzkurse oder bestimmte Emittentenindikationen mit nur frischem Empfang (300 s) verwenden. Der generische DE-Warrant-Sitzungskalender und LAST_AVAILABLE sind kein Nachweis dieser strengeren Baseline-Regel. | Für B04 separat Original-BID des gehaltenen Instruments, passende Währung/Skala, verifizierte laufende Sitzung und offenen Markt verlangen. Originalkurszeit darf nicht zukünftig und muss höchstens 900 s alt sein; Empfang darf sie nicht ersetzen. Mindestens 20 abgeschlossene Basiswertsitzungen müssen bereits zu dieser Originalkurszeit erreicht sein, Starttag 0. Fehlende Kalenderdeckung/Quellzeit oder ungeeignete Ersatzwerte führen je Regel zu nicht beurteilbar; bestehende andersartige Indikationsregeln bleiben getrennt.<br>[F207-3](#f207-3) | [M04][M04], [M36][M36], [M37][M37], [M06][M06], [T01][T01], [T14][T14] |

## 5. Abgegrenzte Folgeaufgaben

Die vier Implementierungsaufgaben sind getrennt reviewbar. Ihre Datenabhängigkeiten
stehen jeweils dabei; sie sind keine Behauptung, jede Aufgabe könne ohne die
anderen produktiv aktiviert werden. Sie erweitern die vorhandenen Owner. Eine
zweite Monitoringengine, ein zweiter Ausführungsbestand oder eine Kopie des alten
Entwicklungspakets ist nicht der Lösungsauftrag.

<a id="f207-1"></a>
### F207-1 — Quellengebundener Dokumentationsvertrag

**Umfang dieses PRs:** Alle 58 Originaleinträge erhalten, vorhandene Main-Bausteine
und fehlende Verträge zuordnen, #187/#197 abgrenzen und die nachfolgenden Aufgaben
mit prüfbaren Ergebnissen sichern. Der Verweis im bestehenden Backlogeintrag
macht diese Anforderungen auffindbar. Der Backlog-Arbeitsstatus bleibt
`Technical Review`.

**Abnahme dieses Schnitts:** Titel, Solltext, Status und ID aller 58 Einträge
entsprechen dem historischen Katalog; B08 bleibt der einzige ausgeschlossene
Eintrag. Jede Zeile besitzt eine aktuelle oder ausdrücklich historische Quelle
und eine Zuständigkeit. Die Dokumentation enthält keine Behauptung einer
vollständigen Baseline-Implementierung oder einer neuen Fach-/Liveabnahme.

<a id="f207-2"></a>
### F207-2 — Dauerhafte Zielereignisse und überwachte Schutzvorschläge

**Owner und Wiederverwendung:** Position Monitoring verwendet die bestehenden
Subject-, Preisbindungs-, Management- und Ausführungsreader. Der eigene
Baselinezustand ergänzt deren Fakten um Z1/Z2-Treffer, dokumentierte
Stopberührungen und bekanntgegebene Schutzvorschläge. Die ATR-Policy bleibt ein
eigener lesender Vertrag.

**Lieferergebnis:** Dauerhafte, versionierte Ereignisse mit Preisachse, Quelle,
Beobachtungsintervall, Ereignis-/Feststellungszeit und Korrekturbezug. Zielrückgänge
löschen frühere Treffer nicht. Z1 führt zur einmaligen 50%-Orientierung und zur
Einstandsschutzprüfung; die SELL-Ausführung bleibt davon getrennt. Z2 und eine
belegte Stopberührung begründen eine Restausstiegsprüfung. Schutzvorschläge
speichern Bekanntgabe und höchstes vergleichbares Niveau; reguläre Folgevorschläge
senken es nicht. Die 20-Sitzungen-/80%-Z1-Regel verwendet den Kalender aus F207-3
und die ursprünglichen Werte aus F207-4.

**Grenzen und Abhängigkeiten:** F207-4 liefert ursprüngliche Einstiegsgruppe,
Mengen- und persönlichen Basiswertbezug; F207-3 liefert belegte Sitzungszählung;
F207-5 liefert Darstellung und Meldungslebenszyklus. Ein Vorschlag erzeugt weder
Managementevent noch Brokerstop oder Ausführung. B07/B08 werden nicht zu neuen
Positionsausstiegsregeln. Eine tägliche Bar darf nicht durch ihre Endzeit allein
als vollständig nach dem Einstieg oder nach einer Stopbekanntgabe liegend gelten.

**Gezielte spätere Abnahmefälle:**

1. Z1 trifft, der Kurs fällt zurück, die Anwendung startet neu: dasselbe belegte
   Ereignis und derselbe Handlungsbedarf bleiben erhalten, ohne Dublette.
2. Schutzmeldung entsteht beim Z1-Treffer auch ohne SELL; Restmenge und echter
   Managementstop bleiben unverändert. Tatsächliche Z1-Verkäufe werden nur mit
   expliziter Zuordnung berücksichtigt.
3. Kauf, Z1, Stopwechsel oder Bekanntgabe liegen innerhalb derselben groben
   Tagesbar: unbekannte Reihenfolge bleibt unbekannt; kein rückwirkender Treffer.
4. Gleichzeitige Stop-/Zielbefunde bleiben gemeinsam sichtbar. Eine vollständige
   Restausstiegsprüfung wird vor Teilverkauf/Stopanhebung dargestellt; dadurch
   entsteht keine künstliche Ausführungsreihenfolge.
5. Ein bereits höherer Schutz bleibt nach Nachkauf oder schwächerem neuem
   ATR-Kandidaten erhalten. Eine verifizierte Korrektur/Skalierung besitzt einen
   eigenen Nachweis.
6. Bei Bekanntgabe ist ein geeigneter aktueller Punkt bereits auf/unter dem neuen
   Schutz: gegenwärtiger Risikohinweis, ohne rückwirkende Stopgültigkeit.

<a id="f207-3"></a>
### F207-3 — Kalender, Produktfristen und qualifizierte Verlustepisoden

**Owner und Wiederverwendung:** Market Data/Product liefern qualifizierte
Beobachtungen, Produktbedingungen und vorhandene Laufzeit-/Risikoevidenz;
Position Monitoring wertet diese für die jeweilige Regel aus. Eine vorhandene
`maturity_date` oder `expiry_at` ist weiterzuverwenden. Ergänzt werden der
verifizierte letzte Handelstag, der fest zugeordnete Produktausstiegshandelsplatz,
dessen Kalender und die belegte instrumentbezogene Schlusszeit.

**Lieferergebnis:** Nachvollziehbare Sitzungszählung mit Kalenderidentität,
Zeitzone, Gültigkeit, Abdeckung und Belegquelle. Kauf- bzw. Z1-Tag zählen als 0;
nur danach abgeschlossene Basiswertsitzungen zählen für B04/B06. B05 verwendet
den früheren verifizierten Produkttermin, schließt ihn aus der Rückwärtszählung
aus und bestimmt die 20. vorherige Produkthandelssitzung. Vorwarnung, Fälligkeit
und Überschreitung bleiben getrennte, unveränderlich auf dieselbe Frist bezogene
Stufen. Fristen sind unabhängig von einer aktuell erreichbaren Kursquelle.

Die B04-Verlustprüfung akzeptiert ausschließlich einen geeigneten Original-BID
des gehaltenen Instruments in passender Währung/Skala. Originalzeit, offene
verifizierte Sitzung und Alter `0 <= Alter <= 900 Sekunden` müssen passen.
Die mindestens 20 abgeschlossenen Basiswertsitzungen müssen schon **zur
Originalkurszeit** erreicht sein. Ein verlässlicher entsprechend qualifizierter
Kurs `>= Einstand` beendet die Verlustepisode; erst erneuter geeigneter Verlust
begründet eine neue Episode. Datenlücke bedeutet weder Erholung noch Feiertag.
Auch ein gespeicherter BID bleibt nur anhand seiner unveränderten Originalzeit
und aller Sitzungs-/Qualitätsnachweise geeignet; Speicherung ist weder ein
pauschaler Ausschluss noch ein Frischenachweis.

**Grenzen und Abhängigkeiten:** F207-4 liefert qualifizierten Ausführungsbeginn
und gehaltenen Gross-Einstand; F207-2 liefert Z1-Ereigniszeit; F207-5 hält
Ergebnis-/Meldungszustand. Historische Rohdaten aus #197 und ein generischer
Wochentags-/Warrantkalender sind keine verifizierte Sitzungsevidenz. Benötigt eine
Quelle Nutzungsrechte oder eine Lizenz, ist deren Eignung vor Integration zu
belegen; diese Aufgabe aktiviert keinen neuen produktiven Provider. Die
bisherigen andersartigen Indikationsregeln bleiben getrennt.

**Gezielte spätere Abnahmefälle:**

1. Kauf-/Z1-Tag 0, Wochenende, echter Feiertag, fehlende Bar, verkürzte Sitzung
   und Zeitzonenwechsel: nur kalenderbelegte vollständige Sitzungen zählen.
2. Verfall und letzter Handelstag unterscheiden sich: der frühere verifizierte
   Termin und der Produktkalender bestimmen Frist und Schlussgrenze. Unbekannter
   letzter Handelstag wird nicht durch Auszahlungstag oder Schätzung ersetzt.
3. Wiederanlauf nach ausgefallenen Sitzungen holt relevante Stufen nach; Ereignis
   und spätere Feststellung bleiben getrennt. Verspätete Feststellung verschiebt
   weder Frist noch Handelsschluss und erfindet keine vergangenen Zustellungen.
4. Geldkurs genau 900 Sekunden alt, älter, zukünftig, ohne Originalzeit, nur frisch
   empfangen, Last/Close/Ask oder Markt geschlossen: nur belegte zulässige Fälle
   sind für B04 auswertbar. Ein gespeicherter BID mit unveränderter Originalzeit
   muss dieselben Anforderungen erfüllen; sein neuer Abruf setzt das Alter nicht
   zurück.
5. Die 20. Sitzung endet zwischen Kurszeit und Abrufzeit: der ältere Kurs wird
   nicht durch die spätere Abrufzeit für die Frist qualifiziert.
6. Verlust, Datenlücke, geeigneter Kurs auf Einstand, erneuter Verlust: Lücke
   beendet nichts; verlässliche Erholung und neue Episode bleiben unterscheidbar.

<a id="f207-4"></a>
### F207-4 — Baseline-Evidenz an die vorhandene Ausführungswahrheit binden

**Owner und Wiederverwendung:** Trade Position bleibt allein für effektive
Ausführungen, Korrekturen, Restmenge, Beginn und gehaltene Gross-Kostenbasis
zuständig. Seine vorhandene Restmengengewichtung wird gelesen und geprüft, nicht
erneut implementiert. Management-/Produkt-/Market-Data-Owner behalten ihre
jeweiligen Tatsachen.

**Lieferergebnis:** Nachvollziehbare Referenzen auf dieselbe ursprüngliche
Einstiegsauftragsgruppe, zugehörige tatsächliche Teilausführungen, ursprüngliche
Z1-Bezugsmenge und ausdrücklich zugeordnete echte Z1-Verkäufe. Fehlende
Orderzugehörigkeit wird nicht aus Uhrzeitnähe oder allen Käufen eines Trades
erfunden. Für Optionsscheinkäufe kommt eine belegte historische
Basiswertbeobachtung je effektiver Ausführung hinzu: letzter geeigneter Trade
zum oder vor dem Kauf, mit eigener historischer und späterer Erfassungszeit.
Es gibt keine pauschale 60-Sekunden-Nachtragsgrenze.

Persönlicher Basiswert-Einstieg wird mit Produktstückzahlen gewichtet; fehlende
Teilbelege machen die betreffende Gesamtevidenz unvollständig. Bei Nachkäufen
werden qualifizierte vorhandene Restmengen verwendet, ohne bereits verkaufte
Stücke neu einzubeziehen. Originale Preis-/Mengenbelege bleiben erhalten.
Vergleiche nach Splits brauchen verifizierte, konsistente und nur einmal
angewendete Skalenanpassungen. Produktänderungen brauchen produktspezifische
Belege; ein Basiswertsplit verändert nicht von sich aus Optionsscheinmenge,
Kosten oder Bedingungen.

**Grenzen und Abhängigkeiten:** Diese Aufgabe ist der vorgelagerte Datenvertrag
für F207-2/3. Sie benötigt keine neue Order- oder Depotbuchhaltung und keine
pauschale Benutzer-Migration je Position. Fehlende historische Belege dürfen
nachvollziehbar nachgetragen werden; bis dahin bleiben betroffene Regeln
gegebenenfalls nicht beurteilbar. Die neuere Eingabepolicy von #187 wird nicht
durch ein neues Formular für unbekannte Formeln oder Schätzwerte ersetzt.

**Gezielte spätere Abnahmefälle:**

1. Mehrere tatsächliche Fills derselben belegten Einstiegsgruppe, spätere
   Nachkäufe und Korrekturketten: ursprüngliche Z1-Bezugsmenge bleibt richtig und
   wächst beim Nachkauf nicht.
2. Historischer Basiswertpreis fehlt für einen Fill oder liegt erst nach dem
   Kauf: keine Teilgewichtung nur der verfügbaren Belege, kein Zukunftsersatz.
   Ein späterer belegter Nachtrag erzeugt neue Evidenz statt Überschreibung.
3. Teilverkauf und Nachkauf: Einstand stammt aus dem bestehenden qualifizierten
   Restkostenprojektor; verkaufte Stücke werden nicht erneut gewichtet. Beginn,
   frühere Z1-Verkäufe und höhere Schutzmarken bleiben erhalten.
4. Vollständiger Verkauf und späterer Wiedereinstieg: neue vorhandene
   Positionsidentität, eigener Beginn und eigene Baselinehistorie; die alte
   bleibt lesbar. Kein Wiederaufleben von B08.
5. Gleiche Währung bei anderem Instrument, abweichende Skalen oder nur
   Basiswertsplit ohne Produktbeleg: keine ungeprüften Quervergleiche und keine
   Änderung tatsächlicher Mengen/Kosten.
6. Hinweis, Gesehen, Ablehnung oder Zieltreffer verändern keine BUY-/SELL-Fakten,
   Mengen, Gebühren oder Brokerstopps.

<a id="f207-5"></a>
### F207-5 — Meldungslebenszyklus, API/UI und Wiederanlauf

**Owner und Wiederverwendung:** Position Monitoring hält fachliche Ergebnisse,
Alert die logischen Hinweise und Notification die Zustellversuche. Bestehende
Persistenz, Deduplizierung und Durable Delivery werden erweitert. Sie bleiben
von Ausführungen und tatsächlichen Managementänderungen getrennt.

**Lieferergebnis:** Eine zentral versionierte Baseline mit dokumentiertem
Geltungsbeginn für offene und künftige Positionen, ohne Bestätigungs-/Migrations-
workflow pro Position. Der heutige opt-in-Vertrag `POSITION_RISK_V1` wird dafür
nicht still umgedeutet. Aktivierung und Statusfortschritt benötigen später einen
eigenen qualifizierten Integrationsschnitt.

Je Regel werden auswertbar/ausgelöst/nicht beurteilbar mit konkretem Grund und
Evidenzstand lesbar. Eine ungeeignete Eingabe blockiert keine davon unabhängige
Regel. Meldungen zeigen Position, Regel-ID, Version, Ereignis-/Feststellungszeit,
Werte, Preisachse, Fristen und Einschränkungen. Gleichzeitige Ursachen bleiben
sichtbar; die priorisierte Restausstiegsprüfung verdrängt keine Evidenz.
Gesehen, nicht umsetzen und tatsächlich ausgeführt sind getrennte Ereignisse.
Unveränderter Handlungsbedarf erzeugt keine neue logische Benachrichtigung;
erneute Zustellversuche sind keine neuen fachlichen Ereignisse. Jede neue
Friststufe darf einmal melden, auch nach Gesehen oder Ablehnung der vorigen.

Ein normaler vollständiger Verkauf beendet neue Baseline-Handlungsmeldungen
einschließlich bereits ausstehender Zustellungen. Das muss typbezogen geprüft
werden: Die heutige Prüfung auf annullierten Trade/invalidierten Alert ist dafür
allein nicht ausreichend. Historie bleibt auch geschlossen lesbar; Schluss
markiert frühere Empfehlungen nicht automatisch als ausgeführt. Ungebundene alte
Preisregeln bleiben gesperrt; neue Baseline-Typen erweitern diese Schutzgrenze
ohne bestehende andersartige Alerts pauschal zu verwerfen.

**Grenzen und Abhängigkeiten:** Fachliche Ereignisse und Evidenzen kommen aus
F207-2/3/4. API/DTO/UI-Erweiterungen sind additiv und müssen zu den aktuellen
Ownerverträgen passen; dieser Dokumentations-PR friert noch kein unbesehen
übernommenes historisches Schema ein. Eine Ablösung bisheriger Policysemantik
benötigt eine eigene ausdrückliche Version/Entscheidung.

**Gezielte spätere Abnahmefälle:**

1. Prozessneustart, wiederholter identischer Input, Zustellfehler und Retry:
   genau ein logischer Hinweis je unverändertem Anlass; Versuchshistorie bleibt
   nachvollziehbar.
2. Gesehen und Ablehnung verändern keine Ereignis-/Ausführungswahrheit. Eine
   neue Friststufe oder verlässlich neue Verlustepisode kann trotzdem melden.
3. Vollverkauf während einer ausstehenden Zustellung unterdrückt neue
   Baseline-Handlungsaufforderungen; Historie bleibt lesbar, andere Alerttypen
   behalten ihren geltenden Vertrag.
4. Fehlender BID bei belegter Produktfrist: Verlustregel nicht beurteilbar,
   Produktfrist weiter auswertbar; keine leere Ausgabe als Entwarnung.
5. Korrigierte Ausführungs-/Produkt-/Kalenderevidenz erzeugt eine neue
   referenzierte Prüfung. Frühere Bewertungen bleiben nachvollziehbar.
6. API-, Frontend- und Browserregressionen zeigen korrekte Position/Version,
   Preisachsen und Zustände auch bei Navigationswechsel, alter Antwort und
   geschlossener Position. Bestehende Monitoring-, Handels- und
   Benachrichtigungsflüsse bleiben qualifiziert.

## 6. Integrationsreihenfolge und konkrete Blockaden

Die erste Implementierungsabhängigkeit ist **F207-4: der nachgewiesene
Ausführungs-/Einstiegsbezug**. Der Kalender-/Quellenvertrag aus F207-3 kann parallel
geklärt werden. F207-2 verbraucht beide Verträge; F207-5 integriert die Ergebnisse
und hält den Meldungslebenszyklus. Die Aufteilung erlaubt getrennte Reviews und
Tests, aber keine stillschweigende Aktivierung eines unvollständigen Regelpakets.

| Blockade | Vor einer fachlich vollständigen Integration nachzuweisen |
| --- | --- |
| Evidenzlücken | Ursprüngliche Einstiegsgruppe, persönliche historische Basiswertbeobachtung, Z1-Verkaufszuordnung und verifizierte Produkt-/Kalenderdaten; betroffene Regeln bleiben sonst konkret begründet nicht beurteilbar. |
| Policygrenzen | B08 bleibt ausgeschlossen, B11 löst beim Treffer aus; #187-Preview, #197-Forschung, bestehende ATR-/Phase-/Score-Policies und allgemeine Indikationsregeln behalten ihren eigenen Vertrag. Eine spätere Kombination wird ausdrücklich versioniert. |
| Historisches Paket | Der aktuelle #207-Diff liefert nur den Exporthelper. Aus dem nicht lesbaren späteren Gesamtbaum wird kein vorhandener Runtime-Code oder erfolgreicher Integrationsnachweis abgeleitet. Die lesbaren historischen Entwürfe sind Quellen, keine blind anzuwendenden Patches. |
| Persistenz und Migration | Schema und Revisionen am dann aktuellen Main entwerfen. Der alte Vorschlag für Migration 0039 laut [#207](https://github.com/burckhju/trading-workspace/pull/207) passt nicht unverändert auf den geprüften Stand: [0039 ist anders belegt][migration-0039], [0048 ist bereits vorhanden][migration-0048]. Keine Übernahme alter Migrationsnummern, alten Workerimports oder Entwicklungsworkflows ohne neuen Diff-/Ownerabgleich. |
| Qualifikation | Je Implementierungsschnitt aktuelle commitgebundene Backend-/Frontend-/Browsernachweise nach Repositoryregeln, zusätzlich die betroffenen fachlichen Grenzfälle. Alte grüne Helper-CI oder Main-CI qualifiziert keine künftig geschriebene Baseline. |
| Freigabestatus | Implementiert, PR-geprüft, integriert, veröffentlicht, am Nutzer-PC installiert und fachlich abgenommen sind getrennte Nachweise. Ein Dokumentations-Draft setzt keinen dieser Runtime-Status weiter. |

Kein eigener Provider, Release, Tag oder PC-Update gehört zu diesen
Dokumentationsänderungen. #187/#197 bleiben eigenständig. Eine spätere Schließung
von #207 ist eine gesonderte Bereinigungsentscheidung nach gesicherter Erhaltung
der Anforderungen; dieser PR schließt und mergt keinen Alt-PR.

## 7. Nachweise für diesen Dokumentationsschnitt

Für F207-1 sind ein vollständiger Wortlaut-/Statusabgleich des historischen
Katalogs, die Prüfung der commitgebundenen Belegpfade und ein auf die vorgesehenen
Dokumente begrenzter Diff maßgeblich. Die in der Matrix genannten vorhandenen
Tests wurden als Quelltextbelege gelesen; sie sind keine hier erneut ausgeführten
Testläufe. Vollständige Anwendungstests werden für die reine Dokumentationsanalyse
nicht manuell gestartet. Automatisch durch GitHub ausgelöste Prüfungen sind
separat am tatsächlichen Draft-Head zu bewerten.

| Stufe | Aussage dieses Vertrags |
| --- | --- |
| Dokumentiert / zur Prüfung vorgelegt | Vollständiger historischer Katalog und aktuelle Zuordnung liegen in diesem Dokument vor. |
| Implementiert | Vorhandene Bausteine sind in Abschnitt 4 einzeln belegt; die vollständige Baseline ist nicht als implementiert nachgewiesen. |
| PR-geprüft | Fachliche Begutachtung und CI eines jeweiligen konkreten PR-Heads sind eigene spätere Nachweise; der Draftstatus ersetzt sie nicht. |
| In Main integriert | Die im Prüfstand gepinnten Bausteine sind vorhanden; die neu abgegrenzten Implementierungsaufgaben sind hier nicht integriert. |
| Veröffentlicht | Tag v1.5.34 gehört zum geprüften Main, nicht zu einer vollständigen Umsetzung der hier fehlenden Regeln. |
| Auf dem PC installiert | In diesem Schnitt nicht geprüft. |
| Fachlich abgenommen | Historische Katalogbestätigungen bleiben erhalten; eine aktuelle vollständige Integrations-/Betriebsabnahme wird nicht behauptet. |

## 8. Commitgebundene Belegstellen

Die folgende Liste löst die Belegkürzel der Matrix auf. `Main` bedeutet stets
`46cb2693e38751ca330074e8606142d0c5e9d24b`; #187 ist an
`bad00a420f56994216ad1def6a580b00b0f5772f`, #197 an
`08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` gebunden. Historische Git-Blobs werden
ausdrücklich separat ausgewiesen und nicht als aktuelle Main-Dateien verlinkt.

| Kürzel | Stand | Datei / Quelle |
| --- | --- | --- |
| H01 | historischer Git-Blob, nicht Main/#207-Head | [backend/app/features/position_monitoring/domain/baseline_catalog.py][H01] |
| H02 | historischer Git-Blob, nicht Main/#207-Head | [backend/app/features/position_monitoring/domain/baseline_contracts.py][H02] |
| M01 | Main | [backend/app/features/position_monitoring/service/subjects.py][M01] |
| M02 | Main | [backend/app/features/position_monitoring/service/application.py][M02] |
| M03 | Main | [backend/app/features/position_monitoring/domain/evaluator.py][M03] |
| M04 | Main | [backend/app/features/position_monitoring/service/rule_prices.py][M04] |
| M05 | Main | [backend/app/features/position_monitoring/service/alert_projection.py][M05] |
| M06 | Main | [backend/app/features/position_monitoring/service/position_analytics.py][M06] |
| M07 | Main | [backend/app/features/trade_position/domain/management.py][M07] |
| M08 | Main | [backend/app/features/trade_position/domain/projector.py][M08] |
| M09 | Main | [backend/app/features/trade_position/domain/models.py][M09] |
| M10 | Main | [backend/app/features/trade_position/service/valuation_basis.py][M10] |
| M11 | Main | [backend/app/features/trade_position/domain/timeline.py][M11] |
| M12 | Main | [backend/app/features/product/service/risk_reference.py][M12] |
| M13 | Main | [backend/app/features/product/domain/models.py][M13] |
| M14 | Main | [backend/app/features/position_monitoring/service/dynamic_stop.md][M14] |
| M15 | Main | [backend/app/features/alert/domain/models.py][M15] |
| M16 | Main | [backend/app/features/trade_position/service/application.py][M16] |
| M17 | Main | [backend/app/features/trade_position/api/dtos.py][M17] |
| M18 | Main | [backend/app/features/product/service/valuation_evidence.py][M18] |
| M19 | Main | [backend/app/features/position_monitoring/service/runner.py][M19] |
| M20 | Main | [backend/app/features/position_monitoring/domain/transitions.py][M20] |
| M21 | Main | [backend/app/features/notification/service/creation.py][M21] |
| M22 | Main | [backend/app/features/notification/service/durable_delivery.py][M22] |
| M23 | Main | [backend/app/features/alert/api/router.py][M23] |
| M24 | Main | [backend/app/features/position_monitoring/service/cycle.py][M24] |
| M25 | Main | [backend/app/features/position_monitoring/domain/models.py][M25] |
| M26 | Main | [backend/app/features/position_monitoring/service/risk.py][M26] |
| M27 | Main | [backend/app/features/position_monitoring/persistence/models.py][M27] |
| M28 | Main | [backend/app/features/position_monitoring/persistence/risk_records.py][M28] |
| M29 | Main | [backend/app/features/position_monitoring/service/runtime.py][M29] |
| M30 | Main | [backend/app/features/notification/persistence/durable_delivery.py][M30] |
| M31 | Main | [backend/app/features/alert/persistence/read_repository.py][M31] |
| M32 | Main | [backend/app/features/position_monitoring/service/dynamic_stop.py][M32] |
| M33 | Main | [backend/app/features/analysis/domain/risk_analytics.py][M33] |
| M34 | Main | [backend/app/features/analysis/domain/product_comparison.py][M34] |
| M35 | Main | [backend/app/features/trade_position/persistence/repositories.py][M35] |
| M36 | Main | [backend/app/features/position_monitoring/service/quote_freshness.py][M36] |
| M37 | Main | [backend/app/features/position_monitoring/domain/quote_quality.py][M37] |
| P187E | #187, offener Draft | [backend/app/features/trade_plan/domain/hebeltrader.py][P187E] |
| P187M | #187, offener Draft | [backend/app/features/position_monitoring/domain/hebeltrader.py][P187M] |
| T01 | Main | [tests/unit/backend/features/position_monitoring/test_rule_price_binding.py][T01] |
| T02 | Main | [tests/unit/backend/features/trade_position/test_projector.py][T02] |
| T03 | Main | [tests/unit/backend/features/position_monitoring/test_monitoring_application.py][T03] |
| T04 | Main | [tests/unit/backend/features/notification/test_creation.py][T04] |
| T05 | Main | [tests/unit/backend/features/notification/test_durable_delivery.py][T05] |
| T06 | Main | [tests/unit/backend/features/position_monitoring/test_cycle.py][T06] |
| T07 | Main | [tests/unit/backend/features/trade_position/test_application.py][T07] |
| T08 | Main | [tests/integration/backend/test_trade_capture_safety.py][T08] |
| T09 | Main | [tests/unit/backend/features/trade_position/test_management_events.py][T09] |
| T10 | Main | [tests/unit/backend/features/position_monitoring/test_dynamic_stop_service.py][T10] |
| T11 | Main | [tests/unit/backend/features/position_monitoring/test_dynamic_stop.py][T11] |
| T12 | Main | [tests/unit/backend/features/position_monitoring/test_risk_signals.py][T12] |
| T13 | Main | [tests/unit/backend/features/trade_position/test_projector_trace.py][T13] |
| T14 | Main | [tests/unit/backend/features/position_monitoring/test_issuer_indicative_rules.py][T14] |

Zusätzliche Einordnungen und Integrationsgrenzen in den Abschnitten 1–3 und 6
verlinken ihre Belege unmittelbar im Text.

[M01]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/subjects.py
[M02]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/application.py
[M08]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/projector.py
[M09]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/models.py
[M04]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/rule_prices.py
[M14]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/dynamic_stop.md
[M07]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/management.py
[M10]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/service/valuation_basis.py
[M03]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/domain/evaluator.py
[M06]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/position_analytics.py
[M12]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/product/service/risk_reference.py
[M13]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/product/domain/models.py
[P187E]: https://github.com/burckhju/trading-workspace/blob/bad00a420f56994216ad1def6a580b00b0f5772f/backend/app/features/trade_plan/domain/hebeltrader.py
[H01]: https://api.github.com/repos/burckhju/trading-workspace/git/blobs/2df37e7ba2a2aa4734412aebec9dee419002da73
[M11]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/timeline.py
[M16]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/service/application.py
[T02]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/trade_position/test_projector.py
[P187M]: https://github.com/burckhju/trading-workspace/blob/bad00a420f56994216ad1def6a580b00b0f5772f/backend/app/features/position_monitoring/domain/hebeltrader.py
[T01]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_rule_price_binding.py
[H02]: https://api.github.com/repos/burckhju/trading-workspace/git/blobs/a6b272e06a7fbda58262b149559835ec8dea0984
[M18]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/product/service/valuation_evidence.py
[M19]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/runner.py
[M15]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/alert/domain/models.py
[M17]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/api/dtos.py
[M05]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/alert_projection.py
[T03]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_monitoring_application.py
[M20]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/domain/transitions.py
[M21]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/notification/service/creation.py
[M22]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/notification/service/durable_delivery.py
[T04]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/notification/test_creation.py
[T05]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/notification/test_durable_delivery.py
[M23]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/alert/api/router.py
[M24]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/cycle.py
[T06]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_cycle.py
[M25]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/domain/models.py
[M26]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/risk.py
[M27]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/persistence/models.py
[M28]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/persistence/risk_records.py
[T07]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/trade_position/test_application.py
[M29]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/runtime.py
[M30]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/notification/persistence/durable_delivery.py
[M31]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/alert/persistence/read_repository.py
[T08]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/integration/backend/test_trade_capture_safety.py
[M32]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/dynamic_stop.py
[T09]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/trade_position/test_management_events.py
[T10]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_dynamic_stop_service.py
[M33]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/analysis/domain/risk_analytics.py
[T11]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_dynamic_stop.py
[M34]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/analysis/domain/product_comparison.py
[T12]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_risk_signals.py
[M35]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/persistence/repositories.py
[T13]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/trade_position/test_projector_trace.py
[M36]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/quote_freshness.py
[M37]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/domain/quote_quality.py
[T14]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/tests/unit/backend/features/position_monitoring/test_issuer_indicative_rules.py
[historical-comment]: https://github.com/burckhju/trading-workspace/pull/207#issuecomment-5661655043
[historical-catalog]: https://api.github.com/repos/burckhju/trading-workspace/git/blobs/2df37e7ba2a2aa4734412aebec9dee419002da73
[historical-contracts]: https://api.github.com/repos/burckhju/trading-workspace/git/blobs/a6b272e06a7fbda58262b149559835ec8dea0984
[pr207-helper]: https://github.com/burckhju/trading-workspace/blob/85921b9a6db30028a25b9c69a3e9a97a50482c10/.github/workflows/hebeltrader-baseline.yml
[refresh-diagnostics]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/market_data/service/refresh_diagnostics.py
[refresh-quality]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/market_data/service/refresh_quality.py
[position-projector]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/projector.py
[valuation-basis]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/service/valuation_basis.py
[price-binding]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/trade_position/domain/price_binding.py
[rule-prices]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/rule_prices.py
[phase-policy]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/phase_engine.md
[score-policy]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/score_engine.md
[stop-policy]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/app/features/position_monitoring/service/dynamic_stop.md
[pr187-input]: https://github.com/burckhju/trading-workspace/blob/bad00a420f56994216ad1def6a580b00b0f5772f/docs/features/HEBELTRADER_INPUT_POLICY.md
[pr187-entry]: https://github.com/burckhju/trading-workspace/blob/bad00a420f56994216ad1def6a580b00b0f5772f/backend/app/features/trade_plan/domain/hebeltrader.py
[pr187-management]: https://github.com/burckhju/trading-workspace/blob/bad00a420f56994216ad1def6a580b00b0f5772f/backend/app/features/position_monitoring/domain/hebeltrader.py
[pr197-collector]: https://github.com/burckhju/trading-workspace/blob/08d2a5c9abe91ef518eb2c940eff9bbeceb073f8/scripts/research/collect_public_history.py
[pr197-workflow]: https://github.com/burckhju/trading-workspace/blob/08d2a5c9abe91ef518eb2c940eff9bbeceb073f8/.github/workflows/research-public-history.yml
[pr197-research]: https://github.com/burckhju/trading-workspace/blob/08d2a5c9abe91ef518eb2c940eff9bbeceb073f8/docs/research/HEBELTRADER_EXECUTION.md
[migration-0039]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/migrations/versions/20260918_0039_position_quote_source_selection.py
[migration-0048]: https://github.com/burckhju/trading-workspace/blob/46cb2693e38751ca330074e8606142d0c5e9d24b/backend/migrations/versions/20261028_0048_currency_source_evidence.py
