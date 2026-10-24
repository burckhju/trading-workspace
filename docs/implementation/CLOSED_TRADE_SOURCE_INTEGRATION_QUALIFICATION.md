# Abschlussauswahl → Trade-Ergebnis und genaue Quellen

## Auftrag und feste Abhängigkeiten — 21.10.2026

Der Nutzer hat den getrennten Integrationsschritt mit **„Wie vorgeschlagen umsetzen“**
beauftragt. Kein Merge nach main, Release, Tag, Deployment oder PC-Update ist darin
enthalten. Keine reale Buchung, Nachricht oder Provideraktivierung erfolgt.

| Grundlage | Fest verwendeter Stand |
|---|---|
| main / v1.5.11 | `5e9ede2dc29f52eaff601d30614df6bc9c25c426` |
| Abschlussreport, Draft-PR #270 | `de413843a814ac6a1016f474f3e5366cd81ea96a` |
| Unabhängige Quellenansicht, Draft-PR #272 | `950865415598c04338fdafb9f78d9222d9f53a3f` |
| Gemeinsamer Entwicklungsbranch | `integration/closed-trade-result-sources` |

Die beiden vollständigen Abhängigkeiten werden auf dem eigenen Branch mit zwei
Eltern nachvollziehbar verbunden. Nur der gemeinsame native Runner erforderte
Konfliktauflösung: dynamische Auswahl beider Spec-Dateien aus #270 **und**
Trace-Aufzeichnung aus #272 bleiben erhalten. Das ist keine Alt-PR-Mergeserie und
kein Merge nach main. #268/#269/#204 werden nicht übernommen. #271 war zunächst
getrennt; sein späterer Main-Merge gehört ausschließlich zur unten belegten
Basisfortschreibung, nicht zu einer neuen Alt-PR-Mergeserie.

Frühere grüne Abhängigkeitsläufe sind historische Nachweise, keine Qualifikation
dieses integrierten Trees. Die genaue neue Head-/Tree-/CI-Checkoutbindung,
Run-IDs, Ergebnisse, Fehlversuche, Artefakthashes und Bildprüfung werden im
zugehörigen Integrations-PR festgehalten. Testcode/Collection allein ist kein
Ausführungsnachweis. Der Product Backlog bleibt die einzige Aufgabenstatusquelle.

## Begrenztes Quelleninventar

| Abschnitt / Owner | Read und Identität | Version, Konsistenz und Consumer | Integrationsänderung |
|---|---|---|---|
| Geld / Performance + FT-010 | `GET /api/v1/performance/closed-trades`, eigener Workspace, exakte Trade-ID und Produkt-ID | `closed-trade-gross-v1`; bestehender begrenzter REPEATABLE READ READ ONLY; `ClosedTradeSources` | Ein vorhandener Reportread liefert den ausgewählten vollständigen Eintrag **und** alle monetären Quellen; keine Rechenschleife. |
| Identität / Durchführung | `.../trade-position/trades/{id}/sources` | Eigenes begrenztes Lesefenster; effektive/historische Timeline, aktuelle Währungsableitungen und getrennte Originalfakten | Bestehender Core wird vor Kindlesern geprüft; sein Zustandslabel benennt ausdrücklich sein Ausführungs-Lesefenster. |
| Originalplan | `.../sources/plan` | Konkret gebundene P1 und vorhandene Freigabe, nicht latest P2 | Bestehender Reader unverändert. |
| Exit-Bewertung | `.../sources/reviews?version_id=...` | Gespeicherte Version/Status und separate heutige Quellenprüfung | Historische Links behalten den Berichtskontext; kein Geld → GOOD/IMPROVABLE-Schluss. |
| Journal | `.../sources/journal?version_id=...` | Konkrete Version, DRAFT-Bearbeitungsrevision, exakte Reviewquelle | Kontext bleibt bei beiden Pins erhalten; mehrfach vorhandene Kontextwerte werden nicht durch Object-Konvertierung still bereinigt. |
| Evidence / Lessons | `.../sources/evidence`, genaue Lessonversionsroute | Bestehende Relationsarten, genaue E-/L-Versionen; getrenntes Lesefenster | Keine neue Persistenz, Materialisierung oder Umdeutung. |
| Rückweg / Performance-UI | Feste interne Route `/performance/closed-trades` | Zeitraum, Währung, Zone, Zeilenfilter, lokale Seite; neu gelesener Report | Allowlist statt allgemeinem `returnTo`; Browser-Back und Reload ebenfalls unterstützt. |

