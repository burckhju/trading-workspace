# UX4-C — Startprompt Performancevisualisierung

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Eigenständiger Implementierungsauftrag, Draft 0.1 |
| Status | Vorbereitung durch UX4-A; keine Implementierungs- oder Integrationsabnahme |
| Datum | 31.10.2026, Europe/Vienna |
| Repository | `https://github.com/burckhju/trading-workspace` |
| Historische Prüfbasis | `1883f7f330719453958f8be1dd51d48db816662e`, `v1.5.35` |
| Ziel | Vorhandene qualifizierte Performancewerte verständlich visualisieren |
| Grenze | Keine neue Finanzberechnung; kein Merge, Release oder PC-Update |

## Rolle, Ausgangspunkt und Pflichtlektüre

Du verantwortest UX4-C im genannten Repository. Implementiere eine begrenzte
Performancevisualisierung aus den vorhandenen Ownerantworten und liefere einen
eigenständigen Draft-PR. Dieser Startprompt ist ein späterer Implementierungsauftrag;
der UX4-A-PR selbst enthält ausschließlich Analyse und Verträge.

Prüfe zu Beginn den tatsächlichen aktuellen Main, die Repositoryvorgaben und
vorhandene `AGENTS.md`-Dateien. Die historische SHA oben ist ein überprüfter
Ausgangspunkt, keine Behauptung über den Main bei deinem Arbeitsbeginn.
Verwende einen eigenen Branch vom dann geprüften Main. Lies die tatsächlichen
Heads paralleler UX-Arbeiten; keine gegenseitigen Feature-Branch-Merges und
keine Übernahme offener Implementierungen als vermeintlicher Main-Bestand.

Lies mindestens:

- [UX4-A-Inventur](ux4-visualization-inventory.md), besonders I13–I19,
  Kennzahlenlexikon und Performance-Quellenvertrag.
- [Konsolidierten Visualisierungsvertrag](ux4-visualization-contract.md),
  besonders V01–V04, V07–V10 und V12–V14.
- [UX4-A-Prüfplanung](../implementation/UX4_A_QUALIFICATION.md),
  [Product Backlog](../planning/PRODUCT_BACKLOG.md),
  [Roadmap](../foundation/ROADMAP.md) und
  [Teststrategie](../reference/TEST_STRATEGY.md).
- [ADR-S10-008: Währungsherkunft und SELL-Bericht](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md),
  [ADR-S10-009: vollständige Tradeergebnisse](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md)
  und den später ergänzten [Statistikvertrag](../implementation/CLOSED_TRADE_STATISTICS_V1.md).
- [Performance-Konsolidierung](../implementation/UI_PERFORMANCE_CONSOLIDATION.md)
  und [Quellenintegration](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md).

Lies außerdem die konkret veröffentlichten Koordinations- und UX-Verträge.
Der Konsolidierungsstand vom 31.10.2026 bindet folgende **Drafts**, getrennt
vom historischen Main-Bestand:

