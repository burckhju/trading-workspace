# Integration und kleine Folgearbeiten

[Übersicht](README.md) · [Hinweisinventur](inventory.md) ·
[Hinweisvertrag](notice-contract.md) · [Komponenten](components-and-actions.md) ·
[Tests und Abnahme](test-and-acceptance.md)

Der B1/F1-Produktpilot wurde mit
[PR #320](https://github.com/burckhju/trading-workspace/pull/320) integriert und über
[#323](https://github.com/burckhju/trading-workspace/pull/323) als
[v1.5.38](../../releases/V1.5.38-UX3-CURRENCY-NOTICE.md) veröffentlicht.
Der [Pilotbericht](../../implementation/UX3_B1_CURRENCY_NOTICE.md) trennt Umfang,
Prüfungen und offene Abnahmen. Die damalige Draftfortsetzung und Rücknahme der
parallelen Releasevorbereitung bleiben historische Schritte. Der erste B2/F4-Schnitt
in `ProductValuationPanel` ist über #324 integriert und mit #328 als
[v1.5.39](../../releases/V1.5.39-UX3-VALUATION-NOTICE.md) veröffentlicht; Umfang und
Nachweise stehen im [B2-Qualifikationsbericht](../../implementation/UX3_B2_VALUATION_NOTICE.md).
Der folgende PositionDetails-Schnitt aus #326 ist seit dem 05.11.2026 integriert;
seine Beleggrenze und die getrennten Produkt-/Veröffentlichungsnachweise stehen in
[Abnahmeabschnitt 10](test-and-acceptance.md#10-b2f4--q12-in-positiondetails).
Abschnitt 7 bereitet danach genau einen B3-Schnitt für Alert-Invalidierungstexte vor.
Die folgenden UX3-K-Quellen-/Parallelstände sind historische Konsolidierungsbelege.

## 1. Umfang und Zuständigkeit

**UX3-K war der Konsolidierungsschnitt in #314.** Er setzte die
[Masterentscheidung](../../coordination/UX_SHARED_CONTRACTS.md#kanonischer-ux3-hinweisvertrag--masterentscheidung-phase-1)
auf Main `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` um: #314 ist die führende
Grundlage, #315 liefert verpflichtende Präzisierungen. Genau ein Einstieg,
Hinweisvertrag und Dokumentationstypmodell liegen unter `docs/ui/ux-3/`.
#315 wird weder als zweiter Normvertrag integriert noch durch diesen Auftrag
geschlossen. Die Produktinventur auf `1883f7f330719453958f8be1dd51d48db816662e`
bleibt für den damaligen Produktcode nachvollziehbar.

Produktkomponenten wurden für UX3-K nicht umgebaut. B1/F1 ist der gesonderte
Produktschnitt auf dem anschließend integrierten UX1/UX2-Stand aus #318.
Sein schmaler Renderer und seine tatsächlichen Exports sind in den
[Komponenten-APIs](components-and-actions.md#6-exemplarische-komponenten-apis)
vom vollständigen konzeptionellen Vertrag abgegrenzt. Fachliche Zustände und
der eine normative Hinweisvertrag bleiben erhalten. Ein gelesener Diff oder
grüne technische Prüfung behauptet keine bereits erfolgte Ownerabnahme,
Tagveröffentlichung oder PC-Installation. Arbeitsstatus führt ausschließlich
[Product Backlog — Operational Workspace](../../planning/PRODUCT_BACKLOG.md#operational-workspace).

| Owner | Verantwortet | Übergabe an UX-3 |
| --- | --- | --- |
| Fachlicher Domain-Owner | Berechenbarkeit, Zulässigkeit, Status, Resolver, Provenienz, Versionierung, Retry, Recovery und Commands | Vorhandene DTO-Fakten und Fehlercodes einschließlich ihrer Aussagegrenzen. |
| UX-1 — Eingabeautomatisierung | Feldermittlung, Vorbelegung, fachliche Validierung, Herkunft und notwendige Eingaben | Bereits aufgelöste Werte, Belege und noch fehlende Voraussetzungen. UX-3 berechnet oder bestätigt kein Feld selbst. |
| UX-2 — gemeinsamer Arbeitsbereich | Navigation, Informationshierarchie, Bereichswechsel, Kontextführung, Layout und Integration vorhandener Fachkomponenten | Validierter Objekt-/Versionskontext, vorhandenes Navigationsziel und Fokusführung. UX-3 erstellt keine konkurrierende Arbeitsbereichsseite. |
| UX-3 — Hinweise | Hinweiskatalog, verständliche Ursache/Wirkung/Aktion, Darstellungsart, Priorität innerhalb einer Hinweisgruppe, Details und Rückverfolgbarkeit | Rein präsentationale View-Props; keine Finanzrechnung, neue Fachstatusmaschine oder automatische Schreibentscheidung. |
| UX-4 — Datenvisualisierung | Visualisierung vorhandener Qualität, Abdeckung und Zeitbezüge | Eine Qualitätssprache aus dem kanonischen Hinweisvertrag; fachliche Bedeutung bleibt beim Domain-Owner, keine zweite Notice-API. |

Eine spätere Änderung an einem UX-1-Formular oder UX-2-Host wird vor ihrer Umsetzung
mit dessen Owner abgegrenzt. Die Abstimmung benennt betroffene Dateien, Kontext-
und Callback-Verantwortung sowie Tests. Fremde Feature-Branches werden nicht
eigenständig gemergt. Die Folgeplanung erzeugt keine neuen GitHub-Issues/FT-/PB-IDs
und erweitert UX3-K nicht um Produktänderungen.

## 2. Integrationsmatrix am vorhandenen Code

Die Matrix nennt tatsächliche Komponenten und Verträge. „Künftige Nutzung“ ist
ein Vorschlag und kein bereits ausgelieferter Integrationsstand.

| Bestehende Fläche | Vorhandene fachliche Quelle | Künftige UX-3-Nutzung | Bleibende Verantwortung und Grenze |
| --- | --- | --- | --- |
| [ExecutionCurrencySources](../../../frontend/src/features/trade/components/ExecutionCurrencySources.tsx), [ExecutionCurrencyPanel](../../../frontend/src/features/trade/components/ExecutionCurrencyPanel.tsx) | `ExecutionCurrencyResolution`, `ExecutionCurrencyHistory` und Confirmation aus [trade/types/api.ts](../../../frontend/src/features/trade/types/api.ts); bestehender [Währungsresolver](../../../backend/app/features/trade_position/domain/currency_resolution.py) | Automatisch belegte Währung neutral erklären; UNKNOWN/MIXED/CONFLICT mit konkretem Reason und Ausführung darstellen; gleiche Ursache nur einmal. | Trade-Position entscheidet über Nachweis. UX-1 behält Bestätigungsformular, Quellenprüfung und Minimalinput; UX-3 erzeugt keine `USER_CONFIRMED`-Angabe. |
| [ExecutionDatesPanel](../../../frontend/src/features/trade/components/ExecutionDatesPanel.tsx), [CurrencyEvidenceEditor](../../../frontend/src/features/product/components/CurrencyEvidenceEditor.tsx) | Effektive Ausführungen, Korrekturketten, Evidenceversionen, Gültigkeitsintervalle und bestehende CAS-/Requestpins | Readfehler, Kontextkonflikt, bestätigter Schreibabschluss und unklarer Schreibausgang verständlich trennen. | Korrektur, Widerruf und Bestätigung bleiben explizite Commands. Kein neuer zentraler Retry und kein Umbau der UX-1-Eingaben in dieser Phase. |
| [PositionValuationBasisDetails](../../../frontend/src/features/trade/components/PositionValuationBasisDetails.tsx), [PositionDetails](../../../frontend/src/features/operational_workspace/components/PositionDetails.tsx), [TradeManagementPage](../../../frontend/src/features/trade/pages/TradeManagementPage.tsx) | `PositionValuationBasis`, `ProductPositionValuationResponse`, zugleich unqualifizierte `PositionResponse`-Zahlen; [valuation_basis.py](../../../backend/app/features/trade_position/service/valuation_basis.py) | Fehlende Kostenbasiswährung und Wirkung auf genau den betroffenen G/V erklären; Provenienz zusammenführen. | Finanzqualifikation bleibt Trade-Position. Umgang mit rohen Positionszahlen ist Entscheidung O1 unten; UX-2 verantwortet deren Platzierung. Kein zusätzlicher G/V-Rechner. |
| [RealizedGrossSources](../../../frontend/src/features/performance/components/RealizedGrossSources.tsx), [ReportSourceEntry](../../../frontend/src/features/performance/components/ReportSourceEntry.tsx), [ClosedTradeSources](../../../frontend/src/features/performance/components/ClosedTradeSources.tsx) | `RealizedGrossSource.currency_resolution`, wirksamer Kostenbasispräfix und `sources` derselben [Berichtsantwort](../../../frontend/src/features/performance/types/api.ts) | Eine lesende Währungserklärung und vorhandene Belege zeigen; historische Ersetzung als Historie kennzeichnen. | Performance besitzt Auswahl und Herkunft der finanziellen Basis. Keine spätere Quelle in denselben Bericht mischen; kein Buchungswrite durch Quellenansicht. |
| [PerformanceWorkspace](../../../frontend/src/features/performance/pages/PerformanceWorkspace.tsx), [RealizedGrossReportView](../../../frontend/src/features/performance/components/RealizedGrossReportView.tsx), [ClosedTradesReportView](../../../frontend/src/features/performance/components/ClosedTradesReportView.tsx) | `RealizedGrossReport`, `ClosedTradeReport`, `summary`, `reasons`, `definition_version`, `basis.id`; [report.py](../../../backend/app/features/performance/domain/report.py) | Einzelwert-/Aggregatwirkung, bekannte Teilsumme und vollständige Summe erklären; Berichtsdefinition/Filter erhalten. | `PARTIAL`/`NOT_COMPUTABLE` bleiben Ownerzustände. Belegtes `EMPTY` mit vollständiger Nullsumme 0 ist von unbekanntem Wert `null` zu unterscheiden. Keine FX- oder Aggregationslogik in Komponenten. |
| [TradeSourcesView](../../../frontend/src/features/trade/components/TradeSourcesView.tsx) | `SourceSnapshot`, Review-/Journalpins, `SOURCE_*`-Codes und [sourceView](../../../frontend/src/features/trade/services/sourceView.ts) | Abschnittsbezogene Readfehler, genaue historische Bindung und verfügbare Quellenlinks. | UX-2 behält Quellenansicht und Navigation. „Nicht lesbar“ beweist keine fehlende Quelle. Historische Pins werden nicht durch aktuelle Versionen ersetzt. |
| [MarketDataRefreshPanel](../../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx) | Private `RefreshCheck`/`RefreshStatus`-Typen, `PROCESS_LOCAL`-Diagnostik; [refresh_diagnostics.py](../../../backend/app/features/market_data/service/refresh_diagnostics.py), [refresh_quality.py](../../../backend/app/features/market_data/service/refresh_quality.py) | Job/SOURCE, Retention, Wartephase, echte Fehlerfolge und qualifizierte Recovery getrennt erklären. | Market Data besitzt Scheduler, Identität, Frische und Recovery. Öffentlicher Typzugang ist vor Wiederverwendung zu klären (O3); keine kopierte Recoverylogik. |
| [QuoteCoveragePanel](../../../frontend/src/features/operational_workspace/pages/QuoteCoveragePanel.tsx), [PositionStatus](../../../frontend/src/features/operational_workspace/components/PositionStatus.tsx) | Private Coverage-Typen; `ProductPositionValuationResponse`; [quote_freshness.py](../../../backend/app/features/position_monitoring/service/quote_freshness.py) | Reguläres `LAST_AVAILABLE`, echte Staleness, Referenzkurs und Ersatzkurs verständlich differenzieren. | Bestehende Frischepolicy gilt. Kein neues Alterlimit, keine eigene Quoteauswahl und kein Sofort-Retry aus Hinweisrendering. |
| [TradeAlertsPanel](../../../frontend/src/features/alert/components/TradeAlertsPanel.tsx), [MonitoringRuntimePanel](../../../frontend/src/features/alert/components/MonitoringRuntimePanel.tsx) | `AlertResponse`, `NotificationResponse`, `PositionMonitoringHealthResponse` aus [alert/types/api.ts](../../../frontend/src/features/alert/types/api.ts); Laufdiagnostik | Fachalert, Monitoringabdeckung und Versandfehler auseinanderhalten; echte fehlende Regelbindung konkret erläutern. | Monitoring/Alert/Notification bleiben verschiedene Owner. Keine Quittierung, Alertinvalidierung, Stopmutation oder Handelsentscheidung durch Anzeige. |
| [PositionPriceHistory](../../../frontend/src/features/operational_workspace/components/PositionPriceHistory.tsx) | [PositionPriceHistoryReport](../../../frontend/src/features/operational_workspace/positionPriceHistory.ts): Serie, Preisart, Originalzeit, `truncated`, Ausschlüsse und Events | Leere Historie, begrenzte Abdeckung, historische Fehlversuche und technischen Readfehler unterscheiden. | Market Data/Trade-Position liefern Historie. Keine interpolierten Fehlwerte, künstliche Backfills oder Platzierung anhand einer erfundenen Originalzeit. |
| [ExistingTradePlanPage](../../../frontend/src/features/trade_plan/pages/ExistingTradePlanPage.tsx), [TradePlanVersionContent](../../../frontend/src/features/trade_plan/components/TradePlanVersionContent.tsx) | Exakte `TradePlanVersionResponse`, Approval, Lifecycle und [planViewContext](../../../frontend/src/features/trade_plan/services/planViewContext.ts) | Fehlende Version, regulären DRAFT/SUPERSEDED-Stand, konkrete Freigabevoraussetzung und unklaren Speicherabschluss erklären. | TradePlan besitzt Lifecycle und Freigabe; UX-1 Inhalte/Validierung, UX-2 Versionsnavigation. Historische Version bleibt gebunden. |
| [PlanPurchaseStatus](../../../frontend/src/features/trade_plan/components/PlanPurchaseStatus.tsx) | Vorhandene Kaufstatus-/Executionprojektion | UNKNOWN und fehlenden Nachweis korrekt erklären; B4-Vertiefung als eigener F6-Teilschnitt. | Kein NOT_STARTED aus fehlenden Feldern, keine Planfreigabe aus Kaufstatus und kein unbelegtes Backend-/PC-Updategebot. |
| [ProductSelectionPage](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.tsx) | `ProductEvaluationResponse`, `CriterionResultResponse`, `EvaluationInputResponse`, `UniverseOmissionResponse`; [planContext](../../../frontend/src/features/product_selection/services/planContext.ts) | Fehlende Notierung/Terms/Quotes mit Wirkung erklären; Originalzeit anzeigen; `NOT_APPLICABLE` als regulär ausgelassenen Schritt behandeln. | `INELIGIBLE` ist gesperrt; `NOT_EVALUABLE` bleibt mit ausdrücklicher Begründung auswählbar. Auswahl, neuer Run und Datenpflege bleiben Commands der bisherigen Owner. |
| [TradeJournalPanel](../../../frontend/src/features/learning/components/TradeJournalPanel.tsx), [PostTradeLearningPage](../../../frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) | `JournalHistory`, `JournalEntry`, `JournalReceipt`; `Ft011MaterializationStatus`; konkrete Handoff-/Journal-/Materialisierungscodes | Offenen Entwurf neutral darstellen, Quellenvoraussetzungen und Konflikte erklären, Receipt von aktuellem Read unterscheiden. | Journal/FT-011/FT-012 behalten persönliche Bewertung, Finalisierung, Quellenneubindung und Materialisierung. Keine automatische Lesson. |
| [EvidenceSourceStatus](../../../frontend/src/features/learning/components/EvidenceSourceStatus.tsx), [JournalEvidenceOrigin](../../../frontend/src/features/learning/components/JournalEvidenceOrigin.tsx), [LessonReviewPanel](../../../frontend/src/features/learning/components/LessonReviewPanel.tsx) | `SourceInspection`, exakte `LessonVersionSnapshot`, `ReviewContext`/`ReviewReceipt` aus [lessonReviewClient](../../../frontend/src/features/learning/services/lessonReviewClient.ts) | Historische Quelle, heutige Currentness, offene Entscheidung und unvollständigen Read verständlich zeigen; gleiche Provenienz nicht mehrfach ausgeben. | Lesson-Owner bewahrt unveränderliche EvidenceLinks und explizite Interpretation. `CURRENT` ist kein Reparaturnachweis für STALE/UNKNOWN-Quellen. |
| [ProposalApprovalPanel](../../../frontend/src/features/model/components/ProposalApprovalPanel.tsx), [RuntimeActivationPanel](../../../frontend/src/features/model/components/RuntimeActivationPanel.tsx) | [ProposalApprovalResult](../../../frontend/src/features/model/types/proposalApproval.ts), [RuntimeActivation](../../../frontend/src/features/model/types/runtimeActivation.ts) | Genehmigte und aktive Version getrennt erklären; unbelegten Aktivierungsstand begrenzt anzeigen. | Governance entscheidet und aktiviert ausdrücklich. Freigabe, neueste Version und aktuelle Aktivierung bleiben unterschiedliche Tatsachen. |
| [CandidatePage](../../../frontend/src/features/candidate/pages/CandidatePage.tsx) | Bestehender Readiness-Workflow und Gesamtguard `can_evaluate` | Teilstatus COMPLETE von gesamter Bewertungsfreigabe trennen; konkrete Anleitung erhalten. | Kein erfundener Governancepfad aus Modell-ID, keine automatische Evaluation nach Readinessrefresh und keine Aktivierung durch Hinweis. |
| [OperationalWorkspacePage](../../../frontend/src/features/operational_workspace/pages/OperationalWorkspacePage.tsx), [OpenPositionsPanel](../../../frontend/src/features/operational_workspace/pages/OpenPositionsPanel.tsx) | `OperationalAction`, `OperationalPosition`, `PositionAttentionState` aus [types.ts](../../../frontend/src/features/operational_workspace/types.ts); [prioritization.py](../../../backend/app/features/operational_workspace/service/prioritization.py) | Später kompakte Hinweiszusammenfassung mit Verweis auf genaue Fachdetails. | UX-2 bleibt Owner des Hosts und der Informationshierarchie. UX-3 ersetzt weder ACTION/REVIEW/BLOCKED noch die bestehende globale Sortierung durch ein zweites Aufgabenmodell. |

## 2a. Verbindlicher Koordinationsstand

Für die aktuelle Konsolidierung gelten [Shared Contracts](../../coordination/UX_SHARED_CONTRACTS.md)
und [UX Dependencies](../../coordination/UX_DEPENDENCIES.md), nicht frühere
Einzelentwurfsannahmen. Die dort geprüften Heads sind:

| Partner / Stand | Verbindliche Übergabe an den späteren Produktschnitt |
| --- | --- |
| UX2 #311, `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Navigation bereits unter `frontend/src/shared/trade-workspace-navigation/`; erhalten, nicht erneut entwickeln. UX2 bleibt einziger Hostintegrator mit Kontext, Fokus, Guards, Formulardauer und Invalidierung. |
| UX1 #312, `8f67442daac6879d7dfb28416f2171f67aead0e5` | Kontrollierte Währungsvorschau, erforderlicher schmaler öffentlicher BUY-Adapter und gemeinsamer Zeitzonenhelper nach Mastervertrag. Preview ist kein gespeicherter Ausführungsbeleg; manuelle Entwürfe bleiben beim Formular. |
| UX4 #316, `ae8c792f3e3ad74994894fac581cb4cf81ba5de7` | Eigenständiger Dokumentationsvertrag, kein ausgelieferter Chart-/Hinweisumbau. Vor Produktarbeit den dann aktuellen Host und diesen einen Hinweisvertrag binden. |
| UX3 #314 / #315 | #314 `52a24266dce1ec048b23360b4b75d5b3f54d746b` plus #315 `d9d85f1af3159c4356c8773d076decbf1dc604e4`; vier Typpräzisierungen, Inventur- und Fallzuordnung sind Bestandteil von UX3-K. |

Vor Produktarbeit werden Main, integrierte Heads und tatsächliche Datei-/Ownergrenzen
erneut aufgelöst. Shared importiert keine Featureinternas; Finanz-/Quellenvalidatoren
bleiben beim Owner. Gemeinsame URLs genau einmal transportieren oder fertige geprüfte
Ownerlinks über Props übergeben. Der dokumentierte Ablauf ist Koordination,
UX4-A-Dokumentation, konsolidierter UX3-Vertrag, UX2-Helperschnitt und danach
qualifizierter UX1/UX2-Gesamtstand; erst anschließend B1/F1. Das ist keine
Erlaubnis zum blinden Übernehmen fremder Branches oder ein Beleg ihrer CI.

### Historischer Analysebeleg aus #314

Die nachstehenden früheren Head-/Code-/CI-Bezüge bleiben als Herkunft erhalten.
Sie beschreiben ausschließlich den damaligen Abgleich und sind keine aktuellen
Abhängigkeitsstände oder Ergebnisse für UX3-K.

Die Main-Inventur bleibt an `1883f7f330719453958f8be1dd51d48db816662e`
gebunden. Die folgenden **offenen Draftänderungen** wurden zusätzlich direkt
über Git-Diffs und Dateiinhalte geprüft, ohne Checkout oder Merge ihres Branches.
Tests dieser Branches wurden gelesen, hier aber nicht lokal ausgeführt.

| Parallelstand | Tatsächlicher Code | Konkreter UX-3-Integrationspunkt |
| --- | --- | --- |
| [UX-1 #312](https://github.com/burckhju/trading-workspace/pull/312), `feature/ux1-evidence-aware-inputs-20261031`, Head `74d29bb8197d4819f3edc948143a41f4cd7046c8`, 31 Dateien | Bestehender `execution-currency-v3`-Resolver wird für lesende Vorschau-GETs zu Produkt oder Trade wiederverwendet. `ExecutionCurrencyPreview` bindet Datum/Seite/Produkt bzw. Trade und lässt manuelle Eingabe bestehen. Hinzu kommen automatisches lesendes Öffnen eines einzigen passenden Auswahlruns und Vorschlag der gültigen Browserzeitzone für Berichte. | Vorschau ist kein gebuchter Ausführungsnachweis, kein Receipt und keine Behebung einer bestehenden Performance-Lücke. UX-1 besitzt Vorschau, Nutzerdraft und erneute Prüfung beim Speichern. UX-3-Pilot konsumiert ausschließlich passend gebundene gespeicherte Berichts-/Ausführungsfakten. |
| [UX-2 #311](https://github.com/burckhju/trading-workspace/pull/311), `feat/ux2-a-trade-workspace-navigation`, Head `6782bc7a567ce24d480e3e7996f919399f28896f`, 25 Dateien | `workspaceNavigation.ts` und `TradeWorkspaceNavigation.tsx` erhalten Quellpins und Berichtskontext über Management, Quellen, Journal und Lessons; neue Abschnittsanker und Fokusführung, keine Backend-/Routerdateiänderung. | Nach Integration diesen Navigationsowner nutzen. UX-3 erzeugt keine eigene Hashfokuslogik. `#execution-dates` bleibt Bereichsziel; ein exakter Ausführungs-/Evidencefokus oder Providercheck für Listing/`identity_key` fehlt weiterhin. |

**Konfliktgrenze UX-1:** `RealizedGrossSources.tsx` und
`ExecutionCurrencySources.tsx` sind am geprüften UX-1-Head unverändert. Letztere
Komponente wird aber neu durch `ExecutionCurrencyPreview` eingebettet und damit
auch bei Erstkauf, Nachkauf und Verkauf verwendet. Der Pilot F1 darf sie nicht
ungeplant umstellen; neue Vorschau, Override und Formulare bleiben bei UX-1.
Mögliche Wiederholungen zwischen Vorschauzusammenfassung und Quellenhinweis sind
eine spätere abgestimmte Präsentationsaufgabe.

Codebelege am UX-1-Head:
[Vorschau](https://github.com/burckhju/trading-workspace/blob/74d29bb8197d4819f3edc948143a41f4cd7046c8/frontend/src/features/trade/components/ExecutionCurrencyPreview.tsx),
[GET-Routen](https://github.com/burckhju/trading-workspace/blob/74d29bb8197d4819f3edc948143a41f4cd7046c8/backend/app/features/trade_position/api/router.py),
[Read-only-Quellenreader](https://github.com/burckhju/trading-workspace/blob/74d29bb8197d4819f3edc948143a41f4cd7046c8/backend/app/features/trade_position/service/source_view.py),
[Kontexttests](https://github.com/burckhju/trading-workspace/blob/74d29bb8197d4819f3edc948143a41f4cd7046c8/frontend/src/features/trade/components/ExecutionCurrencyPreview.test.tsx),
[PostgreSQL-Read-only-Tests](https://github.com/burckhju/trading-workspace/blob/74d29bb8197d4819f3edc948143a41f4cd7046c8/tests/integration/backend/test_execution_currency_preview_postgres.py).

**Navigationsgrenze UX-2:** `tradeWorkspaceLink(view, tradeId, from, hash)`
unterstützt `management`, `sources`, `journal` und nutzt `getAll` für historische
Pins sowie `preserveClosedContext`. Mehrdeutige Pins bleiben zur späteren
Zurückweisung erhalten. Beim Abschnittswechsel desselben Owners bleibt die
ursprüngliche unterstützte Query unverändert; Hashwechsel allein remounten die
Quellenansicht nicht. Bei einem bewusst ausgewählten anderen Trade entfernt der
Post-Trade-Owner alte Journal-/Reviewpins. Lessonlinks erhalten die exakte
Lessonversion und einen geprüften Rückkehrbereich.

Die neuen Ziele sind `#trade-overview`, `#position-price-history`,
`#execution-dates`, `#trade-risk`, `#trade-plan-sources`, `#trade-journal` und
zusätzliche Quellen-/Managementanker. Sie werden nur als **PR-Vertrag** genannt,
nicht als heute in Main verfügbare UX-3-Ziele. Eine direkte Planversionsverknüpfung
öffnet im UX-2-Diff einen neuen Tab; Beschriftung und Fokusverhalten bleiben beim
Navigationsowner. Noch fehlende exakte Ziele werden dadurch nicht vorgetäuscht.

Codebelege am UX-2-Head:
[Builder](https://github.com/burckhju/trading-workspace/blob/6782bc7a567ce24d480e3e7996f919399f28896f/frontend/src/features/trade/services/workspaceNavigation.ts),
[Abschnittsnavigation](https://github.com/burckhju/trading-workspace/blob/6782bc7a567ce24d480e3e7996f919399f28896f/frontend/src/features/trade/components/TradeWorkspaceNavigation.tsx),
[Quellenansicht](https://github.com/burckhju/trading-workspace/blob/6782bc7a567ce24d480e3e7996f919399f28896f/frontend/src/features/trade/components/TradeSourcesView.tsx),
[Buildertests](https://github.com/burckhju/trading-workspace/blob/6782bc7a567ce24d480e3e7996f919399f28896f/frontend/src/features/trade/services/workspaceNavigation.test.ts),
[Browserweg](https://github.com/burckhju/trading-workspace/blob/6782bc7a567ce24d480e3e7996f919399f28896f/tests/e2e/trade-workspace-navigation.spec.ts).

Beim CI-Snapshot der genannten Heads war bei #312
[`Frontend / quality`](https://github.com/burckhju/trading-workspace/actions/runs/41203796168/job/124544681820)
fehlgeschlagen und bei #311
[`End-to-End / journal and evidence owner`](https://github.com/burckhju/trading-workspace/actions/runs/41203752901/job/124544558258); weitere
Jobs liefen noch. Das ist keine Ursachenanalyse dieser fremden Änderungen und
keine Aussage über spätere Heads. Beide werden hier weder als vollständig
qualifiziert noch als Main-Bestandteil behandelt. UX-3 verändert keine fremden
Branches, Checks oder PR-Zustände.

## 3. Vorgeschlagene gemeinsame Schnittstellen

Die [TypeScript-Verträge](contracts.ts) bilden das eine konsolidierte
Dokumentationstypmodell. Die folgenden Übergaben präzisieren die verbindlichen
Ownergrenzen; sie behaupten keine bereits implementierten öffentlichen Produkt-APIs.
Zusätzliche Domainfelder entstehen nur in einem
gesondert abgestimmten Ownerschnitt, wenn der bestehende Read sie nicht liefert.

| Übergabe | Lieferant → Verbraucher | Benötigter Inhalt | Gültigkeit / noch abzustimmen |
| --- | --- | --- | --- |
| Qualifizierte Fachfakten | Domain-Owner → Feature-Adapter | Unveränderte DTOs, konkrete Codes, Wirkung/Usability, Objekt-/Quellversionen und bekannte Zeitpunkte | Keine neue Feldableitung oder Freitextheuristik. Bei nicht gelieferter Ursache bleibt die Diagnose begrenzt. |
| Eingabe-/Quellenbedarf | UX-1 + Domain-Owner → Feature-Adapter | Bestehendes Resolverergebnis, vorhandene Evidence, bereits automatisch gelöste Voraussetzung und tatsächlich verbleibende Nutzerentscheidung | Hinweise übernehmen z. B. `ExecutionCurrencyResolution`; sie verlangen keine erneute Bestätigung einer belegten Währung. Quellenprüfung und Freigabe sind unterschiedliche Tatsachen. |
| Validierter Ansichtskontext | UX-2/Feature-Host → Adapter und Präsentation | Workspace aus Requestkontext, Objekt/Version, lokaler Besuch bzw. Requestgeneration; bei Reports Definition, Filter und `basis.id` | A→B→A ist ein neuer Besuch. Veraltete Notice, Details, Aktion und Erfolg werden gemeinsam invalidiert. Kein globaler zuletzt geladener Trade. |
| Sicheres Leseziel | UX-2/Navigation-Owner → Kontextaktion | Bereits vorhandene Route, exakte Objekt-/Versionspins, verständlicher Linktext, ggf. bestehender Bereichsanker | Vorhandene Validatoren weiterverwenden. Fehlende Zeilen-/Governanceziele bleiben explizite Integrationslücken, keine erfundenen URLs. |
| Hinweispräsentation | Feature-Adapter → UX-3-Komponenten | Identität, Art, Ursache/Wirkung, begründete Priorität, Provenienz, automatische Lösung, Nutzerbedarf und Behebungsnachweis | Komponenten zeigen Fakten. Sie bestimmen keine Finanz-/Risikologik und lösen weder beim Mounten noch beim Aufklappen einen Command aus. |
| Übergang zu bewusster Änderung | UX-3-Kontextaktion → bestehender Domainworkflow | Ziel auf vorhandenen Editor/Review samt geprüfter Identität; Schreibabsicht klar erkennbar | Öffnen ist lesend. Tatsächlicher Write behält bestehende Bestätigung, Versionspins, Idempotenz und Navigation-Guard. Kein generischer zentraler Schreibcallback. |
| Lokale Zusammenfassung | Fachadapter/UX-3 → UX-2-Host | Zusammengefasste gleiche Ursachen, betroffene eindeutige Objekte und Detailsverweise | Nur Präsentation deduplizieren. Persistierte Alerts, Outbox, Quittierung und globale Aufgabenpriorität bleiben beim bisherigen Owner. |

Für historische Währungsbelege existiert heute der sichere Link
`/trade-management?trade_id=…#execution-dates`, etwa in
[RealizedGrossSources](../../../frontend/src/features/performance/components/RealizedGrossSources.tsx).
Er führt zum Buchungsbereich des richtigen Trades. Er fokussiert **keine einzelne
Ausführung**. Ein `execution_id`-Deep-Link oder direkter Evidenceeditor-Aufruf
wird hier nicht als vorhanden behauptet. Bis zur UX-2-Abstimmung nennt die Karte
die betroffene Ausführung fachlich und bezeichnet den Link entsprechend als
„Buchungen und Währungsbelege im Trade prüfen“.

Für Review-/Journalquellen bleibt
[sourceLink](../../../frontend/src/features/trade/services/sourceView.ts)
maßgeblich; für Produktpflege
[selectionRepairUrl](../../../frontend/src/features/product/services/selectionRepairContext.ts).
Quellreferenzen dürfen nicht als beliebige externe URL ausgeführt werden. Ein
genauer Versionslink wird nur aus den dafür geprüften Ownerreferenzen gebildet.

## 3a. Nachweis der Pflichtübernahmen aus #315

Quelle ist der [vollständig gebundene #315-Vertrag](https://github.com/burckhju/trading-workspace/blob/d9d85f1af3159c4356c8773d076decbf1dc604e4/docs/ui/ux3-notice-contract.md).
Die [Detailinventur](detail-inventory.md) bewahrt seine Herkunfts-IDs, während
[inventory.md](inventory.md#herkunft-und-zuordnung-der-detailbelege) die Zuordnung
zum Hauptkatalog führt. Kein zweiter Normvertrag und kein zweites Aufgabenprogramm.

| Pflichtübernahme / Quell-IDs | Kanonischer Ort und überprüfbarer Nachweis |
| --- | --- |
| Vertrag §§2–3/6.3; T04–T07, C06–C08, JL03–JL06/JL10, MG08–MG10 | Vertrag §§2/5; diskriminierter `SubjectRef`, Owner-Writeklassifikation, getrennte Governance-Reads in contracts.ts; TC-39/40/53–55/60 und Typgegenfälle. |
| Vier Typpräzisierungen einschließlich Finanzpopulation | Ein contracts.ts und contracts.type-test.ts; [Typmatrix](test-and-acceptance.md#5c-typnachweise-und-ihre-runtimegrenze). Realized-/Closed-DTOs und Ownervalidatoren bleiben getrennt; keine neue Domainengine. |
| §7.2, P02–P08 | Vertrag §6; TC-01/05/08/09/35/58/59 sichern monetären Ownerbeleg, EXCLUDED+Reason, echten BUY-Bezug statt Prefix, unterschiedliche Populationen und unveränderte Identität trotz Basis/Remount. |
| §8, M06–M07, JL07–JL13 | Vertrag §6; TC-12/14/16/17/29/51/56 trennen Source-Recovery, Alertabschluss, Invalidierung, EXITED, Storno, Vollabschluss, Delivery und Lessoncurrentness. |
| Q12 / B2 | Vertrag §8; TC-49 und F4/B2 für unbelegte Staleness-/Referenzkurstexte, ohne neue Geldqualifikation. |
| M02/M06 / B3 | Vertrag §6; TC-50/51 und eigener F4/B3-Schnitt für Healthteilfehler, belegte Nichtanwendbarkeit und grundtreue Alertinvalidierung. |
| TP05–TP07 / B4 | Vertrag §8; TC-52 und eigenständiger F6/B4-Schnitt für fehlende/ungeklärte Kaufstatusfelder, ohne Planfreigabe-/Updatebehauptung. |
| M01/M04–M11, MG01–MG11 | Komponenten §3, Vertrag §§5/6; TC-30/55/57/63/64 für Read-/Writewirkung, unabhängige Health-/Risiko-/IV-/Attentiongrenzen, Candidate-Gesamtguard, CONTRADICTS und getrennte Approval/Runtime. |
| Quellenregister, 48/24 Abnahmefälle, B/C/D | Bestehende TC-01–48 erhalten, TC-49–64 schließen Präzisierungslücken. [A01–A24-Crosswalk](test-and-acceptance.md#5b-vollständige-zuordnung-der-24-fälle-aus-315) und genau ein F1–F8-Rollout unten. Keine addierte Anzahl unabhängiger fertiger Tests. |
| Backlog-/Workspace-Verweise | Nur kanonischer Dokumenteinstieg und korrekte Nachweisgrenzen; Product Backlog bleibt einzige Arbeitsstatusquelle. Dokumentintegration ist kein Produkt-/Fachabschluss. |

## 4. Offene fachliche und technische Entscheidungen

Die Fälle sind unterscheidbar: ein bestehender Domainvertrag muss korrekt
dargestellt werden; eine fehlende fachliche Aussage darf UX-3 nicht erfinden.
„Offen“ bedeutet im folgenden Abschnitt fehlende Ownerabstimmung, nicht eine
pauschale Aufforderung an Endnutzer, Daten zu ergänzen.

### O1 — Unqualifizierte Positionszahlen

[PositionResponse](../../../frontend/src/features/trade/types/api.ts) und die
[Backend-Antwort](../../../backend/app/features/trade_position/api/dtos.py)
enthalten `cost_basis`, `average_entry_price` und `realized_gross_pnl` ohne eigene
Währungsqualifikation. Demgegenüber führen `PositionValuationBasis` und
`ProductPositionValuationResponse` bereits Währungsevidenz und konkrete
Verwendbarkeitsaussagen. Die Inventur zeigt rohe Zahlen in Trade-/Positionsansichten.

**Zu entscheiden:** Der Trade-Position-/Performance-Owner und UX-2 legen fest,
welche bestehenden qualifizierten Read-Modelle jede Zahl tragen und wie ein nicht
belegbarer Wert dargestellt wird. Falls eine fachliche Qualifikation für einen
Wert noch fehlt, muss der Owner sie liefern oder den Wert ausdrücklich als
nicht qualifiziert kennzeichnen. Ein allgemeines `currency_status=KNOWN` beweist
nicht ohne passenden Ownervertrag die Berechenbarkeit sämtlicher historischer
G/V-Werte. UX-3 setzt weder rohe Beträge eigenständig auf null noch ergänzt es
eine Ersatzrechnung oder eine Währung aus dem aktuellen Produktlisting. Der
Währungspilot unten verändert keine Positionszahlen.

### O2 — Genaue Ursachen bei groben Fehlercodes

Die vorhandenen Übersetzer für
[TradePlan](../../../backend/app/features/trade_plan/api/errors.py),
[Produktauswahl](../../../backend/app/features/product_selection/api/errors.py)
und [ModelGovernance](../../../backend/app/features/model/api/errors.py) liefern
teilweise nur NOT_FOUND/CONFLICT/VALIDATION_ERROR. Stornoblocker sind zudem eine
Freitextliste, obwohl `can_cancel=false` die konkrete Aktionssperre belegt.

**Zu entscheiden:** Ob der jeweilige Owner für tatsächlich erforderliche
Unterscheidungen additive strukturierte Ursachen bereitstellt. Bis dahin zeigt
UX-3 den bekannten Vorgang, seine belegte Einschränkung und den Originalfehler in
Details. Weder HTTP 409 noch Wörter wie „missing“, „stale“ oder „failed“ beweisen
allein eine bestimmte Fachursache oder Schwere. Eine vorhandene konkrete
`ApplicationError.code`-Unterscheidung wird erhalten, nicht pauschal verworfen.

### O3 — Öffentlicher Zugang zur Refreshdiagnostik

`RefreshCheck`/`RefreshStatus` sind derzeit lokale Typen in
[MarketDataRefreshPanel](../../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx).
Coverage besitzt weitere private Typen. Der vorhandene
[`GET /market-data/refresh/status`](../../../backend/app/features/market_data/api/router.py)
liefert ein `dict[str, object]`. Ein zweiter UX-3-Typ mit kopierten Statuslisten
wäre kein belastbarer gemeinsam verantworteter Vertrag.

**Zu entscheiden:** Market Data und UX-2 vereinbaren einen zugänglichen Read-Typ
bzw. ein geprüftes Adapterinterface auf Basis exakt dieser Payload, einschließlich
älterer/teilweise fehlender Felder. Das ist eine eigene begrenzte Vorbereitung
vor Wiederverwendung. `qualified_success`, `recovered_at`, laufende Fehlerfolge,
`observed_in_latest_run`, `identity_key`, `quote_usable`, Retention und Zeitpunkte
bleiben Ownerfakten. Fehlende Felder werden nicht zu false/0/„wiederhergestellt“
umgedeutet. Prozesslokaler Verlust und ein Recoveryzeitpunkt aus einem älteren
Snapshot dürfen keine Entwarnung erzeugen. Der aktuelle Owner setzt `recovered_at`
bei einem neuen echten Fehler zurück. Die Komponente berechnet keine Recovery.
Diese Vorbereitung betrifft Refreshdiagnostik; sie blockiert nicht pauschal
den getrennten F4/B3-Schnitt mit bereits vorhandenen Alert-/Health-DTOs.

### O4 — Exakte Navigation und Fokus

**Zu entscheiden:** UX-2 definiert bei Bedarf den gezielten Ausführungs-/Evidence-
Fokus sowie einen sicheren Governancekontext für direkte Verweise. Für die
erste Umsetzung genügen tatsächlich vorhandene Trade-/Versionsziele mit ehrlicher
Beschriftung. Die technisch ungesicherte Auswahl einer anderen Version oder
eines anderen Trades ist kein zulässiger Navigationsfallback.

### O5 — Notwendige Entscheidung versus optionaler Folgeschritt

**Zu entscheiden:** Eine zusätzliche fachliche Pflicht, etwa Journalabschluss,
Review oder Aktivierung nach einem normalen Lifecyclezustand, benötigt einen
ausdrücklichen Ownervertrag. `is_closed`, ein DRAFT oder eine genehmigte, noch
nicht aktive Version begründen allein keine solche Pflicht. Fehlende optionale
Risikonotizen sind ebenfalls keine belegte neue Freigabesicherung. Bis zu einer
anderen begründeten Fachentscheidung bleiben diese Schritte optionale Aktionen.

### O6 — Keine neue Entscheidung bei bereits klarer Semantik

Die folgenden Schutzgrenzen stehen schon fest und werden nicht als offene
Geschmacksfrage behandelt: `NOT_EVALUABLE` bleibt in der Produktauswahl mit
expliziter Begründung wählbar; `INELIGIBLE` bleibt gesperrt. Ein nach bestehender
Sitzungspolicy verwendbarer `LAST_AVAILABLE`-Kurs ist nicht pauschal `STALE`.
Historische Versionen bleiben gebunden. Unbekannte Geldwerte werden nicht zur Zahl 0. Der [Vertrag aus #309](../../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md)
aktiviert keine Hebeltrader-Regeln. Seine historischen Schwellen werden nicht als
neue allgemeine Hinweisgrenzen übernommen.

## 5. Begrenzte Folge-PRs und Abhängigkeiten

UX3-F1 bis UX3-F8 sind **lokale Planungskürzel**, keine angelegten Issues.
F1/B1 liegt als begrenzter Produktdiff in #320 vor; die übrigen Schnitte bleiben
getrennte Aufträge. Jeder Schnitt erhält einen eigenen
prüfbaren Diff und wird auf den dann tatsächlichen Main-Stand abgeglichen. Die
Frontend-/Backend-/E2E-Gates des Repositorys bleiben unverändert; gezielte Tests
ergänzen sie und ersetzen sie nicht. Ein grüner früherer Head qualifiziert keinen
neueren Änderungssatz. Die Umsetzung und technische Qualifikation des Piloten
ersetzen keine fachliche Abnahme oder Freigabe zusätzlicher Folgeumfänge.

| Schnitt | Enger Umfang und Abhängigkeit | Konkrete Prüfung / Abnahmekriterium | Grenze |
| --- | --- | --- | --- |
| **UX3-F1 / B1 — Genau ein lesender Währungspilot** | Nach qualifiziertem UX3-K und am tatsächlich integrierten UX1/UX2-Gesamtstand: reiner Adapter auf bereits gelieferte gespeicherte `ExecutionCurrencyResolution`, kompakte Karte, Details und vorhandener Buchungslink in genau `RealizedGrossSources`. Konkreten Diff mit Performance, UX1 und UX2 abgrenzen. | Passende Fälle aus TC-01–09, TC-33/35/41/44–48/58/59: Ownerqualifikation, automatische Herkunft ohne Pflichtbestätigung, null zusätzliche Reads/Writes, vollständige Basisbindung, keine neue Warnung durch Remount, unabhängige Ursachen, sichere Links, Tastatur/Screenreader/320–1280 px. TC-60/61 nur soweit der konkrete Pilot solche Zustände zeigt; keine fremde Writeworkflowprüfung vorziehen. | Kein Preview als Executionbeleg, kein Formular-/Hostumbau, neuer Resolver oder heutiges Listing als historische Quelle; kein globaler Store und kein globaler Austausch von `ExecutionCurrencySources`. |
| UX3-F2 — Fachlich qualifizierte Positionsanzeige | Erst nach O1: einen betroffenen Zahlen-/Hinweisbereich an ein vom Finanz-Owner verantwortetes Read-Modell anbinden; mit UX-2 konkrete Fläche festlegen. | Unbekannte Währung, gemischte Quellen, echter Nullbetrag und korrigierte Historie; Geldwert und Erklärung beziehen sich auf denselben Basisstand. Owner-Berechnungs- und API-Tests plus betroffene UI-Regression. | Keine Frontend-Kostenbasis-/G/V-Rechnung; ein eventuell nötiger Domainvertrag wird gesondert reviewed. |
| UX3-F3 — Refresh-Lesevertrag zugänglich machen | Nach O3: vorhandenen Diagnose-Payload-Typ unter Market-Data-Verantwortung zugänglich machen bzw. typisieren. Noch keine breite Darstellungsumstellung. | Bestehende Payloads und ältere optionale Felder, JOB/SOURCE-Identität, `PROCESS_LOCAL`, Retention und Recovery unverändert; vorhandene Diagnose-/Qualitätstests. | Keine zusätzlichen Zustände, API-Writes, Provideraufrufe, Retryzeiten oder neuen Recoveryregeln. |
| UX3-F4 — Getrennte Kurs-/Monitoringdarstellungsschnitte | **B2 separat:** Q12 in `ProductValuationPanel`/`PositionDetails`, falsche Auffangursachen korrigieren. **B3 separat:** M02/M06 in `TradeAlertsPanel`, Healthteilfehler/Nichtanwendbarkeit/Invalidierungsgrund. Weitere Source-Recoveryfläche erst bei Bedarf nach F3; vorhandene Alert-/Health-DTOs brauchen F3 nicht. | B2: TC-49 und vorhandene Bewertungsregressionen. B3: TC-50/51, Health-/Alertregressionen. Spätere Kursfläche: TC-10–18, andere Quelle, Throttling, passende Episode und Neustart. Jeder Teilschnitt eigener PR mit konkreter Ownerfläche. | Textkorrektur ist keine F2-Finanzqualifikation. Keine eigene Frische-/Recoveryberechnung, globale Sortierungsänderung oder Umstellung sämtlicher Alert-/Coverageflächen. |
| UX3-F5 — Ein Performance-Zusammenhang | Nach F1: eine Berichtsart verknüpft kompakten Datenlückenhinweis mit betroffenen Einzelbeiträgen; bestehenden Quellenabschnitt wiederverwenden. | PARTIAL/NOT_COMPUTABLE/EMPTY, bekannte Teilsumme versus vollständige Summe, anderer Filter/Zeitzone/Definition, geänderte `basis.id`, verspäteter Read; keine mehrfach gezählte gleiche Ursache. | Zweite Berichtsart erst gesondert; kein Finanzalgorithmus und keine vereinheitlichte Grundgesamtheit. |
| UX3-F6 — Getrennte Kaufstatus-/Plan-/Auswahlfälle | **B4 separat:** TP05–TP07 in `PlanPurchaseStatus`, fehlende/ungeklärte Felder erklären. Ein anderer kleiner PR adaptiert eine konkrete historische Plan-/Produktauswahlsituation mit abgestimmtem Versionsziel. | B4: TC-52 und PlanPurchaseStatus-Regressionsfälle. Historie/Auswahl: TC-19–23/38/62, kein Latest-Fallback, ältere APPROVED-Version erhalten, INELIGIBLE versus begründet wählbares NOT_EVALUABLE, rungebundene Reparatur. | Kaufstatuskorrektur ist keine Planfreigabe oder zweite Gesamtmigration. Keine Formulare, Auswahlregeln oder Product-Admin-Layouts umbauen. |
| UX3-F7 — Jeweils ein Quellen-/Review-/Governanceadapter | Nach F1 und O4 nur für das betroffene Ziel: ein bestehender Reader-/Editorzugang mit historischen Pins. Journal, Lesson-Create/Review und Governance in getrennten konkreten PRs statt einer generischen Errorumstellung. | TC-24–31/39/40/53–57/60/64 nach tatsächlichem Scope: zulässiger Draft-SAVE, drei Currentnessachsen, Journal503-Unknown/identischer Retry, kein Create-Replay, Receipt+Readback, getrennte Governance-Reads und Candidate-Gesamtguard. | NoticeAction bleibt Navigation. Readbutton/Verwerfen/Command beim bisherigen Owner, keine neue Retryengine, automatische Evidence/Lesson/Reviewentscheidung oder Modellaktivierung. |
| UX3-F8 — Lokale Priorisierung, dann Redundanz, dann Recovery | Nach abgenommenen Einzeladaptern mit UX2 genau eine lokale Hostfläche. **D1:** scopebegrenzte Reihenfolge. **D2:** belegte doppelte Currency-/Statistikhinweise. **D3:** Quellen-/Versions-/Episodenbindung und Recovery. Jeweils kleiner getrennter PR. | TC-12/14/17/35/41/42/47/51/58/59/63: kritischer Alert bleibt sichtbar, erlaubter Verkauf erreichbar, echte BUY-Ursache, kein Populationsmix, Remount stumm, Erstread keine Neuheit, neue Episode nicht durch Timer unterdrückt; genau ein Ansagehost. | Keine persistierten ack/dismiss/resolved-Datensätze, keine Alertquittierung, neue Workspaceprojektion oder Finanzrechnung. Globale ACTION/REVIEW/BLOCKED-Reihenfolge bleibt bestehen. |

F2 und F3 sind durch verschiedene Ownerentscheidungen begrenzt; ihr Beginn folgt
nicht automatisch aus F1. Die späteren Gruppen F6/F7 sind jeweils auf eine
konkrete Situation beschränkt. Ein PR nimmt nicht sämtliche dort erwähnten
Fehlercodes oder Verbraucher gleichzeitig auf.

Die C-Aufträge aus #315 werden innerhalb dieser F-Schnitte geführt, nicht als
zweite Migration:

| Herkunft | Einziger Umsetzungsauftrag |
| --- | --- |
| C1 — Vorhandene genaue Ziele | Im jeweils betroffenen F1/F6/F7-Schnitt die qualifizierten UX2-Helper beziehungsweise Ownerprops verwenden; Trade-/Plan-/Run-/Analyse-/Journal-/Lessonpins und vorhandene rungebundene Warrantreparatur erhalten. |
| C2 — Fehlende Zielpräzision | O4 separat entscheiden: exakter Execution-/Incidentfokus oder Warrant ohne belegten Auswahlrun. Consumer, Parameter, echte Identität und fehlendes Ziel vor Produktänderung benennen; kein erfundener Routerparameter. |
| C3 — Bewusste Owneraktionen | Im betroffenen F-Schnitt Navigation zum bestehenden Reader/Editor/Command-Owner; Links führen keinen Readcallback, kein Verwerfen und keinen Write aus. Verschiedene Retrygarantien und bestätigte Receipts bleiben erhalten. |

Die vollständige Übergabe jedes Produktschnitts nennt Ausgangs-SHA, Datei-/Ownerliste,
konkreten Producer/Consumer, erlaubten Umfang und ausgewählte TC-Fälle. Danach
folgen tatsächlicher Head, Testmerge/Tree, Diff und CI-Run-/Jobbelege. Kein neuer
Aufgabenstatus- oder Lockkatalog neben dem Product Backlog.

## 6. Gemeinsame Test- und Abnahmebedingungen

Für jeden implementierten Schnitt gelten die im
[Test- und Abnahmekonzept](test-and-acceptance.md) beschriebenen Positiv- und
Negativfälle. Die Prüfung umfasst drei voneinander getrennte Nachweise:

1. **Ownervertrag:** Fachfakten, Quellenqualifikation, Versionen und Nullsemantik
   sind unverändert. Vorhandene Regressionen werden weiterverwendet, insbesondere
   [historische Währungsauflösung](../../../tests/unit/backend/features/trade_position/test_historical_currency_resolution.py),
   [historische Währungsberichte](../../../tests/unit/backend/features/performance/test_historical_currency_reports.py),
   [Refreshdiagnostik](../../../tests/unit/backend/features/market_data/test_refresh_diagnostics.py)
   und [Kursqualifikation](../../../tests/unit/backend/features/market_data/test_refresh_quality_diagnostics.py).
2. **Adapter und Interaktion:** Bekannte Fakten erzeugen genau die belegte
   Meldung/Handlung; unbekannte Codes erzeugen keine erfundene Diagnose. Rendern,
   Aufklappen und Navigation senden keine Schreibbefehle. Bestehende Guards,
   Receipts und explizite Bestätigungen bleiben beim Fachbereich. Die vorhandenen
   [Trade-Kontexttests](../../../frontend/src/features/trade/pages/TradeManagementContext.test.tsx)
   und [Performance-Kontexttests](../../../frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx)
   werden um den tatsächlich integrierten Hinweis ergänzt, nicht durch reine
   Snapshottexte ersetzt.
3. **Darstellung und Freigabe:** Auf kleinem Bildschirm bleiben Hauptaussage und
   Aktion bedienbar. Tastatur, Fokus, verständliche Statusänderungen und fehlende
   Doppelankündigungen werden an der konkreten Komponente geprüft. Erst danach
   fachliche Prüfung durch den zuständigen Owner und gesonderte UI-Abnahme; ein
   TypeScript-Check oder grüner CI-Lauf allein ist keine fachliche Freigabe.

Backend-Coverage bleibt bei 85 %, Frontend Lines/Functions/Statements bei 80 %
und Branches bei 70 % gemäß den verlinkten Workflows in der [Übersicht](README.md).
Es werden keine Tests deaktiviert, Coveragegrenzen gesenkt oder vollständige
Gate-Erfolge aus Teiltests abgeleitet. Das historische UX3-K-Prüfprotokoll und
seine 42 Typgegenfälle qualifizieren den Dokumentvertrag. Sie prüfen nicht
unmittelbar die schmalen produktiven `NoticeView`-Props. Aktuelle B1-Produktbelege
stehen getrennt in der Pilotqualifikation und am tatsächlichen PR-/Testmerge-Head.

## 7. Wichtigster nächster Umsetzungsschritt

**PositionDetails ist umgesetzt und integriert; nächster Produktschnitt ist
UX3-B3/F4, zunächst nur M06 in `TradeAlertsPanel`.** B1/F1 aus #320 bleibt über
#323/v1.5.38 veröffentlicht. Die erste Q12-Fläche `ProductValuationPanel` aus
[#324](https://github.com/burckhju/trading-workspace/pull/324) ist im separaten
Release #328/v1.5.39 auf `14913454ddecd1a9559639ec19d7373cf5269e90` enthalten;
dieser Tag enthält auch den zuvor integrierten UX4-B-Stand aus #322.

Die zweite Q12-Fläche `PositionDetails` wurde am **05.11.2026** mit
[#326](https://github.com/burckhju/trading-workspace/pull/326) integriert:
Main `a68b3a928129b42b19dc2a6de07be1bf7c91a811`, Produkt-Head
`cd469037656dff05c6deb6704a94d371adeeb95a`, Testmerge
`c5cc04d8c532cd2d2d5c18a632ae715564aeffd1`, gemeinsamer Tree
`5e71e12af4d8fb1a10d074c7ec9c30079988c4d9`. Alle neun regulären Produktjobs sind
für diesen Testmerge erfolgreich; die Quellen und der aufgelöste TC-49-Punkt stehen
in [Abnahmeabschnitt 10](test-and-acceptance.md#10-b2f4--q12-in-positiondetails).
`STALE` bleibt positiver Veraltungsbeleg, `LAST_AVAILABLE` mit mehrdeutigem
OUTDATED-Code neutral. Es fehlen dafür keine zusätzlich zu erfindenden Ownerflags.
Der bislang veröffentlichte v1.5.39-Tag enthält #326 noch nicht; der getrennte
Release-/Dokumentationsschnitt v1.5.40 benötigt eigene CI- und Main-Push-/Tagbelege.
Eine tatsächliche PC-Installation oder gesonderte menschliche Abnahme wird nicht
behauptet. Die historische Draft-only-Grenze vom 03.11.2026 erweitert sich durch
die Fortsetzung vom 05.11.2026 unter der bestehenden ausdrücklichen Freigabe
„wenn grün mergen und für den PC bereitstellen“; sie ist kein aktuelles Mergeverbot.

Die beiden genannten Q12-Textkorrekturen sind damit technisch integriert; daraus
folgt kein pauschaler Abschluss aller B2-/F4-/UX3-Abnahmen. Der
[Product Backlog](../../planning/PRODUCT_BACKLOG.md#operational-workspace) bleibt
Arbeitsstatusowner. F2-Finanzqualifikation, B3/B4/C/D und die gesonderten
menschlichen Abnahmen bleiben getrennt.

Für den kleinsten folgenden B3-Schnitt sind die Ownerfakten bereits vorhanden:
[TradeAlertsPanel](../../../frontend/src/features/alert/components/TradeAlertsPanel.tsx)
erklärt derzeit jeden `invalidation_reason` als ungeklärten Kursbezug.
[Legacy-Invalidierung](../../../backend/app/features/position_monitoring/service/legacy_alerts.py)
liefert `LEGACY_RULE_PRICE_BASIS_UNCONFIRMED`, der
[Risiko-Lifecycle](../../../backend/app/features/alert/service/risk_lifecycle.py)
liefert hingegen `RISK_CONFIGURATION_OR_IDENTITY_SUPERSEDED`.
[Alert-Read-Model](../../../backend/app/features/alert/service/read_models.py),
[API-Abbildung](../../../backend/app/features/alert/api/router.py) und
[AlertResponse](../../../frontend/src/features/alert/types/api.ts) erhalten diese
Gründe bereits. Für ihre verständliche Erklärung ist keine neue Domainentscheidung
oder Datenabfrage erforderlich.

Der am 05.11.2026 gelesene Parallelstand #325 (`555538fa...`, UX2-Host/Produktbewertung),
#327 (`2d134bcd...`, Performance) und #207 (`85921b9a...`, nur Workflow) ändert
weder `TradeAlertsPanel.tsx` noch dessen Test. Das ist ein begrenzter Dateiabgleich,
kein Integrationsnachweis dieser PRs; vor Beginn neu prüfen. Insbesondere der
UX2-Host aus #325 bleibt außerhalb des folgenden M06-Schnitts.
M02/TC-50 folgt separat: Der bestehende Health-Reader ist nur für offene Positionen
anwendbar, aber das Panel erhält derzeit nur `tradeId`. Weder HTTP 404 noch eine
leere Alertliste belegt einen Positionsabschluss. Der Startprompt implementiert
deshalb noch keine neue Health-/Anwendbarkeitsgrenze und keine B3-Gesamtmigration:

```text
Setze den ersten gesonderten UX3-B3/F4-Schnitt zu M06 in trading-workspace um:
nur ursachengetreue Invalidierungstexte im vorhandenen TradeAlertsPanel.
Prüfe zunächst aktuellen Main, #326-/Releaseintegration, kanonischen UX3-Vertrag,
Product Backlog sowie tatsächliche offene PR-Diffs, insbesondere #325/#327/#207.
Erhalte fremde Änderungen; vorhandene Arbeit am selben Schnitt weiterführen,
keinen konkurrierenden Auftrag oder zweiten Status-/Hinweisvertrag beginnen.

Prüfe frontend/src/features/alert/components/TradeAlertsPanel.tsx und .test.tsx,
frontend/src/features/alert/types/api.ts sowie die vorhandenen Ownerbelege:
backend/app/features/position_monitoring/service/legacy_alerts.py,
backend/app/features/alert/service/risk_lifecycle.py,
backend/app/features/alert/service/read_models.py und alert/api/router.py.
Der kanonische Bezug ist detail-inventory.md M06/M07 und TC-51; die vollständige
TC-51-Matrix wird nicht allein durch diese lokale Textkorrektur abgenommen.

Korrigiere den vorhandenen Invalidierungsabsatz nur aus geliefertem Alertstatus
und invalidation_reason: LEGACY_RULE_PRICE_BASIS_UNCONFIRMED erklärt den
unbestätigten historischen Regelkursbezug; RISK_CONFIGURATION_OR_IDENTITY_SUPERSEDED
erklärt die abgelöste Risikokonfiguration oder Identität, ohne eine der beiden
Alternativen zu erfinden. Unbekannter oder fehlender Grund bleibt begrenzt
erklärt; Originalcode bei Bedarf sekundär in vorhandenen/kleinen nativen Details.
Leite INVALIDATED nicht selbst aus Text oder Feldanwesenheit ab. OPEN, RESOLVED
und INVALIDATED bleiben Ownerzustände; Invalidierung ist keine Kurserholung,
kein Vollverkauf, Storno, Regel-EXITED, Quittieren oder Zustellerfolg.

Produktumfang zunächst genau TradeAlertsPanel.tsx mit lokalem reinem Textmapper
und den gezielten Fällen in TradeAlertsPanel.test.tsx. Benenne vor einer nötigen
Erweiterung die konkrete Datei-/Ownergrenze. Erhalte Alertgrund, ursprüngliche
Werte, Quellen-/Preisart-/Identitätsbezüge, Originalzeiten, Reihenfolge und Zähler.
Notification-/Deliveryzustände einschließlich unterdrücktem Versand bei
INVALIDATED + PENDING bleiben unabhängig; keine automatische Wiederzustellung.

Keine neuen Reads, Retrybuttons, Writes, Alertquittierung, DTO-/Statusmodelle,
Domain-/Provider-/Trading-/Freigabe-/Recoveryregeln oder gemeinsame Hinweisengine.
UX2-Host/Navigation, UX4-Historie und die abgeschlossenen Q12-Flächen unverändert
lassen. B1-NoticeCard nicht um eine unbelegte Aktion erweitern.
M02/TC-50-Healthteilfehler und Nichtanwendbarkeit separat belassen: 404 und leere
Alerts beweisen keine geschlossene Position; keine Health-Recovery erfinden.

Prüfe beide echten Invalidierungsgründe, unbekannten/fehlenden Grund, unveränderte
OPEN-/RESOLVED-Anzeige und Alert-/Deliverytrennung mit positiven und negativen
Assertions. Bewahre die vorhandenen TradeAlertsPanel-/Monitoringregressionen;
prüfe nur bei tatsächlicher Hostwirkung den bestehenden Browserpfad
tests/e2e/position-monitoring-health.spec.ts zusätzlich. Keine automatischen
Writes/Navigation oder neue Live-Ansage; native Details bei Bedarf per Tastatur
bedienbar, technische Referenzen sekundär. Keine künstlichen neuen Gatefälle.
Liefere einen kleinen eigenen PR mit aktuellem Head/Testmerge/Tree, regulären
CI-Nachweisen und ehrlich getrennten menschlichen Abnahmen. Bestehende Gates
beibehalten; keinen pauschalen Abschluss von B3/TC-51/F4 oder UX3 behaupten.
```