## Lese- und Darstellungsvertrag

Die bestehende Tradeverwaltung wird erweitert, keine konkurrierende Detailseite.
Der Listenlink `Trade … prüfen` öffnet `view=sources` mit der exakten Trade-ID.
Der neue reine UI-Consumer `ClosedTradeResult` ruft den bestehenden Report auf und
verwendet dessen einen passenden Eintrag. Definition, zurückgelieferte Filter,
Währung und Trade-/Produktidentität werden geprüft. Fehlender oder doppelter
Tradeeintrag ist ein Fehler, kein Ersatztrade. Der Backend-Workspacefilter bleibt
maßgeblich; die URL kann keinen Workspace vorgeben.

Betrag, qualifizierende Buchungshistorie, effektive IDs, historische Korrekturen,
Währungsbelege und Abschlusszustand im Ergebnisabschnitt stammen aus **derselben
Reportantwort**. Auch frühere SELL-Beiträge gehören dazu. Die UI addiert nichts,
leitet keine Währung ab und setzt bei unbekanntem Betrag keine Null ein. Offene,
stornierte, nicht sicher projizierbare, nicht qualifizierte oder inzwischen aus
der Auswahl ausgeschlossene Trades behalten den tatsächlichen Ownerstatus;
kein alter Closed-Status oder Betrag wird festgehalten. Ausgeschlossene Zeilen
heißen ausdrücklich „aus dieser Auswahl“, nicht pauschal „Geld unbekannt“.

Der wiederverwendete Reportfingerprint umfasst die **gesamte Reportgrundlage**,
nicht nur den ausgewählten Trade. Eine Abweichung kann deshalb auch durch andere
Trades oder Referenzdaten verursacht werden. Der Hinweis behauptet weder eine
bestimmte Änderung an diesem Trade noch die Rekonstruktion eines alten Reports.
Fehlender Listenfingerprint ist ausdrücklich „Vergleich nicht belegt“, nicht gleich.
Ein mitgegebener Fingerprint beglaubigt keine URL; Geld kommt ausschließlich vom
Backend. Direkte Quellenlinks ohne Berichtskontext bleiben lesbar, zeigen aber
keinen Rohpositionsbetrag als vollständiges Ergebnis.

Plan-, Ausführungs- und Lernabschnitte behalten ihre eigenen kurzen Leser. Sie
bestätigen nicht automatisch den Finanzsnapshot. Insbesondere wird eine gespeicherte
Exit-Bewertung nicht als geprüfte Bewertung der neueren Ergebnisgrundlage ausgegeben.
Keine gemeinsame globale Snapshot-/CURRENT-Garantie, Transaktion über die
Benutzerinteraktion oder neue Datenbankisolation wird eingeführt.

Ein optionaler Journalfehler löscht das qualifizierte Ergebnis nicht; sein bewusster
Retry ruft keinen Geld-Owner erneut auf. Ein Geldlesefehler lässt genaue Reflexion
sichtbar und besitzt einen eigenen Retry. Abbruch, Unmount, neue Besuche derselben
Trade-ID und Pinwechsel dürfen weder Daten noch Fehler/Ladezustand zurückschreiben.

## Navigation und Sicherheit

Die flache Allowlist enthält ausschließlich `report_context=closed-trades`,
`from_date`, `to_date`, `report_currency`, `report_timezone`, `report_view`,
`report_page` und optional `report_basis`. Echte Kalenderdaten, Reihenfolge,
dreistellige Großbuchstabenwährung, gültige IANA-Zone, fünf bestehende Zeilenfilter,
Seiten 1–100 (2.000 Trades / 20 Zeilen) und 64-stelliger Hex-Fingerprint werden
validiert. Mehrfache bekannte Parameter bleiben ein sichtbarer Fehler, auch nach
historischer Quellenwahl. Unbekannte URLs, Beträge, `returnTo`, externe oder
verschachtelte Rückziele werden nicht übernommen.

Die Liste schreibt den angewendeten Filterkontext in ihre URL. Lokaler
Zeilenfilter/Seitenwechsel verwendet weiterhin dieselbe Antwort ohne neuen Read.
Die Rückkehr liest ausdrücklich neu; sie verspricht keinen gespeicherten alten
Report. Ist die alte Seite nicht mehr verfügbar, erscheint ein Hinweis auf die
nun angezeigte letzte Seite. Es gibt keine neue Sortierfunktion; die bestehende
Ownerreihenfolge bleibt erhalten. Eingabefilter werden erst beim bewussten
„Bericht lesen“ angewendet. Quellenmodus mountet keine Buchungs-/Journalformulare;
der bestehende Neue-Tab-Einstieg aus einem Editor wird nicht geändert.