- Master-Koordination [#313](https://github.com/burckhju/trading-workspace/pull/313),
  Head `2312abfe8834a1b652b100fc635c4d36172d5c32`:
  [UX_MASTER_PLAN](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_MASTER_PLAN.md),
  [UX_OWNERSHIP](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_OWNERSHIP.md),
  [UX_SHARED_CONTRACTS](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_SHARED_CONTRACTS.md),
  [UX_DEPENDENCIES](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_DEPENDENCIES.md) und
  [UX_INTEGRATION_STATUS](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_INTEGRATION_STATUS.md).
- UX-3 [#314](https://github.com/burckhju/trading-workspace/pull/314),
  Head `52a24266dce1ec048b23360b4b75d5b3f54d746b`:
  [Hinweisvertrag](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/notice-contract.md) und
  [Komponenten und Aktionen](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/components-and-actions.md).
  Die gemeinsamen Hinweisrenderer sind dort Vorschläge, keine bereits
  integrierten Komponenten.
- UX-2 [#311](https://github.com/burckhju/trading-workspace/pull/311),
  Head `79e9b97e31d3bf80936fb5c026798bf8ebb10b33` mit
  [Workspacevertrag](https://github.com/burckhju/trading-workspace/blob/79e9b97e31d3bf80936fb5c026798bf8ebb10b33/docs/ui/ux2-trade-workspace.md),
  sowie UX-1 [#312](https://github.com/burckhju/trading-workspace/pull/312),
  Head `8f67442daac6879d7dfb28416f2171f67aead0e5` mit
  [Qualifikation und Übergabe](https://github.com/burckhju/trading-workspace/blob/8f67442daac6879d7dfb28416f2171f67aead0e5/docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md).

Prüfe ihre aktuellen Heads, Inhalte und Integrationszustände beim Start erneut.
Die zeitgebundenen Aussagen im Koordinationssnapshot zu noch ausstehenden
UX-3-/UX-4-Übergaben sind keine Aussage über inzwischen veröffentlichte Drafts.
Eine veröffentlichte Dokumentation erteilt weder eine Integrationsabnahme noch
eine Mergefreigabe. Das Product Backlog bleibt der fachliche Statusowner.

## Belegter Iststand und Berechnungsgrenzen

Die historische Prüfbasis enthält bereits zwei Berichte, eine gemeinsame
Performanceoberfläche und vier Backendstatistiken. Es fehlt die grafische
Darstellung der Beiträge, nicht deren Finanzberechnung.

| Vorhandener Vertrag | Grundgesamtheit und Aussage |
| --- | --- |
| `realized-gross-sell-v2` | Einzelne wirksame SELL-Beiträge im Berichtszeitraum, einschließlich Teilverkäufen weiterhin offener Trades. Einheit ist SELL, nicht Trade. |
| `closed-trade-gross-v1` | Genau ein vollständiges Lebenszeitergebnis je Trade-ID. Der tatsächliche wirksame SELL, der positive offene Menge auf null reduziert, bestimmt die Abschlussperiode. Frühere Teilverkäufe außerhalb der Periode bleiben im Gesamttrade enthalten. |
| `closed-trade-statistics-v1` | Trefferquote, Durchschnitt, Median und Profit-Faktor der vollständig qualifizierten Abschlusskohorte. Nur `summary.status=COMPLETE` und `counts.qualified > 0`. |

Die beiden GETs sind `/api/v1/performance/realized-gross` und
`/api/v1/performance/closed-trades`. Beide verwenden explizite `from_date`,
`to_date`, `report_currency` und IANA `report_timezone`. Die bestehende
Oberfläche ist auf EUR festgelegt. EUR ist ein Filter belegter Währungen;
es bestätigt keine Ausführungswährung und rechnet nichts um.

Der vorhandene
[PositionProjector](../../backend/app/features/trade_position/domain/projector.py)
besitzt Average Cost, Mengen und Bruttobeiträge. Der bestehende historische
Währungsresolver in Trade/Position liefert die Währungsbelege. Performance
qualifiziert deren Ergebnisse für den jeweiligen Bericht:
[SELL-Report](../../backend/app/features/performance/domain/report.py),
[Volltrade-Report](../../backend/app/features/performance/domain/closed_report.py),
[Statistik](../../backend/app/features/performance/domain/closed_statistics.py),
[Perioden](../../backend/app/features/performance/domain/periods.py) und
[Snapshotreader](../../backend/app/features/performance/service/reader.py).
Keinen dieser Owner nachbauen oder für diesen Darstellungsauftrag verändern.

Ein Volltradeergebnis ist nur bei vollständig qualifizierter Geldherkunft des
gesamten Trades verfügbar. Bekannte SELL-Beiträge eines monetär ungeklärten
Trades bleiben Herkunftsdetails; sie ergeben keine Trade-Teilsumme. Ein
gespeichertes CLOSED-Flag, Storno, Journal, Review oder Lesson beweist keinen
wirtschaftlichen Vollabschluss. Journal und Learning sind keine Voraussetzung
und vermehren die Berichtspopulation nicht.

## V1-Lieferumfang

### 1. Bestehende Abschlusskennzahlen verständlich erklären

Behalte die vier Karten und ihre Backendwerte. Ergänze eine kurze zugängliche
Definition pro Kennzahl sowie den eindeutigen Bezug zu N, Zeitraum,
Berichtswährung und vollständiger Abschlusskohorte. Rohwerte, Gründe und
Herkunft bleiben erreichbar.

| Kennzahl | Vorhandene Definition; ausschließlich anzeigen |
| --- | --- |
| Trefferquote | Exakt positive vollständige Tradeergebnisse / N × 100; neutrale Trades gehören zum Nenner. |
| Ø Bruttoergebnis | Bereits vorhandene vollständige ungerundete `summary.total / N` in Berichtswährung; keine zweite Summenrechnung. |
| Median | Mittlerer ungerundeter Tradebetrag in Berichtswährung; bei geradem N Addition der beiden mittleren Beträge, dann /2. |
| Profit-Faktor brutto | Dimensionslos: Summe positiver Rohbeträge / Absolutbetrag der Summe negativer Rohbeträge. Ohne Verlustbeträge nicht definiert; mit Verlustbeträgen und ohne Gewinne gültiger Wert 0. |

`statistics.population` ist bei COMPLETE die positive Zahl qualifizierter
Trades, bei EMPTY `0` und bei PARTIAL/NOT_COMPUTABLE `null`. Bei unvollständiger
Grundlage bleiben alle vier Kennzahlen ohne Wert. Keine Ersatzstatistik des
bekannten Teilbestands und keine vermeintliche Erfolgsbewertung aus guten Zahlen.

### 2. Einzelne SELL-Beiträge zeitlich darstellen

Verwende ausschließlich die bereits gelieferten `items` des angenommenen
SELL-Berichts und deren `realized_gross_pnl_delta`, Anzeigewert, Zeitpräzision,
Status und Quellen. Eine geeignete erste Darstellung sind unverbundene
Einzelpunkte oder einzelne Ereignisbalken mit zugänglicher Liste.

- Monetär verwendbare Beiträge dürfen einen Geldwert zeigen. Fehlende oder
  nicht berechenbare Beiträge bleiben mit ihren Gründen auffindbar; niemals
  als Null-Euro-Punkt oder Nullbalken zeichnen.
- `TIMESTAMP` bezeichnet die tatsächliche Ausführungszeit; Anzeige in der
  Berichtszone. `recorded_at`, Readzeit oder Berechnungszeit sind kein Ersatz.
- `DATE_ONLY` behält `executed_on` und die Originalzeitzone. Zulässig sind eine
  ausdrücklich datierte Kategorie, die Ereignisliste oder das unverändert
  gelieferte mögliche Intervall `possible_start_at` bis `possible_end_at`.
  Kein Mitternachts-/Mittagsinstant, kein nächster Marktkurspunkt und keine
  künstliche Reihenfolge innerhalb eines unbekannten Tages.
- Sichere Zugehörigkeit zur gesamten Reportperiode belegt keinen kleineren
  Tagesbucket. Insbesondere kann ein Originaltag in einer anderen Zeitzone
  mehrere Berichtstage berühren. Keine lokale Neuklassifikation oder Aggregation.
- Unbekannte beziehungsweise nicht eindeutig zeitlich plottbare Ereignisse
  bleiben in einer klar bezeichneten Liste. Sie verschwinden nicht aus der
  Abdeckungs- und Quelleninformation.
- Zeitgleiche SELLs behalten ihre eigene Execution-ID und ihren Einzelbetrag.
  Nicht zu einem Punktbetrag verschmelzen oder durch eine Durchschnittssumme ersetzen.
- Quellenzugriff zeigt die vorhandene Kostenbasis und Korrekturherkunft aus
  derselben Antwort. Ausführungspreise und Bruttobeiträge sind keine Marktpreise.

Die Grafik bleibt an die vollständige akzeptierte Reportantwort gebunden.
Lokale Zeilenfilter oder Seiten dürfen Gesamtsumme, N und Abdeckungszähler
nicht verändern. Falls eine begrenzte Grafikansicht erforderlich ist, muss
der rein visuelle Ausschnitt ausdrücklich erkennbar sein; die vollständigen
Daten bleiben zugänglich. Kein stilles Downsampling oder Verschweigen von
ungeklärten Fällen und keine neue Geldaggregation zur Verringerung der Punktzahl.

### 3. Bestehende Abdeckungsinformationen erhalten

Abdeckungsdarstellungen verwenden die vorhandenen absoluten Zähler mit
eindeutiger Einheit. Eine neue Abdeckungsdiagramm-Komponente ist für V1 nicht
zwingend; die vorhandene Tabelle und die Gründe dürfen nicht verloren gehen.

Beim Abschlussbericht sind genau diese acht Gruppen disjunkt, in der
bestehenden Priorität: `CANCELLED`, `HISTORY_UNRESOLVED`, `OPEN`,
`OUTSIDE_PERIOD`, `OTHER_CURRENCY`, `PERIOD_UNRESOLVED`,
`MONETARY_UNRESOLVED`, `QUALIFIED`. `in_period`, `unresolved` und die
Vorzeichenzähler sind Teilgruppen, keine zusätzlichen Segmente.

Beim SELL-Bericht bilden Periodenstatus und monetäre Verwendbarkeit
verschiedene überlappende Sichten. `cancelled` zählt stornierte Trades,
`examined` wirksame SELLs. Keine gemeinsame Torte oder 100-%-Leiste aus diesen
Zählern. Ungeklärte Trades sind weder negativ noch neutral. Die Klassifikation
eines Volltrades stammt vom Owner, nicht aus dem gerundeten Anzeigebetrag.

## Geld-, Null-, Zeit- und Quellenvertrag

| Zustand | Unverändert zu erhaltende Darstellung |
| --- | --- |
| `EMPTY` | Backend-Gesamtsumme 0 ausdrücklich als leere geprüfte Auswahl; keine vier Statistikwerte. |
| `COMPLETE` | Vollständige Summe, auch exakt null möglich; Abschlussstatistiken bei N>0. |
| `PARTIAL` | Vollständige Summe unbekannt; vorhandene Teilsumme als solche kennzeichnen. Alle vier Abschlussstatistiken unavailable, N unbekannt. |
| `NOT_COMPUTABLE` | Weder Gesamtsumme noch Teilsumme vorhanden; Gründe statt Ersatznull. Alle vier Abschlussstatistiken unavailable. |
| Profit-Faktor ohne Verlustnenner | „Nicht definiert: keine Verlusttrades“, kein Infinity, NaN, Ersatznull oder Maximalwert. |
| Laden / Fehler | Eigener Zustand ohne fremde oder überholte Antwort; kein leeres Erfolgsdiagramm. |

Geldrohdaten bleiben Decimal-Strings. Zeige die vom Backend gelieferten
`display`-Werte und Gründe; Finanzanzeigen nutzen Currency-Minor-Units und
`ROUND_HALF_EVEN`, Trefferquote und Profit-Faktor zwei Nachkommastellen.
`+0.004` und `-0.004` bleiben positiv bzw. negativ, auch bei Anzeige `0.00`.
Rundungsdifferenzen bleiben erklärte Backendwerte und werden keinem Einzeltrade
zugeschlagen. Keine `Number`-/Float-Summe, keine neue Signumklassifikation
aus gerundeten Strings und keine Neuformatierung mit abweichender Rundungsregel.

Eine Umwandlung vorhandener Werte in Plotkoordinaten ist ausschließlich
Darstellung. Überlauf, Unterlauf oder nicht darstellbare Werte dürfen nicht
still zu Null oder zu fehlenden Daten werden; die exakte Zahl und ein
Darstellungshinweis bleiben in der zugänglichen Liste. Das vorhandene
`portfolioTotals` oder dessen BigInt-Formatter ist kein Rechen-/Rundungsowner
für neue Performancewerte.

Die Berichtsperiode reicht vom Beginn des Von-Tages bis ausschließlich zum
Beginn des Tages nach Bis in der gewählten Zone. Verwende die Backendgrenzen;
keine pauschalen 24-Stunden-Tage oder lokale Neuqualifikation. Bewahre die
explizite Auswahl aus URL/Workspace. Der Main-Default der historischen Basis
war `Europe/Berlin`; UX4 erfindet keine neue Defaultzone und übernimmt
gegebenenfalls die inzwischen integrierte UX-1-Regel: gültige Browserzone als
editierbarer Vorschlag, explizite URL-Auswahl mit Vorrang. Der geprüfte UX-1-Draft
ist keine Erlaubnis, ihn in diesem Auftrag vorab zu integrieren.

`basis.knowledge=CURRENT_EFFECTIVE_FACTS` bedeutet heute wirksame korrigierte
Fakten, auch für alte Berichtsperioden. `basis.id` ist kein wiederherstellbarer
historischer Bericht und keine Behauptung, dass allein der ausgewählte Trade
geändert wurde. `read_started_at`, `read_completed_at` und `calculated_at`
bleiben getrennte Lese-/Berechnungszeiten.

Die bestehende vollständige Antwortgrenze beträgt 2.000 Trades, 20.000
Executions, 40.000 Währungsbestätigungen, 10.000 CurrencyEvidence-Objekte und
100.000 Provenienzlinks. Der Reader verwendet `REPEATABLE READ READ ONLY` mit
10 Sekunden Statementtimeout. Überschreitungen führen zu
`REPORT_RESOURCE_LIMIT` (413), ungültige Eingaben zu `REPORT_INPUT_INVALID`
(422), Quellenlesefehler zu `REPORT_READ_UNAVAILABLE` (503). Keine dieser
Grenzen umgehen, erhöhen oder durch einen gekürzten Erfolgsbericht ersetzen.

## Wiederverwendung, Scope und Abstimmung

Arbeite in `frontend/src/features/performance` und passenden Tests. Bewahre
die vorhandenen Owner:

- [PerformanceWorkspace](../../frontend/src/features/performance/pages/PerformanceWorkspace.tsx)
  mit gemeinsamer Filter-/Requestlebensdauer und den dünnen Page-Wrappern.
- [RealizedGrossReportView](../../frontend/src/features/performance/components/RealizedGrossReportView.tsx),
  [ClosedTradesReportView](../../frontend/src/features/performance/components/ClosedTradesReportView.tsx),
  [ClosedTradeSummary](../../frontend/src/features/performance/components/ClosedTradeSummary.tsx)
  und [ClosedTradeStatistics](../../frontend/src/features/performance/components/ClosedTradeStatistics.tsx).
- `RealizedGrossSources`, `ClosedTradeSources`, `ClosedTradeResult`,
  `ReportSourceEntry` sowie die vorhandenen API-Typen und Presenter.
- `verifyRealizedReport`, `verifyClosedReport`, `verifyClosedStatistics`
  und die bestehenden URL-Kontextvalidatoren.

Verwende die vorhandene Chartbibliothek Recharts und geeignete vorhandene
Darstellungsmuster. Der Positionskursrenderer ist kein Performance-Datenowner;
keine Preis-/Ereignis-DTOs in Performance umdeuten. Keine zweite Chartsammlung,
Performance-Shell, Filtersteuerung oder Datenengine schaffen.

`statistics.report_basis_id` muss `report.basis.id` entsprechen,
`statistics.report_status` dem `summary.status`; Definition, Berichtstyp,
Filter und Währung bleiben validiert. Ein tatsächlicher Wechsel der
Berichtsauswahl oder ihrer Identität entwertet die zugehörige Antwort
einschließlich Grafik, Statistik, Quellen und Hinweise. Verspätete
Erfolge/Fehler sowie A→B→A-Wechsel dürfen keine alte Antwort wiederbeleben.
Ein bloßer Abschnitts-/Hashwechsel innerhalb desselben Trades ist dagegen
kein fachlicher Kontextwechsel: vorhandene Drafts bleiben bestehen, es
entsteht kein zusätzlicher Trade-, Position-, Timeline- oder Reportread.
Lokale Seiten, Quellenaufklappen und Grafikfokus verwenden vorhandene Daten
und lösen keine zusätzlichen Report-/Providerreads oder Writes aus. Ein
bewusster Sprung in die vorhandene Quellenansicht behält deren bisherigen
Readvertrag, Rückweg und Hinweis auf möglicherweise jüngeren Quellenstand.
Getrennte Quellen- und Performance-Reads bilden keinen gemeinsamen atomaren
Snapshot; die zusammengehörigen Teile einer Reportantwort werden gemeinsam ersetzt.

UX-2 besitzt Hostkomposition, Readback und Hostinvalidierung. Nach einer
bestätigten Buchung oder Quellenkorrektur konsumiert UX4 die vom Host
koordinierten neuen Ownerantworten; bestehende Formulardrafts anderer Bereiche
bleiben erhalten. Ein bestätigter Schreibabschluss und ein fehlgeschlagener
Readback sind unterschiedliche Fakten. Eine Grafik führt keinen eigenen
Schreibretry, Eventbus oder parallelen Hostread ein. Vorhandene fachlokale
Readzuständigkeiten, etwa die Timeline von `ExecutionDatesPanel`, bleiben erhalten.

Die öffentliche Importgrenze ist vor einer gemeinsamen Einbindung mit UX-2
konkret festzulegen. Keine direkten featurefremden Imports interner Komponenten
oder Services wie `trade/services/sourceView` oder
`performance/services/closedReportContext` und kein bloßer Reexport als Umgehung.
Ein abgestimmtes schmales Modul unter dem bestehenden `frontend/src/shared/`
darf nur gemeinsame Darstellungs-/URL-Transportverträge enthalten; alternativ
erhält der Renderer bereits vom Owner qualifizierte Links über typisierte Props.
Eine solche neue gemeinsame Schnittstelle ist ein Vorschlag, kein Main-Bestand.
Berichtsvalidatoren, Quellenqualifikation und Finanzlogik verbleiben vollständig
bei ihren Feature-/Domainownern. URLs und Rücksprungparameter sind kein
Finanz- oder Quellenbeleg.

Hinweise folgen dem gelesenen UX-3-Draft: Der Performance-Adapter ordnet
vorhandene Status-/Reason-Felder einer verständlichen Ursache und konkreten
Auswirkung zu. Ein Readfehler belegt keine fehlende historische Währung; ein
vollständig geprüfter leerer Bericht ist kein Fehler. Relevante Einschränkungen
bleiben neben den Werten sichtbar, Quellen und Gründe dürfen aufklappbar sein.
Unbekannte erfolgreiche Statuswerte bekommen weder eine erfundene Blockade
noch ein grünes Qualitätsurteil. Neue Schweregrade oder finanzielle Ursachen
entscheidet weiterhin der Domainowner.

Hinweisaktionen öffnen nur geprüfte vorhandene Ziele oder eine bestehende
Entscheidungsoberfläche. Ein Lese-Retry bleibt beim zuständigen Host neben dem
Hinweis; kein versteckter Fetch/Write in Navigationscallbacks. Interne
Hinweisfokussierung und Darstellung folgen UX-3, Hostziele und Übergänge UX-2.
Unveränderte Hinweise werden nicht bei jedem Render oder Poll erneut angekündigt;
zusammenfassender Hinweis und Detail erzeugen keine doppelte Live-Ankündigung.

| Abhängigkeit | Konkrete Verantwortung / Integrationsgrenze |
| --- | --- |
| Bestehende Performance-/Finanzowner | Performance besitzt Berichtsbasis, Kohorte, Kennzahlendefinition und Berichtvalidatoren; Trade/Position besitzt Projektion und historische Währungsqualifikation. Neue Aggregationen sind vorgelagerte Domainaufträge. |
| UX-1 | Sichere belegte Ableitungen und editierbare Filtervorschläge; keine Übernahme der Performance-Domainzuständigkeit und keine parallele UX4-Währungsauflösung. |
| UX-2 | Einbindungsposition, gemeinsame Workspacekomponenten, öffentliche Import-/Navigationsgrenze, Read-Lebensdauer, Readback und Hostinvalidierung. Vor Änderungen Slot, Props, Anker/Fokusziele, Ladeowner und reservierte Konfliktdateien mit konkretem PR/Head/Integrationsschritt abstimmen. |
| UX-3 | Die veröffentlichten Hinweisverträge aus #314 auf Ownerdaten anwenden: Ursache, Auswirkung, belegte Navigation und zugängliche Ankündigung. Vorgeschlagene Komponenten nicht als vorhanden voraussetzen; keine eigene globale Qualitätsampel oder Schweregradlogik. |
| UX4-B / UX4-D | Keine technische Implementierungsabhängigkeit erforderlich. Bestehende Datenverträge nutzen; keine gemeinsame neue Infrastruktur voraussetzen. |

Solange die gemeinsame Einbindung nicht abgestimmt ist, bereite eine fachlich
lokale darstellende Komponente mit Props-/Test-/Integrationsvertrag vor.
Implementiere keine neue gemeinsame Workspace-Komponente. Halte die offene
Abstimmung im Draft sichtbar, ohne sie mit einer zweiten Oberfläche zu umgehen.
Unabhängige fachlokale Darstellungsarbeit kann gemäß Koordinationsdraft parallel
qualifiziert werden; gemeinsame Hoständerungen integriert UX-2 in abgestimmter
Reihenfolge. Vor einer Dateireservierung den vollständigen Umfang der aktuellen
parallelen PRs vergleichen.

## Ausdrücklich außerhalb dieses Auftrags

Keine Tages-/Monatssummen, kumulierten Geldbeträge, Equity-/Depotkurven,
TWR/MWR, Rendite, Drawdown, Sharpe, Nettoergebnisse, FX oder Benchmarkberechnungen.
Keine Neurekonstruktion vollständiger Trades aus periodischen SELL-Zeilen.
Keine Addition realisierter und unrealisierter Ergebnisse. Keine synthetischen
historischen Preise, Gebühren, Steuern, Cashflows oder historischen Wissensstände.

Falls eine gewünschte Grafik solche Daten benötigt, dokumentiere die konkrete
fehlende Voraussetzung und den zuständigen Owner. Halte diesen Umfang zurück,
statt im Frontend eine scheinbar einfache Ersatzberechnung einzuführen.
Keine neue Backend-API, Migration, Persistenz, Provideraktivierung, Order,
Buchung, Korrektur oder Learning-Mutation für die Grafik.

## Qualitätssicherung und Abnahme

Verwende die vorhandenen Goldens und Ownerregressionen; neue Tests prüfen die
Darstellung und die fachlichen Grenzen. Tests und Coverage-Gates nicht abschwächen.
Synthetische Fixturewerte dienen ausschließlich der Testqualifikation und
belegen keine tatsächliche Nutzer-Datenabdeckung.

| Prüfung | Erwartung |
| --- | --- |
| Zwei Populationen, mehrmonatiger Trade, offener Teilverkauf | SELL-Beitrag und vollständiges Tradeergebnis behalten unterschiedliche Bedeutung. Frühe Verkäufe werden im Abschlussbericht nicht abgeschnitten. |
| Referenz `100, -50, 0, 200` | Backendwerte unverändert: N=4, Trefferquote 50.00 %, Durchschnitt 62.50 EUR, Median 50.00 EUR, Profit-Faktor 6.00. Kein Test berechnet die Erwartung aus dem zu prüfenden Ergebnis. |
| EMPTY, COMPLETE exakt null, PARTIAL bekannte null, NOT_COMPUTABLE | Keine fehlenden Werte als Nullpunkte; echte Null bleibt vorhanden; Teilbetrag bleibt Teilbetrag. |
| Kleine positive/negative Rohbeträge, neutrale Trades, nur Gewinne/Verluste | Ownerklassifikation erhalten, neutral in N; Profit-Faktorgründe und gültige 0 unterscheiden. |
| HALF_EVEN, Minor Units, lange Decimal-Strings, Plotüber-/unterlauf | Roh-/Anzeigewerte und Gründe erhalten, keine neue Geldrechnung oder stille Ersatznull. |
| Historische EUR/USD/CHF, gemischte/widersprüchliche Quellen, Korrekturen | Keine FX-/Listing-Defaultannahme; ersetzte Ausführungen nicht doppelt zählen; Berichtsbasis vollständig austauschen. |
| TIMESTAMP, DATE_ONLY, fremde Zone, DST, gleiche Ereigniszeit, UNKNOWN | Keine erfundene Uhrzeit, Tageszuordnung oder Punktverschiebung; unplottbare Fälle bleiben auffindbar. |
| Browserzone, explizite Berichtszone, URL-Vorrang und UTC-Testruntime | Berichtsfixtures wählen ihre eigene Zone ausdrücklich; abweichende Browserzone beeinflusst keine akzeptierte Antwort. Initialvorschlag und Fallback separat prüfen, Kontextvalidatoren erhalten. Die UX-1-Korrektur der beiden Performance-Seitentests an `8f67442d…` ist der gelesene Referenzfall. |
| Zeilenfilter, Seitenwechsel und Grafikfenster | Globale Population, Summen, Statistik und Abdeckung bleiben unverändert; keine zusätzlichen Reads. |
| Neue Filter, Berichtstyp, verspätete Antwort, A→B→A, Quellenrückkehr | Guards und atomarer Austausch der zusammengehörigen Antwort gelten auch für die Grafik. |
| Abschnitts-/Hashwechsel im selben Trade, bestätigte Korrektur und Readback | Navigation erhält Drafts und löst keinen zusätzlichen Read aus. Hostkoordinierter Readback ersetzt betroffene Ownerdaten, ohne andere Eingaben zu verlieren; fehlgeschlagener Readback behauptet keinen fehlgeschlagenen bestätigten Write. |
| Alle acht Abschlussgruppen und überlappende SELL-Zähler | Keine Doppelzählung, keine gemischten Einheiten oder neue Erfolgsquote auf Partial-Basis. |
| Ressourcenfehler und Readfehler | Kein gekürzter Erfolg, keine alte Grafik unter neuer Auswahl, Retry über vorhandenen Owner. |
| Hinweisursache, unbekannter Status und wiederholter Read | Keine erfundene Finanzdiagnose, kein grüner unbekannter Status, keine doppelte Live-Ankündigung. Hinweisziele bleiben Navigation; Retry bleibt benannter Hostread. |
| Gemeinsame Imports und öffentliche Props | Keine featurefremden internen Service-/Komponentenimports oder Reexportumgehung; validierte Ownerlinks und bestehende Performancevalidatoren bleiben erhalten. |
| Mobile 320/390px, Desktop 1280px, 200 % Zoom | Keine horizontale Dokumentrolle, abgeschnittenen Einheiten oder überdeckten Controls; eigene beschriftete Tabellenscrollbereiche bei Bedarf. |
| Tastatur, Touch und zugängliche Datenalternative | Sichtbarer Fokus, Name/Wert/Einheit/Datum/Grund/Quelle ohne Hover erreichbar; sinnvolle Reihenfolge, keine reine Rot-/Grüncodierung. |
| Unveränderte finanzielle Owner | Runtime-Diff ohne Änderungen an Projection, Currency Resolver, Reportqualifikation, Summen, Statistik und Periodenregeln; vorhandene finanzielle Referenzerwartungen bleiben gültig. |

Testanker sind
[Backend-Performance-Units](../../tests/unit/backend/features/performance),
[Frontend-Performance-Tests](../../frontend/src/features/performance),
[Workspace-Browserreise](../../tests/e2e/performance-workspace-ui.spec.ts),
[SELL-PostgreSQL-Nachweis](../../tests/integration/backend/test_realized_gross_report_postgres.py),
[Volltrade-PostgreSQL-Nachweis](../../tests/integration/backend/test_closed_trades_report_postgres.py)
und die vorhandenen nativen Report-E2E-Fälle samt Datenbankguards.
Die neue Grafik benötigt zusätzliche tatsächliche Mobil-/Tastaturprüfungen;
`accessibilityLayer` und ein erfolgreicher JSDOM-Test allein reichen nicht.
Eine vollständige Liste/Tabelle bleibt erforderlich. Tausende Einzelpunkte
dürfen keine unbedienbare Tab-Reihe erzeugen; ein nachvollziehbares
Auswahl-/Paginierungsmodell verändert keine fachliche Grundgesamtheit.

Führe für den tatsächlich geänderten Stand die passenden lokalen Prüfungen
mit der Projekttoolchain aus und prüfe die unveränderte reguläre PR-CI.
Übersprungene oder nicht verfügbare PostgreSQL-/Browsernachweise als solche
melden. Historische grüne Läufe sind kein Testnachweis des neuen PR-Heads.

## Abschlusslieferung

Liefere einen eigenständigen **Draft-PR** mit geprüftem Main, eigenem Head,
konkreten Änderungen, übernommenen Ownerverträgen, tatsächlichen Testergebnissen,
Mobil-/Tastaturnachweisen und offenen Daten-/Integrationsvoraussetzungen.
Nenne ausdrücklich, welche Diagramme implementiert sind und welche wegen eines
fehlenden Fachvertrags zurückgestellt bleiben. Dokumentiere jeden notwendigen
UX-1/UX-2/UX-3-Abgleich und halte Runtimecode und Dokumentation konsistent.

Kein Merge, Release, Versions-/Tagwechsel, Deployment, PC-Update oder Eingriff
in reale Bestände. Eine implementierte und getestete Grafik ist keine fachliche
Gesamtabnahme der Depotperformance.

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | Eigenständiger UX4-C-Startprompt aus UX4-A-Codeinventur und Visualisierungsvertrag; konkretisiert anhand Koordination #313, UX-3 #314 und UX-1-Head `8f67442d…`: Host-/Readback-/Importgrenzen, Hinweisvertrag und Zeitzonenregression; keine Runtimeänderung |
