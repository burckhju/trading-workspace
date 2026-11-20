# UX-Masterplan

## Soll-Ist-Abgleich und Umsetzungsfolge vom 11.11.2026

**Gemeinsame technische Basis:** Main und veröffentlichter Tag `v1.5.46` zeigen auf
[`d01c259f4b79fdfbdcec8743ececda035b69f9d1`](https://github.com/burckhju/trading-workspace/commit/d01c259f4b79fdfbdcec8743ececda035b69f9d1),
Tree `2371c76ac02f747d1961494c011b4cccdb3ad651`. Tatsächliche Main-CI und Publisher
sind erfolgreich. Die [getrennten Nachweise](UX_INTEGRATION_STATUS.md#technischer-snapshot-v1546)
gelten für diesen Commit; sie sind keine menschliche Fach- oder PC-Abnahme.
Vor Beginn eines Folgeauftrags Main, Tag und offene Dateiarbeit erneut prüfen.

Dieser Abgleich vergleicht die bestehenden UX-Aufträge mit dem Code. Er ändert
keinen Arbeitsstatus im [Backlog](../planning/PRODUCT_BACKLOG.md#pflegevertrag-und-statusbedeutung),
erzeugt keine neuen FT-/PB-IDs und berechnet keinen Fertigstellungsprozentsatz.
Ein integrierter Teilschnitt erfüllt nicht automatisch das gesamte ursprüngliche
Ziel. Insbesondere ist UX4-D4 nicht gleichbedeutend mit vollständigem UX2-D.

| Bestehendes Ziel | Technischer Istbefund | Verbleibender begrenzter Bedarf |
|---|---|---|
| UX1-A/B/C/D: belegte Eingaben wiederverwenden | Erst-/Nachkauf-/SELL-Preview, einzelner gespeicherter Auswahlrun, Browserzone und vorhandene Journal-/Lessonübernahme sind implementiert; #331 ergänzt den editierbaren Planwährungsvorschlag. | Für diese vereinbarten Schnitte keine konkrete fehlende Automatik gefunden. Zwei vorhandene Berichte aktualisieren und reale Verständlichkeit, Quellenabdeckung und Bedienung getrennt abnehmen. |
| UX2-A/B/C: gemeinsamer Kontext, Überblick, Historie | Gemeinsame Navigation und Entwurfsschutz, qualifizierter Positions-/Bewertungsreadback, ein Positionschart und ein Timelineowner sind vorhanden. O1 bleibt auf qualifizierte Ownerwerte begrenzt. | Vorhandene Wege abnehmen; rohe Kostenbasis oder realisierten G/V nicht durch einen Layoutpatch zu qualifizierten Geldwerten erklären. |
| UX2-D: historische Quellenwege | Plan-, Review-, Journal- und Lessonpins sowie sechs Beleggruppen sind vorhanden. Analyse-/Kandidatenquellen bleiben im Tradeweg überwiegend Text; der Run der konkreten historischen Selection wird nicht an den Consumer ausgegeben. | Zuerst gebundene Kandidaten-/Analyseversion mit sicherem Trade-Rückweg, danach exakten Selection-Run über einen qualifizierten bestehenden Readvertrag anbinden. |
| UX3-B/C/D: verständliche Ursachen und sichere Folgewege | Kanonischer Vertrag, B1/F1, Q12-Flächen und viele lokale Fehler-/Quellen-/Rückwege sind vorhanden. | M06-Invalidierungsgrund, M02-Health-Teilreadfehler und TP06-Updatebehauptung korrigieren; weitere Konsolidierung nur an konkret vereinbarten Hostflächen. |
| UX4-B/C/D: belegte Visualisierungen | Positionsquellenwahl, Ereignisbelege, einzelne SELL-Beiträge, erklärte Abschlussstatistiken und lokale Qualitäts-/Lebenszyklusdarstellung sind integriert. #340 ergänzt die Chartwatchlist. | Menschliche Abnahme; Positionscoverage als spätere gemeinsame Oberfläche erst nach Host-/Readtypvertrag. Neue Finanzzeitreihen und weitergehende M8-Funktionen behalten ihre Domainvoraussetzungen. |

Code-/Sollbezüge: [UX1-Qualifikation](../implementation/UX1_INPUT_REUSE_QUALIFICATION.md),
[Planwährung](../implementation/UX1_B_PLAN_CURRENCY_SUGGESTION.md),
[UX2-Auftrag](../ui/ux2-trade-workspace.md),
[UX3-Rollout](../ui/ux-3/integration-and-rollout.md),
[UX4-D-Grenzen](../implementation/UX4_D_IMPLEMENTATION_SCOPE.md) und
[UX4-C-Grenzen](../implementation/UX4_C_QUALIFICATION.md).

### Aktueller Auftrag an UX1

Ziel ist der überprüfbare Abschluss der vorhandenen Wiederverwendung, mit
sichtbarer Trennung von Vorschlag, manueller Entscheidung und gespeichertem Fakt.
Erlaubter Dateischnitt: `docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md`
und `docs/implementation/UX1_B_PLAN_CURRENCY_SUGGESTION.md`. Bestehende
A/B/C/D- und finale #331-Nachweise auf die gemeinsame Basis beziehen; den
ursprünglichen Einzelrun-B-Schnitt vom späteren Planwährungsvorschlag unterscheiden.
UX1 besitzt Eingabe-/Herkunftsdarstellung, die bestehenden Domains ihre Fakten.

Prüfen: belegte und UNKNOWN/MIXED/CONFLICT-Währung, manuelle Overrides und späte
Antworten; ein versus mehrere Runs; vollständiger historischer Analysesnapshot
bei unverändertem Formular; URL-Vorrang der Zone; Journal-/Lessonpins und
Entwurfserhalt. Vorhandene Tests/CI zuordnen, menschliche Prüfung gesondert
belegen. Keine neue Produktfunktion, Recovery, Backlogänderung oder Domainregel.
Abschluss: beide Berichte mit datiertem Nachtrag und konkreten vorhandenen bzw.
noch fehlenden Abnahmebelegen, Branch/PR/Head und exaktem Zwei-Dateien-Diff.

### Aktueller Auftrag an UX2

Ziel des nächsten Produktschnitts ist der historische Weg aus dem Trade zur
belegten Kandidatenevaluation bzw. Analyseversion und zurück zum selben
Trade-/Review-/Journal-/Berichtskontext. Vor dem Produktdiff den konkreten
URL-/Rückwegvertrag mit Analysis/Candidate festhalten. Wiederverwenden:
`TradeSourcesView.tsx`, `CandidatePage.tsx`, `MarketAnalysisDetailPage.tsx`,
`analysisWorkflowContext.ts` und die reine öffentliche Grenze
`shared/trade-workspace-navigation/{links,context,types}.ts` samt Tests.
`TradePlanVersionContent.tsx` ist nur nach ausdrücklicher Consumerabstimmung
zusätzlicher Dateischnitt. UX2 besitzt Navigation; die Domains validieren Typ,
Identität und Version. UX4 ändert die Quellenansicht nicht parallel.

Nur belegtes `ANALYSIS` mit passender ID und positiver ganzzahliger Version
entspricht dem vorhandenen Zielvertrag. Andere Quellentypen bleiben lesbare
Provenance; keine unbelegte Alias- oder Latest-Zuordnung. Prüfen: genaue Pins,
ungültige/doppelte/fremde Parameter, Kopieren/Reload, Dirty-/Busy-Schutz,
A→B→A, keine zusätzlichen Source-Reads oder Writes allein durch Linkdarstellung
sowie Tastatur und schmale Ansicht. Zielseiten behalten ihre bestehenden Owner-Reads.
Abschluss: exakt belegter historischer Hin- und Rückweg im kleinen Draft mit
aktueller kombinierter CI. Neue Analyse, Produktauswahl und Finanzlogik sind
Nicht-Ziele.

Danach separat: FT-008/FT-009 qualifizieren die vorhandene Zuordnung
`product_selection_id → selection.run_id` für den bestehenden Source-DTO.
Prüffläche: `trade_position/service/{resolvers,source_view}.py`,
`api/source_router.py`, passende DTO-/PostgreSQL-Tests; UX2 konsumiert
anschließend in `trade/services/sourceView.ts` und `TradeSourcesView.tsx`.
Keine neue Persistenz und kein Ersatz durch die neueste Planauswahl. Mehrere
Runs, spätere Auswahl, EXTERNAL und fremder Workspace müssen erhalten bleiben.
Das bestehende UX2-Dokument begleitet beide Schnitte und die separate Abnahme
der bereits integrierten A/B/C-Wege.

### Aktueller Auftrag an UX3

Zuerst M06 aus dem bestehenden B3/F4-Auftrag: genau
`frontend/src/features/alert/components/TradeAlertsPanel.tsx` und dessen Test.
Ein lokaler reiner Textmapper erklärt gelieferten Status und Grund:
`LEGACY_RULE_PRICE_BASIS_UNCONFIRMED` gegenüber
`RISK_CONFIGURATION_OR_IDENTITY_SUPERSEDED`; unbekannter/fehlender Grund bleibt
neutral. Keine neue Domainableitung, Quittierung, Zustellung oder Recovery.
Beide Gründe, unbekannt/fehlend, OPEN/RESOLVED und unabhängigen Deliveryzustand
positiv/negativ prüfen; Originalwerte und historische Bezüge erhalten.

Danach M02/TC-50 in derselben Fläche, seriell: Health-Teilreadfehler sichtbar
halten. Vor einem neuen Anwendbarkeitsverhalten vereinbaren UX2 und
PositionMonitoring den autoritativen Positionskontext; 404 oder leere Alerts
beweisen keinen Vollabschluss. Der vorhandene `positionRead`-Zustand gehört
zum Vertrag: Ein nach invalidiertem/fehlgeschlagenem Readback weiterhin sichtbarer
alter `is_closed`-Wert ist kein aktueller Abschlussbeleg. Ein Health-GET kann
Providerzugriff enthalten.
Keine zusätzlichen Healthreads durch Navigation oder Anzeige.

Unabhängig vorbereitbar ist der enge B4/TP06-Schnitt in
`trade_plan/components/PlanPurchaseStatus.tsx` und dessen Test: aus fehlenden
optionalen Executiondaten kein erforderliches Backend-/PC-Update behaupten.
Vorhandene UNKNOWN/NOT_STARTED-, Versions- und Tradeverknüpfungen erhalten.
C-/D-Konsolidierung folgt danach nur für eine benannte Hostfläche mit Ownerfakten,
Fokus-/Ansagevertrag und konkreten Negativfällen, nicht als globale Migration.
Ein belegter späterer C3/M11-Schnitt betrifft `PositionRiskPanel.tsx` samt Test:
Read/Preview, Configure-/Evaluate-Write und bestätigten Write mit fehlgeschlagenem
Readback getrennt erklären; Operationsvertrag zuerst, kein generischer Retry.
Für D2/F8 ist `ClosedTradeStatistics.tsx` samt Test ein konkreter späterer
Kandidat: denselben belegten Unverfügbarkeitsgrund innerhalb einer Reportbasis
einmal erklären, alle betroffenen Werte weiterhin als unbekannt ausweisen.
Performance besitzt Bedeutung/Population, UX4 den Renderer, UX3 Sprache und
Ursachenbindung. Der gesonderte Profit-Faktor-Grund ohne Verluste bleibt getrennt.

### Aktueller Auftrag an UX4

Die gelieferten B/C/D- und #340-Schnitte erhalten einen begrenzten gemeinsamen
Bedien-/Quellenabgleich: Quellenwahl, überlagerte Originalbelege, DATE_ONLY,
unbekannte Werte statt Null, getrennte Reportpopulationen, exakte Rohwerte,
Tabellenfallback, Tastatur, 320/390/1280 CSS-Pixel sowie nativer Zoom. Automatisierte
CI ist vorhanden; tatsächlicher Screenreader, Touch, repräsentative Nutzerdaten
und PC-Providerabdeckung bleiben eigene Nachweise. Technische Übergaben in den
bestehenden UX4-Qualifikations-/Scopedokumenten nachführen; kein neuer Statuskatalog.

Als nächster möglicher Produktumfang bleibt die bereits benannte
Positionscoverage: bestehender GET `/market-data/positions/quote-coverage`,
keine zweite Kursquelle. Zuerst UX2-Slot, Props, Readowner, Invalidierung/Fokus
und öffentliche Market-Data-Readtypgrenze vereinbaren. Danach darf UX4 einen
schmalen Renderer mit gelieferten absoluten Zählern und Quellen einplanen.
Überlappende Populationen, fehlende Felder, zwei Positionen desselben Produkts,
Readfehler und Nebenwirkungsfreiheit prüfen. Kein lokaler Qualitätsprozentsatz.
Der ursprüngliche Auftrag enthält hierfür noch keinen endgültigen Dateischnitt;
dieser ist vor Umsetzung konkret zu übergeben.

### Verbleibende Fachentscheidungen und Abnahme

PB-019-Regelabweichungen und Entscheidungsqualität benötigen weiterhin erklärte
Kriterien der bestehenden FT-011-/FT-012-Owner. Performanceexport, breitere
Statistiken und zusätzliche Zeitreihen bleiben eigene erhaltene Anforderungen;
ohne Gebühren-/Cashflow-/FX-/Zeitreihenvertrag entstehen keine Equity-, Netto-,
Drawdown- oder Sharpewerte. Diese offenen Fachgrenzen verhindern die oben
belegbaren kleinen UX-Verbesserungen nicht.

Die [Integrationsfolge](UX_DEPENDENCIES.md#umsetzungsfolge-ab-v1546) trennt
unabhängige Arbeit, gemeinsame Dateien, reguläre CI und erforderliche Freigaben.
Genau nächster UX-Produktschnitt ist M06; der aktuelle CI-Umgebungsbefund wird
vor Integration gesondert vom CI-Owner aufgelöst. PC-Updates oder produktive
Datenänderungen sind kein Teil dieser Planung.

## Auftrag und gemeinsame Basis

**Historischer technischer Snapshot vom 01.11.2026:** Die damalige Basis und die nachfolgenden ursprünglichen Übergabepakete bleiben als Herkunft erhalten. Aktuelle technische Befunde und Folgeaufträge stehen im datierten Abschnitt oben; allgemeine Prinzipien gelten unverändert.

MASTER-LEAD koordiniert Architektur, Zuständigkeiten, Abhängigkeiten, technische Prüfung und Integration der vier UX-Stränge. Dieser Dokumentationsschnitt implementiert keine Produktfunktion.

Erneut geprüfte technische Basis am **01.11.2026, 21:20 Uhr Europe/Berlin**: [Main `484143d33aa5f2d443da6b2edf097ae1cb5aee3a`](https://github.com/burckhju/trading-workspace/commit/484143d33aa5f2d443da6b2edf097ae1cb5aee3a), Tree `08aaa9d41e64abd5021a391a9e6a1ebb6fbc8778`, enthält inzwischen den Dokumentationsnachtrag #319. Der veröffentlichte Tag [`v1.5.37`](https://github.com/burckhju/trading-workspace/tree/v1.5.37) bleibt auf `bb49ffe781933270746b9f86f4aee99b6f8144c2`. Der finale #318-Head `54eaba19fc626194237e8280af2e6cc315b1bac7`, sein qualifizierter Testmerge `341f9a031928268827710186446268217770e1ac` und der veröffentlichte Produktmerge `bb49ffe…` besitzen Tree `a924db2985cba84f37952faef6b73c16be8984ed`. Der aktuelle Main unterscheidet sich davon ausschließlich in den beiden #319-Dokumentdateien. [Getrennte Nachweise](UX_INTEGRATION_STATUS.md#technischer-snapshot-nach-v1537).

Die frühere Basis `1883f7f330719453958f8be1dd51d48db816662e` / `v1.5.35` und der Snapshot vom **01.11.2026, 15:28 Uhr Europe/Berlin** bleiben [historische Nachweise](UX_INTEGRATION_STATUS.md#historischer-snapshot-vom-01112026-1528-uhr). Vor jedem Arbeitslauf Main, Tag, PR-Zustände und parallele Dateiarbeit erneut auflösen.

**Alle fachlichen Aufgaben- und Abnahmestände bleiben ausschließlich im [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md).** UX-1 bis UX-4 sind Verantwortungsbereiche, keine neuen FT-/PB-IDs. Die folgenden Aufträge und technischen Prüfnachweise ändern keinen Backlogstatus und erteilen keine fachliche Abnahme.

## Bestehende Vorgaben und Wiederverwendung

Maßgeblich sind [Projektprinzipien](../foundation/PROJECT.md), [Systemarchitektur](../foundation/ARCHITECTURE.md), [Source Architecture](../architecture/Source_Architecture.md), [Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md), [Backendarchitektur](../architecture/BACKEND_ARCHITECTURE.md), bestehende [ADRs](../decisions/) und der [Modul-/Featurekatalog](../planning/MODULE_AND_FEATURE_CATALOG.md#ownership). Neue Widersprüche werden vor Integration geklärt; historische Berichte ersetzen keinen Codebefund.

Die Bestandsaufnahme bestätigt vorhandene TradePlan-, Trade-/Positions-, Journal- und Performanceansichten sowie historische Währungsauflösung, Positionskursverlauf und Monitoring-Datenqualität. Diese Bausteine werden weiterverwendet. Die konkrete Prüfbreite und offene Nachweise stehen im [Integrationsprotokoll](UX_INTEGRATION_STATUS.md).

Für alle vier Stränge gilt:

- Belegte vorhandene Informationen wiederverwenden; manuelle Eingaben nicht still überschreiben.
- Keine unbelegte Währung, Kursqualität, Zeitgenauigkeit oder Risikobewertung annehmen.
- Keine zweite Finanzberechnung, Trade-/Positions-/Kursdatenhaltung oder Alertengine.
- Historische Versionen, Originalzeiten, Quellen und Korrekturen erhalten.
- Keine automatischen Trades, Produktentscheidungen, Freigaben oder Strategieaktivierungen.
- Kompakte Hauptansicht, aufklappbare Details, responsive Darstellung und zugängliche Bedienung.
- Domainregeln und Schreibvorgänge bleiben beim bestehenden Owner; UI-Nähe begründet keinen gemeinsamen atomaren Snapshot.

## Dokumente und Zuständigkeit

| Dokument | Zweck |
|---|---|
| [UX_OWNERSHIP](UX_OWNERSHIP.md) | Ein Owner je gemeinsamer Schnittstelle; Consumer und Änderungsgrenzen. |
| [UX_SHARED_CONTRACTS](UX_SHARED_CONTRACTS.md) | Verbindliche Integrationsbedingungen auf bestehenden Fachverträgen. |
| [UX_DEPENDENCIES](UX_DEPENDENCIES.md) | Dateiabstimmung, Reihenfolge und gemeinsame Regressionen. |
| [UX_INTEGRATION_STATUS](UX_INTEGRATION_STATUS.md) | Datierter technischer Nachweis zu Main, PR-Heads, CI und Integrationshindernissen; keine fachliche Statusverwaltung. |

MASTER pflegt diese fünf Dokumente. Die Leads pflegen ihre vorhandenen PRs und Übergabeberichte. Einen Implementierungsstand nur an der Stelle im Backlog ändern, die die betreffende Teilfähigkeit bereits führt.

**Tatsächlich ausgeführte Phase 1:** Masterkoordination #313, UX4-A #316 und der kanonische UX3-K-Vertrag #314 sind integriert. [#318](https://github.com/burckhju/trading-workspace/pull/318) hat UX1 und UX2-A gemeinsam integriert; #311 und #312 sind mit erhaltener Abstammung im selben Mainmerge enthalten. BUY-Adapter, einmaliger Shared-Zeitzonenhelper, Host-/Testintegration und qualifizierte Preview-Fixture sind vorhanden. Der A→B→A-Reviewfix und die finale E2E-Synchronisation gehören zum ausgelieferten Stand `v1.5.37`. Die frühere Einzel-PR-Reihenfolge bleibt in [UX_DEPENDENCIES](UX_DEPENDENCIES.md#integrationsreihenfolge-phase-1) als historischer Auftrag erhalten und wird nicht erneut verteilt.

**Historische Folgearbeit vom 01.11.2026:** Der kanonische Hinweisvertrag aus #314 gilt; #315 bleibt offene Draft-Quelle und wird weder als zweiter Vertrag integriert noch geschlossen. Genau der vorhandene UX3-B1/F1-Pilot in `RealizedGrossSources` ist der nächste Präsentationsschnitt; dafür existiert bereits [Draft #320](https://github.com/burckhju/trading-workspace/pull/320) am Head `71e971a67be7f1ca10192e04e3832f843b8099bd`. Seine Produktprüfung ist eigenständig. UX4-B/C/D bleiben getrennte, an ihre konkreten Host-/Hinweis-/Domainverträge gebundene Aufträge. Diese technische Fortschreibung erteilt keine neue Produkt-, Fach- oder Mergefreigabe.

## Übergabepaket UX-1 — Eingaben und Herkunft

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Belegte Eingaben und historische Herkunft wiederverwenden; den in #318 ausgelieferten begrenzten UX1-Schnitt nachvollziehbar erhalten. |
| Nicht-Ziele | Neue Finanzlogik, automatische Buchung oder Bestätigung, neue Navigation, heutige Währung als historischen Beleg verwenden. |
| Ausgangscommit | Aktuelle Main-Basis oben; historischer finaler [#312-Head](https://github.com/burckhju/trading-workspace/commit/b1df1c1000815786a6623d35bf3f8631661a9543) `b1df1c1000815786a6623d35bf3f8631661a9543`, über #318 integriert. Frühere Einzelprüfungen bleiben im historischen Protokoll. |
| Komponenten / Dateien | `frontend/src/features/trade/components/ExecutionCurrencyPreview.tsx`, `AdditionalPurchasePanel.tsx`, `trade/services/client.ts`, `trade/types/api.ts`; `product_selection/pages/ProductSelectionPage.tsx`; `performance/services/performanceReportContext.ts`; `backend/app/features/trade_position/{api,domain,service}`. Gemeinsame `TradeManagementPage.tsx` nur mit UX-2. Vollständige Dateiliste im PR. |
| Vorhandene Implementierung | Bestehende Währungsresolver und schreibgeschützter `TradeSourceReader`; integrierte Vorschau vor BUY/SELL, öffentlicher BUY-Adapter, Wiederöffnung eines eindeutigen gespeicherten Auswahlruns und editierbare Berichtszeitzone. Journal-/Lessonverknüpfung bleibt Bestandsaufnahme. |
| Schnittstellen / Abhängigkeiten | TradePosition besitzt Resolver/DTO/GET-Vertrag; UX-2 die Host-/Readbackintegration; UX-3 das Hinweismuster. `InitialPurchaseCurrencyPreview` und der einmalige `reportTimezoneError` sind im Main implementiert; Browserableitung bleibt beim Performance-Feature. Die vier gemeinsamen Dateien wurden mit #318 zusammengeführt. |
| Testanforderungen | Vorhandene Preview-Unit-/PostgreSQL-/Browserfälle, UNKNOWN/MIXED/CONFLICT, historische Zeitbindung, keine Preview-Writes, manuelle Eingaben, späte Antworten und A→B→A; gemeinsame Navigation/Readback-Regression mit #311. Fehlerkorrekturen am aktuellen Head vollständig qualifizieren. |
| Erlaubte Änderungen | Im eigenen Implementierungsauftrag: eigene Eingabebausteine, bestehende Clients, additive lesende API nur mit Domain-Owner-Prüfung; keine alleinige Änderung der Hostnavigation oder Domainprioritäten. MASTER ändert diese Dateien nicht. |
| Abschlusskriterien | Begrenzte technische Implementierung, gemeinsame PR-/Mainqualifikation und Veröffentlichung als `v1.5.37` sind belegt. PC-Installation und menschliche Fachabnahme bleiben getrennt und nicht nachgewiesen. Keine pauschale Freigabe von UX1-B/C/D. |

Vorhandene Übergabe: [UX1_INPUT_REUSE_QUALIFICATION im geprüften Main](https://github.com/burckhju/trading-workspace/blob/484143d33aa5f2d443da6b2edf097ae1cb5aee3a/docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md). Der separate [Dokumentationsnachtrag #319](https://github.com/burckhju/trading-workspace/pull/319), finaler Head `5e58fc49781e0b944d94edcf2b298336051955c8`, ist seit 21:06:41 Uhr im aktuellen Main integriert. Er ergänzt ausschließlich diesen Bericht und PB-016 Eröffnung im Backlog; beide Dateien bleiben außerhalb dieses Master-Diffs. Die frühere offene Draft-Einordnung ist historisch und bezeichnete keinen Produktfix. Fachliche Zuordnung: [PB-016 Eröffnung](../planning/PRODUCT_BACKLOG.md#pb-016-opening), [PB-015 Vergleich](../planning/PRODUCT_BACKLOG.md#pb-015-comparison), [PB-019 Auswertungen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations).

## Übergabepaket UX-2 — Trade-/Positionsarbeitsbereich

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Einen vorhandenen Trade zwischen Position, Buchungen, Quellen und Lernen verfolgen, ohne Kontext, historische Pins oder ungespeicherte Eingaben zu verlieren. |
| Nicht-Ziele | Zweite Trade-/Positionshaltung, neue Fachberechnung, neue Freigabe/Lifecycleentscheidung, unbelegte Beziehungen zwischen Plan, Run, Analyse und Journal. |
| Ausgangscommit | Aktuelle Main-Basis oben; historischer [#311-Head](https://github.com/burckhju/trading-workspace/commit/55072f8e90c00d309c3bd6ed6dd17f61ab33bd32) `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32`, mit erhaltener Abstammung über #318 integriert. |
| Komponenten / Dateien | `frontend/src/features/trade/pages/TradeManagementPage.tsx`, `trade/pages/index.ts`, `trade/components/TradeSourcesView.tsx`, neue Navigation/Linkhelper; `post_trade/pages/PostTradeLearningPage.tsx` und betroffene Journal-/Lessonconsumer. Vollständige Dateiliste im PR. |
| Vorhandene Implementierung | Kontext-/Dirty-/Busy-Guards, Abort-/Generationsschutz, ein Timelineowner, Quellen und historische Journal-/Lessonversionen. UX2-A-Navigation, Shared-Helper und gemeinsame UX1-Hostintegration sind ausgeliefert. UX2-B/C/D sind dadurch nicht abgeschlossen; die bestehende zusätzliche Positionsabfrage des Bewertungsbausteins ist weiterhin kein hier konsolidierter Schnitt. |
| Schnittstellen / Abhängigkeiten | Einziger Integrationsowner der gemeinsamen Hostseite; UX-1-Formularverhalten, UX-3-Hinweisplatzierung und UX-4-Charts konsumieren. `shared/trade-workspace-navigation` einschließlich einmaligem Zeitzonenhelper und die vereinbarten Preview-/Reloadprops sind im Main vorhanden und wiederzuverwenden. |
| Testanforderungen | Kontext/Pins/Rückwege, Tastatur/Fokus, 390/1280-px-Ansichten, keine Zusatzreads bei Hashnavigation, zwei parallele Entwürfe, A→B→A, geschlossen/storniert/fehlend; gemeinsame #311/#312-Regression und bestehende Journal-/Performance-Gates. |
| Erlaubte Änderungen | Im eigenen Implementierungsauftrag: Navigation, darstellende Komposition, schmale Link-/Slotverträge und Tests; Hoständerung für andere Stränge abgestimmt übernehmen. Keine Domain- oder Formeländerung. |
| Abschlusskriterien | Der gemeinsame #318-Stand einschließlich Helper, UX1-Hunks, Preview-Fixture, A→B→A-Fix und finaler E2E-Synchronisation ist PR-geprüft, Main-integriert und veröffentlicht. Belege und Nachweisgrenzen im Integrationsprotokoll; keine Vollständigkeitsbehauptung für UX2-B/C/D oder menschliche Fachabnahme. |

Vorhandene Übergaben: [ux2-trade-workspace im geprüften Main](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/docs/ui/ux2-trade-workspace.md) und [gemeinsame Integration #318](https://github.com/burckhju/trading-workspace/pull/318). Fachliche Zuordnung: [PB-016 Positionen](../planning/PRODUCT_BACKLOG.md#pb-016-positions), [PB-017 Historie](../planning/PRODUCT_BACKLOG.md#pb-017-history), [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) und [Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).

## Übergabepaket UX-3 — Hinweise und sichere Folgeaktionen

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Vorhandene Hinweise konsistent als Feststellung, Ursache, Auswirkung und bewussten nächsten Benutzerweg darstellen. Der kanonische Vertrag ist integriert; nächster begrenzter Präsentationsschnitt ist genau B1/F1 in `RealizedGrossSources`. |
| Nicht-Ziele | Neue Alert-/Notificationengine, neue fachliche Prioritätsberechnung, pauschale Risikoampel, automatischer Refresh/Write/Trade oder Aktivierung. |
| Ausgangscommit | Aktuelle Main-Basis oben. #314, finaler Head `cc547ef662d1bc28315d25df1930c32b94278d6b`, ist über `d80bd45d84d845aa920a7eac5b19a7fe6cd63307` integriert. #315 `d9d85f1af3159c4356c8773d076decbf1dc604e4` bleibt Quelle. Produktentwurf: #320 `71e971a67be7f1ca10192e04e3832f843b8099bd` auf Main `484143d…`; kanonische Dokumente und Backlog gehören nicht mehr zu seinem aktuellen Diff. |
| Komponenten / Dateien | Für B1/F1 die tatsächlich in #320 bearbeiteten `performance/components/RealizedGrossSources.tsx`, `ReportSourceEntry.tsx`, `ReportCurrencyEvidence.tsx`, der Featuremapper `realizedCurrencyNotice.ts` sowie `shared/notices` und zugehörige Tests. Vollständiger 18-Dateien-Diff im PR; gemeinsame Hostseite bleibt bei UX-2. |
| Vorhandene Implementierung | Ein kanonischer Dokumentvertrag unter `docs/ui/ux-3/`, alle vier Typpräzisierungen und Übernahmen aus #315 sind integriert. Ein neuer produktiver gemeinsamer Hinweisrenderer ist im geprüften Main noch nicht enthalten; der konkrete B1/F1-Code liegt separat im offenen #320. |
| Schnittstellen / Abhängigkeiten | UX-1 liefert Validierungs-/Herkunftsfakten; UX-2 Platzierung/Fokus; UX-4 konsumiert Qualitätsmuster. Fachliche Bedeutung und Blockierungen bleiben beim jeweiligen Domain-Owner. |
| Testanforderungen | Fehlend/veraltet/Fehler nie als gesund; Alert versus Zustellung versus Scheduler unterscheiden; keine Mutation durch Rendering oder Link; Retry nur für den benannten Read; Tastatur, Fokus, Live-Region und schmale Ansicht. |
| Erlaubte Änderungen | Der vorhandene B1/F1-Auftrag und sein tatsächlicher Diff bilden die Abstimmungsfläche; keinen zweiten parallelen Piloten eröffnen. Produktprüfung und gegebenenfalls Vertragsabgleich erfolgen separat. Dieser Masterlauf ändert ausschließlich die fünf Koordinationsdateien. |
| Abschlusskriterien | UX3-K-Vertragskonsolidierung ist technisch integriert. Der getrennte lesende Pilot #320 benötigt seinen eigenen aktuellen Code-/CI-/Ownernachweis; Performance prüft Wirkung, UX1 Herkunft, UX2 Kontext/Guard/Fokus, UX3 Sprache/Deduplizierung/Ansage. Keine Fachabnahme aus Dokumentvertrag oder vorbereitetem Versionstext ableiten. |

Fachliche Zuordnung: [Monitoringregeln](../planning/PRODUCT_BACKLOG.md#monitoring-rules), [Zustellung](../planning/PRODUCT_BACKLOG.md#notification-delivery), [Datenqualität](../planning/PRODUCT_BACKLOG.md#market-data-quality), [PB-017 Stop](../planning/PRODUCT_BACKLOG.md#pb-017-stop).

## Übergabepaket UX-4 — Diagramme und Kennzahlen

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Bestehende Diagramme/Kennzahlen lesbar, zugänglich und hinsichtlich Herkunft, Zeitraum und Datenlücken nachvollziehbar darstellen. Der UX4-A-Vertrag ist integriert; spätere B/C/D-Schnitte bleiben gesondert daran gebunden. |
| Nicht-Ziele | Zweite Kursspeicherung, Backfill/Providerabruf beim Anzeigen, neue Finanzformel, eigene Normalisierung, erfundene Netto-/FX-/Equitywerte. |
| Ausgangscommit | Aktuelle Main-Basis oben; #316, finaler Head `82b11711a70aacf39fddf59a6545662fb7102b92`, ist über `5f2e12667759bfb54eb14f39c6d8426c9cd8080f` integriert. Seine sechs Dokumente belegen keine neue UX4-B/C/D-Produktoberfläche. Tatsächlich vorhandene lokale B-Folgearbeit: Draft #322 `e3365df7afc70ec52fe6fb19aabc4050250091e3` mit zwei History-Komponenten-/Testdateien; eigene Qualifikation erforderlich. |
| Komponenten / Dateien | `frontend/src/features/operational_workspace/components/{PositionPriceHistory,PositionPricePlot,PositionPriceHistoryEvidence}.tsx`, zugehörige Präsentationshelper; `analysis/components/TimeSeriesChart.tsx`; `performance/components/ClosedTradeStatistics.tsx`; passende Tests. |
| Vorhandene Implementierung | Lesender Positionsverlauf mit Scatterpunkten und Evidenztabelle, Marktcharts mit Backendnormalisierung und Lücken, serverseitige Abschlussstatistik mit Nenner/Definitionsversion. #205 ist keine aktuelle Implementierungsvoraussetzung. |
| Schnittstellen / Abhängigkeiten | UX4-A und UX3-K sind integriert. Für B/C/D besitzt UX-2 weiterhin Hostslots/Props/Readback, UX-3 den kanonischen Präsentationsvertrag. Bei gemeinsamen Quellenflächen die aktive #320-Arbeit beachten. Market Data, TradePosition, Analysis und Performance behalten ihre getrennten Daten-/Berechnungsverträge. |
| Testanforderungen | Quelle/Währung/Preisart getrennt; Originaldezimalwerte; fehlend ungleich Null; leer/Fehler/Kürzung unterscheiden; date-only nicht als präzisen Zeitpunkt plotten; verspätete Antworten; Tabelle/Keyboard/Mobilansicht; keine Mutation beim Öffnen. |
| Erlaubte Änderungen | Nach konkreter Dateiabstimmung im eigenen Auftrag bestehende Darstellungs-/Evidenzkomponenten und Tests; Hostnavigation nur über UX-2. Ownerantworten unverändert konsumieren. |
| Abschlusskriterien | Übergabe mit konkretem Diff; Einheiten, Quellen und Lücken erhalten; zugängliche Alternative und gemeinsame Qualitätsprüfung belegt; aktuelle CI; weitergehende Performancefunktionen und Abnahme ausdrücklich abgegrenzt. |

Fachliche Zuordnung: [Marktübersicht](../planning/PRODUCT_BACKLOG.md#pb-013-overview), [Kennzahlen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics), [Statistiken](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics), [Dashboards](../planning/PRODUCT_BACKLOG.md#pb-019-performance-dashboards).

## Übergabe zwischen getrennten Chats

Alle vier Leads erhalten dieselbe Main-Basis, diese fünf Dokumente und den exakten Koordinations-PR-Head als Einstieg. Ein Link im Repository ist ein überprüfbares Übergabeangebot; er belegt keinen automatischen Empfang in einem anderen Chat.

Jeder Folgeauftrag ergänzt vor Änderungen: Ziel/Nicht-Ziele, Ausgangs-SHA, vollständige Dateiliste, bereits vorhandenen Code, Owner/Consumer, Abhängigkeiten, Tests, erlaubte Änderungen und Abschlusskriterien. Die Übergabe nennt anschließend Branch, PR, Head-/Testmerge-SHA, tatsächlichen Diff, CI-Run-/Joblinks, offene Konflikte und getrennte Fach-/Release-/PC-Nachweise. UX3 und UX4 haben jetzt überprüfbare Dokumentationsübergaben; die technischen Folgeaufträge stehen in [UX_DEPENDENCIES](UX_DEPENDENCIES.md#präzise-folgeaufträge). Ein dokumentierter Rollenauftrag belegt keinen bestätigten Empfang in einem anderen Chat.

Erlaubnis dieses MASTER-Laufs nach `v1.5.37`: technische Fortschreibung ausschließlich dieser fünf Koordinationsdokumente auf frisch geprüftem Main, eigener Dokumentationsbranch und Draft-PR sowie Dokumentprüfung und reguläre PR-CI. #313 ist bereits integriert; #319s Bericht/Backlogdatei und alle Produkt-, Workflow-, Versions- und Finanzvertragsdateien bleiben außerhalb des Diffs. Merges, Releases, Tags, Workflow-Neustarts, PC-Updates, produktive Änderungen und PR-Schließungen benötigen ausdrückliche gesonderte Freigabe. Automatische Handelsentscheidungen gehören nicht zu diesem Auftrag.