## Neue und weiterverwendete Nachweisstellen

| Kriterium | Konkrete Prüfung / Grenze |
|---|---|
| A1 | `ClosedTradeSourceJourney.test.tsx`: echte Routerkomponenten, Seite 2, beide historischen Pins, Rückweg/Browser-Back/Reload; `closed-trades-report-postgres.spec.ts`: tatsächlicher Listenlink, Seite 2 und Filterrückkehr. |
| A2 | Bestehender nativer Sechs-Buchungs-Referenzfall behält September 10→30 und lifetime 50→70; neue Detailanzeige liest 50 und später 70 aus dem echten Report. Native Cross-Owner-Assertions in `test_trade_source_view_postgres.py`. |
| A3 | Echter Referenzfall ohne Review/Journal/20-EOD/Lesson zeigt 50/70; UI-Gegenrichtung zeigt Reflexion trotz Geldlesefehler. |
| A4 | Bestehende P1/P2-Browser-/PostgreSQL-Identitätsprüfungen bleiben erhalten; Quellenreise startet jetzt tatsächlich aus der Abschlussliste. |
| A5 | Bestehende Timeline-/Ownerfälle und ersetzte September-Execution bleiben; neue UI-Matrix prüft OPEN, CANCELLED, unbekannte Historie und Auswahl-Ausschlüsse ohne alten Betrag. |
| A6 | `trade_source_journey.ts` zeigt einen gesonderten älteren synthetischen +50-Trade mit gespeichertem IMPROVABLE sowie Verlust −10 / Korrektur −11 mit unverändertem GOOD; NOT_ASSESSABLE, DRAFT und fehlend bleiben getrennt. Kein objektives Qualitätsurteil. |
| A7 | Keine neue Regelprüfung. Bestehende Preisachsen-/Freitext-/fehlende Bindungsfälle und Originalplanwarnung bleiben maßgeblich. |
| A8 | Exakter Journalpin, Revision 2/Reload und unveränderte finale J1 nach Korrektur bleiben im nativen Quellenfall erhalten; finanzielle Kontextwerte bleiben auch beim Reviewquellenlink erhalten. |
| A9 | Native E1/L1 trotz L2, Tastatur/Reload, CONTRADICTS und ungültiger Pin ohne latest-Fallback bleiben erhalten. |
| A10 | Bestehende mehrfachen E-/L-Relationslinks teilen sich genau einen ausgewählten finanziellen Tradeeintrag, keine Multiplikation oder neue Summenbildung. |
| A11 | Optionale Transportstörung und gezielter Retry bei weiterhin −11; UI-Fälle für unbekannt, Null, technische Finanzfehler, fehlenden Kontext und fehlenden Fingerprint. |
| A12 | Kontrollierte Promises A→B→A für Geld einschließlich Fehler/Abschlussantworten; bestehende Quellen-/Versionsisolation plus gemeinsamer Routertest. |
| A13 | Echter Listeneintrag vor Septemberkorrektur öffnet anschließend 70 mit Basiswechselhinweis; Rückkehr zeigt neuen 60-Kohortenteilbetrag. Bestehende vier Performance- und zwei Quellen-PostgreSQL-Races bleiben erhalten. |
| A14 | Zusätzliche komplette Tabellenfingerprints und beobachtete Browser-GET-Fenster für Einstieg, Korrekturread, Pins, Rückweg und Pagination; unveränderte Netzwerk-/Stackguards. |
| A15 | Bestehende Workspace-/Trade-/Versions-Readerguards unverändert; neue UI-Identitäts-/Definitions-/Filter-Ablehnungen, strikt interne Ziele und doppelte Parameter. |
| A16 | Beide vorhandenen geschützten nativen Fälle werden erweitert, nicht ersetzt. Unveränderte vollständige Backend-/Frontend-/Smokegates sowie tatsächliche Desktop-/Mobil-Sichtprüfung bleiben erforderlich und werden nur nach Ausführung im PR als bestanden ausgewiesen. |

