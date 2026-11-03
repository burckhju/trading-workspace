# UX4-C — Einzelne SELL-Beiträge und erklärte Abschlusskennzahlen

## Auftrag und verifizierte Basis

Stand: 03.11.2026, Europe/Berlin. Eigenständiger Draft-PR auf Branch
`feat/ux4-c-performance-visualization-20261103`. Keine Merge-, Release-,
Versionswechsel-, Deployment- oder PC-Freigabe.

| Bezug | Exakter Stand |
| --- | --- |
| Verifizierter Main bei Start und vor Veröffentlichung | `3397399e7bf8364501437f9509a4fb18dbe32c08` |
| Main-Tree / integrierter UX4-B-Tree | `c9362029d9fc3a1d0ccf7bee4e1f5b942e474807` |
| Zuerst aktualisierter Startprompt, eigener erster Commit | `c3d9469902c3772c701c03a3ed253f4be0cec1ab` |
| Implementierungs- und Testsnapshot vor diesem Dokumentnachtrag | `c1a8fc72ad3d143deb072fa79662b420c435fb96` |
| Vollständiger Tree dieses Implementierungssnapshots | `61308222774165896fc093121cd2cd73a8753a79` |

Der lokale Planungsschritt `d19d221` und der publizierte erste Commit besitzen
exakt denselben Tree `90639b4ebc1b02445fcebf533adf5717d076d290`. Die Veröffentlichung
über die vorhandene GitHub-Verbindung verändert nur Commitmetadaten; der
lokale Checkout ist anschließend auf die tatsächlichen Remotecommits angeglichen.
Lokaler Index und publizierter Implementierungstree wurden ausdrücklich verglichen.

Die nachfolgende CI gehört ausschließlich zum tatsächlichen aktuellen
PR-Head und seinem realen Checkout. **Die PR-Beschreibung führt die finalen
Run-/Joblinks, Checkout-SHA, Treevergleich und Ergebnisse.** Dieses Dokument
hält den fachlichen Schnitt und die lokale Nachweisgrenze fest; es erklärt
keinen späteren Head allein aufgrund älterer grüner Läufe für qualifiziert.

## UX4-B-Abschluss

