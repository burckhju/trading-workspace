# UX-2: Einheitlicher Trade- und Positionsarbeitsbereich

## Prüfgrundlage und Umfang

Die Bestandsaufnahme vom 31.10.2026 beruht auf dem tatsächlich geklonten Main-Commit
`1883f7f330719453958f8be1dd51d48db816662e`. Der live geprüfte veröffentlichte Versions-Tag
`v1.5.35` zeigt genau auf diesen Commit. Der erfolgreiche
[Version-Tag-Lauf 41172652775](https://github.com/burckhju/trading-workspace/actions/runs/41172652775)
einschließlich Tag-Job `124453728314` bestätigt die Veröffentlichung. Der Publisher erzeugt
Git-Tags; das separate letzte GitHub-Release-Objekt ist weiterhin `v1.0.0-product-selection`.
Tag und GitHub-Release-Objekt werden deshalb nicht gleichgesetzt.

Main-CI auf genau diesem Commit: [Backend](https://github.com/burckhju/trading-workspace/actions/runs/41171213873),
[Frontend](https://github.com/burckhju/trading-workspace/actions/runs/41171213875) und
[End-to-End](https://github.com/burckhju/trading-workspace/actions/runs/41171214040) erfolgreich.
Main wurde unmittelbar vor PR-Vorbereitung erneut abgefragt und war unverändert.

UX2-A erweitert die vorhandene Tradeverwaltung. UX2-B bis UX2-D werden hier vorbereitet,
aber nicht zusammen mit UX2-A implementiert. Die folgende Matrix beschreibt ausdrücklich
den Ausgangsstand; der implementierte A-Umfang und seine Testbelege folgen getrennt weiter unten.

Feature-Branch: `feat/ux2-a-trade-workspace-navigation`.

### Offene relevante PRs und parallele Arbeit

Die erste vollständige Live-Abfrage ergab fünf offene PRs. Während der Prüfung wurden
zusätzlich UX-1, die gemeinsame Koordination und der UX-3-Hinweisvertrag veröffentlicht.
Der ergänzte Parallelstand ist:

| PR | Head | Relevanz für UX2 |
| --- | --- | --- |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Quellenforschung, nur Dokumentation; kein produktiver Providerqualitätsnachweis |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Draft; veröffentlichter Diff nur Entwicklungsworkflow, beschriebene Regelimplementierung nicht enthalten |
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Alter Kursverlaufsentwurf, Draft mit Konflikt; #302/#306 sind bereits integriert |
| [#197](https://github.com/burckhju/trading-workspace/pull/197) | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Forschungsworkflow; kein produktiver Historienfeed |
| [#187](https://github.com/burckhju/trading-workspace/pull/187) | `bad00a420f56994216ad1def6a580b00b0f5772f` | Draft mit Konflikt; Hebeltrader-Eingaben/Regeln, u. a. TradePlanWorkflowPage, nicht TradeManagementPage |
| [#312](https://github.com/burckhju/trading-workspace/pull/312) | `8f67442daac6879d7dfb28416f2171f67aead0e5` | UX-1: Währungsvorschau, belegte Eingaben und Auswahlruns; einzige gemeinsame Produktionsdatei ist TradeManagementPage |
| [#313](https://github.com/burckhju/trading-workspace/pull/313) | `2312abfe8834a1b652b100fc635c4d36172d5c32` | Fünf neue Koordinationsdokumente, keine Dateischnittmenge; weist auf die bestehende öffentliche Feature-Importgrenze hin |
| [#314](https://github.com/burckhju/trading-workspace/pull/314) | `52a24266dce1ec048b23360b4b75d5b3f54d746b` | Zehn neue UX-3-Dokumentations-/Vertragsdateien, keine produktive Hinweisimplementierung und keine Dateischnittmenge |

Die grünen alten PR-Läufe vom September qualifizieren keinen heutigen Testmerge. Keiner der
fünf älteren Diffs berührt TradeManagementPage. Beim ersten Abgleich aller 292 veröffentlichten
Branches war UX-1 noch nicht identifizierbar; der später erschienene tatsächliche Diff von #312
wurde deshalb erneut geprüft. Die eigene Umsetzung liegt in [#311](https://github.com/burckhju/trading-workspace/pull/311);
maßgebliche finale Heads, Testmerge und CI stehen dort, ohne selbstreferenzierende Commitangaben
in dieser Datei zu erzeugen.

## Navigations- und Komponentenmatrix des Ausgangsstands

Die Wechsel beziehen sich auf die angegebenen Wege, nicht auf eine pauschale Zahl aller
möglichen Klicks. Aufklappen oder Scrollen ist kein Seitenwechsel. Die Routerdefinition
steht in [`frontend/src/app/router.tsx`](../../frontend/src/app/router.tsx).

| Nutzerziel | Aktuelle Ansicht und Kontext | Erforderliche Wechsel im Ausgangsstand | Bestehende Komponenten / Datenquellen | Konsolidierung |
| --- | --- | --- | --- | --- |
| Position auswählen und zugehörigen Trade öffnen | `/workspace`, offene Positionen; serverseitiges `position.target` enthält `/trade-management?trade_id=…` | Auswahl in der Liste, ein Seitenwechsel zur Tradeverwaltung | `OperationalWorkspacePage`, `OpenPositionsPanel`, `PositionDetails`; `operationalWorkspaceApiClient.getPositions` | UX2-A: vorhandenen Einstieg nutzen, zentralen Trade-Kontext beibehalten; keine zweite Positionsliste |
| Eine konkrete Analyseversion nachvollziehen | `/market-analyses/:analysisId?version=N`; zusätzliche Kontextparameter `candidate_id`, `evaluation_id`, `overview_context` | Von einer Planquelle sind Analyse-ID und Versionsnummer bisher in Provenance sichtbar, aber nicht direkt verlinkt | `MarketAnalysisDetailPage`, `analysisSetupContext`; `TradePlanProvenance`, `candidate_evaluation.sources` | UX2-D: nur belegte `source_id`/`source_version` verlinken; nicht die neueste Analyse einsetzen |
| Aus einer bestimmten Kandidatenbewertung planen | `/candidates`, danach `/trade-plans?candidate_id=…&candidate_evaluation_id=…` | Ein bewusster Seitenwechsel mit gebundener Evaluation | `CandidatePage`, `TradePlanWorkflowPage`, bestehendes `TradePlanPage`, `TradePlanContentForm` | Bereits konsolidiert; Eingabeableitungen und Formularsemantik gehören UX-1 |
| Bestehenden Plan und historische Version öffnen | `/trade-plans/overview`, danach `/trade-plans?trade_plan_id=…&trade_plan_version_id=…` | Ein Wechsel aus der Planliste; die Tradeverwaltung zeigt bisher nur die Planreferenz und technische IDs | `TradePlanOverviewPage`, `ExistingTradePlanPage`, `TradePlanVersionContent`, `TradePlanProvenance`; `tradePlanApiClient.get/versions/version` | UX2-A: direkter Link zur am Trade gespeicherten Planversion; UX2-D: gemeinsame historische Quellennavigation |
| Produktauswahl für bestätigte Planversion bearbeiten | `/product-selection?trade_plan_id=…&trade_plan_version_id=…` | Ein Wechsel von der geöffneten Planversion; neuer Run wird nur ausdrücklich ausgelöst | `ProductSelectionWorkflowPage`, `ProductSelectionPage`, `loadSelectionPlanContext` | Bestehende Auswahl und historische Runs wiederverwenden; kein paralleler Produktworkflow |
| Einen konkreten historischen Auswahlrun lesen | `/product-selection?run_id=…`; Run liefert seine Plan- und Versionsbindung | Direkter Runlink aus Arbeitsbereich/Produktauswahl; vom Trade liegt keine direkte `run_id` vor | `ProductSelectionPage`, `productSelectionApiClient.get/listForTradePlanVersion` | UX2-D: vorhandene Quellenbeziehung auflösen, bevor ein Runlink ergänzt wird |
| Bestätigtes Instrument und tatsächlichen Erstkauf verfolgen | Produktauswahl zeigt bestätigte Selection, Kaufstatus und Link `/trade-management?trade_id=…` | Ein Seitenwechsel nach vorhandener, expliziter Kaufbuchung | `ProductSelectionPage`; `TradeResponse.product_selection_id`, `product_evaluation_id`, Produkt-ID | UX2-A: denselben Trade als Arbeitskontext übernehmen; Kauf- und Freigabelogik erhalten |
| Position und aktuellen Bewertungsstand prüfen | `/trade-management?trade_id=…`; `ProductValuationPanel` hängt im Routenexport hinter der Basisseite | Kein weiterer Seitenwechsel; bisher langes Scrollen zwischen Positionskopf und Bewertung | `TradeManagementContext`, `ProductValuationPanel`, `PositionValuationBasisDetails`; Trade-, Position-, Management- und Bewertungs-GETs | UX2-A: Bereichsnavigation; UX2-B: begründete Kennzahlen und Qualität zusammenführen, ohne neue Berechnung |
| Historische Kurse, Herkunft und Ausführungsmarken lesen | Positionsdetails im `/workspace` und Positionsabschnitt in `/trade-management` | Bereits ohne Seitenwechsel verfügbar; Öffnen beider Ansichten liest Historie erneut | `PositionPriceHistory`, `PositionPricePlot`, `PositionPriceHistoryEvidence`; `readPositionPriceHistory` | Bereits integriert; UX2-A: direkt adressierbarer Bereich; UX2-C: dieselbe Komponente beibehalten |
| Käufe, Nachkäufe und Verkäufe in ihrer Historie prüfen | `/trade-management?trade_id=…#execution-dates`, Tabs „Aktuelle Buchungen“ und „Historie“ | Kein Seitenwechsel, ein lokaler Tabwechsel zur Historie | `ExecutionDatesPanel` besitzt den Timeline-Read; `TradeTimelinePanel` erhält `entries` | Bereits konsolidiert; kein zusätzlicher Timeline-Owner und keine zweite Buchungshistorie |
| Nachkauf, Teilverkauf oder Vollverkauf dokumentieren | Bestehende Nachkaufsektion und `/trade-management?trade_id=…#sale-capture` | Kein weiterer Seitenwechsel; Formularwechsel innerhalb des Trades | `AdditionalPurchasePanel`, bestehendes Verkaufsformular, `ExecutionDateInput`, `ExecutionCurrencyOverride` | UX2-A: direkte Bereichslinks; keine Felder, Defaults oder Buchungsregeln verändern |
| Buchungsfehler korrigieren oder Trade stornieren | Buchungseditor in `#execution-dates`, `TradeCancellationPanel` am Seitenende | Kein Seitenwechsel; lokale Editoren mit bewusstem Verwerfen | `ExecutionDatesPanel`, `ExecutionCurrencySources`, `TradeCancellationPanel`, `TradePendingChangesProvider` | Navigation darf Editor und Recoveryzustand nicht unbemerkt verlieren; Storno bleibt vom Verkauf getrennt |
| Historische Ausführungswährung und Belege prüfen | Buchungen/Währungseditor; zusätzlich `/trade-management?trade_id=…&view=sources` | Im Buchungsbereich kein Seitenwechsel; zur lesenden Quellenansicht bislang neuer Tab | `ExecutionCurrencySources`, Währungsbestätigungs- und Evidence-Komponenten, `TradeSourcesView`; bestehende Currency-GETs | UX2-A: Quellen direkt erreichbar; UX2-C: vorhandene Nachweise präsentieren, keine neue Währungsauflösung |
| Positionsrisiken, Warnungen und Monitoring prüfen | Risiko-/Alertabschnitte in `/trade-management`; lesender Risikoabschnitt auch in `/workspace`-Details | Kein weiterer Seitenwechsel; bisher Scrollen | `PositionRiskPanel`, `TradeAlertsPanel`, `MonitoringRuntimePanel`; Risiko-, Alert-, Health- und Runtime-Reader | UX2-A: direkter Bereich; UX2-B: fachliche Hinweise, Kursqualität und operative Fehler weiterhin unterscheiden |
| Geschlossenen Trade wirtschaftlich auswerten | `/performance/closed-trades`; Quellenansicht enthält `ClosedTradeResult` | Ein Wechsel vom Bericht zur konkreten Tradequellenansicht; gültiger Berichtsrückweg schon vorhanden | `PerformanceWorkspace`, `ClosedTradesReportView`, `ClosedTradeResult`, `ClosedTradeSources`; `performanceApiClient` | UX2-A: vorhandenen Berichtskontext durch weitere Bereichswechsel erhalten; keine neue Ergebnisberechnung |
| Verkäufe einschließlich Teilverkäufen im Zeitraum vergleichen | `/performance/realized-gross`; gemeinsamer Filterowner mit Abschlussbericht | Berichtstypwechsel übernimmt gültige Auswahl, liest aber den fachlich anderen Bericht | `PerformanceWorkspace`, `PerformanceFilters`, `RealizedGrossReportView` | Bereits konsolidiert; kein zweiter Performancebereich und keine Vermischung beider Berichtstypen |
| Ursprünglichen Plan, Ausführungen, Review und Journal lesen | `/trade-management?trade_id=…&view=sources`, optional `review_version_id`, `journal_version_id` | Tradeverwaltung öffnet bislang neuen Tab; Rückweg trägt nur `trade_id` | `TradeSourcesView`, `ReadSection`, bestehender Source-Reader; `ClosedTradeResult` als separater wirtschaftlicher Owner | UX2-A: gemeinsame Navigation, bestehende Pins und Berichtskontext bewahren; historische Quellen bleiben lesend |
| Nachbeobachtung, Review und Journal bearbeiten | `/post-trade?trade_id=…`, optional `journal_version_id=…` | Von geschlossenem Trade über „Nachbeobachtung starten“ bzw. Arbeitsbereich; keine gleichwertige durchgängige Bereichsnavigation | `PostTradeLearningPage`, `PostTradeReviewPage`, `TradeJournalPanel`, `useTradeJournal` | UX2-A: direkt erreichbarer vorhandener Owner mit Trade-Rückweg; kein implizites Starten, Finalisieren oder Materialisieren |
| Frühere Evidence und zugehörige Lessons prüfen | Post-Trade enthält `Ft011EvidenceHistory`; Quellenansicht zeigt Evidence- und Lessonversionen | Ein Wechsel zur Lesson; Original-Trade fehlt im bisherigen allgemeinen Rücklink | `Ft011EvidenceHistory`, `TradeSourcesView`, `lessonReadbackClient`, `LessonDraftFromEvidence` | UX2-A: Trade-Rückkontext mitführen; bestehende historische `lesson_version_id` erhalten |
| Lessonversion, Reviewentscheidung und Herkunft lesen | `/lessons/:lessonId?lesson_version_id=…#lesson-history` | Bisheriger Rücklink `/post-trade` erfordert neue Tradeauswahl; belegte Journalquelle hat bereits einen exakten Direktlink | `LessonDetailPage`, `LessonReviewPanel`, `JournalEvidenceOrigin`, `LessonHypothesisPanel` | UX2-A: qualifizierter Rückweg zum mitgegebenen Trade; Governance und Quellenauflösung unverändert |

## Bereits integrierte Konsolidierungen

Diese Funktionen sind im geprüften Main vorhanden und werden nicht neu implementiert:

| Integration | Nachweis im Main | Vorhandene Zuständigkeit |
| --- | --- | --- |
| TradePlan und Produktauswahl, PR #284 | Merge `059860ea` | Exakte Planversion, historische freigegebene Version trotz neuerem Entwurf, Quellen- und Kontextprüfung, vorhandene Formulare |
| Trade und Buchungen, PR #287 | Merge `36db3910` | Ein Buchungsowner für aktuelle Einträge, Korrekturen und Timeline; koordinierte Schreibsperren und Navigationsschutz |
| Journal, PR #289 | Merge `38cac1a0` | Post-Trade, Journal, Evidence und Lessonübergabe teilen fachlich getrennte, koordinierte Bearbeitungen |
| Performance, PR #290 | Merge `ca4258fd` | Gemeinsame Filter und URL-Zuständigkeit für zwei fachlich unterschiedliche Berichtstypen |
| Historische Währungsherkunft, PR #298 | Merge `271d2abb` | Ausführungsgebundene Nachweise, explizite Bestätigungen, nachvollziehbare Quellen und Konflikte |
| Positionskursverlauf, PR #302 | Merge `e8703a65` | Persistierte Beobachtungen, Quelle, Preisart, Währung, tatsächliche Kurszeit und qualifizierte Ausführungsmarker |
| Ergänzung Positionskursverlauf, PR #306 | Merge `2534d7c5` | Verfügbare Zeiträume, Abdeckungsgrenzen und weitere belegte Historien-/Darstellungsfälle |

## Bestehende Kontext- und Ladegrenzen

### Trade und Position

`TradeManagementPage` verwendet `trade_id` als Identität und keyed den gesamten
`TradePendingChangesProvider` danach. Trade, Position und Management werden parallel gelesen;
das Produkt wird anschließend nach der gelesenen Produkt-ID aufgelöst. Die Antworten werden
auf Trade-, Produkt- und Positionszugehörigkeit geprüft. Generation und AbortController
verhindern, dass ein überholter Read eine neuere Projektion ersetzt. Fachliche Schreibaktionen
verwenden den bestehenden synchronen Schreibschutz und Readback.

`ExecutionDatesPanel` besitzt einen einzelnen Timeline-Read für aktuelle Buchungen, Historie
und Bearbeitungsgrundlage. `TradeTimelinePanel` ist eine reine Darstellung dieser `entries`.
Ein Bereichswechsel darf keinen neuen Timelineowner und keinen zusätzlichen GET auslösen.

`ProductValuationPanel` wird im ursprünglichen `trade/pages/index.ts` separat angehängt. Es liest
die Position erneut, obwohl die Basisseite sie bereits besitzt, und liest danach die Bewertung.
Das ist eine konkrete verbleibende Doppelladung. Im Ausgangsstand ist es außerdem nicht nach
Trade-ID keyed und erscheint auch im Quellenmodus. Eine zukünftige Zusammenführung muss seine
Read-Lebensdauer, Timeline-Invalidierung und Unterscheidung aktueller Bewertung versus
historischem Ergebnis ausdrücklich erhalten. UX2-A darf einen bestehenden Bewertungstext
nicht als atomaren gemeinsamen Datenstand mit anderen Abschnitten ausgeben.

### Quellen, Plan und Analyse

`TradeSourcesView` liest zunächst den Tradequellenkern und danach Plan, Reviews, Journal und
Evidence in eigenen `ReadSection`-Lesefenstern. Ein Fehler in Journalquellen ist kein Fehler des
wirtschaftlichen Ergebnisses. `ClosedTradeResult` bleibt der Owner qualifizierter finanzieller
Ergebnisse. Die getrennten Lesefenster werden bereits sichtbar erklärt; ein globaler Cache
oder ein künstlich gemeinsamer Snapshot wäre eine zusätzliche fachliche Änderung.

Ein Quellenbesuch ist durch `location.key` und `location.search` isoliert. Historische Pinwechsel
lesen die Quellen neu. Das ist beim geprüften Ausgangsstand beabsichtigt und darf nicht durch
ungeprüfte Wiederverwendung einer anderen Version ersetzt werden. Hashnavigation innerhalb
unveränderter URL-Parameter benötigt dagegen keinen neuen fachlichen Read.

`ExistingTradePlanPage` lädt Plan, Versionsliste und gegebenenfalls exakt angeforderte Version.
Eine fehlende oder fremde explizite Version führt zu einer Fehlermeldung und nicht zu `latest`.
Aktuelle Basiswertnamen sind nur optionale Anzeige. Planinhalt und Kandidatenbewertung bleiben
an der historischen Version gebunden.

`TradeResponse.product_selection_id` bezeichnet eine bestätigte Selection, **nicht** ihren Run.
`/product-selection?run_id=…` benötigt die tatsächliche `selection.run_id`. Der bestehende
`SqlAlchemyWorkspaceSelectionResolver` prüft Selection, Evaluation, Produkt, Plan und Version;
`source_view.plan` nutzt ihn bereits. UX2 darf `product_selection_id` nicht als `run_id` ausgeben.
Ebenso liegen Analysequellen in `candidate_evaluation.sources`; eine beliebige aktuelle Analyse
des gleichen Basiswerts ist kein Ersatz für den dokumentierten Quellstand.

### Post-Trade und Lessons

`PostTradeLearningPage` liest Trade/Produkt erneut für seinen Kontextkopf. Review, Journal,
Materialisierungsstatus, frühere Evidence und Lessonreferenzen haben getrennte Reader und
explizite Invalidierungen. Diese Antworten haben unterschiedliche fachliche Bedeutungen.
Ein vorhandener Journalentwurf beweist weder Finalisierung noch Lessonfreigabe.

`LessonDetailPage` wahrt die konkrete Lessonversion, aber der ursprüngliche allgemeine
Rücklink `/post-trade` verliert den Trade. Lessonlinks aus Post-Trade und Tradequellen geben
bisher lediglich Lesson- und gegebenenfalls Lessonversions-ID weiter. `JournalEvidenceOrigin`
besitzt dagegen schon einen fachlich geprüften Direktlink zur exakt materialisierten
Journalversion mit passender Trade-ID.

### Berichtskontext

`closedReportContext.ts` definiert eine begrenzte Liste erlaubter Navigationsparameter:
`report_context`, `from_date`, `to_date`, `report_currency`, `report_timezone`, `report_view`,
`report_page`, `report_basis`. Sie sind Navigationskontext und kein übergebener Geldbetrag.
`sourceLink` bewahrt diese Werte auch in einem ungültigen Zustand, damit mehrdeutige Links
nicht stillschweigend repariert werden. Der ursprüngliche Rücklink zur Tradeverwaltung
reduziert dagegen auf `trade_id` und verliert diesen Kontext.

## UX2-A: implementierter, separat prüfbarer Umfang

1. Gemeinsame, responsive Bereichsnavigation in der bestehenden Tradeverwaltung und ihren
   vorhandenen Quellen-/Post-Tradeansichten; sichtbare Tradeidentität aus dem tatsächlichen Kontext.
2. Hashlinks zu den bereits vorhandenen Tradeabschnitten. Bestehende `#sale-capture` und
   `#execution-dates` bleiben gültig. Formularowner und Eingaben bleiben beim Bereichswechsel
   gemountet; Hashnavigation löst keinen neuen Trade- oder Timeline-Read aus.
3. Direkte Links zur gespeicherten Planversion und zu bestehenden Review-, Journal- und
   Quellenfunktionen. Ein Link liest oder navigiert; er startet keine Nachbeobachtung und
   finalisiert oder materialisiert nichts.
4. Trade-ID, historische Pins und begrenzten Berichtskontext beim Wechsel und Rückweg erhalten.
   Zielrouten und Parameternamen bleiben explizit; kein ungeprüftes freies `returnTo`.
5. Kontextbezogener Lesson-Rückweg, ohne Lessonversion, Evidenzbindung oder menschliche
   Reviewentscheidung umzudeuten.
6. Lade-, Fehler- und Leerzustände verständlich halten. Fehlende Position oder unbekannte
   Quelle ergibt weder einen Bestand von null noch einen vermeintlich abgeschlossenen Schritt.

Die Navigation verwendet native Links mit sichtbarem Tastaturfokus. Hashziele sind
nach dem Laden fokussierbar. Ein Nachladen darf den Tastaturfokus nicht wiederholt aus
einem aktiven Eingabefeld ziehen. Eine einfache Bereichsnavigation braucht keine zusätzlichen
Tabrollen; die vorhandenen echten Buchungstabs behalten ihre Pfeiltastensteuerung.

Die neue `TradeWorkspaceNavigation` und ihre Linkfunktionen liegen hinter der öffentlichen
Schnittstelle `frontend/src/shared/trade-workspace-navigation`. Das gemeinsame Modul enthält
ausschließlich Darstellung und reine URL-Verträge; es importiert keine internen Features.
Die vorhandenen URL-Schlüssel, Berichtsauswahlfilter und Navigationsfunktionen werden genau
einmal ausgegliedert. Die bisherigen Ownerimporte bleiben über kompatible Exporte gültig.
`sourceQueryError`, `verifyClosedReport`, `verifyClosedStatistics`, API-Reader und Finanzlogik
verbleiben bei ihren Fachownern. Die Ausgliederung ändert keine Filter- oder Quellenprüfung.
Damit wird die bereits in `FRONTEND_ARCHITECTURE.md` festgelegte Featuregrenze eingehalten;
der während der Prüfung erschienene Koordinations-Draft #313 hat diesen Integrationspunkt
konkret benannt. Dies ist ein eigener, kontrollierter Architekturcommit.

Erlaubte bestehende Suchparameter bleiben innerhalb eines
Owners bytegenau erhalten; unbekannte Parameter wie `returnTo` oder Geldwerte werden nicht in
erzeugte Links übernommen. Die Quellenansicht wird nur nach `location.search` gekeyt, sodass
ein Hashwechsel keine Quellen neu lädt. Historische Pinwechsel bleiben neue Lesekontexte.

Der vorhandene Routenexport keyed die aktuelle Produktbewertung nun nach Trade-ID und hängt
sie nicht mehr an die historische Quellenansicht an. Die doppelte Positionsabfrage innerhalb
der aktiven Tradeverwaltung bleibt eine ausdrücklich noch offene UX2-B-Aufgabe.
Der genaue Planlink öffnet die belegte Planversion im neuen Tab, damit der vorhandene
Arbeitskontext erreichbar bleibt. Es wird kein Produkt-Run und keine Analyseversion erraten.

Lessonlinks und kopierbare Lessonversionslinks führen den Rückkontext mit. Beim bewussten
Tradewechsel in Post-Trade werden beide alten Review-/Journal-Pins entfernt; ein Reload
desselben Trades erhält sie. Die optionale `lessonHref`-/`versionHref`-Anbindung ändert nur
Links, keine Felder, Quellenbindung, Reviewentscheidung oder Speicheraktion.

### Konkreter Nutzen gegenüber dem Ausgangsstand

| Nutzerweg | Nachgewiesene Änderung |
| --- | --- |
| Überblick → Kurs → Buchungen → Risiko | Vier direkt fokussierbare Ziele im selben Trade; kein zusätzlicher API-Read, beide offenen Verkaufs-/Korrekturentwürfe bleiben erhalten |
| Trade → Quellen | Kein zwingender neuer Browser-Tab mehr; normaler Router-Link mit bestehendem Eingabenschutz |
| Quellen → Trade → Quellen | Trade, Review-/Journal-Pins und Abschlussberichtskontext bleiben erhalten; vorher gingen Pins und Berichtsrückweg beim ersten Rücksprung verloren |
| Post-Trade/Quellen → historische Lesson → zurück | Eine erneute Tradeauswahl entfällt; Lessonversion sowie ursprünglicher Quellen-/Journalbereich bleiben adressierbar, auch nach Reload |
| Quellen → gebundene Planversion | Direkter Link mit exakter Plan-/Versions-ID; keine manuelle Übertragung technischer IDs und kein Umweg über die Planliste nötig |
| Historische Quellen lesen | Die dort bisher zusätzlich angehängte aktuelle Produktbewertung und ihre Reads entfallen |

Bereits vorhandene Chart-, Buchungs-, Journal- und Performancekonsolidierungen werden nicht
als neue UX2-A-Leistung gezählt. Plan, Journal und Lessons behalten ihre bestehenden Owner;
UX2-A behauptet deshalb nicht, alle fachlichen Bearbeitungen auf eine einzige Route zu verlegen.

## Schutz ungespeicherter Änderungen

`PendingNavigationGuard` schützt Änderungen von Pfad oder Suchparametern und native
Seitenentladung. Reine Hashwechsel sind bereits ausgenommen. Das ist sicher, solange die
betroffenen Formulare beim Hashwechsel gemountet bleiben. `TradePendingChangesProvider`
koordiniert Buchungseditor, Verkaufs-, Management-, Nachkauf- und Stornozustände.

Post-Trade koordiniert seine Review-, Journal-, Lesson- und Materialisierungszustände mit dem
bestehenden Guard. `LessonDetailPage` koordiniert Lessonreview und Hypothesenentwurf. UX2-A
benutzt diese Mechanismen und führt weder eine weitere Draftablage noch eine automatische
Verwerfentscheidung ein. Ein bestätigtes Verwerfen ist eine bewusste Nutzerentscheidung;
ein Reload verspricht keine dauerhafte Wiederherstellung ungespeicherter Texte.

## UX2-B bis UX2-D: fachliche Vorbereitung, nicht implementiert

### UX2-B – Überblick

- Bestehende Trade-/Produktidentität, Positionsstatus und nächste mögliche Aktion zusammen
  mit belegter Kursqualität präsentieren. Werte kommen aus bestehenden Antworten.
- `ProductValuationPanel` und `PositionValuationBasisDetails` weiterverwenden. Die doppelte
  Positionsabfrage erst nach einer gezielten Zuständigkeits- und Invalidierungsprüfung reduzieren.
- Verfügbarkeit und Währung jedes Geldwerts mitführen. Unbekannt, nicht berechenbar und null
  bleiben verschieden; Buchungsprojektion, qualifizierter Bericht und aktuelle Bewertung nicht
  als gleichwertige Ergebnisse darstellen.
- `TradeAlertsPanel`, `PositionRiskPanel` und `MonitoringRuntimePanel` behalten ihre getrennten
  Bedeutungen: fachliche Meldung, Risikobeurteilung, operativer Daten-/Providerzustand.
- Gemeinsame Terminologie vorbereiten: „Ausführung“, „Planversion“, „Kostenbasis“,
  „Realisierter Bruttobeitrag“, „Nicht berechenbar“, „Quelle ungeklärt“, „Fachliche Prüfung“.
  Eine Umbenennung ersetzt keine fachliche Qualifikation.

### UX2-C – Kursverlauf und Buchungen

- Vorhandene `PositionPriceHistory` samt Plot und Evidence bleibt die einzige Kurskomponente.
  Im Plot sind Linien ausdrücklich deaktiviert; zwischen Beobachtungen ist keine Entwicklung
  belegt. Währungen, Provider und Preisarten bleiben getrennt.
- Nur vom bestehenden Report als `plottable` qualifizierte, zeitlich zuordenbare Kauf-/Verkaufs-
  events in passender Währung markieren. Ein Buchungsdatum ohne Uhrzeit ist kein erfundener
  Intradaykurs.
- `ExecutionDatesPanel` und sein Timelineowner bleiben erhalten. Währungserklärung,
  historischer Beleg und Mengen-/Preiskorrektur behalten getrennte Bedienvorgänge.
- Eine Vermögens-, Einstands- oder Gewinnkurve ist durch die vorhandenen einzelnen Markt-
  und Ausführungskurse nicht automatisch belegt. Ohne fachlich qualifizierte Zeitreihe wird
  keine zusätzliche Positionsentwicklungskurve erzeugt.

### UX2-D – Plan, Journal und Lessons

- Exakte Planversion, Kandidatenevaluation und deren konkrete Analysequellen verknüpfen.
  Fehlende oder widersprüchliche Referenzen verständlich kennzeichnen.
- Historischen Auswahlrun erst nach belegter Selection-zu-Run-Zuordnung verlinken.
- Vorhandene Quellenansicht, `TradeJournalPanel`, `Ft011EvidenceHistory`, `JournalEvidenceOrigin`
  und `LessonReviewPanel` nutzen. Historische Journal-/Reviewpins und Lessonversions-IDs bewahren.
- Eine kompakte Lebenszyklusanzeige kann tatsächliche Quellen referenzieren. Jeder Schritt
  erhält seinen eigenen belegten Status; ein späterer Datensatz beweist keine Freigabe oder
  Fertigstellung eines früheren Schritts. Ein externer Trade darf ohne Plan existieren.

## Abgrenzung und Integrationskonflikte mit UX-1

UX-1 wurde nach Veröffentlichung von #312 am tatsächlichen Head
`8f67442daac6879d7dfb28416f2171f67aead0e5` geprüft. Die gemeinsame Ausgangsbasis ist exakt
`1883f7f330719453958f8be1dd51d48db816662e`. Nur `TradeManagementPage.tsx` wird von beiden
Features verändert; die geänderten Zeilen überschneiden sich nicht. Ein rein rechnerischer
Dreiwegevergleich verändert weder Branch-Referenzen noch Main und ersetzt keine gemeinsame CI.

UX-1 ersetzt dort die Währungseingabe durch `ExecutionCurrencyPreview` und bindet den bestehenden
`historyReloadToken` an Nachkauf- und Verkaufsvorschau. UX2 ergänzt Navigation und Bereichsanker.
Bei Integration sind beide Änderungen zu erhalten, statt die gesamte Datei eines Branches
zu übernehmen. Der UX-1-Readkey enthält keinen URL-Hash; Navigationswechsel dürfen daher keine
zusätzliche Währungsvorschau oder Formularänderung auslösen. Die gemeinsame lokale Qualifikation
und ihre genauen Heads werden im PR nachgehalten. Eine gemeinsame reale PostgreSQL-/GitHub-
Qualifikation bleibt vor späterer Integration auf dem dann aktuellen Main erforderlich.

UX2-A beschränkt gemeinsame Dateien auf Navigation, Bereichsanker und Darstellung. Besonders
`TradeManagementPage.tsx` ist als gemeinsame Integrationsstelle zu behandeln: Navigation und
Anker sollen in kleinen, getrennten Hunks bleiben. `AdditionalPurchasePanel`,
`ExecutionDatesPanel`, `ExecutionCurrencyOverride`, `TradePlanContentForm` und Kauf-/Verkaufs-
ableitungen werden von UX2 nicht semantisch umgebaut. Kein Feature-Branch wird ungeprüft in
den anderen übernommen. Die gemeinsame Regression erfolgt später auf dem dann aktuellen Main.

## Reproduzierbare Prüfwege und vorhandene Regressionen

| Prüfweg | Erwarteter Nachweis | Bereits vorhandene Regressionen / geplante Ergänzung |
| --- | --- | --- |
| Trade A aus Arbeitsbereich öffnen, zu Kursen und Buchungen wechseln | Gleiche `trade_id`, passende Identität, kein zweiter Trade-/Timeline-Read | `TradeManagementContext.test.tsx`, `trade-management-context.spec.ts`; ergänzt durch `TradeWorkspaceNavigation.test.tsx` und `trade-workspace-navigation.spec.ts` |
| Direkten Buchungs-/Verkaufslink kopieren und neu öffnen | Gültiger Kontext wird aus URL geladen, Ziel erhält Fokus | `TradeManagementPage.test.tsx`, `trade-execution-dates.spec.ts`; neue Anker und Reload in `trade-workspace-navigation.spec.ts` |
| Verkaufsmenge oder Korrekturentwurf eingeben und Hashbereich wechseln | Eingabe bleibt erhalten; kein Verwerfendialog für bloßes Scrollen | `TradeManagementContext.test.tsx`, `trade-execution-consolidation.spec.ts` |
| Mit ungespeicherten Daten zu Quellen, Plan, Post-Trade oder anderem Trade wechseln | Bestehender Guard; „Hier bleiben“ erhält Eingaben; während Schreiben kein Verwerfen | `TradeManagementContext.test.tsx`, `trade-capture-safety.spec.ts`; neue Links und nativer Reloadschutz in `trade-workspace-navigation.spec.ts` |
| A → B → A mit verspäteter A-Antwort | Alter Besuch überschreibt keine neue Identität oder Eingaben | `TradeManagementContext.test.tsx`, Plan-/Post-Trade-/Lesson-Kontexttests |
| Fehlende Position, nicht vorhandener Trade oder stornierter Trade öffnen | Verständlicher Lade-/Fehler-/Leerzustand, keine alten Daten und keine erfundenen Schreibaktionen | Bestehende Trade-Kontexttests; ergänzte Navigationsfälle für fehlende Position sowie geschlossen/storniert |
| Geschlossenen Trade öffnen | Keine neue Verkaufsfreigabe; vorhandenes Post-Trade/Quellenziel erreichbar | `TradeManagementPage.test.tsx`, `PostTradeLearningPage.integration.test.tsx` |
| Trade mit historischer Planversion öffnen, obwohl neuer Entwurf existiert | Exakt gespeicherte Version; kein Wechsel auf `latest` | `ExistingTradePlanPage.test.tsx`, `TradePlanPage.deep-link.test.tsx`, `ft007-plan-context-postgres.spec.ts` |
| Abschlussliste → Quellen → Bereich → Quellen → Bericht | Filter, Seite und historische Pins bleiben erhalten; veränderter Bericht wird erneut qualifiziert | `ClosedTradeSourceJourney.test.tsx`, `ClosedTradeResult.test.tsx`, `workspaceNavigation.test.ts`, realer Quellen-Rundweg in `trade_source_journey.ts` |
| Journal/Review → historische Lesson → Rückweg | Original-Trade und konkrete Quellpins bleiben erhalten | Erweiterte `LessonDetailPage.governance.test.tsx`, `lesson-detail-consolidation.spec.ts` sowie Quellen-/Journal-E2E |
| Navigation per Tastatur und schmalem Viewport | Sichtbarer Fokus, erreichbare Links, kein Layoutüberlauf; bestehende Buchungstabs weiterhin bedienbar | Fokussierter neuer Playwright-Nutzerweg sowie bestehende mobile UI-Tests |
| Buchungs-/Finanzregression | Bestehende Mengen-, Storno-, Average-Cost-, Währungs- und Berichtsregeln bleiben erfolgreich | Backend-Suiten für Trade/Position, historische Währung und Performance; bestehende E2E-Nutzerwege |

## Verifikationsstand

Lokal erfolgreich am 31.10.2026:

- Node **22.16.0** entsprechend `frontend/.nvmrc`: TypeScript, ESLint (0 Warnungen), Prettier
  und Produktionsbuild erfolgreich. Vite meldet weiterhin den bestehenden großen Hauptchunk;
  die Grenze wurde nicht verändert.
- Vollständiges Frontend-Coverage-Gate: **1.861 Tests in 160 Dateien** erfolgreich.
  Statements/Lines **95,84 %**, Branches **90,25 %**, Functions **91,07 %**;
  unveränderte Mindestwerte **80/80/80/70** bestanden.
- Python **3.12**: **558 Backend-Tests** aus `trade_position` und `performance` erfolgreich.
  Eine vorhandene Starlette/AnyIO-DeprecationWarning; kein lokaler vollständiger PostgreSQL-
  oder 85-%-Backend-Coverage-Nachweis behauptet.
- Chromium: **8 neue UX2-Navigationsfälle** und **2 bestehende Buchungs-UI-Fälle** erfolgreich.
  390 px und 1280 px, Tab/Enter, sichtbarer Fokus, zwei gleichzeitige Entwürfe, konstante
  GET-Zahl, native Reloadwarnung, direkte/alte Anker, fehlende Position, geschlossen und storniert.
  Die API-Fixtures blockieren alle Writes; diese Fälle ersetzen keine PostgreSQL-Owner-Suite.
- Unabhängiges Review und `git diff --check` erfolgreich. Ein gefundener fremder Review-Pin
  nach Tradewechsel wurde behoben und mit einer eigenen Regression abgesichert.
- Nach Ausgliederung der öffentlichen Navigationsschnittstelle erneut erfolgreich:
  vollständiges Frontend-Coverage-Gate mit denselben 1.861 Tests und Coveragewerten,
  TypeScript/ESLint/Prettier/Build sowie **13 Chromium-Fälle** (acht Navigation, fünf Handoff).
  Ein unabhängiger strukturierter Vergleich bestätigt **35 unveränderte Deklarationen**,
  einschließlich Finanz-/Quellenvalidatoren, URL-Parsern und Navigationskomponente.

Die vorinstallierte Node-24-Laufzeit verursachte `AbortSignal`-Fehler auch auf einem separat
geprüften, unveränderten Main. Die Tests wurden mit der festgeschriebenen Node-22-Laufzeit
vollständig wiederholt; keine Tests oder Qualitätsgrenzen wurden dafür geändert/deaktiviert.

Reproduzierbare Befehle mit der Projektlaufzeit:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run format
npm run test:coverage -- --coverage.thresholds.lines=80 --coverage.thresholds.functions=80 --coverage.thresholds.statements=80 --coverage.thresholds.branches=70
npm run build
npm run e2e -- trade-workspace-navigation.spec.ts
cd ..
python -m pytest -c backend/pyproject.toml tests/unit/backend/features/trade_position tests/unit/backend/features/performance -q
```

Die lokale Browserprüfung benötigt den Frontend-Testserver und synthetische API-Fixtures.
Die unveränderte GitHub-CI ergänzt PostgreSQL-, Backend-Coverage-, Smoke- und Owner-Jobs.
PR-Head, Testmerge und konkrete CI-URLs werden im zugehörigen Draft-PR dokumentiert, damit
eine reine Aktualisierung von Laufnummern keine neue ungeprüfte Codeversion erzeugt.

| Stufe | Status dieser Dokumentfassung |
| --- | --- |
| UX2-A implementiert | Ja, Navigation und Rückkontext; B-D bleiben Vorbereitung |
| Lokal getestet | Ja, oben aufgeführte erfolgreiche Läufe |
| PR-geprüft | Maßgeblich sind tatsächlicher PR-Head/Testmerge und die im Draft-PR nachgehaltene CI |
| In Main integriert | Nicht beauftragt |
| Veröffentlicht | Nicht beauftragt |
| Auf dem PC installiert | Nicht beauftragt |
| Fachlich abgenommen | Nicht behauptet |

Der UX2-A-PR soll abschließend konkret belegen, welche vorher notwendigen erneuten
Tradeauswahlen oder Rückwege entfallen und welche reinen Hashwechsel ohne neue Datenabfrage
auskommen. Bereits vorhandene gemeinsame Ansichten und bereits entfallene Wechsel aus früheren
PRs zählen nicht als neuer UX2-A-Erfolg.