Der ursprüngliche Oktober-Referenztrade bekommt **keine erfundene zukünftige
20-EOD-Nachbeobachtung**, nur um eine Bewertung zu erzeugen. Für Gewinn/IMPROVABLE
wird deshalb ein ausdrücklich separater, älterer August-Trade über echte Commands
angelegt, dessen bestehende synthetische vergangene Beobachtungen ausreichen.
Die Oktoberdaten und unabhängigen 50/70-Sollwerte bleiben unverändert. Das ist
kein Nachweis einer finalen Bewertung des noch nicht nachbeobachteten Oktobertrades.

## Ausführung und Grenzen

Lokale Werkzeuge: aus dem vorhandenen verifizierten Toolchainpaket Python 3.12.15,
Node 22.16.0, npm 10.9.2, unveränderte Projektpins. Docker und PostgreSQL sind lokal
nicht verfügbar; native Collection ist kein Lauf. Native Ausführung erfolgt im
bereits eingerichteten isolierten CI-Runner, nicht auf einem Nutzerstack.

Vor jedem neuen schreibenden Setupaufruf wird das markierte Wegwerfziel geprüft.
Der bestehende begrenzte EOD-Seed bleibt unverändert. Die bestehende Observation-GET
mit Ownerrefresh wird ausschließlich als ausdrücklich schreibwirksames Setup
außerhalb der Readfenster aufgerufen. Die neue Quellenstrecke ruft sie nicht auf.
Keine fremden Daten, Credentials, private .env oder echte Providerbeobachtungen.
Keine Änderung an Dependencies, Version, Arithmetik, Resolver, Timeouts, Retries,
Assertions der ursprünglichen Geldfälle oder Coveragegrenzen.

Frühere rote lokale Versuche (aufgebautes Node-Modullayout, veraltete URL-/Text-
Assertions, mehrdeutiger Geldselektor, asynchrone Mock-Lintregeln und unterbrochener
Vollgatelauf) bleiben in den Logs. Korrekturen betreffen Testaufbau/Selektoren oder
die ausdrücklich gewollte Navigation, nicht finanzielle Sollwerte.

Technische Qualifikation ersetzt keine menschliche Fachabnahme, Installation,
allgemeine Regelabweichungsbewertung oder den vollständigen M7-/M8-Umfang.

## Parallele Main-Fortschreibung und erneute Qualifikation

Während der ersten vollständigen Integrationsprüfung wurde main außerhalb dieses
Arbeitspakets am 21.10.2026 um 20:27:52 UTC auf
`5c76ff495b0797c4de00666ee358219858e33afd` fortgeschrieben: #271 samt bestehenden
v1.5.12-Metadaten. Die vorherige Integrationsprüfung auf `f1898487` / Tree
`3c282766c937a3a9623d66ef0032dcc7b74bedf0` war tatsächlich grün (3.034 Backendtests,
670 Frontendtests, beide nativen Fälle und 63 Smoke-Erfolge), verwendete aber noch
main `5e9ede2d`. Der unabhängige Abschlussabgleich erkannte diesen Basiswechsel;
diese Erfolge wurden nicht als aktuelle Main-Kompatibilität umgedeutet.

Die neue Main-Basis wird mit eigenem zweiten Elterncommit in den Integrationsbranch
übernommen. Der tatsächliche Merge ist konfliktfrei; beide getrennten Änderungen
an Traceability und Backlog bleiben erhalten. Der Main-Delta enthält zwei bereits
freigegebene Pacing-Bedingungszeilen, seine Regressionen/Dokumentation und die
konsistenten 1.5.12-Versionsfelder; keine Dependencyversion wurde dabei geändert.
Die finanzielle Integration und ihre Tests werden nicht angepasst oder gelockert.
Es wird weder main geändert noch eine weitere Version, ein Tag oder Deployment
für die Quellenintegration erzeugt. Die Version 1.5.12 bezeichnet die übernommene
Basis, nicht eine Veröffentlichung dieses noch offenen Integrations-PRs.

Alle regulären Gates und beide isolierten nativen Browserwege werden auf dem
neuen gemeinsamen Head erneut ausgeführt. Ihre tatsächlichen Ergebnisse und
exakten Head-/Tree-/Testcheckout-Identitäten stehen anschließend in PR #273;
der vorherige komplette Lauf bleibt ein getrennt datierter Nachweis.

## 23.10.2026 — gemeinsame Entwicklungsqualifikation mit Journal/FT-011

