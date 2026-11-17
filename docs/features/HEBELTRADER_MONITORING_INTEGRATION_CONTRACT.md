# Hebeltrader-Positionsmeldungen: Integrationsvertrag zu #207

**Additiver Stand 16.11.2026:** Der historische F207-1-Abgleich bleibt erhalten.
Der [Evidenzschnitt F207-4](#f207-4-evidence-read) wurde mit
[PR #344](https://github.com/burckhju/trading-workspace/pull/344) auf Main
`e6738c291b0701d00cce20a370aba7496a9f24d0` integriert. Die
[F207-3-Schnittstellenübergabe](#f207-3-interface-handoff) bleibt maßgeblich.
Der begrenzte [Zielhistorien-Schnitt F207-2](#f207-2-target-history) wurde mit
[PR #345](https://github.com/burckhju/trading-workspace/pull/345) auf Main
`6efa74d3bd0978c7ef8975fdc9c506de7a0aa348` integriert. Der
[Vergleichsbeleg-Schnitt F207-3](#f207-3-history-qualification) wurde mit
[PR #346](https://github.com/burckhju/trading-workspace/pull/346) auf Main
`1d63d001216ef6f9294697f54707f3ae89a58ac4` integriert. Der
[Sitzungsevidenz-Schnitt F207-3](#f207-3-session-evidence) wurde mit
[PR #347](https://github.com/burckhju/trading-workspace/pull/347) auf Main
`19a10ad484293995e200b5eb9a99b4ae11a49ee2` integriert.
Der anschließende [Original-Geldkurs-Schnitt](#f207-3-original-bid-evidence)
baut ausdrücklich auf dessen Head `093e97899fd35a1f8f508518ebe606fad8e2e237`
auf; dessen Inhalt ist identisch mit dem inzwischen integrierten Main-Tree.
Der [Originalstatus-Anschluss](#f207-3-market-status-evidence) baut auf den noch
offenen Drafts [#348](https://github.com/burckhju/trading-workspace/pull/348) und
[#349](https://github.com/burckhju/trading-workspace/pull/349) auf. Er erhält
ausdrückliche Statuspunktbelege und erklärt ihre Grenzen im vorhandenen Read;
eine qualifizierte aktuelle Statusversorgung ist weiterhin nicht belegt.
Aufgabenstatus bleibt ausschließlich im Product Backlog; vollständige Baseline,
Regelaktivierung und Betrieb werden dadurch nicht als abgeschlossen erklärt.

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

<a id="f207-3-interface-handoff"></a>
## Anhang: F207-3-Schnittstellenübergabe vom 14.11.2026

Gezielte, ausschließlich lesende Codeprüfung auf Main
`b84544edabccbe5a9102ee883eb26ebf01f40f9a` (`VERSION` 1.5.46).
Dieser Anhang ergänzt die historische Anforderungszuordnung; er implementiert
keine F207-3-Regelauswertung und belegt keine aktuelle Versorgung auf dem
Nutzer-PC. Aufgabenstatus bleibt ausschließlich im Product Backlog.

### Vorhandene Owner und wiederverwendbare Reads

| Bedarf | Vorhandener öffentlicher Vertrag | Grenze am geprüften Main |
| --- | --- | --- |
| Gespeicherte Produktquote | [`RiskMarketDataReader.saved_quote(workspace_id, position_id, as_of)`](../../backend/app/features/market_data/service/risk_read.py) | Rein lesend; prüft Source Selection, Route, Instrument, Währung, Qualität und Zeit. Keine Aussage über verifizierte offene Sitzung oder 20 abgeschlossene Sitzungen. |
| Historische Produktkurse | [`QuoteHistoryReader.prices/report`](../../backend/app/features/market_data/service/quote_history.py), [`WarrantPriceHistory`](../../backend/app/features/market_data/service/warrant_price_history.py) | Persistierte Samples und Last-success, getrennte BID-/ASK-/Referenzserien und Original-/Abruf-/Erfassungszeiten. Keine vollständige Zeitabdeckung. |
| Produkttermin und Bedingungen | [`RiskProductReader.read(workspace_id, warrant_id, as_of)`](../../backend/app/features/product/service/risk_reference.py) | Liefert Bedingungen-ID, `maturity`, optional `expiry_at`, Evidenzrevision, Herkunft und Dokumentreferenz. Letzter Handelstag fehlt. |
| Produktbelegrevisionen | [`ValuationEvidenceService.view` / `current_evidence`](../../backend/app/features/product/service/valuation_evidence.py) | An Produktidentität und Bedingungen-ID gebunden; Prüf- und Erfassungszeit getrennt. Kein Rückgriff auf eine ältere passende Revision bei geänderter letzter Evidenz. |
| Basiswertlisting | [`RiskListingReader.read`](../../backend/app/features/market/service/risk_reference.py) | Eindeutige aktive primäre Notierung, Symbol und Währung; noch kein historisch fest gebundener Kalenderread. |
| Basiswerttagesdaten | [`MarketDataReader.list_daily_prices`](../../backend/app/features/market_data/service/query.py) | Vorhandene OHLC-/Adjusted-Close-Daten sind weder vollständiger Kalender noch Intraday-Trade zum Kauf. |

Der [Kursvertrag](../../backend/app/features/market_data/domain/models.py) erhält
bereits Originalzeit, Kursseite, Währung, Listing/ISIN, Venue/MIC, Zeitbasis und
Quellenmodus. [`SavedQuoteEvidence`](../../backend/app/features/market_data/domain/risk_evidence.py)
ergänzt Abrufzeit und Routenidentität. Diese Verträge bleiben die Preisgrundlage.
`ProductPositionValuationService.for_trade` und `WarrantListingQuoteProvider`
können dagegen Provider-I/O auslösen; der Retentionwrapper kann zudem speichern.
Ein Coverage-GET verwendet deshalb ausschließlich gespeicherte Reader.

### Vier vorgeschlagene Anschlussverträge für F207-3

Die folgenden Namen beschreiben **noch nicht implementierte** schmale Reads bei
Market Data/Product. Sie beschaffen im Read keine Daten und aktivieren keine
Quelle. Vorhandene Identitäts-, Beleg- und Preisobjekte werden wiederverwendet.
`known_at` bezeichnet den Wissensstand; Originalereigniszeit und spätere
Erfassungszeit bleiben jeweils eigenständige Felder.

**`read_session_evidence(binding, interval, known_at)`** — Market Data liefert
fest gebundenes Basiswert-/Produktlisting, Handelsplatz/MIC, Zeitzone,
Kalender-ID/-Version, Gültigkeit, belegten Deckungsbereich und Quellreferenz.
Jede Sitzung enthält lokalen Sitzungstag, tatsächliches `opens_at`/`closes_at`
und gegebenenfalls verkürzte Zeiten; Nicht-Sitzungstage und Deckungslücken sind
explizit unterscheidbar. Market besitzt bereits Listing-/Venue-Identitäten und
IANA-Zeitzone, aber keinen solchen Sitzungsevidenzreader. Der generische
[`DE_WARRANT_SESSION_FRESHNESS_V1`](../../backend/app/features/position_monitoring/service/quote_freshness.py)
mit 08–22 Uhr und regulären Feiertagen ersetzt ihn nicht. Kauf-/Z1-Tag zählt 0;
der Consumer zählt nur spätere, zur maßgeblichen Ereigniszeit abgeschlossene
Sitzungen. Fehlende Tageskerzen werden nicht als Feiertage interpretiert.

**`read_product_deadline_evidence(workspace_id, warrant_id, terms_id,
exit_listing_id, known_at)`** — Product verwendet `RiskProductReader`,
`ValuationEvidence` und `WarrantListing`; ergänzt werden verifizierter letzter
Handelstag/-schluss, ausdrücklich gebundenes Ausstiegslisting, Terminart und
instrumentbezogene Schlusszeit mit Quelle und Revision. `expiry_at` ist kein
Synonym für letzten Handelstag. Die vorhandene Produktbelegvalidierung bindet
sein lokales Datum an `maturity_date`; abweichende Bewertungs-/Zahlungstage sind
dadurch nicht unterstützt. B05 benötigt den früheren verifizierten maßgeblichen
Termin und die 20. vorherige Produktsitzung, unter Ausschluss des Termintags.
Diese Frist bleibt unabhängig davon, ob gerade ein Produktkurs erreichbar ist.

**`read_saved_original_bid(workspace_id, position_id, as_of)`** — Market Data
baut auf `RiskMarketDataReader.saved_quote` und dem unveränderten
`WarrantQuoteSnapshot` auf. Der spätere Baseline-Qualifier verlangt tatsächlichen
BID des gehaltenen Instruments, passende Währung und belegte Skala, echte
Originalzeit, `0 <= Alter <= 900 Sekunden` und verifiziert laufende offene Sitzung.
Die 20. Basiswertsitzung muss bereits **zur Originalkurszeit** abgeschlossen sein.
Empfang nach dem Sitzungsschluss qualifiziert einen älteren Kurs nicht nachträglich.
Retention ist weder pauschaler Ausschluss noch Frischenachweis. Last, Close, Ask,
Mid oder eine nur frische Empfangszeit ersetzen keine fehlende BID-Evidenz.

**`read_underlying_trade_at_or_before(binding, execution_time_evidence,
known_at)`** — Market Data liefert einen unveränderlichen Beobachtungsbezug mit
Basiswert/Listing/Venue, `price_kind=TRADE`, Preis, Währung, Preismaßstab und
gegebenenfalls verifizierter Anpassungsevidenz. Originalzeit samt Genauigkeit,
Herkunft, Korrekturbezug und Erfassungszeit bleiben sichtbar. Die Auswahl muss
belegen, weshalb dies der letzte geeignete Trade zum oder vor dem Kauf ist.
Am geprüften Main existieren nur Tagesdatenprovider, kein solcher historischer
Basiswert-Tradereader. `source_updated_at` und `retrieved_at` sind keine
Tradezeitpunkte. Unbekannte Kaufuhrzeit wird nicht erfunden, spätere Trades werden
nicht rückdatiert und ein belegter späterer Nachtrag hat keine pauschale
60-Sekunden-Grenze. F207-4 liefert dafür den Ausführungs-/Belegbezug.

### Reale Quellenqualifikation und verbleibender Betriebsnachweis

| Bestehender Pfad | Vorhandene Evidenz | Verbleibende B04-/B58-Grenze |
| --- | --- | --- |
| JPMorgan | Gebundene Produktindikation; Originalzeit ausdrücklich unbekannt (`DATE_AND_TIMEZONE_UNKNOWN`). | Frischer Empfang ersetzt weder Datum noch Zeitzone; kein geeigneter Original-BID-Zeitnachweis. |
| Morgan Stanley | Produktindikation mit lokalem Zeittext, `LOCAL_DATETIME_TIMEZONE_UNKNOWN` oder fehlendem Zeitstempel. | Unverifizierte Zeitzone; `observed_at` bleibt unbekannt. |
| gettex delayed | Genaue MUND-/MUNC-/ISIN-/Währungsbindung, getrennte Seiten und originale UTC-Zeit. | Marktstatus ist `UNKNOWN`; nominal 900 Sekunden Delay belegt kein tatsächliches Alter ≤900 Sekunden einschließlich Transportlatenz. |
| Frankfurt normalisierter Snapshot | BID/ASK, Originalzeit, Marktstatus, MIC und Delay sind transportierbar. | Kalender-/Sitzungsbezug und instrumentbezogene aktuelle Versorgung sind gesondert zu belegen. Der öffentliche Websitepfad liefert dagegen Last/Previous Close. |
| Stuttgart delayed | Genaue ISIN/MIC/Währung, Originalzeit und Seitenvalidierung. | Kein vollständiger verifizierter Kalender-/Markt-offen-Bezug und hier kein lokaler Feednachweis. |
| EODHD | Bestehende Basiswert-EOD-Versorgung. | Optionsschein-Bid/Ask wird im Adapter ausdrücklich abgewiesen; kein historischer Intraday-Trade-Nachweis aus OHLC. |

Die [Quellenqualifikation vom 30.10.2026](../reviews/ISSUER_QUOTE_QUALIFICATION_2026-10-30.md)
ordnet #220 bereits als historische Forschung ein. Deren frühere technische
Beobachtungen sind keine heutige Liveabdeckung oder zusätzliche Nutzungsfreigabe.
Dieser Anhang führt keine neue Providerzustimmung, Beschaffung oder Aktivierung
ein. Verifizierte Kalenderabdeckung, produktbezogene Schluss-/Handelstermine,
tatsächliche Originalgeldkurse und historische Basiswert-Trades bleiben pro
Instrument nachzuweisen. Eine Regel mit fehlenden Belegen bleibt konkret nicht
beurteilbar; eine Datenlücke beendet insbesondere keine Verlustepisode.

Die hier genannten bestehenden Tests für Quotehistorie, Retention,
Produktbelegrevisionen und Risikoreader sind wiederverwendbare Regressionen,
aber wurden für diese lesende Teilprüfung nicht ausgeführt. Im späteren F207-3-
Schnitt sind insbesondere verkürzte Sitzungen, Zeitzonen, Deckungslücken, Alter
genau 900 Sekunden und die zwischen Kurs- und Abrufzeit endende 20. Sitzung zu
prüfen. Kalenderintegration und B04/B05/B06/B57-Auswertung bleiben Folgeschritte.

<a id="f207-4-evidence-read"></a>
## F207-4: implementierter Evidenzvertrag und Positionsconsumer

### Umfang und verbleibende Grenze

Dieser additive Schnitt verbindet vorhandene wirtschaftliche Fakten mit
nachvollziehbaren historischen Belegen. Er implementiert die Referenzen auf die
ursprüngliche Auftragsgruppe, effektive Teilausführungen, ursprüngliche
Z1-Bezugsmenge, historische Basiswert-Trades, tatsächlich zugeordnete
Z1-Verkäufe und eine genau gebundene bestätigte Hebeltrader-Quellenversion.
Die Positionsdetails zeigen die Abdeckung und konkrete Lücken dieser Eingaben.

Das ist **der vorgelagerte Evidenz- und Abdeckungsteil von F207-4**. Er liefert
keine Baseline-Regelauswertung, keine Zielereignisse, Schutzvorschläge,
Kalenderintegration oder Meldungszustände. B07 bleibt eigenständig, B08
ausgeschlossen. Eine neue Verlagsquelle aktiviert keine Regelversion. Auch bei
vollständigen Belegen bleiben `implementation_status=F207_4_EVIDENCE_ONLY` und
`operation_status=NOT_ASSESSED` erhalten.

**Anpassungsgrenze innerhalb F207-4:** Dieser erste Schnitt berechnet keine
Split- oder Produktnormalisierung. Ein ausdrücklich belegter unveränderter
gemeinsamer Originalmaßstab ist vergleichbar. Unterschiedliche Maßstäbe oder
`ADJUSTMENT_REQUIRED` sperren die betroffene Preisgewichtung sichtbar.
Die spätere Anbindung verifizierter Market-Data-/Produktanpassungen muss deren
Owner, Originale und einmalige Anwendung erhalten; ein Basiswertsplit verändert
hier weder Optionsscheinmenge noch Kosten oder Produktbedingungen.

### Producer, Consumer und historische Zuordnung

| Vertrag | Owner / Verantwortung |
| --- | --- |
| `read_position_execution_basis(session, trade, position_id)` | Trade Position: derselbe vorhandene Projektionsgang liefert komplette Korrekturhistorie, effektive Ausführungen, qualifizierte Bewertungsbasis und BUY-Restgewichte. Bestehende Geldarithmetik und `position-unrealized-gross-v1`-Basisidentität bleiben erhalten. |
| `HebeltraderSourceReader.read(...)` | Learning: exakte historische Version, Workspace-/Produkt-/Basiswertgrenzen, bestätigte PDF-Annahmerow und Dateihash; strukturierte Produkt- und Basiswertmarken bleiben getrennt. Keine Artikeltexte oder neue Quellenannahme. |
| `HebeltraderEvidenceDeclaration` / Revision | Trade Position: ausschließlich Referenzen und neue historische Beobachtungsbelege; keine kopierte Ausführungshistorie. Eindeutige Vorgangskennung und Vorgängerrevision sichern Wiederholung und konkurrierende Änderungen. |
| `HebeltraderEvidenceReader` | Trade Position: kurzer PostgreSQL-Snapshot mit `REPEATABLE READ READ ONLY`, ohne Autoflush und mit Rollback. Kein Provider, Command, Regelzyklus oder Zustellpfad. |
| `HebeltraderEvidenceCoverage` in `PositionDetails` | Operational Workspace: Darstellung des öffentlichen Reads; keine eigene Mengen-, Währungs-, Regel- oder Qualitätsrechnung. Bestehender Ausführungseditor und dessen Entwürfe werden nicht verändert. |

Die Einstiegsgruppe benötigt einen ausdrücklichen Orderbeleg und die zugehörigen
Execution-IDs. Ihre vollständige Mitgliedschaft wird bestätigt; weder Uhrzeitnähe
noch alle BUYs eines Trades ersetzen diese Angabe. Die Bezugsmenge ist die Summe
genau dieser effektiven Fills. Ein späterer Nachkauf wird niemals automatisch
Mitglied. Eine Korrektur folgt der vorhandenen expliziten Kette derselben Seite;
Original-ID, Korrekturkette und aktuelle effektive ID bleiben sichtbar.

Ein historischer Tradebeleg referenziert genau einen BUY, Originalpreis,
`PriceBinding`, Maßstab, Herkunft und die geprüfte Auswahl als letzter geeigneter
Trade zum oder vor dieser Ausführung. Das ist eine ausdrückliche Quellenprüfung,
kein neu behaupteter Marktfeed. `observed_at` oder `observed_on` mit Quellzeitzone
erhalten die Genauigkeit; die serverseitige `recorded_at` der Revision hält die
spätere Erfassung. Ein gleicher Kalendertag ohne Uhrzeit beweist keine
Intraday-Reihenfolge. Ein früherer eindeutig abgegrenzter Tag kann sie belegen.
Eine korrigierte Kaufzeit verlangt eine erneute as-of-Zuordnung; unveränderte
Kaufzeit bei Mengen-/Preiskorrektur kann den vorhandenen Beleg weiterverwenden.
Es gibt keine pauschale 60-Sekunden-Nachtragsgrenze.

Die persönliche Basiswertgewichtung verwendet ausschließlich die Restbeiträge
aus `PositionProjector.project_with_trace`. Nach BUY 100, SELL 40 und BUY 20
werden 60 und 20 gewichtet; verkauftes Gewicht wird nicht erneut einbezogen.
Fehlende Teilbelege verkleinern den Nenner nicht. Der aktuelle persönliche
Basiswerteinstieg bleibt dann unbekannt. Ein vollständig belegter ursprünglicher
Gruppenwert bleibt unabhängig von einer späteren Nachkauflücke lesbar. Diese
analytischen Mengenbeiträge sind keine FIFO- oder Steuerbuchhaltung.

Eine vorhandene unveränderte initiale TradeLink-Version darf ihre bereits
explizite historische Quellenversion liefern. Mehrdeutige oder nachträglich
geänderte Links erzeugen keine automatische Auswahl. Bei der ersten bewussten
Belegbestätigung wird ein wiederverwendeter Pin in der Revision gesichert;
spätere Reads folgen ausschließlich diesem Pin. Bewusst entfernte oder ersetzte
Pins werden nicht durch eine aktuelle Empfehlung aufgefüllt.

Z1-Verkäufe benötigen echte SELL-IDs und ausdrückliche Belegzuordnung. Eine
geprüfte leere Zuordnung bedeutet null zugeordnete Verkäufe; eine ungeprüfte
Zuordnung bleibt unbekannt. Kein Zieltreffer, Gesehen-Status oder 50%-Richtwert
erzeugt eine Verkaufsausführung oder eine vorgeschlagene Ordermenge.

### Schmaler API-Vertrag

| Methode / Pfad unter `/api/v1/trade-position/trades/{trade_id}` | Verhalten |
| --- | --- |
| `GET /hebeltrader-evidence?position_id={position_id}` | Abdeckung aus einem Snapshot. `position_id` ist genau einmal erforderlich; fremde Positionen werden abgewiesen. |
| `GET /hebeltrader-evidence/history?position_id={position_id}` | Unveränderte Revisionen samt Deklarationen, Vorgängern und Erfassungszeiten. Kein Quellenrefresh. |
| `POST /hebeltrader-evidence` | Ausdrücklich bestätigte vollständige neue Belegrevision; schreibt ausschließlich Evidenzreferenzen. Keine Ausführung, Regelaktivierung oder Nachricht. |

Der POST enthält `position_id`, eine neue `request_id`, den genau gelesenen
`supersedes_evidence_id` (beim ersten Beleg `null`),
`confirmation="CONFIRM_HISTORICAL_EVIDENCE"` und `declaration`.
Die Deklaration kann unvollständig sein; vorhandene Belege werden in der neuen
Revision ausdrücklich mitgeführt. Frühere Revisionen bleiben unverändert.
Identische Wiederholung derselben Vorgangskennung erzeugt keine neue Revision;
abweichender Inhalt oder veralteter Vorgänger liefert einen Konflikt.

Die begrenzten Deklarationsfelder sind:

- `entry_order`: `source_reference`, ausdrücklich bestätigte `execution_ids`
  und `complete`;
- `source_version_id`: feste historische Version aus dem vorhandenen PDF-Owner;
- `underlying_trades`: je BUY `execution_id`, `source_reference`, `price`,
  `binding`, `scale_reference`, `last_trade_verified`, `price_kind="TRADE"`
  und entweder genauer Originalzeitpunkt oder Originaldatum mit Quellzeitzone;
- `z1_sales`: tatsächliche SELL-IDs mit `source_reference`, ergänzt um die
  ausdrückliche Prüfung `z1_sales_reviewed`;
- `source_scale_reference`, `scale_review_status` und `scale_review_reference`:
  nachvollziehbarer gemeinsamer Maßstab oder sichtbarer Anpassungsbedarf.

Keine Währungs-, Kalender- oder unbekannten Kurswerte werden beim Benutzer als
Schätzung abgefragt. Bereits qualifizierte historische Währungsevidenz wird über
den bestehenden Resolver gelesen. Die Ausnahmen können über diesen schmalen
Command ergänzt werden; dieser PR baut dafür keinen zusätzlichen Editor.

`definition_version="hebeltrader-evidence-v1"` bindet das Readformat.
`coverage_status` ist `COMPLETE`, `INCOMPLETE` oder `CONFLICTED` **nur für diese
Evidenzmenge**. Die einzelnen `items` unterscheiden `PRESENT`, `MISSING`,
`CONFLICT` und `UNSUITABLE`, benennen betroffene spätere B-Regeln, konkrete
Klärung und Referenzen. `valuation_basis` bleibt der vorhandene Ownernachweis;
`execution_links` ergänzen Original-/Korrektur-/effektive IDs und Zeitgenauigkeit.
Quellenversion, Dateihash, Ausgabedatum, Import-/Annahme-/Erfassungszeit sowie
Lesebeginn/-abschluss sind getrennt. Gleiche Fakten ergeben dieselbe `basis_id`;
der Lesetakt ändert sie nicht. Ein Lesefehler bedeutet keine fehlende Evidenz.

### Integration, Prüfung und Übergabe

Die additive Migration `20261114_0050` folgt dem tatsächlich geprüften einzigen
Kopf `20261109_0049`. Sie ergänzt Revisionen und abgeleitete FK-Schutzreferenzen,
ändert keine bestehenden Depotfakten und erzeugt keinen Backfill. Datenbankguards
sichern Identitäten, Korrekturvorgänger, Chronologie und Unveränderlichkeit.
Ein Downgrade mit vorhandenen neuen Belegen wird wegen Datenverlust verweigert.

Vor Umsetzung wurden alle neun offenen PR-Dateilisten geprüft. #335 besitzt
keine Dateiüberschneidung mit diesem Schnitt. #207 enthält weiterhin nur seinen
Exporthelper; kein Gesamtpatch und keine historische Migrationsnummer wurden
übernommen. Die fünf UX-Koordinationsdateien aus #342 bleiben unberührt. Die
Überschneidungen mit #341/#315 betreffen die gemeinsame Backlogdatei; dieser PR
ändert darin ausschließlich den bestehenden Monitoringeintrag, deren andere
Einträge bleiben erhalten. Der oben benannte Read/Consumer ist die begrenzte
Ownervereinbarung für diese neue Positionsfläche, kein neuer allgemeiner Dashboardvertrag.

Gezielte synthetische Tests liegen bei Trade Position und Learning; sie prüfen
Gruppen/Nachkäufe, Restgewichtung, fehlende/zukünftige/ungenau datierte Belege,
Korrekturketten, fremde Identitäten, Währung/Skala, historische Quellenpins,
Idempotenz und konfliktgesicherte Revisionen. PostgreSQL-Tests verwenden eine
eindeutig geprüfte Wegwerfdatenbank und gesperrte externe HTTP-Aufrufe. UI-Tests
sichern Positionswechsel einschließlich A→B→A, verspäteten Erfolg/Fehler,
unveränderte fremde Eingaben und ausschließlich lesende Wiederholung.
Die bestehenden E2E-Wegwerfprüfungen erwarten weiterhin genau einen verifizierten
Migrationskopf; ihre Schemaerwartung wird mit dieser Migration von `0049` auf
`0050` nachgeführt. Isolation, Datenbankidentität und übrige Gates bleiben erhalten.
Tatsächliche Prüfergebnisse werden im [PR #344](https://github.com/burckhju/trading-workspace/pull/344)
an dessen Head und Testmerge gebunden; übersprungene Prüfungen sind kein Erfolg.

Die Backendpfade `POST /trade-position/purchases/external` und der Learning-
`execute-as-trade` sind vorhanden; Main besitzt dafür keinen direkten
Frontendaufruf. Für die Evidenz bestehender Positionen ist kein neuer Kaufdialog
erforderlich. Eine Empfehlung erzeugt weiterhin keine Depotbuchung; ein
universeller Brokerimport oder eine Depotsynchronisation ist nicht enthalten.

Die damalige Übergabe an F207-2 benötigt diese Referenzen für dauerhafte Zielereignisse und
Schutzvorschläge; F207-3 benötigt zusätzlich die im vorigen Anhang definierten
verifizierten Kalender-/Termin-/Originalkursverträge; F207-5 ergänzt erst den
Regel-/Meldungslebenszyklus und dessen Aktivierung. Reale Positionsbelege,
Installationsstand und laufende Provider-/Zustellzustände auf dem Nutzer-PC
sind ein späterer gesonderter Betriebsnachweis. Merge, Release, Installation,
produktive Datenkorrektur, Providerzustimmung und echte Nachrichten gehören
nicht zu diesem Draft-Auftrag.

<a id="f207-2-target-history"></a>
## F207-2: erster Schnitt für dauerhafte Z1-/Z2-Nachweise

### Nutzungsverhalten und genaue Grenze

Dieser Folgeschritt basiert auf dem integrierten F207-4-Main
`e6738c291b0701d00cce20a370aba7496a9f24d0`. Die vorhandenen Positionsdetails
erhalten einen Zielhistorienblock. Öffnen und Aktualisieren lesen ausschließlich
gespeicherte Fakten. Erst **„Gespeicherte Belege prüfen“** startet einen ausdrücklich
bestätigten Prüflauf über vorhandene Kursdaten. Er hält Ergebnis, originale
Preisbelege, Eingangsstand, Vergleichsfreigabe und Vorgänger unveränderlich fest.

Implementiert ist der **Z1-/Z2-Evidenz- und Verlaufsteil von F207-2**: ein
qualifizierter ursprünglicher Zielnachweis, die einmalige ursprüngliche
50-%-Orientierung nach Z1, der Prüfhinweis für den Restpositionsausstieg nach Z2
und eine persönliche Einstandsschutz-Prüfgrundlage. Letztere ist ausdrücklich
**kein bekanntgegebener oder überwachter Schutzvorschlag**. Die nachfolgenden
F207-2-Teile bleiben offen: historische dokumentierte Stopberührungen,
gleichzeitige Stop-/Zielkonstellationen, höherer vergleichbarer Schutzboden,
Bekanntgabezeitpunkt und anschließende Schutzüberwachung sowie deren
Korrekturfreigabe. B06 benötigt weiter den F207-3-Kalendervertrag.

Die Oberfläche trennt `PROVEN`, `NOT_PROVEN`, `NOT_ASSESSABLE` und
`REVIEW_REQUIRED`. `NOT_PROVEN` bedeutet ausschließlich, dass die verfügbaren
geeigneten Belege keinen Treffer nachweisen. Es bestätigt keine lückenlose
Kalender-/Kurshistorie und keine Entwarnung. `CHANGED_INPUTS` kennzeichnet einen
gespeicherten Prüfstand mit inzwischen veränderter Basis sofort als historisch.
`F207_2_TARGET_HISTORY_ONLY` und `NOT_ACTIVATED` bleiben getrennt sichtbar; eine
vollständige Hebeltrader-Baseline oder ein laufender Betriebszustand folgt daraus
nicht. Das bisherige generische Monitoring und die F207-4-Abdeckungsanzeige
behalten ihre eigenen Aussagen.

### Bestehende Owner und neuer schmaler Vertrag

| Vertrag | Verantwortung und Grenze |
| --- | --- |
| `read_hebeltrader_monitoring_basis(session, workspace_id, trade_id, position_id, lock=False)` | Trade Position liefert denselben vorhandenen Ausführungs-/Korrektur-/Währungs-/Restmengen-/Einstandsowner wie F207-4. Hinzu kommen feste Evidenzrevision, bestätigte Quelle und Richtung aus dem vorhandenen Produktbedingungs-Owner. Fehlende oder widersprüchliche historische Richtung bleibt unbekannt. Keine zweite Bestandsrechnung. |
| `HebeltraderHistoryReader.read(..., listing_id, start_date, end_date, known_at)` | Market Data liest ausschließlich gespeicherte originale Tageskurse und aktuelle Listing-/Venue-Referenzen. Workspace, Basiswert und optionale Dateninstrument-Zuordnung werden geprüft. Ein bestehendes eindeutig aktives Primary-Listing dient einmalig der Auswahl; nach einer gespeicherten Prüfung bleibt dessen Listing-ID gebunden. |
| `evaluate_hebeltrader_targets(...)` | Reine Funktion des bestehenden Monitoring-Owners. Preisqualifikation, dauerhafte Zielbelege, ursprüngliche Orientierung und getrennte aktuelle Auswertbarkeit; keine ORM-, Provider-, Order- oder Zustellabhängigkeit. |
| `HebeltraderTargetReader` | Eigener kurzer `REPEATABLE READ READ ONLY`-Snapshot, ohne Autoflush, mit Timeout und Rollback. Lesen erzeugt keinen neuen Prüflauf. |
| `HebeltraderTargetService.assess(...)` | Expliziter Command, konsistenter Snapshot und vorhandene Trade-Sperre; unveränderliche Bewertungskette und idempotente Vorgangsbelege. Keine Ausführungsbuchung, Aktivierung, Alert-/Notification-Erzeugung oder Providerabfrage. |
| `HebeltraderTargetHistory` in `PositionDetails` | Ephemerer Consumer mit genau gebundenem Trade/Position/Basisstand. Er zeigt Ownerwerte, ohne Mengen, Preise oder Regeln selbst zu berechnen. |

Die gespeicherte Kursreihe bleibt auf **UNDERLYING** beschränkt; Warrantpreise
werden hier nicht mit Basiswertmarken verglichen. Der erste Schnitt qualifiziert
die bestätigte aufsteigende CALL-Konstellation. PUT, unbekannte Richtung oder
widersprüchliche Zielreihenfolge erhalten einen konkreten Sperrgrund. Die
Bestätigung einer Regelbasis ersetzt keinen fehlenden Instrument-/Richtungsbeleg.

Der Market-Data-Read erhält Originalzeilen-ID, Fingerprint, OHLC-Werte,
Währung, Provider/Symbol, Warnungen und getrennte Quellaktualisierungs-, Abruf-,
Anlage- und Änderungszeiten. Er liest maximal 5.000 Zeilen vollständig; bei
Überschreitung gibt es keinen still gekürzten Auswertungsbereich. Ein vollständiger
gespeicherter Bereich belegt noch keine vollständige Folge von Handelssitzungen.
Momentane Listing-/Venue-Daten tragen weiterhin
`CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED`.

### Zeit, Preismaßstab und wenige tatsächliche Ausnahmen

Ein Tageshoch kann Z1 beziehungsweise Z2 einschließlich exakter Schwelle belegen,
wenn das vollständige lokale Tagesintervall nach dem belegten eigenen Einstieg
liegt. `DATE_ONLY` wird als ganzer lokaler Kalendertag mit exklusivem Ende
behandelt, einschließlich Zeitumstellung. Das ist keine behauptete Handelssitzung
oder Trefferuhrzeit. Der Kauftag eines nur tagesgenauen Kaufs wird nicht als
nachträglicher Treffer verwendet. Quellaktualisierung, Abruf und spätere Erfassung
werden niemals zum wirtschaftlichen Ereigniszeitpunkt umgedeutet.

Auch die historische Quelle muss vor dem betrachteten Ereignis verfügbar gewesen
sein. Der PDF-Owner belegt ihr Ausgabedatum, nicht Publikationsuhrzeit oder
Verlagszeitzone. Deshalb muss der Kursintervallbeginn außerhalb der gesamten
möglichen Datumsgrenze liegen: spätestens endet dieser Unsicherheitsbereich am
Folgetag um 12:00 UTC bei UTC−12. Diese konservative Grenze ist **keine erfundene
Publikationszeit**. Ein früherer unklarer Tag sperrt keinen späteren geeigneten
Beleg. Import-/Annahme-/Erfassungszeit bleiben gesondert erhalten.

F207-4 bestätigt gegebenenfalls den gemeinsamen Maßstab von Quelle und
historischen Kaufbelegen. Diese Bestätigung gilt **nicht automatisch für neu
hinzukommende Tageskurse**. Hierfür ist eine zusätzliche konkrete Qualifikation
von historischer Listingbindung und unverändertem Originalmaßstab erforderlich.
Sie bindet genau den History-Fingerprint, Listing-Fingerprint, die historische
Quellenversion, deren Skalenreferenz und eine Belegreferenz. Ein nominell passender
Provider oder eine übereinstimmende Währung allein genügt nicht.

Eine solche Qualifikation kann über den unten beschriebenen Command erfasst
werden; der ursprüngliche F207-2-Schnitt ergänzt dafür keinen eigenen Editor.
Der anschließende [Vergleichsbeleg-Schnitt](#f207-3-history-qualification) ergänzt
die konkrete Prüfung und Bestätigung in den Positionsdetails. Ohne den zusätzlichen
Beleg liefert auch der Prüfbutton einen gespeicherten, verständlich begründeten
Status `NOT_ASSESSABLE`. Bereits passende Qualifikationen desselben Eingangsstands
werden wiederverwendet; keine erneute Eingabe ist nötig. Eine erweiterte oder
korrigierte Reihe verlangt vor neuen Treffern eine zu ihr passende Qualifikation.
Ein reiner Tageswechsel oder erneuter Abruf identischer bereits geeigneter
Originalkurse entwertet die Qualifikation nicht. Abruf- und Speicheränderungszeit
bleiben im Audit erhalten; Quellenzeit, Originalwerte, Identitäten und tatsächliche
Eignungsänderungen bleiben Teil des Vergleichsstands.
F207-3 muss später die wiederverwendbare verifizierte Beschaffung ergänzen.
Dies ist die wesentliche Bedien- und Betriebsgrenze dieses ersten Schnitts.

Abweichendes `adjusted_close`, Split-/Anpassungswarnungen oder widersprüchliche
Originalbelege sind sichtbare Prüfungsindizien. Daraus wird weder ein Split
behauptet noch ein Faktor abgeleitet. Selbst eine pauschale Bestätigung des
unveränderten Maßstabs ersetzt keine benötigte verifizierte Anpassungsevidenz.
Eine spätere Normalisierung bleibt beim bestehenden Market-/Produktowner.

### Dauerhaftigkeit, Korrektur und Mengen

Die Ereignisidentität ist pro Workspace, Position, Baselineversion und Z1/Z2
stabil. Kursrückgang, Neustart, Nachkauf oder eine spätere Kursdatenlücke löschen
einen ursprünglich belegten Treffer nicht. Die aktuelle Vergleichbarkeit der
Eingangsreihe wird separat ausgewiesen. Die ursprüngliche Quelle, Skala,
Marke, Kurszeile, Tagesintervall und Feststellungszeit bleiben pro Ziel sichtbar,
auch wenn ein späterer Prüflauf eine andere Quellenbasis besitzt.

Erkannte Änderungen an Quellengrundlage, Kaufzeit, Produktrichtung,
Listingreferenz oder ursprünglichem Kursbeleg setzen `REVIEW_REQUIRED` und
erhalten den Originalproof unverändert. Eine weitere normale Auswertung hebt
diesen Klärungsbedarf nicht auf. Ein zusätzlicher fachlicher Freigabe- oder
Verwerfungscommand für korrigierte Zielereignisse gehört zum folgenden
F207-2-Schnitt; bis dahin werden daraus keine neuen Handlungshinweise abgeleitet.

Die ursprüngliche Z1-Menge kommt ausschließlich aus der belegten Einstiegsgruppe.
Nachkäufe erhöhen sie nicht. Ausgegeben werden Anteil `0.5`, ursprüngliche Menge
und ausdrücklich zugeordnete tatsächliche Z1-Verkäufe; keine gerundete oder
verbleibende Ordermenge. Teilverkauf und Nachkauf verwenden für Restmenge und
persönlichen Basiswerteinstand die vorhandenen Ownerbeiträge. B03 steht bei
gleichzeitigem Z1-/Z2-Treffer vor der Z1-Orientierung; alle belegten Ursachen
bleiben erhalten. Ein Treffer erzeugt keinen SELL. Geschlossene/stornierte
Positionen sind historisch lesbar und erhalten keinen neuen Prüflauf.

### API, Migration und Prüfnachweise

| Pfad unter `/api/v1/position-monitoring/trades/{trade_id}` | Vertrag |
| --- | --- |
| `GET /hebeltrader-targets?position_id=...` | Aktuelle Eingangsreferenzen, gespeicherter letzter Prüfstand, Anzahl, Aktualität und lesbare Lücken; keine neue fachliche Bewertung. |
| `POST /hebeltrader-targets/assessments` | Ausdrückliche neue Prüfung gespeicherter Belege; vollständige unveränderliche Ergebnisrevision oder Wiederverwendung identischer letzter Eingaben. |
| `GET /hebeltrader-targets/assessments/{assessment_id}?position_id=...` | Exakt zugeordneter Auditstand mit Originaleingängen, Ergebnis und Vorgänger; unverändert auch nach späteren Korrekturen lesbar. |

Der POST benötigt `position_id`, `request_id`, den genau gelesenen
`expected_basis_id`, `expected_assessment_id` (anfangs `null`) und
`confirmation="ASSESS_SAVED_HEBELTRADER_EVIDENCE"`. Optionales `qualification`
enthält `history_fingerprint`, `listing_fingerprint`, `source_version_id`,
`source_scale_reference`, `evidence_reference` sowie ausdrücklich
`confirmation="CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE"`.
Veraltete Basis/Vorgänger erzeugen 409; falsch gebundene Qualifikation erzeugt
422. Gleiche Vorgangskennung mit gleichem Inhalt schreibt nichts erneut,
abweichender Inhalt erzeugt einen Konflikt. Gleiche aktuelle Eingaben mit neuer
Vorgangskennung erhalten lediglich einen Wiederholungsbeleg, kein zweites
Zielereignis. Eine unklare POST-Antwort löst keinen automatischen Retry aus; die
Oberfläche verlangt zunächst einen bewusst ausgelösten erfolgreichen Read.

Der Writer erwirbt die vorhandene Trade-Sperre unter `READ COMMITTED`. Erst
nach deren Erhalt beginnt ein separater kurzer `REPEATABLE READ READ ONLY`-
Snapshot für alle Owner- und Marktinputs. So bleibt eine während des Wartens
abgeschlossene additive Evidenzkorrektur sichtbar und wird durch den Basisvergleich
erfasst. Die Sperre bleibt bis zum atomaren Append/Receipt-Commit erhalten.
Auch ein ungeeigneter historischer Quellenpin samt Ablehnungsgründen wird im
Audit gespeichert, ohne ihn zur gültigen Vergleichsquelle hochzustufen.

Die additive Migration `20261114_0051` folgt dem einzigen aktuellen Kopf
`20261114_0050`. Sie ergänzt `hebeltrader_target_assessments` und
`hebeltrader_target_requests`, ohne Backfill oder Änderung von Depotfakten.
FK-/Scope-/Quellen-/Vorgänger-/Chronologieguards, genau ein Wurzelstand und
höchstens ein Nachfolger je Revision sichern die Kette. Änderungen/Löschungen
und ein Downgrade mit vorhandenen Zielbelegen werden verweigert. Die vorhandenen
E2E-Wegwerfguards werden exakt auf den neuen Kopf nachgeführt; Identitätsprüfung,
Isolation und übrige Gates bleiben unverändert.

Gezielte Tests prüfen Ownerwiederverwendung, konservative Zeitgrenzen,
Publikationsdatum, Skala/Preisachse/Währung, Korrekturen, unveränderliche
Originalbelege, Replays/Konflikte, reinen GET und verspätete UI-Antworten samt
A→B→A. PostgreSQL-Guards laufen ausschließlich in eindeutig identifizierten
synthetischen Wegwerfumgebungen mit gesperrten externen HTTP-Aufrufen.
Reguläre Prüfergebnisse und verbleibende Umgebungsgrenzen werden im zugehörigen
PR an tatsächlichen Head und Integrationsstand gebunden; übersprungene Prüfungen
gelten nicht als bestanden.

### Übergabe

Der verbleibende **F207-2-Schnitt** ergänzt historische dokumentierte Stops,
vergleichbaren höheren Schutzboden, Vorschlagsbekanntgabe und anschließende
Überwachung sowie explizite Korrekturklärung. **F207-3** ergänzt verifizierte
historische Referenz-/Skalen-/Anpassungsbelege, Kalender, Produkttermine und
regelgeeignete Originalkurse einschließlich B04/B58; der neue gespeicherte
History-Read ist dafür wiederverwendbar, kein Ersatz für Kalender- oder
Providerqualifikation. **F207-5** ergänzt Regel-/Meldungslebenszyklus, Aktivierung
und Zustellzustände. B07 bleibt eigenständig, B08 ausgeschlossen. ATR, Phase,
Score und Risiko behalten ihre Bedeutung. Neue Quellen aktivieren keine
Regelversion. Release, PC-Installation, produktive Korrektur, neue
Providerzustimmungen und echte Nachrichtentests benötigen einen gesonderten
Auftrag.

<a id="f207-3-history-qualification"></a>
## F207-3: konkrete Prüfung historischer Vergleichsbelege

### Abgegrenzter Anschluss und vorhandene Daten

Dieser Schnitt setzt auf Main `6efa74d3bd0978c7ef8975fdc9c506de7a0aa348`
mit dem integrierten Zielhistorien-PR #345 auf. Er schließt dessen konkreten
Bedienengpass: Die bereits vorhandene zusätzliche Vergleichsqualifikation lässt
sich anhand der gespeicherten Originalbelege in den Positionsdetails prüfen und
ausdrücklich bestätigen. Er implementiert **weder den vollständigen F207-3-Vertrag
noch eine automatische historische Quellenverifikation**.

Die gespeicherten Ownerfakten liefern Identität, technische Qualität, Originalwerte
und Zeitangaben. Aktuelle Listing-/Venue-Versionen und technische Providerzuordnungen
beweisen aber keine historische Gültigkeit. Beispielsweise übernimmt der vorhandene
EODHD-Mapper die Währung aus dem Listingkontext; zwei gleiche Währungsfelder sind
deshalb keine zwei unabhängigen historischen Nachweise. `VALID`, ein Providername
oder ein technischer Symbolabgleich ersetzt keinen belegten gemeinsamen Maßstab.

Die zusätzliche Bestätigung bleibt eine **ausdrückliche Nutzererklärung mit konkreter
Belegreferenz**. Die Software prüft ihre exakte Bindung und die technischen
Voraussetzungen, verifiziert den Inhalt des externen Nachweises aber nicht
unabhängig. Eine Referenz soll Dokument, datierten Quellenstand und relevante
Fundstelle benennen und tatsächlich die historische Zuordnung sowie den
unveränderten Originalmaßstab tragen. Es gibt keinen automatischen Abruf beliebiger
URLs und keine pauschale Freigabe durch Providername, Währung oder ein Kontrollkästchen.

### Öffentliche Reads beim bestehenden Monitoring-Owner

| Pfad unter `/api/v1/position-monitoring/trades/{trade_id}` | Vertrag |
| --- | --- |
| `GET /hebeltrader-targets/qualification-preview?position_id=...` | Konsistenter Vergleichsbeleg-Read mit dem bisherigen Report, Einstieg, exakter historischer Quelle, F207-4-Skalenbezug, vollständigem gespeicherten Kursbestand, getrennten Voraussetzungen und vorhandener Nutzererklärung. |
| `GET /hebeltrader-targets/requests/{request_id}?position_id=...` | Ausschließlich der zu Trade/Position/Workspace gehörende Vorgang: `RECORDED` mit seinem ursprünglichen Prüfstand und seiner Erklärung oder `UNKNOWN`. Kein neuer Prüflauf und keine Bestätigung eines anderen Requests. |

Beide Reads verwenden die bestehende eigene `REPEATABLE READ READ ONLY`-Session,
ohne Autoflush, mit Timeout und Rollback. Die Ausführungswahrheit bleibt beim
Trade-Position-Owner. Quelle und Kurse kommen aus den bestehenden Learning- und
Market-Data-Readern. Es werden keine Kurse beschafft, Ausführungen gebucht,
Regelversionen aktiviert, Alerts erzeugt oder Nachrichten zugestellt.

Der Preview enthält den **Report aus demselben Snapshot**. Dessen
`current_basis_id` und letzter Assessment-ID sowie die separat ausgegebene
`qualification_binding` sind die Bindung für den unveränderten bestehenden
Assessmentcommand. Ein früherer separat gelesener Report darf diese Tokens nicht
ersetzen. Identität, Originalmarken, Währung, Fingerprints und Quellenversion werden
übernommen; sie müssen nicht erneut vom Nutzer eingegeben werden.

Die gesamte gespeicherte Reihe bleibt bis zur vorhandenen Grenze von 5.000 Zeilen
lesbar. Eine seitenweise Darstellung ändert den bestätigten Bereich nicht. Eine
Limitüberschreitung oder ein unvollständiger Read ergibt keine scheinbar vollständige
Bestätigung. Originalzeilen, OHLC, Adjusted Close, Provider/Symbol, Qualität,
Warnungen, Fingerprints sowie Quellaktualisierung, Abruf, Anlage und spätere
Änderung bleiben unterscheidbar. Listingprovenienz bleibt
`CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED`; `DATE_ONLY` und lokale Tagesintervalle
bleiben erhalten. Es entstehen keine erfundenen Sitzungs- oder Trefferzeiten.

### Getrennte Aussagen und unveränderte fachliche Prüfung

`review_hebeltrader_target_inputs` prüft ausschließlich die vorhandenen
Vergleichsvoraussetzungen. Derselbe reine Zeilenprüfer wird von der anschließenden
Zielauswertung verwendet; es gibt keinen zweiten Preis-/Zeit-/Skalenalgorithmus.
Der Read erzeugt keine Qualifikation, keine Zielereignisse und keine Proofs.

| Aussage | Bedeutung |
| --- | --- |
| `REVIEWABLE` | Die Voraussetzungen erlauben die gezielte Nutzererklärung für diesen Stand; mindestens eine Originalzeile ist danach technisch verwendbar. Kein bereits ausgewerteter Zieltreffer. |
| `BLOCKED` | Globale Voraussetzungen fehlen oder keine gespeicherte Zeile ist technisch geeignet. Die Gründe bleiben sichtbar; keine gültige Commandbindung wird angeboten. |
| `NOT_APPLICABLE` | Geschlossene/stornierte Position; vorhandene Belege bleiben lesbar. |
| `SUITABLE_AFTER_CONFIRMATION` / `UNSUITABLE` | Technischer Befund je Originalzeile. Ungeeignete Zeilen bleiben auch nach einer Erklärung gesperrt. |
| `MISSING` / `REUSABLE` / `STALE` | Getrennter Zustand der bereits gespeicherten Nutzererklärung; Wiederverwendbarkeit bedeutet exakte Bindungsgleichheit, nicht automatisch aktuelle Dateneignung. |

Bei einer übergeordneten Sperre kann die Zeilenprüfung entfallen. Die Originale
bleiben dann lesbar und als **nicht zeilenweise geprüft** gekennzeichnet; ein
fehlender Einzelbefund wird nicht in eine Ablehnung dieser Zeile umgedeutet.

Der ursprüngliche persönliche Einstieg und die konkrete Quellenskalenreferenz
werden weiterhin vom zuständigen Owner gelesen. Fehlt diese Referenz, zeigt der
Preview den tatsächlichen Blocker; er setzt keinen erfundenen Standardmaßstab ein.
Die F207-4-Bestätigung bleibt auf Quelle und Kaufbelege begrenzt und wird nicht auf
neue Marktdaten ausgedehnt. Anpassungsindizien, falsche Achsen/Währungen,
ungeeignete Zeiten und widersprüchliche Originale bleiben gesperrt. Ein bestehendes
`REVIEW_REQUIRED` wird durch die neue Vergleichserklärung nicht aufgehoben.

Eine unveränderte passende Erklärung wird ohne erneute Eingabe wiederverwendet.
Sie wird als **„enthalten in Prüfstand …“** mit dessen Zeitpunkt angezeigt. Dieser
Zeitpunkt oder Autor wird nicht zum ursprünglichen Bestätiger umgedeutet, weil eine
Erklärung in spätere Prüfstände übernommen werden kann. Neuer Kursbestand,
materielle Korrektur, andere Quelle oder Listingbindung benötigen weiterhin eine
passende Erklärung; identischer Neuabruf und reiner Tageswechsel allein nicht.

### Bedienung, Entwurf und unklarer Commandausgang

Die Belegansicht wird ausdrücklich im bestehenden Zielhistorienblock geöffnet.
Ein konkretes Referenzfeld und die inhaltlich bezeichnete Aktion bestätigen die
historische Listing-/Zeit-/Währungszuordnung sowie den gemeinsamen Originalmaßstab
mit genau dieser Quelle für den benannten gespeicherten Bereich. Der bestehende
`POST /hebeltrader-targets/assessments` bleibt der einzige Writer.

Der Operational Workspace hält den Formular- und Vorgangszustand ausschließlich
ephemer und getrennt nach Trade/Position im vorhandenen Positionshost. Schließen,
Filter, Seitenwechsel, ein Reload der Positionsdetails oder die globale Aktion
„Aktualisieren“ löschen den Entwurf nicht. Eine geänderte Basis erhält den Text
als bisherigen Entwurf, erfordert aber
die erneute Prüfung des neuen Stands. Der Entwurf gehört zur Lebensdauer der
Positionsübersicht; deren Verlassen oder ein Neuladen der Anwendung ist keine
persistierte Entwurfssicherung.

Beim bewussten Absenden werden Payload und `request_id` eingefroren. Verspätete
Antworten, A→B→A und unmountete Details dürfen keine fremden oder neueren Belege
überschreiben. Konkrete Ablehnung und unklarer Transport-/Schreibausgang bleiben
unterscheidbar. Ein unklarer Ausgang hält den unveränderten Vorgang fest; ein
beliebiger erfolgreicher Report-GET bestätigt nicht nachträglich genau diesen
Schreibvorgang.

Der gezielte Vorgangsread kann `RECORDED` anhand des gespeicherten Receipts belegen.
Er liefert dessen ursprünglichen Prüfstand, auch wenn inzwischen ein neuerer
existiert. `UNKNOWN` bedeutet ausschließlich, dass in diesem Lesesnapshot kein
passender Receipt sichtbar ist. Es beweist weder ein Scheitern noch einen laufenden
Vorgang und gibt keinen neuen Idempotency-Key frei. Eine bewusste Wiederholung
verwendet denselben eingefrorenen Command und dieselbe Kennung; kein automatischer
POST oder Retry. Die Ablehnung einer solchen Wiederholung beweist nicht das
Scheitern der ursprünglichen unbestätigten Sendung und erhält deshalb deren
unklaren Ausgang. Die bestehenden CAS-/Scope-/Replayprüfungen bleiben maßgeblich.

### Persistenz, Nachweise und nächste Abhängigkeiten

Die vorhandenen unveränderlichen Assessmentinputs speichern Quelle, vollständigen
Kursstand und konkrete Erklärung; der bestehende Receipt bindet den Vorgang.
Es entsteht keine zweite Kurs-, Ausführungs- oder Qualifikationshistorie.
**Keine Migration:** Der Migrationsgraph bleibt unverändert bei `20261114_0051`.

Gezielte Regressionen prüfen reine Reads, identischen Snapshot und CAS, fehlende
Quellenskala, gemischte geeignete/ungeeignete Originalzeilen, Daten-/Quellenwechsel,
deklarierte Wiederverwendung trotz gesperrter Eignung, unveränderte frühere Proofs,
Requestauflösung sowie Entwurfserhalt und verspätete Antworten. Der tatsächliche
PostgreSQL-Nachweis verwendet die vorhandene geschützte synthetische
Wegwerfumgebung mit abgefangenen externen Aufrufen. Reguläre Ergebnisse bleiben
an den tatsächlichen PR-Head/Testmerge gebunden; fehlende oder übersprungene
Prüfungen und der Nutzer-PC sind kein Erfolgsnachweis.

Verifizierte historische Beschaffung/Referenzgültigkeit, Anpassungsevidenz,
Basiswert-/Produktkalender, Produktfristen, historische Trades zum Kauf und
Original-BIDs bleiben weitere F207-3-Schritte. Insbesondere ersetzt dieser Read
keine B04-/B58-Prüfung auf offene verifizierte Sitzung, Originalzeit, höchstens
900 Sekunden Alter und bereits zum Kurszeitpunkt abgeschlossene 20. Basiswertsitzung.
B04/B05/B06/B57-Auswertung, restlicher F207-2-Schutzvertrag und F207-5-Aktivierung/
Zustellung bleiben getrennt. B07, der Ausschluss B08 sowie ATR-/Phase-/Score-/
Risikoverträge behalten ihre Bedeutung. Aufgabenstatus steht ausschließlich im
Product Backlog; VERSION, Providerzustimmungen und produktiver Betrieb werden
durch diesen Schnitt nicht geändert.

<a id="f207-3-session-evidence"></a>
## F207-3: Originalkalenderbelege und abgeschlossene Basiswertsitzungen

### Abgegrenzter Anschluss und Wirkung für die Position

Dieser Schnitt setzt auf Main `1d63d001216ef6f9294697f54707f3ae89a58ac4`
mit dem integrierten Vergleichsbeleg-PR #346 auf. Er implementiert den bislang
fehlenden gespeicherten Sitzungsevidenzvertrag bei Market Data und dessen ersten
Positionsconsumer. Der bestehende Trade-Position-Owner liefert den ursprünglichen
effektiven BUY; der neue Read zeigt abgeschlossene Basiswertsitzungen seit diesem
Tag 0 zum serverseitigen Prüfzeitpunkt. Bestehende Position, Instrumentidentität,
Ausführung und Kaufzeitgenauigkeit werden übernommen, ohne zusätzliche
Positionseingabe oder zweite Ausführungshistorie.

Ein dokumentiertes Kalenderpaket gilt für das ausdrücklich zugeordnete Instrument
und kann von allen zugehörigen Positionen wiederverwendet werden. In den
Positionsdetails erscheint ohne solches Paket die konkrete fehlende Evidenz.
Es gibt keinen Kalendereditor mit täglichen Nutzereingaben. Beschaffung und
inhaltliche Prüfung der Originalquelle bleiben vor dem bewussten Import nötig;
ein generischer Kalender, fehlende Kurszeilen oder der aktuelle Wochentag ersetzen
diesen Nachweis nicht.

**Dieser Schnitt ist keine B04-/B05-/B06-/B58-Auswertung.** Die Zahl bezieht sich
auf den angezeigten Lesezeitpunkt, nicht auf die Originalzeit eines Produkt-BID.
Produkttermine, Z1-bezogene Frist, Verlustepisode, Schutzvorschlag und laufende
Überwachung werden dadurch nicht hergestellt. Auch ein vollständiger importierter
Kalender ist ausdrücklich `MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION`:
Die Software prüft Struktur, Hashes und Bindungen, nicht unabhängig den Inhalt
der externen Quelle und keinen aktuellen Live-Marktstatus.

### Schreibender Owner und kleinster Originalpaketvertrag

`market_data` besitzt ausschließlich die neue Sitzungsevidenz. Market und Product
bleiben Owner von Basiswert-/Produkt-/Listing-/Venue-Identität; Trade Position
besitzt weiterhin effektive Ausführungen, Korrekturen, Restmenge und Einstand.

| Feldgruppe | Bewahrter Inhalt und Grenze |
| --- | --- |
| Originalmanifest | Unveränderter UTF-8-Text `manifest_json`, SHA256 und `schema_version=session-evidence-manifest-v1`. Doppelte JSON-Schlüssel, unbekannte Felder und ungültige Originalwerte werden abgewiesen. |
| Originalquelle | Tatsächliche Dokumentbytes als Base64, SHA256, Dateiname ohne Pfad und unterstützter Medientyp. Der Manifestbezug `source_document_sha256` muss exakt denselben Beleg benennen. Eine URL allein ist kein Importpaket; sie wird nicht abgerufen. |
| Historische Bindung | `instrument_kind` (`UNDERLYING` oder `WARRANT`), Instrument, Listing, Venue-ID/MIC, Marktsegment, IANA-Zeitzone, `valid_from` und `valid_through`. Kein implizites aktuelles Primary-Listing. |
| Kalenderstand | `calendar_id`, `calendar_version`, `coverage_start`, `coverage_end`; chronologisch geordnete, eindeutige Tagesbelege. Jede Revision ersetzt den vorigen Manifestinhalt vollständig. |
| Tagesbeleg | `session_date`, `status=SESSION/CLOSED/UNKNOWN`, konkrete Fundstelle und bei `SESSION` ein bis acht Originalintervalle mit Öffnung/Schluss und explizitem Offset. `CLOSED` und `UNKNOWN` haben keine Intervalle. |
| Quellenzeiten | Herausgeber/Fundstelle, bekannte Publikationsuhrzeit **oder** Publikationsdatum; beides darf fehlen, keine Uhrzeit wird erfunden. Bekannter Abrufzeitpunkt bleibt optional und getrennt. |
| Dokumentprüfung | Expliziter Prüfzeitpunkt, konkrete Prüfbelegreferenz und erfassender Actor. Menschliche Dokumentprüfung ist keine unabhängige Systemverifikation. |
| Revision/Vorgang | Serverseitiges `recorded_at`, Revisions-ID/-nummer, `supersedes_revision_id`, `request_id` und an Actor/Workspace/Paket gebundener Fingerprint. |

Die Grenzen sind 3.660 Kalendertage, 2.000.000 Manifestbytes und 2.000.000
Originaldokumentbytes. Übergrößen werden abgewiesen, nicht gekürzt. Unterstützt
sind PDF, JSON, CSV, Klartext und HTML als aufbewahrte Originalbytes; der Import
führt diese Inhalte nicht aus. Intervalle müssen zur lokalen Kalenderdatums- und
Offsetbindung passen, dürfen auch über Mitternacht reichen und sich weder innerhalb
eines Tages noch über Tagesgrenzen überlappen. Verkürzte Sitzungen und Pausen
bleiben ausdrückliche Originalintervalle.

Listing/Instrument/Venue/MIC werden gegen ihre tatsächlichen Ownerbeziehungen
geprüft. Die historische Zeitzone stammt aus der ausdrücklich geprüften Quelle;
eine spätere aktuelle Venue-Zeitzone schreibt sie nicht um. Der Read ist kein
vollständiger historischer Stammdatensnapshot: Eine inzwischen nicht mehr passende
Instrument-/Listing-/Venue-Zuordnung bleibt als ungeeignet sichtbar.

### Öffentliche Import- und Readschnittstellen

Alle Pfade dieser Tabelle liegen unter `/api/v1/market-data/session-evidence`:

| Schnittstelle | Vertrag |
| --- | --- |
| `POST /imports` | `SessionEvidenceRequest`: Originaltext und Bytes samt Hashes, `request_id`, erwartete `supersedes_revision_id` (beim ersten Import `null`), Prüfbeleg/Prüfzeit, optional Abrufzeit und ausdrücklich `confirmation=CONFIRM_OFFICIAL_SESSION_DOCUMENT_REVIEW`. Liefert die gespeicherte Originalrevision. |
| `GET /current` | Pflichtquery `instrument_kind`, `instrument_id`, zeitzonenbewusstes `known_at`; optional `expected_listing_id`. Liefert Revision, Bindung, Quelle und Eignungsgründe, noch keine vollständige Zeitraumabdeckung. |
| `GET` | Zusätzlich `start_date` und `end_date`; liefert sämtliche Originaltage im angefragten Bereich, `missing_dates`, Fingerprint und `COMPLETE/INCOMPLETE/MISSING/UNSUITABLE/LIMIT_EXCEEDED`. |
| `GET /revisions/{revision_id}` | Pflichtquery Instrumentart/-ID; liefert die exakt zugehörige ursprüngliche Revision einschließlich Originalmanifest und Base64-Dokument. Keine Umhängung auf den jüngsten Stand. |

Workspace und Standardactor folgen dem bestehenden lokalen API-Vertrag. Ein
Instrumentlock mit `READ COMMITTED`, Vorgänger-CAS und eindeutiger Requestbindung
verhindert verzweigte Revisionen. Ein identischer erneut gesendeter Vorgang liefert
seine ursprüngliche Revision; eine andere Payload oder ein anderer Actor mit
derselben Kennung ist ein Konflikt. Der Import erzeugt weder Trade noch
Ausführung, Regelversion oder Benachrichtigung.

Pro Workspace/Instrumentart/Instrument gibt es eine Revisionskette. Der Read wählt
deren letzten gespeicherten Stand mit `recorded_at <= known_at`. Revisionen werden
nicht zu einem scheinbar vollständigen Kalender gemischt. Eine Korrektur bewahrt
den Vorgänger; eine Rücknahme erfolgt mit einer neuen `WITHDRAWN`-Revision und
führt nicht zum stillen Rückfall auf ältere Belege. Eine neue Jahresquelle muss
deshalb den benötigten Gesamtbereich abdecken oder die verbleibende Lücke zeigen.

`COMPLETE` bezeichnet vollständige und strukturell geeignete **importierte
Tagesbelege im angefragten Bereich**. Fehlende Daten stehen in `missing_dates`;
explizite `UNKNOWN`-Tage bleiben als Originalzeilen mit eigenem Grund erhalten.
Beides verhindert `COMPLETE`. Ein vorhandener `CLOSED`-Beleg dagegen belegt einen
Nicht-Sitzungstag. Technischer Datenbankausfall oder verletzte Originalintegrität
liefert HTTP 503, keine scheinbare fachliche Beleglücke.

### Positionsread, Tag 0 und abgeschlossene 20. Sitzung

`GET /api/v1/position-monitoring/trades/{trade_id}/hebeltrader-sessions?position_id=...`
ist der schmale Monitoring-Read. Er akzeptiert genau eine Positionskennung und
keinen vom Consumer erfundenen Prüfzeitpunkt. Trade, Position und Workspace werden
vom bestehenden Ausführungsowner geprüft. Wirtschaftlicher Einstieg, Kalenderkopf
und Tagesbelege stammen aus derselben eigenen `REPEATABLE READ READ ONLY`-Session
ohne Autoflush, mit Timeout und Rollback. Der Kalenderbereich ist an die dort
gelesene explizite Listing-/Revisionsbindung gebunden.

Der erste effektive BUY aus der bestehenden Ownerprojektion bestimmt den Einstieg.
Teilverkauf und Nachkauf starten ihn nicht neu; eine wirksame Ausführungskorrektur
verändert die aktuelle Projektion nachvollziehbar unter Erhalt des Originals.
Bei `DATE_ONLY` wird der interne Sortieranker niemals als Kaufuhrzeit ausgegeben.
Umfasst das belegte Kaufdatum in der historischen Kalenderzeitzone mehrere mögliche
Tage, bleibt Tag 0 ungeklärt. Dieselbe Zeitzone funktioniert auch an 23-/25-Stunden-
Tagen. Fehlende Hebeltrader-Marken oder Optionsrichtung verhindern diese unabhängige
Sitzungszählung nicht.

Der Kaufkalendertag zählt 0. Für jeden folgenden Kalendertag bis zum Lesezeitpunkt
wird ein ausdrücklicher Tagesbeleg benötigt. Eine Sitzung zählt erst ab ihrem
letzten Schlusszeitpunkt, auch bei Pausen, verkürzter Sitzung, Sommerzeitwechsel
und Schluss am Folgetag. Die 20. Sitzung samt Originalschlusszeit wird nur aus
bereits abgeschlossenen Belegen ausgegeben, nie aus einer Zukunftsprojektion.

| Aussage | Bedeutung |
| --- | --- |
| `AVAILABLE` | Vollständiger benötigter Bereich und eindeutiger Einstieg; `completed_sessions` ist eine Zahl, auch **0**. Am Kauftag selbst ist kein Folgetagsread nötig (`period.status=NOT_REQUESTED`). |
| `NOT_ASSESSABLE` | Fehlender/ungeeigneter Kalender, Datumskonflikt, fehlender Tag oder Bereichsgrenze. Anzahl und Schwellenbefund bleiben `null`; keine Teilzählung als Gesamtzahl. |
| `NOT_APPLICABLE` | Geschlossene oder stornierte Position, einschließlich Storno beim Trade-Owner; keine aktuelle Fristzählung. |
| `F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY` | Implementierter Funktionsschnitt; kein Nachweis vollständiger F207-3-Regelfunktion. |
| `B04_B05_B06_B58_NOT_EVALUATED`, `NOT_ACTIVATED`, `READ_ONLY` | Getrennter Regel-, Betriebs- und Readstatus. Kein Assessment, Alert, SELL, Aktivierungscommand oder Provideraufruf. |

Die bestehende Positionsansicht zeigt diese Aussagen, konkrete Gründe, ursprüngliche
Kaufzeitgenauigkeit, Zeitraum, sämtliche Tagesbelege, Revisionen, Quellenversion und
Publikations-/Abruf-/Prüf-/Erfassungszeiten mit Originalhashes. Paginierung verkürzt
den zugrunde liegenden Bereich nicht. Der vorhandene Host-Reloadvertrag und
Generation-/Abortschutz verhindern vermischte Belege bei Positionswechsel und
verspäteten Antworten; bestehende Eingaben zur Zielqualifikation bleiben erhalten.

### Migration, Nachweise und Übergabe

Die additive Migration `20261115_0052` folgt auf den tatsächlichen vorherigen Head
`20261114_0051`. Sie ergänzt `market_session_evidence` mit Scope-/Ketten-/Hash- und
Provenienzschutz. PostgreSQL prüft Originalhashes auch beim INSERT; UPDATE, DELETE
und TRUNCATE sind gesperrt. Ein belegter Downgrade wird verweigert. Kein bestehender
Ausführungs-, Bestands-, Einstands- oder Zielprüfstand wird migriert oder umgeschrieben.
Die vorhandenen E2E-Schemaguards erwarten lediglich den neuen tatsächlichen Head;
ihre Schutzbedingungen und alle regulären Gates bleiben unverändert.

Gezielte Tests sichern Originalpakete, Fremdscope, Preisachsenidentität, Replay/CAS,
Korrektur/Rücknahme, historische Reads, fehlende/UNKNOWN-Tage, Tag 0, Datum ohne
Uhrzeit, Sommerzeit, Pausen, Übernachtschluss, den exakten 20.-Schlusszeitpunkt,
Teilverkauf/Nachkauf, Storno und side-effect-freie Reads. Fünf echte PostgreSQL-Fälle
verwenden den vorhandenen UUID-Wegwerfdatenbankguard und synthetische Ownerfakten,
darunter Migration/Downgrade, SQL-Schutz, konkurrierende Importe und der komplette
BUY→Kalenderimport→Positionsread mit unveränderten übrigen Tabellen. Externe
Aufrufe sind abgefangen. Tatsächliche Ergebnisse und Skips werden im zugehörigen
PR an Head und Testmerge gebunden; lokale Sammlung ist kein Datenbanknachweis.

Für den folgenden F207-3-Schnitt sind `SessionEvidenceReader.current/read` und die
reine Zählfunktion wiederverwendbar. Deren expliziter `event_at` muss bei B04/B58
die **belegte Original-BID-Zeit** erhalten. Zusätzlich fehlen die unabhängig
qualifizierte Quellenbeschaffung, verifizierte offene Produktsitzung, passende
Währung/Skala des gehaltenen Instruments und `0 <= Kursalter <= 900 Sekunden`.
Am Ausgangsstand des Sitzungsschnitts setzt der
[Frankfurt-Snapshotmapper](../../backend/app/providers/frankfurt_quotes/schema.py)
`observed_at=min(bid_at, ask_at)`; der gemeinsame `WarrantQuoteSnapshot`
bewahrt dort noch keine einzelnen Seitenzeiten. Diese kombinierte Zeit darf
nicht als exakte Original-BID-Zeit für den 20.-Sitzungsnachweis umgedeutet werden.
Der nachfolgende [additive Seitenzeitvertrag](#f207-3-original-bid-evidence)
schließt diese Speicherlücke für den bestehenden normalisierten Frankfurt-Pfad;
Legacy- und andere Quellbelege erhalten keine erfundene Seitenzeit.

Product muss verifizierten letzten Handelstag, maßgeblichen Produkttermin und
festes Ausstiegslisting samt instrumentbezogenem Schluss ergänzen. Die vorhandenen
`maturity_date`-/`expiry_at`-Belege sind wiederzuverwenden; ein Bewertungstag oder
Auszahlungstag ist kein Ersatz. B05-Rückwärtszählung und Z1-bezogene B06-Zählung
bleiben offen. F207-2 benötigt den restlichen Schutz-/Korrekturvertrag; F207-5
Regelaktivierung, Meldungslebenszyklus, Zustellung und separaten PC-Betriebsnachweis.
Keine neue Quelle aktiviert eine Regelversion, B08 bleibt ausgeschlossen und B07
eigenständig. VERSION, Providerzustimmungen, produktive Daten und Installation
werden durch diesen Schnitt nicht geändert. Aufgabenstatus bleibt ausschließlich
im Product Backlog.

<a id="f207-3-original-bid-evidence"></a>
## F207-3: Original-Geldkursbelege und passive Eingangsvoraussetzungen

### Abgrenzung, Abhängigkeit und Wirkung

Dieser Anschluss verwendet den überprüften Sitzungsevidenz-Head aus #347
`093e97899fd35a1f8f508518ebe606fad8e2e237`, Tree
`c51703185c713034245306b00bf17ce7e6d80cea`. Main ist beim Beginn weiterhin
`1d63d001216ef6f9294697f54707f3ae89a58ac4`; #347 war eine offene Draft-Abhängigkeit.
Während der Umsetzung wurde #347 am 15.11.2026 um 20:44:57 UTC auf Main
`19a10ad484293995e200b5eb9a99b4ae11a49ee2` integriert. Dessen Tree ist exakt
`c51703185c713034245306b00bf17ce7e6d80cea`; die geprüfte Grundlage bleibt damit
inhaltlich gleich. Der anschließende [PR #348](https://github.com/burckhju/trading-workspace/pull/348)
enthält gegenüber diesem tatsächlichen Main nur den zusätzlichen Schnitt.
Dieser Diff enthält keine Migration.
Der gemeinsame Migrationsgraph bleibt linear mit `20261115_0052` nach
`20261114_0051`; VERSION und veröffentlichter Tag bleiben unverändert.

Die Positionsdetails erhalten einen kompakten Abschnitt **Hebeltrader ·
Original-Geldkurs**. Er liest die aktuelle bestätigte Kursroute und deren
gespeicherten letzten Erfolg. Bereits erfasste Ausführungen, historische
Kaufwährung und Kalenderpakete werden verwendet. Es gibt keine neue Pflichtangabe,
keinen Kalendereditor und keine zusätzliche Bestätigung für vorhandene Belege.
Erneutes Lesen aktualisiert nur diesen Bericht; es beschafft keinen Providerkurs.

Die Anzeige trennt erfüllte, fehlende, ungeeignete, noch nicht erreichte und
nicht anwendbare Eingangsvoraussetzungen. Ein vollständiger Teilbeleg ist keine
ausgewertete B04-/B58-Regel. Insbesondere fehlen weiterhin ein Ownerbeleg zum
historischen **Optionsschein-Preismaßstab** und ein qualifizierter, zeitlich
zugeordneter Nachweis des offenen Produktmarkts. Deshalb kann dieser Bericht
keine vollständige Regeltauglichkeit oder Entwarnung ausgeben.

### Ein additiver Originalseitenvertrag beim bestehenden Kursowner

`market_data.domain.original_quote_evidence` definiert `OriginalQuoteEvidence`
mit `version=original-quote-evidence-v1`, normalisiertem Quellvertrag,
Quellreferenz, Generierungszeit, ISIN, Währung, MIC und optionalen einzelnen
BID-/ASK-Belegen. Jede vorhandene Seite bindet den exakten Decimalpreis an ihre
explizite Originalzeit, den unveränderten ISO-Zeittext einschließlich Offset
und das zugehörige Quellenfeld. Der Zeittext muss denselben Zeitpunkt belegen;
naive Zeitangaben, unbekannte Uhrzeit oder spätere Erfassung werden nicht ergänzt.

Der vorhandene **normalisierte** Frankfurt-Vertrag `frankfurt-quotes-v1` übernimmt
bei `kind=BID_ASK` die tatsächlich übergebenen Originalstrings `bid_at`/`ask_at`.
Er ist kein behauptetes natives Börsen-HTTP-Format. Der bestehende gemeinsame
Snapshotzeitpunkt `min(bid_at, ask_at)` behält seine Bedeutung. Das neue optionale
`WarrantQuoteSnapshot.original_evidence` bindet Seitenwerte, ISIN/Providersymbol,
Währung und MIC an denselben Snapshot. Referenzpreise sind keine BID-Seite.

Der Monitoringconsumer qualifiziert ausschließlich diesen bereits belegten
Pfad: Provider `FRANKFURT_QUOTES`, Quellvertrag `frankfurt-quotes-v1`, BID-Feld
`bid_at`, separate Seitenzeit, XFRA und vorhandener Frankfurt-Realtime-/Delayed-
Monitoringmodus. Eine bloß strukturell gültige neue Quelle erhält keine
automatische fachliche Freigabe. Eine nominelle Verzögerung ist kein Altersbeleg.
Andere Produzenten bleiben unverändert: gettex/Stuttgart mit gemeinsamer Zeit,
Vontobel mit nicht separat belegter BID-Zeit, JPMorgan/Morgan Stanley mit den
bisherigen Zeitpräzisionsgrenzen sowie Frankfurt-LAST-/PREVIOUS_CLOSE-Referenzen
werden daraus nicht zu geeigneten Original-BIDs. Produktive Provider werden
nicht neu aktiviert oder abgefragt.

Die vorhandene Retention und unveränderliche Samples bewahren das additive
Originalobjekt im bestehenden JSON. Neue Samples enthalten außerdem die
äußere Qualitätsstufe, Warnungen und den Grundcode des Ergebnisses. Für Quotes
ohne Originalseitenbeleg wird das neue `None`-Defaultfeld vor Sample-Speicherung
und Quote-Hashing entfernt: bestehende Payloads und der bisherige
`quote_fingerprint` bleiben unverändert. Der Quotehash bindet weiterhin
Route und Quote; der neue lesende Gesamtbelegfingerprint erfasst zusätzlich
die vollständigen gespeicherten Ergebnisdaten einschließlich Metadaten.

### Schmaler gespeicherter Read und seine Zeitgrenzen

`RiskMarketDataReader.saved_quote` erhält additiv `expected_warrant_id`. Der
bestehende Identitätsjoin muss Kursroute und tatsächlich gehaltenes Produkt
belegen. Workspace, Position, Warrant, Listing, Venue, Währung, Auswahl-ID/-Zeit
und unveränderter Identitätsschlüssel werden in `SavedQuoteRouteBinding` sichtbar.
Provider, Capability, Symbol/ISIN/WKN, Exchange/MIC, Währung und Zeitfolge bleiben
geprüft. Eine geänderte oder fremde Route wird nicht automatisch repariert.

`SavedQuoteProvenance` bewahrt Abrufzeit, Lesezeit, Qualitätsstatus, Warnungen,
Grundcode und SHA256 des vollständig gespeicherten kanonischen JSON. Dieser
Fingerprint ist kein Hash ursprünglicher HTTP-Antwortbytes. Der Last-success-
Store besitzt **keine aufgezeichnete Speicherzeit**: `stored_at=null` und
`stored_at_status=NOT_RECORDED_BY_LAST_SUCCESS_STORE` sagen dies ausdrücklich.
Abruf und Speicherung werden nicht gleichgesetzt. `storage_kind=LAST_SUCCESS`,
`mutable=true` und `historical_read=false` grenzen die Aussage auf den aktuell
gespeicherten Erfolg ein; Samples werden nicht zur historischen Rekonstruktion
oder als Rückfall auf eine frühere Route verwendet. Der letzte fehlgeschlagene
Abrufversuch ist diesem Reader nicht bekannt.

```text
GET /api/v1/position-monitoring/trades/{trade_id}/hebeltrader-original-bid
    ?position_id={position_id}
```

Der Monitoring-Read verwendet genau eine `REPEATABLE READ READ ONLY`-Transaktion
ohne Autoflush, mit begrenztem Statementtimeout und Rollback auch bei Fehlern.
Er bezieht die wirtschaftliche Basis direkt aus Trade Position: effektiver
ursprünglicher BUY, Restmenge, gewichteter Bruttoeinstand und historische
Währungsauflösung samt vorhandenen Kaufbelegen. Teilverkauf, Nachkauf und
Korrekturen erzeugen keine zweite Kosten-/Bestandshistorie.

Der Zeitpunkt ist serverseitig. Zusätzliche, doppelte oder historische
Queryparameter werden abgewiesen. Fremde Trade-/Positionszuordnungen sind kein
fehlender Kurs. Inkonsistente Ownerantworten und Datenbank-/Integritätsfehler
liefern einen Lesefehler, keine scheinbare Beleglücke oder Regelerfüllung.
Ein Berichtsfingerprint bindet Wirtschaftsbasis, Seitenbeleg, Route, vollständige
Provenienz, beide Kalenderrevisionen/-quellen, gelesene Zeiträume und Ergebnisse.

### Acht lesbare Voraussetzungen

| Read-Befund | Bedeutung und konkrete Grenze |
| --- | --- |
| `HELD_INSTRUMENT` | Gespeicherter Kurs und bestätigte Route gehören zum tatsächlich gehaltenen Instrument. |
| `ORIGINAL_BID_TIME_AND_AGE` | Echte BID-Seitenzeit; Originalzeit ≤ Quellgenerierung ≤ Abruf ≤ Lesestand; exakt `0 <= Alter <= 900 Sekunden`, ohne Rundung oder Empfangsersatz. |
| `EXECUTION_CURRENCY` | Bekannte historische Ausführungswährung und echter BID in derselben Währung. Gemischte/fehlende Währung wird nicht umgerechnet oder erneut pauschal abgefragt. |
| `PRODUCT_SESSION_AT_BID` | Die BID-Zeit liegt in einem vollständig dokumentierten Intervall des exakt zugeordneten Produktlistings. |
| `PRODUCT_SESSION_AT_READ` | Separater Befund für den serverseitigen Lesestand. Öffnung ist eingeschlossen, Schluss ausgeschlossen; Pausen und Overnight werden erhalten. |
| `TWENTY_UNDERLYING_SESSIONS_AT_BID` | Vorhandener Tag-0-/Präzisionsvertrag, aber Zählung ausdrücklich zur Original-BID-Zeit. Ein späterer 20. Schluss bis zum Lesen zählt nicht nachträglich. |
| `PRICE_SCALE` | Weiter fehlender Ownerbeleg zwischen historischem Optionsschein-Einstand und BID. F207-4-Marken-/Basiswertbelege oder die OHLC-Nutzerqualifikation aus #346 bestätigen diesen Produktmaßstab nicht. |
| `VERIFIED_LIVE_MARKET_STATUS` | Weiter fehlender qualifizierter Nachweis des offenen Instruments. Dokumentierte Kalenderintervalle und Quellstatus `OPEN` bleiben eigenständige Fakten. |

Für den Produktkalender wird ausschließlich das Listing der bestätigten Kursroute
gelesen. Ein begrenzter Zeitraum umfasst die beiden lokalen Ereignistage und
den vorausgehenden Tag, damit eine Übernachtsitzung nachvollziehbar abgedeckt
ist. Auch dieser vorausgehende Tag braucht einen ausdrücklichen Quellbeleg;
fehlend bedeutet nicht geschlossen. Vergleiche erfolgen auf UTC-Zeitpunkten,
einschließlich der wiederholten Stunde bei Zeitumstellung. Liegen BID und Read
in unterschiedlichen dokumentierten Intervallen, wird dies angezeigt; daraus
wird keine zusätzliche, unbestätigte Handelsregel erfunden.

Beide Kalenderreads bleiben auf dieselbe Revision, Originalquelle und den
Lesezeitpunkt gebunden. Fehlende/UNKNOWN-Tage, Rücknahme oder unpassende Bindungen
werden nicht durch ältere Revisionen oder Kurszeilen ersetzt. Ohne geeigneten
BID gibt es keinen ersatzweisen Sitzungszählstand zur Abruf- oder Lesezeit.
Die vorhandene Sitzungsanzeige aus #347 behält ihren eigenen Serverzeitvertrag.

`coverage_status` ist `PARTIAL`, `UNSUITABLE` oder `NOT_APPLICABLE`; es gibt keine
vollständige B58-Freigabe in diesem Schnitt. `F207_3_ORIGINAL_BID_EVIDENCE_ONLY`,
`B04_B05_B06_B58_NOT_EVALUATED`, `NOT_ACTIVATED` und `READ_ONLY` halten Belegstand,
implementierte Funktion, Regelauswertung und Betrieb auseinander. Geschlossene
und stornierte Positionen erhalten keine aktuelle Eingangsqualifikation.

### Consumer, Nachweise und Anschluss

Der Operational Workspace zeigt den serverseitigen Bericht ohne Finanz-,
Alters- oder Sitzungsrechnung. Positions-/Reloadwechsel, Abbruch und verspätete
Antworten sind isoliert; bestehende Formularentwürfe und UNKNOWN-Recovery bleiben
erhalten. Technische Lesefehler werden getrennt von fehlenden Belegen angezeigt.

Gezielte Tests prüfen Originaltexte/-zeiten und Retention über Neustart,
Legacy-Hashkompatibilität, falsche Quellen/Preisachsen/Identitäten, 900 Sekunden
einschließlich Mikrosekundengrenze, 20. Schluss zwischen BID und Read,
Währungsreuse, Teilverkauf/Nachkauf, Zeitumstellung, fehlende/ersetzte Kalender,
Scope, Provenienz und schreibfreie Reads. Ein zusätzlicher echter PostgreSQL-Fall
verwendet die vorhandene bewachte UUID-Wegwerfdatenbank: realer externer Kauf,
bestätigte Währung/Quellenauswahl, gespeicherter separater BID, zwei Original-
Kalenderimporte und tatsächlicher GET mit geprüfter Read-only-Isolation sowie
unveränderten übrigen Tabellen. Alle Daten sind synthetisch und externe Aufrufe
abgefangen. Ausgeführte reguläre Ergebnisse, Skips und Coverage stehen im
zugehörigen PR am konkreten Head und tatsächlichen Testmerge. Eine lokale
Testsammlung ist kein PostgreSQL- oder Betriebsnachweis; Gates bleiben unverändert.

**Folgeschnitt F207-3:** Produkt-Preismaßstab/Anpassungsbelege und qualifizierte
offene Sitzung samt Quellenbeschaffung schließen; darauf B04/B57-Verlustzustände
mit dem persönlichen Einstand implementieren. Verifizierter letzter Handelstag,
Produkttermin/festes Ausstiegslisting, B05-Rückwärtszählung, Z1-bezogene B06-Zählung
und historische Basiswert-Trades zum Kauf bleiben offen. F207-2 benötigt weiter
Schutz-/Korrekturverträge; F207-5 aktiviert später belegte Regelfunktionen und
deren Meldungs-/Zustelllebenszyklus. Einstandsvergleich, Verlustepisode, Order,
Ausführung, Providerzustimmung, Merge, Release und PC-Installation gehören
nicht zu diesem Anschlussauftrag. Die maßgebliche Aufgabenstatusquelle bleibt
der Product Backlog.


<a id="f207-3-product-price-scale"></a>
## F207-3: dokumentierter Optionsschein-Preismaßstab

### Umfang und geprüfte Grundlage

Der Anschluss vom 16.11.2026 baut auf dem Original-Geldkurs-Head aus
[#348](https://github.com/burckhju/trading-workspace/pull/348)
`9a6168c12eca72094fda925862819e49d5df7485` auf. Bei der Bestandsprüfung steht Main
auf `19a10ad484293995e200b5eb9a99b4ae11a49ee2`; #348 ist ein offener Draft und
bleibt eine ausdrücklich benannte Integrationsabhängigkeit. Der eigene Branch
`feat/f207-3-product-price-scale` verändert diesen Vorgängerbranch nicht.
Tatsächlicher Prüfhead, Testmerge, CI-Ergebnisse und späterer Integrationsstand
stehen im zugehörigen PR; der Aufgabenstatus bleibt ausschließlich im Backlog.

Dieser Schnitt ergänzt **einen dokumentgebundenen Produktmaßstab und dessen
Consumer im bestehenden Original-Geldkursbericht**. Ein unveränderter Maßstab
kann damit für alle noch zur gehaltenen Position beitragenden Käufe und den
konkreten Original-BID nachgewiesen werden. Er ist produktbezogen wiederverwendbar;
keine neue Bestätigung pro Position, Fill oder Kurs wird allein durch das Lesen
verlangt. Fehlende oder unzureichende Quellen bleiben konkrete Ausnahmen.

Es gibt keine Umrechnung von Preisen, Kosten oder Stückzahlen. Ein Beleg mit
Anpassungsbedarf sperrt die Vergleichbarkeit. Eine geeignete dokumentierte Skala
ist außerdem kein Nachweis des offenen Produktmarkts, keine B04-Auswertung und
keine aktive Baseline. B07, der Ausschluss B08 und sämtliche anderen bestätigten
Regeln behalten ihre Bedeutung.

### Product als einziger Maßstabsowner

`product.domain.price_scale_evidence` definiert den engen
`product-price-scale-evidence-v1`-Vertrag. Die neue Relation
`product_price_scale_evidence` enthält ausschließlich Originalquellen und ihre
Revisionen. Sie enthält keine Käufe, Verkäufe, Lots, Kosten oder Positionsbestände.
Die bestehende `WarrantValuationEvidence`-Akte bleibt für Produktart,
Ausübungsart, Quanto, Ratio-Konvention und Verfall zuständig. Deren aktuelle
Bewertungsbestätigung wird nicht still zu einem historischen Maßstabsbeleg.

| Belegteil | Vertrag |
| --- | --- |
| Identität | Workspace des Imports, exaktes Produkt, ISIN, Emittent, Basiswert und ausdrücklich referenzierter aktueller `current_terms_id`. Eine spätere Identitäts- oder Termsänderung sperrt die aktuelle Zuordnung. |
| Preismaßstab | Achse `WARRANT`, explizite Währung, Einheit `CURRENCY_PER_WARRANT`, dokumentierte `scale_id` und `source_version`. Gleiche Ratio, gleiche ISIN oder gleiche Währung allein genügen nicht. |
| Historische Gültigkeit | Ausdrückliches endliches, offsetbewusstes Intervall `[valid_from, valid_until)` aus der Quelle. `effective_from` der vorhandenen Produktbedingungen ist eine Erfassungsgrenze und wird nicht als tatsächlicher historischer Anpassungszeitpunkt verwendet. |
| Aussage | `UNCHANGED_ORIGINAL`, `ADJUSTMENT_REQUIRED` oder `WITHDRAWN`. Nur der erste Fall kann unveränderte Originaleinheiten dokumentieren. Ein Faktor, eine automatische Splitverrechnung oder ein günstiger Rückfall auf eine alte Revision existiert nicht. |
| Original | Exakter UTF-8-Manifesttext und Originaldokumentbytes mit getrennten SHA256, Dateiname, Medientyp, Herausgeber und konkreter Fundstelle. Hashprüfung belegt Unverändertheit der übergebenen Bytes, nicht die sachliche Wahrheit des Inhalts. |
| Zeitstände | Veröffentlichung entweder zeit- oder datumgenau; optionale tatsächliche Beschaffungszeit, ausdrückliche Prüfung und serverseitige spätere Erfassung bleiben getrennt. Unbekannte Uhrzeiten werden nicht ergänzt. |
| Korrektur | Eigene `request_id`, unveränderliche Revision, exakter Vorgänger und Requestfingerprint. Identischer Retry erhält den ursprünglichen Beleg; geänderter Requestinhalt oder veralteter Vorgänger wird abgewiesen. |

Die Herkunft bleibt ausdrücklich
`MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION`. Ein dokumentierter
Gültigkeitsanspruch kann über den Erfassungszeitpunkt hinaus reichen; er ist
**keine laufend unabhängig verifizierte Änderungsfreiheit**. Es gibt keine
unbegrenzte Fortschreibung, automatische Anpassungsbeschaffung oder Verlängerung
über das erklärte Ende hinaus. Ein neu erfasster Produktbedingungsstand verlangt
neue passende Evidenz. Ein Basiswertsplit oder eine F207-4-Markenbestätigung
qualifiziert keine Optionsschein-Anpassung.

### Schmaler Import- und Lesevertrag

| Bestehender Owner / ergänzter Einstieg | Wirkung |
| --- | --- |
| `POST /api/v1/warrants/{warrant_id}/price-scale-evidence/imports` | Bewusster Import des konkreten Originalpakets mit `confirmation=CONFIRM_PRODUCT_PRICE_SCALE_DOCUMENT_REVIEW`; erzeugt nur eine Maßstabsrevision. |
| `GET /api/v1/warrants/{warrant_id}/price-scale-evidence/current` | Serverzeitgebundener Read der neuesten bekannten Revision einschließlich ungeeigneter oder zurückgenommener Quelle. Keine historischen Queryparameter, kein günstiger Quellenfallback. |
| `GET /api/v1/warrants/{warrant_id}/price-scale-evidence/revisions/{revision_id}` | Exakter ursprünglicher Beleg einschließlich Manifest und Originalbytes; ursprüngliche und ersetzte Revision bleiben lesbar. |
| `ProductPriceScaleEvidenceReader.current(workspace_id, warrant_id, known_at)` | Interner Product-Read in der bereits geöffneten Snapshottransaktion des Consumers. `known_at` bindet den Wissensstand; er rekonstruiert keine historische Stammdatenwelt. Der kompakte Read enthält keine Dokumentbytes. |

Der Import verwendet die vorhandene Produktidentität und deren vorhandene
Bedingungsversion. Es werden keine Ersatzstammdaten oder historischen
Ausführungen angelegt. Das Paket enthält `manifest_json`, dessen SHA256,
`document_base64`, dessen SHA256, Dateiname/Medientyp, Prüfzeit/Fundstelle,
optionale Beschaffungszeit sowie Request-/Vorgänger-ID. Das darin enthaltene
Manifest nennt exakt die oben beschriebenen Produkt-, Maßstabs-, Zeitraum- und
Quellenfelder. Maximal 64.000 Manifestbytes und 2.000.000 Originaldokumentbytes;
Doppelkeys, unbekannte Felder, numerische Ersatzzeitstempel, ungültige Hashes und
widersprüchliche Publikationszeitgenauigkeit sind keine akzeptierten Originale.
URLs sind Herkunftstext und werden durch Import oder Lesen nicht abgerufen.

Der Backendweg ist ein Integrationsvertrag für tatsächlich vorhandene und
bewusst geprüfte Originale; es gibt in diesem Schnitt keinen neuen Quelleneditor.
Die vorhandenen Positionsdetails bleiben rein lesend. Eine Originalquelle darf
nicht automatisch aus identischen Stammdaten oder aus dem Fehlen eines
Splitvermerks erzeugt werden.

Migration `20261116_0053` folgt dem erneut geprüften linearen Head
`20261115_0052`. PostgreSQL schützt Originalbytes/Hashes, Produkt-/Workspace-/
Termsbindung, Revisionskette und Unveränderlichkeit einschließlich UPDATE,
DELETE und TRUNCATE. Ein Downgrade mit bereits gespeicherten Originalbelegen
bricht ab, statt diese zu löschen. Vorhandene Bewertungsfakten, Ausführungen,
Kursdaten, Kalender und Regeln werden nicht umgeschrieben. VERSION bleibt
unverändert; eine Migration im Test ist kein Installationsnachweis auf dem PC.

### Consumer: bestehende wirtschaftliche Wahrheit vollständig erhalten

Der vorhandene `hebeltrader-original-bid`-GET liest den Product-Beleg in **derselben
`REPEATABLE READ READ ONLY`-Transaktion** wie die übrigen Owner. Er verwendet
unverändert `PositionExecutionBasis` und die vom vorhandenen Projektor gelieferten
`buy_contributions`. Die ursprüngliche Menge, der noch beitragende Anteil,
Ausführungskorrektur, tatsächlicher Preis und historische Währung jedes Kaufs
bleiben nachvollziehbar. Kein eigener Gewichtungs- oder Einstandsrechner kommt
hinzu.

Jeder beitragende Kauf und die tatsächliche Original-BID-Zeit müssen im selben
belegten unveränderten Zeitraum und in derselben Währung liegen. Fehlende
Teilabdeckung entfernt keinen Kauf aus der Basis. Datumgenaue Käufe verlangen
die Abdeckung des ganzen möglichen lokalen Tages einschließlich Zeitumstellung;
ihr interner Mitternachts-Sortieranker wird nicht als bekannte Kaufuhrzeit
angezeigt. Bei einer Ausführungskorrektur werden dieselben neuen effektiven
Ownerfakten erneut gebunden; Originalausführung und ursprünglicher Produktbeleg
bleiben erhalten. Eine Korrektur innerhalb desselben belegten Maßstabs braucht
keine pauschale neue Dokumenterklärung. Ein korrigierter Kauf außerhalb des
Zeitraums bleibt dagegen unvollständig.

Der additive Reportteil `product_price_scale` enthält den kompakten Product-Read,
`execution_basis_id`, Original-BID-Bezug und sämtliche Kaufbeiträge samt
Einzelbefunden. `DOCUMENTED` bedeutet dokumentierte unveränderte Einheiten;
`MISSING`, `UNSUITABLE` und `NOT_APPLICABLE` erhalten konkrete Gründe.
`adjustment_applied=false` bleibt fest. Der Gesamtberichtsfingerprint bindet
Quelle, Revision, Zeiten, wirtschaftliche Basis und diese Einzelbefunde.
Nach dem gemeinsamen Serverlesestart erfasste Ausführungs- oder verwendete
Währungsfakten führen zu einem Konsistenzfehler; der Read filtert sie nicht
heraus und projiziert keine vermeintlich frühere wirtschaftliche Wahrheit.
Ein erneuter passiver Read kann den neuen gemeinsamen Stand lesen.

`PRICE_SCALE` kann dadurch `SATISFIED` werden; die Anzeige benennt ausdrücklich
die manuelle Originalquellenprüfung. `VERIFIED_LIVE_MARKET_STATUS` bleibt für
offene Positionen fehlend. Der Bericht bleibt `PARTIAL` beziehungsweise
`UNSUITABLE`; `F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY`,
`B04_B05_B06_B58_NOT_EVALUATED`, `NOT_ACTIVATED` und `READ_ONLY` trennen Umfang,
Regelfunktion, Betrieb und Wirkung. Die bisherigen v1-Antworten werden vom
Frontend weiterhin erkannt; der neue Implementierungsstatus verlangt den
vollständigen zusätzlichen Maßstabsbericht.

Die bestehende Original-Geldkursanzeige zeigt Zeitraum, Quellen-/Termsrevision,
Prüf-/Erfassungszeiten, Hashes und die beitragenden Käufe. Kein zusätzlicher
Positionsread, Formular oder Provideraufruf wird ausgelöst. A→B→A, verspätete
Antworten, Unmount sowie bestehende Entwürfe und UNKNOWN-Recovery bleiben geschützt.
Technische oder inkonsistente Ownerantworten sind Lesefehler; sie werden nicht
als fehlende oder erfüllte Belege ausgegeben.

### Nachweise und verbleibender Anschluss

Gezielte synthetische Fälle decken Einstiegsfills, Teilverkauf/Nachkauf,
Korrekturen, unbelegte Teilmengen, datumgenaue Käufe/DST, Grenzen des halboffenen
Zeitraums, Währungen, fremde Identitäten, neue Terms, Originalhashes, konkurrierende
Revisionen, Rücknahme, Anpassungsbedarf und reine Reads ab. Echte PostgreSQL-Fälle
verwenden die vorhandenen bewachten UUID-Wegwerfdatenbanken mit abgefangenen
externen Aufrufen; Migration, Originalimporte, tatsächliche Käufe/Verkäufe/
Korrekturen und Read-only-Snapshot werden dort geprüft. Ausgeführte Ergebnisse,
Skips und unveränderte reguläre Gates stehen am konkreten Head/Testmerge im PR.
Lokale Sammlung ersetzt keinen PostgreSQL- oder Betriebsnachweis.

**Nächste F207-3-Abhängigkeit:** Ein tatsächlich belegter Quellvertrag für den
instrumentbezogenen offenen Markt muss eigene Originalstatuszeit, Handelsplatz
und zeitliche Bedeutung liefern. `trading_status=OPEN`, BID-/Generierungszeit
und geplantes Kalenderintervall leisten dies derzeit nicht. Erst damit und mit
ausreichend qualifizierter tatsächlicher Quellenversorgung können B58 und die
B04-/B57-Verlustepisode geschlossen werden. Produktspezifische Anpassungsfaktoren
und ihre einmalige wirtschaftliche Anwendung sind ebenfalls nicht implementiert.
Produkttermine/B05, Z1-bezogene B06-Zählung und historische Basiswert-Trades bleiben
weitere F207-3-Teile; F207-2 benötigt Schutz-/Korrekturverträge, F207-5 den Regel-/
Meldungs-/Zustelllebenszyklus. Kein produktiver Provider, Release, PC-Update,
echte Nachricht oder produktive Datenkorrektur folgt aus diesem Anschluss.

<a id="f207-3-market-status-evidence"></a>
## F207-3: Originalstatusbelege und getrennte zeitliche Aussagen

### Abgegrenzter Nutzen und tatsächliche Grundlage

Dieser Schnitt ersetzt den bisher pauschalen Hinweis auf fehlenden Live-Marktstatus
durch einen nachvollziehbaren Befund zur tatsächlich gespeicherten Quellenmeldung.
Der bestehende Original-Geldkurs-GET zeigt eigenen Originalstatuszeitpunkt,
Quellenfeld und unveränderten Originalzeittext, soweit diese ausdrücklich geliefert
wurden. Er stellt den Bezug zur Original-BID-Zeit und zum Serverlesestand getrennt dar.

Geprüfte Grundlage ist Main `19a10ad484293995e200b5eb9a99b4ae11a49ee2` mit
integriertem #347. Der Arbeitsbranch setzt auf #349-Head
`c258101a490353468bd03a7bf0b531fa0a43b727` auf; #348 und #349 sind bei dieser
Bestandsprüfung noch offene Draft-Abhängigkeiten. Deren Arbeiten bleiben erhalten.
Es gibt keine neue Migration: einziger Head weiterhin `20261116_0053` aus #349.

**Kein bestehender Quellenpfad ist damit als B58-tauglicher Live-Marktstatus
qualifiziert.** Frankfurt besitzt bislang einen normalisierten `trading_status`
ohne eigene Statuszeit, Vontobel `tradingHours.isOpen` ohne Statuszeit und ohne
belegte zeitliche Bedeutung. Die öffentliche Frankfurt-Website liefert an diesem
Pfad Last/Previous Close und keinen tatsächlichen Instrumentstatus. Preis-,
Generierungs- und Abrufzeiten sind keine Ersatzstatuszeiten.

### Originalfakt beim bestehenden Market-Data-Owner

`WarrantQuoteSnapshot.original_market_status` ist ein optionaler
`original-market-status-evidence-v1`-Beleg. Er enthält Quellvertrag/-referenz,
Quellgenerierung, ISIN/MIC, Status `OPEN | CLOSED | SUSPENDED | UNKNOWN`, dessen
Originaltext/Quellenfeld sowie die eigene Originalzeit in UTC mit unverändertem
Zeittext und eigenem Quellenfeld. Seine ausdrückliche zeitliche Bedeutung ist
ausschließlich `OBSERVED_AT_INSTANT`; `SEPARATE_STATUS_TIMESTAMP` bezeichnet die
eigene Statusuhr. Ein Beleg ohne diese Originalzeit wird nicht erfunden.

Der bestehende **anwendungseigene, vendor-neutrale** Frankfurt-Importvertrag
`frankfurt-quotes-v1` erhält dafür das optionale Feld `status_observed_at`.
Nur ein tatsächlicher ISO-Datum/Zeit-String mit explizitem Offset wird übernommen;
Epoch-Zahlen, datumgenaue oder zeitzonenlose Werte sind unzulässig. Fehlt das Feld,
bleibt das neue Objekt `null`; der vorhandene `trading_status` bleibt erhalten.
Das ist keine Behauptung, dass ein konkreter Anbieter dieses Feld bereits liefert.

Status, Instrument und MIC müssen zum Snapshot passen. Wenn beide Originalbelege
vorliegen, müssen Status- und Preisbeleg dieselbe Quellhülle benennen. Es gilt
`Originalstatuszeit <= Quellgenerierung <= Abruf <= gemeinsamer Lesestand`.
Eine neue Quelle, `source_contract`, strukturelle Validierung oder die bestehende
Konfiguration `contract_verified` verifiziert keine neue Statussemantik.

Die vorhandenen JSON-Stores, Retention und Samples erhalten das additive Objekt.
Ohne Objekt wird das neue `None`-Feld vor Samplehashing entfernt; bestehende
Payload-/Sampleidentitäten und historische Belege bleiben erhalten. Es entsteht
keine zweite Kurs- oder Statushistorie und keine geänderte Samplepolitik.

### Passiver Consumer und ausdrücklich nicht belegte Gültigkeit

Der vorhandene Positions-GET ergänzt `live_market_status` im selben
`REPEATABLE READ READ ONLY`-Snapshot. Der Befund ist vollständig in `basis_id`
enthalten. Er übernimmt denselben gespeicherten Kurs und führt keinen zusätzlichen
Provideraufruf, Import, Autoflush, Commit, Assessment oder Zustellvorgang aus.

| Read-Feld | Aussage |
| --- | --- |
| `reported_status`, `original_evidence` | Unveränderte gespeicherte Quellenmeldung und optionaler eigener Originalbeleg. |
| `at_bid`, `at_read` | Vergleich des jeweiligen expliziten Ereigniszeitpunkts mit dem Statuspunkt: davor, zeitgleich, danach oder ohne Original-/Ereigniszeit. Selbst `AT_SOURCE_POINT` bleibt `NOT_ASSESSABLE` hinsichtlich einer qualifizierten Marktöffnung. |
| `source_qualification` | `NOT_INDEPENDENTLY_VERIFIED`: kein unabhängiger Quellenvertrag für Statusbedeutung und zeitliche Gültigkeit. |
| `status_validity_interval` | `NOT_ESTABLISHED`: kein erfundenes Öffnungsintervall und keine Status-TTL. |
| `evidence_scope` | `SAVED_QUOTE_LAST_SUCCESS_ONLY`: weiterhin der veränderliche letzte gespeicherte Kurserfolg. |
| `newer_status_observations` | `NOT_OBSERVED_BY_SAVED_QUOTE_READER`: spätere Statusmeldungen und Abrufausgänge sind durch diesen Read nicht vollständig erfasst. |

Die **900 Sekunden gehören ausschließlich zum BID-Kursalter**. Ein Statuspunkt
wird weder rückwärts zur BID-Zeit noch vorwärts bis zum Lesestand fortgeschrieben.
Die zwei Zeitpunkte bleiben getrennt; daraus wird auch keine neue Forderung nach
durchgehender Öffnung zwischen ihnen oder einem BID nach Wiedereröffnung abgeleitet.

Die vorhandene Preis-Retention kann einen späteren `CLOSED`-/`SUSPENDED`-Befund
ohne geeigneten BID zugunsten des älteren Kurserfolgs verwerfen. Auch der erste
Capture pro Fünf-Minuten-Slot ist kein vollständiger Statusstrom. Der neue Read
behauptet weder, diesen jüngeren Befund zu kennen, noch, es habe keinen gegeben.
Ein alter `OPEN` erhält durch einen späteren Abruf keine neue Originalzeit.

`VERIFIED_LIVE_MARKET_STATUS` bleibt einer der acht bestehenden Checks. Er ist
`MISSING` bei unbelegter Öffnung beziehungsweise `UNSUITABLE` bei widersprüchlichem
Beleg, nicht unterstütztem Status oder gespeicherter `CLOSED`-/`SUSPENDED`-Meldung.
Letzteres bedeutet **ungeeigneter Offen-Beleg, nicht nachweislich jetzt geschlossen**.
Er wird in diesem Schnitt niemals `SATISFIED`. Geschlossene/stornierte Positionen
erhalten weiterhin `NOT_APPLICABLE`.

`F207_3_MARKET_STATUS_EVIDENCE_ONLY` benennt den zusätzlichen implementierten
Vertrag. `B04_B05_B06_B58_NOT_EVALUATED`, `NOT_ACTIVATED` und `READ_ONLY` bleiben
erhalten. Die UI konsumiert denselben GET, bindet Belege an Position, Kursroute,
Status und beide Zeitpunkte und erhält bestehende Entwürfe/A→B→A-Schutz.
Legacyantworten behalten ihren engeren Vertrag; der neue Implementierungsstatus
verlangt die vollständigen zusätzlichen Maßstabs- und Statusbefunde.

### Nachweise und nächste tatsächliche Abhängigkeit

Gezielte Tests prüfen Originaltext/Offset/DST, strikte Zeitformate, Instrument-/
Quellhüllenbindung, fehlende und unbekannte Statuswerte, Punktvergleich ohne
900-Sekunden-TTL, unveränderte alte Samplehashes und originale Retention nach
Neustart. Ein späterer negativer Status ohne geeigneten Preis darf keine positive
Live-Qualifikation des alten `OPEN` erzeugen. Echte PostgreSQL- und API-Prüfungen
verwenden bewachte synthetische Wegwerfdatenbanken und abgefangene externe Aufrufe.
Lesen bleibt ohne Änderung wirtschaftlicher Fakten; UI-Tests erhalten bestehende
Eingaben und verhindern vermischte Belege bei verspäteten Antworten.
Reguläre Ergebnisse stehen am geprüften Head/Testmerge im zugehörigen Draft-PR.

Für eine positive B58-Qualifikation fehlen weiterhin ein tatsächlich belegter
instrumentbezogener Quellvertrag mit geeigneter Originalstatuszeit und zeitlicher
Aussage sowie ein Ownerpfad, der auch negative/status-only Beobachtungen unabhängig
vom Preis erhält. Vorhandene Konfiguration, Kalender oder eine neue DTO-Form
ersetzen diese Nachweise nicht. B04/B57, Produktfristen/B05, Z1-Zählung/B06,
historische Basiswert-Trades und die F207-2-/F207-5-Reste bleiben getrennt offen.
Eine produktive Quellenaktivierung oder Änderung bestehender Zustimmungen folgt
aus diesem Anschluss nicht.

<a id="f207-3-independent-status-observations"></a>
## F207-3: Preisunabhängige Originalstatusbeobachtungen

Historischer Ausgangspunkt dieses Implementierungsnachtrags war der
[erneut verifizierte gemeinsame Stand](../reviews/F207_CHAIN_VERIFICATION_2026-11-17.md)
#350 `77b3312da20b83d207f1da9c9b5f379b705dc8bb` mit den damals offenen
Abhängigkeiten #348 → #349 → #350. Spätere Integrations- und Liefernachweise
ändern diesen Ausgangsbeleg nicht. Historische Soll-Ist-Tabellen und der
bisherige rein lesende Original-BID-Vertrag behalten ihre zeitliche Einordnung;
Aufgabenstatus bleibt allein im Product Backlog.

### Tatsächlicher Quellenbefund

Die [Quellenprüfung vom 17.11.2026](../reviews/B58_SOURCE_QUALIFICATION_2026-11-17.md)
enthält einen tatsächlich abgerufenen Frankfurt-Originalpayload für
DE000VH2LU21/XSC/EUR. Er liefert Last und Last-Zeit, keinen Original-BID und
keinen instrumentbezogenen Status mit eigener Zeit. Die übrigen geprüften
Pfadgrenzen, Primärdokumente und die kleinste offene Beschaffung sind dort
konkret angegeben. **Kein erreichbarer Pfad ist positiv B58-qualifiziert.**
Ein normalisierter Frankfurt-Import ist weiterhin kein Beweis eines existierenden
Lieferanten. Reale Depotdaten, aktuelle Listingbindungen und Nutzer-PC sind hier
nicht erreichbar; der Beispielpfad belegt keine tatsächliche Depotabdeckung.

### Zuständiger Owner, Persistenz und zeitlicher Reader

Market Data ergänzt die Tabelle `warrant_market_status_observations` und
Migration `20261117_0054` auf `20261116_0053`. Der bestehende Retentionwrapper
schreibt unter seinem vorhandenen Listinglock **vor** Preisvalidierung,
Last-success-Auswahl und Fünfminuten-Sampling einen unabhängig geprüften
Originalstatus oder eine ausdrücklich beobachtete Versorgungslücke. Preisretention
und Preis-Samplepolitik behalten ihren bisherigen Zweck. Es wird keine historische
Statusfolge aus einem früheren Last-success zurückgefüllt.

Der vorhandene Frankfurt-Adapter transportiert einen geeigneten Status auch ohne
Preis oder bei separat ungültigen Preisfeldern. Der preislose Snapshot ist
`INCOMPLETE`, hat keinen BID und keine erfundene Kurszeit. Eine unpassende
Instrument-/Listing-/Quellenbindung oder Originalzeit bleibt abgewiesen. Ein
Transportfehler, fehlende Statuslieferung oder error-retained Payload ergibt
`GAP`, niemals `CLOSED` und niemals ein erneuertes `OPEN`.

Jeder Fakt bindet Workspace, Instrument, Listing, Provider, Routenidentität,
ISIN/MIC, Quellenvertrag/-referenz, eigene Originalstatuszeit, Generierung,
Abruf und erste Erfassung. Deterministische Faktidentitäten deduplizieren
Wiederholung ohne die ursprünglichen Zeiten zu erneuern. Sie sind keine Hashes
unveränderter Anbieterbytes. Verspätete Meldungen bleiben erhalten; Auswahl
richtet sich nach Originalzeit. Widersprüche am selben Originalzeitpunkt bleiben
sichtbar. Quellenhistorie und andere Routen werden angezeigt, ohne daraus einen
stillen Quellenwechsel oder Preisfallback abzuleiten.

`MarketStatusReader.read(route, event_at, known_at)` ist ein schreibfreier
Ownerread im Snapshot des Callers. Er liefert Punkte am angefragten Ereignis,
neueste belegte Punkte, letzte Erfassung, letzte Lücke und Quellenhistorie.
`OBSERVED_AT_INSTANT` gilt ausschließlich am eigenen Zeitpunkt; es gibt keine
Status-TTL, keine Fortschreibung bis zum Lesestand und keine zusätzliche
Bedingung durchgehender Öffnung. Auch ein passender Punkt bleibt hinsichtlich
unabhängiger Quellenqualifikation `NOT_INDEPENDENTLY_VERIFIED`.

Die bestehenden passiven Beleg-GETs ändern ihren Vertrag nicht. Der neue Reader
ist die additive Grundlage des nachfolgenden Regelpfads. Dieser Statusschnitt
aktiviert keine Regel, keinen Provider und keine produktive Zustellung.

### Prüfung und Grenzen

Synthetische Tests führen den tatsächlichen Frankfurt-Adapter über Retention bis
in das unabhängige Journal. Sie prüfen preislose/fehlerhafte Preise, negative und
verspätete Meldungen, Wiederholung, Original-/Quellenbindung, Lücken, Neustart und
Schreibfreiheit. Der PostgreSQL-Fall verwendet eine bewachte UUID-Wegwerfdatenbank
mit abgefangenen externen Aufrufen; er prüft konkurrierende Writer, Migration und
unveränderliche Speicherung. Tatsächlich ausgeführte Ergebnisse, offene/übersprungene
Prüfungen und reguläre Gates werden an Head und Integrationsbaum im PR ausgewiesen.

<a id="b04-b57-loss-monitoring-v1"></a>
## B04/B57: versionierter Verlustpfad und begrenzter Betriebsvertrag

Dieser Implementierungsnachtrag vom 17.11.2026 baut auf dem unveränderten
Gesamtstand #348 → #349 → #350 und dem eigenständigen Statusowner in
[#351](https://github.com/burckhju/trading-workspace/pull/351) auf. Er beschreibt
eine neue fachliche Commandstrecke. Die älteren Soll-Ist-Tabellen und die
anschließend dokumentierten rein lesenden Evidenzverträge bleiben historische
beziehungsweise eigenständige Aussagen. Der Product Backlog bleibt die einzige
Aufgabenstatusquelle; PR-Nachweise binden Prüfung und Integration an konkrete
Heads und Trees.

### Regelumfang und zentrale Aktivierung

| Feld | Vertrag dieses Schnitts |
|---|---|
| Regelversion | `hebeltrader-b04-b57-v1` |
| Fachlicher Teilumfang | `B04_B57_WITH_B58_INPUTS` |
| Baselinebezug | `HEBELTRADER_CONFIRMED_BASELINE`, Version `1.0.0`; vollständige Baseline ausdrücklich nicht aktiviert |
| Zentrale Konfiguration | `TRADING_WORKSPACE_POSITION_MONITORING__HEBELTRADER_SCOPE=DISABLED` als Default; ausschließlich der gesondert freigegebene Wert `B04_B57_V1` wählt später diesen Teilumfang |
| Vorhandener Hintergrundrunner | `TRADING_WORKSPACE_POSITION_MONITORING__ENABLED` und dessen Intervall bleiben gesonderte Betriebsparameter |
| Produktive Quellen | `QUALIFIED_B58_PATHS=()`; keine derzeit positiv belegte B58-Quelle |
| Weiter fehlender Umfang | B05, B06, restlicher F207-2-Schutzpfad, vollständiger F207-5-Meldungs-/Aktivierungs-/Betriebsvertrag; B08 ausgeschlossen |

Der Konfigurationswert aktiviert weder einen Provider noch dessen Nutzungsrechte
und ist kein Quellenbeleg. Er migriert keine einzelne Position. Die spätere
Freigabe erfolgt zentral für die benannte Regelversion und deren nachweislich
abgedeckte Quellenpfade. Im jetzigen Lieferstand ist keine Installation aktiviert.
Auch bei testweise gewähltem Teilumfang bleibt eine nicht qualifizierte Quelle
als `NOT_ASSESSABLE` erhalten und erzeugt keinen Verlusthinweis.

`B58SourceRegistry` ist eine interne, geprüfte Bindung an Provider, ISIN, MIC,
Quellenvertrag/-referenz, Original-BID-Feld, Statusfeld, eigene Statuszeit und
belegte zeitliche Bedeutung. Es gibt keinen HTTP-Command, Formularschalter oder
Umgebungsparameter zum Freistellen eines beliebigen Imports. Qualifikationsreferenz
und Dokumentprüfsumme sind interne Beschaffungsbelege, keine Nutzereingaben und
allein noch keine Quellenqualifikation. Der Produktionskatalog bleibt bis zum
wirklichen Quellennachweis leer. Die aktuelle Implementierung unterstützt nur
den ausdrücklich belegten Punktvertrag `OBSERVED_AT_INSTANT`; andere reale
Zeitsemantiken benötigen ihren eigenen verifizierten Adapter-/Readervertrag.

Ein passender OPEN-Punkt muss die tatsächliche Auswertungszeit belegen. Ein alter
OPEN-Punkt wird weder durch Kalender noch Empfangszeit oder 900 Sekunden
fortgeschrieben. CLOSED, SUSPENDED, widersprüchliche Punkte, spätere Lücken und
ein unqualifizierter Quellenwechsel bleiben ungeeignet. Das ist keine zusätzliche
Forderung durchgehender Öffnung zwischen BID und Auswertung. Der synthetische
Testpunkt zur Testuhr ist kein Nachweis eines realen, so liefernden Anbieters.

### Bestehende wirtschaftliche und zeitliche Owner

`read_loss_inputs` übernimmt den tatsächlichen frühesten effektiven BUY,
Korrekturen, Restmenge, gewichteten Bruttoeinstand, noch beitragende Käufe und
historische Ausführungswährung unmittelbar aus `read_position_execution_basis`.
Es gibt keine zweite Depot-, Währungs- oder Kostenrechnung. Vollverkauf und
Stornierung werden vor Kursvoraussetzungen erkannt.

Der vorhandene Market-Data-Owner liefert gespeicherten Original-BID samt Route
und Herkunft sowie das unabhängige Statusjournal. Product liefert die bestehende
maßstabsbezogene Revision innerhalb ihres endlichen Gültigkeitsbereichs. Der
bestehende Kalenderreader liefert Revisionen und dokumentierte Sitzungen.
`underlying_sessions` ruft wie zuvor
`count_completed_sessions(..., event_at=original_bid_at)` auf. Kaufdatum ist
Tag 0; nur spätere, zur Original-BID-Zeit abgeschlossene Sitzungen zählen.
Endet die 20. Sitzung erst zwischen BID und Abruf, bleibt der ältere BID bei 19.

BID-Alter bis einschließlich 900 Sekunden ist zulässig; 901 Sekunden,
Zukunftszeiten, fehlende separate Originalseitenzeit, Ask/Last/Close oder bloße
Empfangszeit qualifizieren nicht. Historische Währung, dokumentierter
Produktmaßstab und erforderliche Kalenderbindung werden mit derselben
gespeicherten wirtschaftlichen Basis geprüft. Korrekturen, Rücknahmen,
Teilabdeckung und Widersprüche ändern den nachvollziehbaren Befund.

B04 fordert keinen Z1-Verkauf, keinen persönlichen historischen
Basiswert-Einstieg, keine Target-Qualifikation und keine pauschal vollständige
F207-Evidenz. Die bestehende historische Target-Erklärung bleibt an ihren
konkreten Kursbestands-Fingerprint gebunden; dieser Schnitt erweitert sie nicht
auf neue Kursbestände. Ihre spätere Beschaffungsautomatisierung ist ein eigener
Vertrag und keine B04-Voraussetzung.

### Dauerhafte Bewertung und Verlustepisode

| Eingangs-/Positionszustand | Bewertung und Wirkung |
|---|---|
| Geeignete B58-Eingänge, mindestens 20 Sitzungen, BID unter Bruttoeinstand | `LOSS`; neue Episode und genau ein logischer `HEBELTRADER_B04_LOSS`-Alert, falls keine Episode aktiv ist |
| Weiterer geeigneter Verlust während derselben Episode | Neue tatsächliche Bewertung bei veränderten Fakten, gleiche Episode und gleicher logischer Hinweis |
| Identische Eingänge und gleiche Ownerbasis | Unveränderte Bewertung; kein zweiter Ledgerstand, Alert oder Outboxeintrag |
| Fehlend, veraltet, ungeeignet, weniger als 20 oder Datenproblem nach einem Verlust | `NOT_ASSESSABLE` beziehungsweise `NOT_REACHED`; aktive Verlustepisode bleibt erhalten und gesondert sichtbar |
| Geeigneter BID mindestens auf persönlichem Bruttoeinstand | `RECOVERED`; aktive Episode und Alert schließen; ausstehende B04-Zustellung wird terminal unterdrückt |
| Späterer geeigneter Verlust | Neue Episode mit neuer nachvollziehbarer Nummer und neuem Hinweis |
| Wirtschaftliche Korrektur | Neue Bewertung mit neuer Ownerbasis; alte Eingänge und Bewertung bleiben unverändert |
| Vollständiger Verkauf oder Stornierung | `CLOSED` ohne Kursvoraussetzung; Episode/Alert schließen, neue Handlungshinweise und ausstehende Zustellungen entfallen; Historie bleibt |

Ein gegenüber einer früheren qualifizierten Bewertung älterer BID oder ein
widersprüchlicher Preis zur selben Original-BID-Zeit darf keine Erholung
beweisen. Der neue Befund bleibt als Datenproblem gespeichert. Es werden keine
früheren Beobachtungen oder angeblich damaligen Meldungen aus heutigem
Last-success rekonstruiert.

Migration `20261117_0055` auf `20261117_0054` ergänzt beim Monitoring-Owner
`hebeltrader_loss_assessments` und `hebeltrader_loss_episodes`. Assessments sind
unveränderlich und kettenförmig referenziert. Eine Episode referenziert ihren
eröffnenden und gegebenenfalls einmalig schließenden Befund sowie den bestehenden
Alert. PostgreSQL schützt Scope, eindeutige Vorgänger, eine aktive Episode je
Position/Regelversion und die historischen Einträge. Eine Downmigration mit
vorhandener Historie wird verweigert.

### Lauf, Transaktion und Zustellung

Der vorhandene `PositionMonitoringRunner` ruft den neuen Teilumfang innerhalb
seines normalen Zyklus auf. Die bestehende Produktbewertung/Quellenauswahl
beschafft Daten außerhalb des wirtschaftlichen Locks; Status/Preis werden bei
ihrem bisherigen Owner erfasst. Danach erhält die Bewertung den vorhandenen
Trade-Lock und liest erst anschließend einen konsistenten READ-ONLY-Snapshot.
Der kurze Snapshot nutzt eine separate NullPool-Verbindung derselben Datenbank,
damit auch ein Anwendungspool mit einer einzigen Verbindung nicht verhungert.
Rollback und Freigabe sind auch bei Fehlern garantiert; pro gerade bewertendem
Lockinhaber entsteht höchstens eine solche zusätzliche Leseverbindung.

Assessment, Episode, fachlicher Alert und optional vorhandene Notification
committen für B04 gemeinsam. Ein Fehler rollt diesen fachlichen Schritt
vollständig zurück; bereits vorher erfasste Marktbelege bleiben bestehen.
Der Ausführungsowner und parallele Bewertungen verwenden denselben Trade-Lock.
Datenbankconstraints und vorhandene Alert-/Channel-/Destination-Eindeutigkeit
ergänzen die Serialisierung. Wiederholung und Neustart erzeugen keinen zweiten
logischen Hinweis. Der Lauf berücksichtigt neben offenen Positionen auch noch
aktive Episoden inzwischen vollständig verkaufter Positionen.

Die bestehende Durable-Delivery-Sequenz erhält ihren eigenen Commit vor dem
externen Aufruf. Vor B04-Zustellung prüft sie unter dem Trade-Lock nochmals
Alertzustand und tatsächlichen effektiven Restbestand. Vollverkauf, Stornierung,
Recovery oder Invalidierung unterdrücken noch ausstehende Zustellungen mit
einem nachvollziehbaren terminalen Versuch. Ein später eintreffender retryable
Transportfehler setzt eine solche Unterdrückung nicht wieder auf PENDING.
Ein bereits an den externen Adapter übergebener Aufruf lässt sich nicht
nachträglich zurückholen; ein tatsächlich bestätigter Versand bleibt wahrheitsgemäß
historisiert. Es wird kein Exactly-once-Versandversprechen für das externe Netz
erfunden. Tests verwenden ausschließlich abgefangene Aufrufe.

Regelauslöser erzeugen ausschließlich Hinweise. Orders, Ausführungsbuchungen,
automatische Stop-/Zieländerungen und andere Handels-/Preisachsenregeln werden
nicht verändert.

### Passive Sicht und wenige Nutzereingaben

`GET /api/v1/position-monitoring/trades/{trade_id}/hebeltrader-loss?position_id=…`
liest gespeicherte Bewertungen und Episoden in einem READ-ONLY-Snapshot. Die
Positionsdetails zeigen Version/Teilumfang, Aktivierungszustand, fehlende Regeln,
letzten Datenbefund und aktive Episode getrennt. Die bestehenden sechs
Evidenzabfragen bleiben erhalten. Navigation, Lesen, Aktualisierung der Ansicht
und Positionswechsel beschaffen keine Kurse und führen keine fachlichen Writes
aus. Der Workspace zeigt B04 mit eigenem Titel und erzeugt aus absichtlich
unterdrückten B04-Zustellungen keine neue Fehler-Handlungsaufgabe.

Vorhandene Positionen, Ausführungen, Währungs-, Kalender-, Produkt- und
Quellenbelege werden wiederverwendet. Es gibt keine täglichen Bestätigungen,
manuellen IDs, Hashes oder Request-IDs. Dokumentierte menschliche Prüfung bleibt
von unabhängiger Systemverifikation getrennt. Tatsächliche Änderungen,
Belegrücknahmen und Widersprüche werden als konkrete Ausnahmen gezeigt.

### Abnahmegrenze und Folgearbeiten

Gezielte Tests decken die 19/20-Grenze und BID-Zeit, 900/901 Sekunden,
Originalseitenzeit, separate preislose Negativmeldungen, Lücken, Verspätung,
Quellenwechsel, Maßstab/Währung, Episodenfolge, echte Ownerkorrekturen,
Parallelität/Neustart, Zustellunterdrückung und schreibfreie Ansichten ab.
Der PostgreSQL-Durchlauf verbindet den tatsächlichen Frankfurt-Parser und
Retention mit Bewertung, Ledger, Episode, Alert und Outbox; ein weiterer Fall
benutzt den vorhandenen getakteten Runner ohne erneute Nutzereingabe.
Ausschließlich ausdrücklich bewachte synthetische Wegwerfdatenbanken und
abgefangene HTTP-Aufrufe sind zulässig. Sammlung, Skips und ausgeführte Prüfung
werden im PR getrennt mit dem tatsächlichen Head/Integrationsstand ausgewiesen.

Die [Quellenblockade](../reviews/B58_SOURCE_QUALIFICATION_2026-11-17.md) ist offen.
Der implementierte synthetische Pfad belegt keine tatsächlich laufende Versorgung
des Nutzerdepots. Als kleinste reale Voraussetzung fehlt ein zugänglicher,
nutzungsrechtlich geeigneter konkreter Anbieter-/Instrument-/Listingpfad mit
Original-BID, eigener BID-Zeit, instrumentbezogenem Status mit eigener Zeit und
belegter Zeitbedeutung sowie Negativ-/Status-only-/Lücken-/Recovery-Lieferung.

B05 benötigt verifizierten letzten Handelstag, maßgeblichen Produkttermin,
festes Ausstiegslisting, dokumentierte Rückwärtszählung und Friststufen; diese
Regel bleibt von aktueller BID-Verfügbarkeit unabhängig. Restliches F207-2/B06
benötigt dokumentierte Stopberührungen, Schutzboden, Bekanntgabe, anschließende
Schutzüberwachung, Korrekturklärung und Z1-bezogene Sitzungszählung. F207-5
benötigt gemeinsame Meldungsdarstellung, gesehen/abgelehnt/ausgeführt, globale
Versionierung und gesonderte Betriebsabnahme. Dieser Schnitt erfüllt davon nur
den ausdrücklich genannten B04-Episoden-/Zustell-/Anzeigeanteil.

**Liefernachtrag 17.11.2026:** Die neue ausdrückliche Freigabe umfasst die
geordnete Integration der grün geprüften Draftkette und die versionierte
Bereitstellung für den vorhandenen PC-Updateweg. #348 → #349 → #350 → #351 →
#352 → #353 sind unverändert integriert; der gemeinsame Main-Commit
`02eb6e1ca87dd8470ff8f17bf59dbfa6f98fc715` besitzt exakt den zuvor geprüften
#353-Tree. Der gemeinsame Release-PR führt diesen Teilumfang mit `1.5.47`
zusammen. Die [Release-Notiz](../releases/V1.5.47-HEBELTRADER-LOSS-PATH.md)
bindet die Integrationsbelege und den kontrollierten Updateweg; Aufgabenstatus
bleibt im Backlog.

Die Bereitstellung ändert keine fachliche Aktivierungsgrenze:
`HEBELTRADER_SCOPE=DISABLED` und `QUALIFIED_B58_PATHS=()` bleiben bestehen.
Die vollständige Baseline wird nicht aktiviert. Der B05-Rechenschnitt bleibt
`DOCUMENTED_CALENDAR_CALCULATION_ONLY` mit `B05_NOT_ACTIVATED`. Ein Softwaretag
ersetzt weder den geeigneten tatsächlichen Quellenpfad noch dessen persönliche
Depotabdeckung. Die Freigabe zur Bereitstellung ist kein Nachweis einer bereits
ausgeführten PC-Installation. Neue produktive Providerzustimmungen, echte
externe Nachrichtentests und die zentrale Regelaktivierung bleiben gesonderte
Entscheidungen.

Der eigene Release-PR synchronisiert `VERSION`, `backend/pyproject.toml`,
`frontend/package.json` und `frontend/package-lock.json`. Nach dessen Integration
verlangt der vorhandene Publisher erfolgreiche neueste Backend-/Frontend-/E2E-
Main-Push-Läufe am noch aktuellen Main-SHA; erfolgreiche Draftprüfungen ersetzen
dies nicht. Bestehende Tags, insbesondere `v1.5.46`, werden nicht verschoben.
Vor einem später genehmigten Update werden Tag und vollständiger
Releasecommit unabhängig geprüft. Der vorhandene verwaltete Linux-Launcher
übernimmt Sicherung des alten Quellstands, PostgreSQL-Custom-Dump,
Consent-State-Archiv, Konfigurations-/Image-/Datenbankprüfungen und Migration im
kontrollierten Wartungsfenster. Der vom alten Tag aus nötige additive Schemapfad
ist `0049 → 0050 → 0051 → 0052 → 0053 → 0054 → 0055`.

Eine automatische Rückkehr zu `1.5.46` wird nicht zugesagt: Die neuen Migrationen
verweigern destruktive Downgrades bei vorhandenen Belegen; der alte Alert-Reader
kennt den neuen B04-Typ nicht. Nach begonnener Migration braucht Recovery eine
eigene geprüfte Entscheidung anhand tatsächlicher Phase, Schema, Images und
Sicherungen. Archivlesbarkeit ist kein Restore-Nachweis. Die anschließende
Betriebsabnahme prüft installierten Commit/Images, Alembic-current und -head,
Readiness, erhaltene Daten/Konfiguration und einen vollständig abgeschlossenen
Hintergrundzyklus. Quellenqualifikation und zentrale Aktivierungsfreigabe bleiben
davon getrennt. Maßgeblich sind die bestehenden Verträge
[Linux-Launcher](../technical/LINUX_LAUNCHER.md) und
[Betrieb/Release](../technical/ISSUER_MONITORING_OPERATIONS.md).

<a id="b05-documented-deadline-calculation"></a>
## B05: unabhängige dokumentierte Rückwärtszählung

Dieser gesonderte Rechenschnitt baut technisch auf dem Reviewstand des
[B04/B57-PR #352](https://github.com/burckhju/trading-workspace/pull/352) auf,
besitzt fachlich aber keine BID- oder B04-Abhängigkeit. Der
[tatsächliche Quellenbefund](../reviews/B58_SOURCE_QUALIFICATION_2026-11-17.md#5-unabhängiger-b05-anschluss-reale-quellen-und-verbleibender-scope)
belegt zugängliche Originalkalender 2026/2027 einschließlich Sonderzeiten; eine
datierte Produktansicht liefert nur einen historischen Produkthinweis. Die
aktuelle persönliche Produkt-/Termin-/Ausstiegslistingbindung bleibt offen.
Aufgabenstatus und verbleibende Beschaffung stehen weiterhin ausschließlich im
Backlog, nicht in einer zweiten Aufgabenliste dieses Anhangs.

`calculate_product_deadline` verwendet explizite Produktdaten für Laufzeitende
und letzten Handelstag, das fest gewählte Ausstiegslisting und den bestehenden
`SessionEvidenceRead`. Die Funktion verifiziert Produkttermine nicht selbst und
besitzt keine Nutzererfassung. Ihr zukünftiger Caller muss diese Eingänge aus
dem qualifizierten Product-Owner liefern. Rückzahlung ist kein Terminersatz.

Der frühere der beiden erforderlichen Produkttermine ist maßgeblich (B17).
Dessen gesamter Kalendertag zählt nicht mit (B18). Die 20. davor dokumentierte
Produktsitzung bestimmt den Ausstiegstag; die erste Öffnung der vorherigen
Sitzung bestimmt die Vorwarnung nach B19. Bei genau 20 belegten Sitzungen ist
der Ausstiegstag vorhanden, die fehlende Vorwarnsitzung bleibt ausdrücklich
`PARTIAL`. Eine spätere Auswertung verschiebt die ursprünglichen Termine nicht.
Fehlende oder unbekannte Kalendertage werden nicht als Feiertage ergänzt.

Instrument, Workspace, festes Listing, endlicher Gültigkeitsbereich,
Originalkalenderrevision, Fingerprint, Wissenzeit und menschliche Prüfung
bleiben gebunden. Verkürzte/geteilte Sitzungen, Sommerzeit und Jahreswechsel
folgen den dokumentierten Intervallen. Die Phasen `BEFORE_WARNING`,
`WARNING_DUE`, `EXIT_SESSION_STARTED` und `CALENDAR_SESSION_ENDED` sind
nachvollziehbare Kalenderbefunde. Die letzte Kalenderschlusszeit ist ausdrücklich
keine unabhängig verifizierte produktspezifische B20-Schlussfrist.

Der Ergebnisumfang lautet `DOCUMENTED_CALENDAR_CALCULATION_ONLY`, der Regelstatus
`B05_NOT_ACTIVATED`. Die Funktion hat keinen BID-Parameter, Provideraufruf,
Schreibpfad, Alert oder Runneranschluss. 47 gezielte synthetische Domainfälle
prüfen die genannten Grenzen. Headgebundene reguläre Nachweise stehen im
zugehörigen PR. Der reale persönliche Terminpfad benötigt weiter qualifizierte
Produkt-/Originalterminbelege, die dauerhafte feste Ausstiegslistingbindung,
produktspezifische Schlusszeit und anschließend seinen ausdrücklichen
Ereignis-/Betriebsvertrag. Diese kleine Vorbereitung ist keine laufende
Fristüberwachung und erweitert die B04/B57-Aktivierung nicht.