[PR #322](https://github.com/burckhju/trading-workspace/pull/322) ist tatsächlich
integriert. Der datierte Nachtrag in
[UX4_B_QUALIFICATION](UX4_B_QUALIFICATION.md) ordnet die lokalen Nachweise,
alle neun finalen PR-Jobs und die tatsächliche nachgelagerte Main-CI exakt zu.
Kein neuer UX4-B-Produktfix wurde gefunden oder implementiert. Die ursprünglichen
Historienkomponenten, Daten und Tests werden nicht erneut entwickelt.

## Fachlich begrenzter Lieferumfang

### SELL-Beiträge

`RealizedGrossVisualization` wird innerhalb des vorhandenen
`RealizedGrossReportView` zwischen Summary und Quellenkarten eingebunden.
Sie erhält die akzeptierte vollständige `RealizedGrossReport`-Antwort und
einen rein lokalen Callback zum vorhandenen Quellenkartenbereich.

- Quelle ist ausschließlich `realized-gross-sell-v2` mit einzelnen wirksamen
  SELL-Ausführungen. Teilverkäufe offener Trades bleiben ausdrücklich SELLs.
- Einzelpunkte verwenden die gelieferte Berichtreihenfolge und eine eindeutige
  SELL-Zeilennummer; es entsteht keine Zeitachse, Tageszuordnung oder Aggregation.
  Gleiche Ausführungszeit und gleicher Betrag behalten getrennte Execution-IDs.
- `TIMESTAMP` wird über den vorhandenen Presenter in Berichtszone gezeigt.
  `DATE_ONLY` bleibt Originaldatum mit unbekannter Uhrzeit und Originalzone.
  `UNKNOWN` bleibt unbekannt; `recorded_at` wird nicht zum Ausführungszeitpunkt.
- Nur vorhandene `USABLE`-Beträge mit `IN_PERIOD`, passender Berichtswährung und
  Roh-/Anzeigewert erhalten eine Koordinate. Ausschlüsse und ungeklärte Fälle
  bleiben mit Gründen in der Tabelle; fehlende Werte werden keine Nullpunkte.
- Original-Decimalstrings und Backendanzeigen bleiben unverändert. `Number`
  dient ausschließlich dem Plot. Nicht endliche Werte, Unterlauf und Beträge
  außerhalb der benannten grafischen Grenze `1e-100 ≤ |Betrag| ≤ 1e100` bleiben
  mit Darstellungshinweis in der Tabelle. Echte Null bleibt ein eigener Punkt.
- Die gemeinsame Achse verwendet nur grafische Extremwerte, keine Geldsumme.
  Sehr kleine Beträge können durch die Pixelauflösung nahe der Nulllinie liegen;
  die Grafik erklärt diese Grenze und verweist auf den maßgeblichen Originalwert.
- Grafik und semantische Tabelle zeigen jeweils 20 gelieferte SELL-Zeilen,
  einschließlich ungeklärter und ausgeschlossener Fälle. Umfang, Seite und
  Gesamtpopulation sind sichtbar. Die Achse bleibt über alle Grafikseiten gleich.
  Bestehende Quellenkartenfilter verändern diese neue vollständige Alternative nicht.
- „Originalquellen zu SELL …“ öffnet die vorhandene Karte auf der richtigen
  lokalen Seite und fokussiert sie. Ein verbrauchter Sprung übernimmt bei späterer
  normaler Navigation nicht erneut den Fokus. Kein neuer Report-/Providerread,
  keine Mutation und kein eigener Router-/API-Owner.
- Der optionale Recharts-Chunk ist lazy geladen. Lade- und Renderfehler werden
  lokal abgefangen; Tabelle, Originalwerte, Pager und Quellen bleiben außerhalb
  dieser Grenze. Die Fehlermeldung ist passiver Text ohne zusätzliche Live-Region.

### Vollständig abgeschlossene Trades

Die bestehende `ClosedTradeStatistics` verwendet weiterhin ausschließlich
`closed-trade-statistics-v1` derselben akzeptierten Abschlussantwort.

| Kennzahl | Sichtbare Definition / unveränderte Backendbedeutung |
| --- | --- |
| Trefferquote | Exakt positive vollständige Tradeergebnisse / N × 100; neutrale Trades zählen zum Nenner. |
| Durchschnitt | Vollständige ungerundete Bruttosumme der Abschlusskohorte / N. |
| Median | Mittleres ungerundetes Tradeergebnis; bei geradem N Mittelwert der beiden mittleren Ergebnisse. |
| Profit-Faktor brutto | Positive Rohbeträge / Absolutbetrag der negativen Rohsumme; ohne Verluste nicht definiert, mit Verlusten ohne Gewinne gültige 0. |

Jede bestehende Karte zeigt Definition, vollständige Abschlusskohorte, N,
Abschlusszeitraum, Berichtszone, Einheit und Kohortenwährung. Die vorhandenen
Präzisionsdetails enthalten jetzt eine semantische Kennzahlentabelle mit
unveränderten `raw`-/`display`-/`reason`-Werten. Es wird keine Kennzahl aus Zeilen
rekonstruiert. Frühere Teilverkäufe bleiben Bestandteile des Lebenszeitergebnisses;
`ClosedTradeItem.sell_contributions` ist niemals Quelle der SELL-Grafik.

`EMPTY` zeigt Population 0, aber keine Statistikwerte. `PARTIAL` und
`NOT_COMPUTABLE` erhalten Population unbekannt und vier fehlende Kennzahlen
mit ihrem Backendgrund. Ein fehlender Wert ohne Reason bleibt „Nicht verfügbar“.
Die bestehenden vollständigen Ergebnisse, Teilsummen, acht disjunkten
Abschlussgruppen, Vorzeichenklassifikationen und Quellenansichten bleiben erhalten.
Ein neues Abdeckungsdiagramm ist für diesen Schnitt nicht erforderlich.

## UX-2- und UX-3-Abgleich

Der technische Abgleich wurde durch getrennte Integrations- und Fachreviews
gegen den tatsächlichen Main vorgenommen. Er behauptet keine persönliche
Ownerfreigabe oder bestätigte Zustellung an einen anderen Chat.

| Verantwortung | Konkreter Vertrag dieses Schnitts |
| --- | --- |
| UX-2 / Host | Vorhandener Slot im Performance-Feature. `PerformanceWorkspace`, `TradeManagementPage`, Router und `shared/trade-workspace-navigation` unverändert. Auswahl/Basis/Generation des bestehenden Reportview-Keys invalidieren Grafik, Pager, Statistik und Quellen gemeinsam. |
| UX-3 / Qualität | Kanonischer Hinweisvertrag aus #314 und integrierter B1/F1-Pilot aus #320 erhalten. Vorhandene `RealizedGrossSources`, `ReportSourceEntry`, Währungsadapter und `NoticeCard` wiederverwendet. Keine zweite Hinweisengine, neue Qualitätsenum oder Recoverybehauptung. |
| Fachowner | `verifyRealizedReport`, `verifyClosedReport`, `verifyClosedStatistics`, Reader, Projektion, Währungsresolver, Periodenregeln und sämtliche Finanzstatistiken unverändert. |
| Offene parallele Arbeit | Vollständige Dateilisten der anfangs sechs offenen Fremd-PRs #315/#220/#207/#205/#197/#187 und der anschließend veröffentlichten UX-PRs #324/#325/#326 geprüft; keine Überschneidung mit dem UX4-C-Schnitt. Der historische History-Scope-Text mit #205-Überschneidung wird nicht verändert. Die PR-Beschreibung hält die geprüften parallelen Heads fest. |

Besonders geprüft: Ein monetär oder zeitlich ungeklärter Fall ist keine Null,
kein Verlust und kein neutraler Trade. `EMPTY` betrifft die gewählte Zeitraum-
und Währungsauswahl; ein ausgeschlossener USD-Verkauf kann dennoch real im
Zeitraum existieren. Grafische Darstellungsgrenzen sind keine neue finanzielle
Ungewissheit. SELL-Zähler sind überlappende Sichten; stornierte Trades sind
keine SELLs und werden nicht in dieselbe Summe oder 100-%-Grafik eingerechnet.

## Tatsächliche lokale Prüfungen und Nachweisgrenzen

Projekttoolchain: Node **22.16.0**, npm **10.9.2**, Python **3.12.14**.
Paket-/Lockdateien, Testkonfiguration und Coveragegates bleiben unverändert.
Die Prüfungen beziehen sich auf den Produkt-/Testinhalt des oben genannten
Implementierungssnapshots; dieser Nachtrag ergänzt nur Dokumentation.

| Prüfung | Tatsächlich beobachteter Stand vor dem finalen PR-CI-Abschluss |
| --- | --- |
| Backend-Performance-Units plus beide Report-PostgreSQL-Integrationsdateien | **199 bestanden, 13 übersprungen**, Exit 0, 4,78 s. Keine lokale disposable PostgreSQL-Testdatenbank; die 13 Skips sind kein Pass. Backendinhalt unverändert gegenüber Main. |
| Neue SELL-Tests | **55 erfolgreiche Dateiergebnisse:** Helper 42, Komponente/Host 12, Lazy-Import 1. Danach fehlender Vitest-Gesamtabschluss im Executor, kontrolliert nach 30 s mit Exit 124 beendet. Kein lokaler Gesamtpass behauptet. |
| Neue Statistiktests | **8 erfolgreiche Dateiergebnisse**; dieselbe lokale Vitest-Abschlussgrenze, kontrollierter Threads-Lauf nach 45 s Exit 124. |
| TypeScript, ESLint, Prettier, Diffcheck | Mit Exit 0 ausgeführt; zusätzliche strikte Typprüfung und Playwright-Discovery der neuen Browsersuite erfolgreich. |
| Separater Produktionsbuild `npm run build` | **Exit 0**, TypeScript und Vite erfolgreich; vorhandene Warnung zu großen Chunks bleibt sichtbar. |
| Neuer Browserumfang | **9 registrierte Fälle**. Chromium 140.0.7339.16 / Playwright-Build 1187 heruntergeladen; lokaler Browserprozess endet vor einer Seite mit SIGTRAP. Kein lokaler Browserpass, keine lokale Screenshotabnahme behauptet. Ausführung und Artefakte müssen aus regulärer CI stammen. |

Das unveränderte `bash scripts/check-frontend.sh` wurde zusätzlich ausgeführt:
Typprüfung, Lint und Formatierung erfolgreich; die Coveragephase lieferte
Dateiergebnisse, beendete sich im Executor aber nicht und wurde kontrolliert
mit Exit 130 abgebrochen. Das ist kein vollständiger lokaler Gatepass.
Die reguläre CI muss den gesamten aktuellen Head
qualifizieren; sie ersetzt weder übersprungene lokale Ergebnisse rückwirkend
noch die menschliche Abnahme.

### Erster CI-Lauf und eng begrenzte Reflowkorrektur

Der erste vollständige PR-CI-Lauf startete auf Head
`72b32d1eedb36b315a9a46fc9a70e10fbf9cf7bb`. Sein tatsächlich ausgecheckter
Testmerge `cb1a69382ab8e2f9acd77bf12ca426ae70c74dca` verbindet diesen Head
mit Main `3397399e7bf8364501437f9509a4fb18dbe32c08`; Head und Testmerge
besitzen denselben Tree `50457543cd441ce48b0212cc565df54b8dafa235`.

- [Frontend-CI 41583877964](https://github.com/burckhju/trading-workspace/actions/runs/41583877964)
  bestand mit **2.145 Tests in 173 Dateien**, Coverage Statements/Lines **96,01 %**,
  Branches **90,54 %**, Functions **91,50 %** sowie Typprüfung, Lint,
  Formatprüfung und Produktionsbuild.
- [Browser-CI 41583877952](https://github.com/burckhju/trading-workspace/actions/runs/41583877952)
  meldete im Smoke-Job **162 bestanden, 5 bewusst ausgelagert, 1 fehlgeschlagen**.
  Alle fünf ausgelagerten Journeys bestanden in ihren drei Ownerjobs. Acht der
  neun neuen UX4-C-Fälle bestanden bereits, einschließlich nativen 200-/400-%-Zooms
  und Chartausfällen. Das ist ausdrücklich kein grüner Gesamtstand dieses Heads.
- Der einzige fehlgeschlagene Fall prüfte extrem lange Original-Decimalstrings
  bei 320 CSS-Pixeln. Die vorhandenen SELL-Quellenkarten ließen wegen intrinsischer
  Grid-Mindestbreite und `overflow-wrap: break-word` die Dokumentbreite überlaufen.
  Trace-DOM und tatsächlich geladene CSS-Regeln bestätigen die Ursache; der
  Fehler war in allen drei vorhandenen CI-Testversuchen reproduzierbar.
- Die Korrektur beschränkt sich auf `min-w-0` an den betreffenden Gridkindern
  und `overflow-wrap: anywhere` an Geldanzeigen in `RealizedGrossReportView`.
  Originalwerte, Berechnung, Semantik und Browserassertions bleiben unverändert.
  TypeScript, Formatprüfung und Diffcheck wurden danach erneut erfolgreich
  ausgeführt. Der neue Head benötigt erneut die vollständige reguläre CI;
  deren endgültige Zuordnung wird in der PR-Beschreibung festgehalten.

### Automatisierte Prüfmatrix

Die neuen 63 Frontendfälle ergänzen vorhandene Owner-/Workspace-Regressionen.
Bestehende Tests werden nur bei nun mehrfach vorhandenen Tabellen-/Textinhalten
auf ihren konkreten ursprünglichen Bereich eingegrenzt; keine Erwartung oder
Coveragegrenze wird abgeschwächt.

Die neun Browserfälle prüfen 320/390/1280 CSS-Pixel, Tabelle und Originalquellen
per Tastatur, lokale Pagination ohne zusätzliche Reads, gleichzeitige SELLs,
DATE_ONLY, Rundungsnull gegenüber fehlendem Wert, lange Decimalstrings,
Über-/Unterlauf, Chartimport-/Renderausfall, Antwortwechsel und 503,
Vier-Trade-Referenz `100, -50, 0, 200`, unvollständige Statistik,
gültigen Profit-Faktor 0 gegenüber fehlendem Verlustnenner sowie nativen
Chromium-Zoom bei 200/400 %. PNGs, zugängliche Tabellen-Snapshots und Zoommessungen
werden als CI-Artefakte erzeugt. Kein CSS-Zoomersatz und kein automatischer
Retry wird als menschliche Accessibilityabnahme ausgegeben.

Statische Kontrastberechnung für die tatsächlichen Plotfarben gegen beide
begrenzenden Flächen `#020617` und `#0f172a`: Punkte `#7dd3fc` mindestens
**10,71:1**, Achsen/Nullreferenz `#cbd5e1` mindestens **12,02:1**. Richtung,
Zeilennummer und Originaltext ergänzen Farbe. Diese konkrete Farbprüfung
belegt keine vollständige WCAG-Konformität.

## Ausdrücklich unverändert und zurückgestellt

Kein Runtime-Diff in Backend, historischen Kursdaten, Projektor, Währungsresolver,
Reportqualifikation, Finanzstatistik, API/Reader, Shared-Modulen, Hostseiten,
Migrationen, Persistenz, Provideranbindung, Dependencies, Versionen oder CI.
Die neue Arbeit konsumiert Recharts und die bestehenden fachlichen Presenter.

Tages-/Monatsaggregate, kumuliertes PnL, Depot-/Equitykurve, Rendite, Drawdown,
Sharpe, Nettoergebnis, Gebühren-/Steuerrekonstruktion, FX und Benchmarkvergleiche
bleiben mangels zusätzlicher Fachverträge außerhalb des Umfangs.

Offen bleiben menschliche UX2-/UX3-/Domainabnahme, tatsächlicher Screenreaderlauf,
durchgängige manuelle Tastaturprüfung, reale mobile Touch-/Lesbarkeitsabnahme
und repräsentative Nutzerdaten. Synthetische Fixtures belegen weder tatsächliche
Depotabdeckung noch einen PC-Installationsstand. Für den lokalen V1-Schnitt
besteht keine neue technische Host-/API-Abhängigkeit.

**Genau ein nächster Schritt nach erfolgreicher finaler CI:** Den eigenständigen
UX4-C-Draft einschließlich der dokumentierten UX4-B-Abnahmegrenzen gemeinsam
fachlich und mit Assistenztechnik abnehmen; eine Mergefreigabe ist davon getrennt.