Der konkretisierte Startprompt 11 beauftragt die gemeinsame Entwicklungsintegration
von #273 und #269, nicht Main-Merge, Veröffentlichung, Schließen anderer PRs oder
PC-Update. Die obige Abgrenzung von #269 gehört zum historischen Auftrag vom
21.10.; ausschließlich dieser datierte Nachtrag erweitert den Übergabeumfang.

| Fest erneut geprüfte Grundlage | Commit |
|---|---|
| main / unveränderter Tag v1.5.12, einschließlich #271 | `5c76ff495b0797c4de00666ee358219858e33afd` |
| #273 vor der gemeinsamen Integration | `550ebfc9c90662cc51bef08f4e34c5d2057d21e7` |
| #269, eigenständige Herkunft bleibt erhalten | `58c842c367b0ce75fa8e445e908fd3e78ff8477c` |
| Gemeinsame Git-Basis von #269 und #273 | `5e9ede2dc29f52eaff601d30614df6bc9c25c426` |

Die vollständige Git-Historie bestätigt #270 (`de413843`), #272 (`95086541`) und
#271 (`6be30fc2`) als Vorfahren von #273. Main ist schon enthalten und wird nicht
noch einmal integriert. #269 wird als zweiter Elternstand übernommen, nicht
nachgebaut oder unabhängig nach Main gemergt. Sein ursprünglicher Branch/PR
bleibt unverändert und offen.

Der tatsächlich reproduzierte Mergekonflikt betrifft ausschließlich
`.github/workflows/e2e.yml`, dort zwei Konfliktblöcke: Trigger und Job-/Uploadende.
Die Auflösung ergänzt die Vereinigung der Trigger und den vollständigen
Journaljob. Smoke und Finanzjob sind strukturell identisch mit #273; der neue
Journaljob ist strukturell identisch mit #269. Beide Finanzfälle, `error` bei
fehlenden Pflichtartefakten und versteckte Nachweisdateien bleiben erhalten.
Die übrigen zwölf übernommenen #269-Dateien bleiben bytegleich. Es gibt keine
Änderung an produktiven Fachownern, Migrationen, Abhängigkeiten, Version oder
Schutz-/Coverage-/Zeit-/Retrygrenzen und keine zusätzliche Produktfunktion.

| Fähigkeit | Tatsächlicher Consumer / Herkunft | Gemeinsamer Nachweis und Grenze |
|---|---|---|
| Vollständiger Tradebetrag und Rückkehr | `ClosedTradeResult`, `ClosedTradesPage`, bestehende Quellenreader aus #273 | Bestehende A1–A16 unverändert; aktuelle vollständige Gates und tatsächliche Abschlussreise erforderlich. |
| Periodische SELL-Beiträge | Bestehender Performance-Owner und erster Finanzrunner | Unveränderte 10/30- sowie 50/70-Referenzen; kein Ersatz des Tradebetrags durch Monatsbeiträge. |
| Journal, Folgeversion, Korrektur | Bestehender Journalfall aus #269 | Separater geschützter Job; keine neue Journalpflicht für finanzielle Auswertung. |
| FT-011 und genaue alte Lessonversion | Bestehender Evidence-Historienfall aus #269 | Zweiter Fall im Journaljob; 19/20-Grenze, SOURCE_BUSY und historische Pins unverändert. |
| Qualität und Betrieb | Reguläre Backend-/Frontend-/E2E-/Versionsschutzworkflows | Technische Prüfung, menschliche Abnahme, Release und beobachtete Installation bleiben getrennt. |

### Verbindliche gemeinsame Ausführungsbindung

[PR #273](https://github.com/burckhju/trading-workspace/pull/273) enthält den
aktuellen Ausführungsbeleg mit finalem Head, Base, tatsächlichem PR-Checkout,
vollständigem Tree, Trigger, Run/Job/Attempt, Rohreports, Artefaktdigests und
Sichtprüfung. [PR #269](https://github.com/burckhju/trading-workspace/pull/269)
bleibt der Herkunftsnachweis. Frühere getrennte grüne Läufe werden weder addiert
noch als neuer gemeinsamer Erfolg gewertet. Ein offener oder fehlender Pflichtlauf
ist kein bestandener Nachweis.

Die vor diesem Auftrag veraltete #273-Beschreibung nannte noch `ac3dc940` und
fehlende native Gesamtprüfungen, während der tatsächliche Head bereits `550ebfc9`
war. Die damaligen erfolgreichen PR-Läufe 39672932252 (Backend), 39672932199
(Frontend), 39672932249 (E2E) und 39672932361 (Version) gehören zu diesem früheren
Head. Die datierte PR-Fortschreibung trennt diese Diskrepanz vom neuen gemeinsamen
Abschluss; sie schreibt historische Aussagen nicht rückwirkend um.

Alle vier vorab festgelegten nativen Fälle müssen auf demselben gemeinsamen Tree
jeweils genau einmal erfolgreich laufen: SELL-/Quellenreise, Abschlusslistenreise,
Journal-/Lesson-/Korrekturweg und FT-011-Historie. Erwartete Dateinamen, Titel und
IDs bleiben in den bestehenden Reportprüfern gebunden. Keine Skips, Flaky-Ergebnisse
oder automatischen Retries in diesen Pflichtfällen. Geschützte Smoke-Skips ersetzen
nicht die Ausführung im zuständigen Ownerjob.

Die Finanzfälle verwenden nacheinander eigene frische UUID-Stacks mit
Loopbackports 35432/38080; der separate Journaljob verwendet 25432/8080.
Artefakt- und Runtimepräfixe sind getrennt. Der Journal-Preishelper wird nur durch
die Lernfälle verwendet; die Finanzquellenreise behält ihren eigenständig
guardierten `seed_source_view_prices.py`. Requestguards, DB-/Netz-/Mountidentität,
kurze reine Lesefenster und ausschließlich eigenes Cleanup bleiben unverändert.

### Zuordnung I01–I16, zusätzlich zu A1–A16

| Kriterien | Maßgeblicher Beleg / Abnahmegrenze |
|---|---|
| I01–I03 | Obige feste Heads, vollständige Git-Ancestry, dokumentierter Zwei-Eltern-Merge und struktureller Workflowvergleich. |
| I04–I09 | Unveränderte A1–A15 und ihre benannten Geld-, Historien-, Fehler- und Navigationsfälle; aktuelle Ausführung im PR. |
| I10–I12 | Vier native Rohreportidentitäten, PostgreSQL-Fälle, Stack-/Fingerprint-/Cleanupbelege und vollständige finale Gates; tatsächliche Fehler/Skips separat. |
| I13 | Dieser Nachtrag, gezielte PB-018/PB-019-/Regressionsfelder und Traceability; aktuelle PR-Übergabe, kein zweites Aufgabenregister. |
| I14 | Ausschließlich Entwicklungsintegration beauftragt; keine Freigabe für Main-Merge oder Veröffentlichung festgestellt. |
| I15 | Neue Veröffentlichung nicht beauftragt, nicht als bestanden bewertet. v1.5.12 bleibt unverändert auf dem alten Main-Commit. |
| I16 | Keine beobachtete PC-Installation oder menschliche Fachabnahme; folgende lesende Checkliste und Wiederherstellungsgrenzen. |

### Lesende spätere Fachabnahme und Betriebsgrenzen

Auf einer gesondert identifizierten Installation eine vorhandene Abschlussauswahl
öffnen, einen belegbaren Trade wählen und vollständigen Betrag, tatsächliche
Ausführungen und ursprünglichen Plan nachvollziehen. Vorhandene genaue historische
Review-/Journal-/Evidence-/Lessonquellen öffnen; gespeicherte Bewertung und heutige
Quellenprüfung unterscheiden. Zur vorherigen Filter-/Seitenauswahl zurückkehren und
sichtbaren Basis-/Seitenwechsel erklären. Fehlende Reflexion, unbekannter Betrag,
exakte Null und unvollständige Gesamtsumme bleiben unterscheidbar. Dafür keine
Testtrades, wirtschaftlichen Korrekturen oder neuen Lernfassungen im echten Bestand
erzeugen; Observation-Refresh ist keine reine Lesediagnose.

Ein späteres ausdrücklich freigegebenes Update verwendet ausschließlich den
[vorhandenen verwalteten Launcher](../technical/LINUX_LAUNCHER.md), einen tatsächlich
veröffentlichten Tag mit exakt geprüftem Commit, die vorhandene private Compose-Kette
und eine kompatible geprüfte Sicherung. Hier wird kein Installationsziel oder
Updatebefehl für diesen unveröffentlichten Entwicklungsstand ausgegeben.
Restore-/Schemakompatibilität ist vor Wiederherstellung zu prüfen; kein Versprechen
eines verlustfreien destruktiven Downgrades. Prompt 09 bleibt der nächste getrennte
fachliche Auftrag, keine automatische Modellaktivierung oder Erweiterung dieses Schnitts.
