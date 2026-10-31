# UX4-A — Diagramm- und Kennzahleninventur

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Codeinventur und Vertragsanalyse, 0.1 |
| Status | Draft; vorhandenen Code geprüft, keine neue Oberfläche implementiert |
| Prüfdatum | 31.10.2026, Europe/Vienna |
| Main / Git-Tag | `1883f7f330719453958f8be1dd51d48db816662e` / `v1.5.35` auf demselben Commit |
| Main-Tree | `e90aa341805c71362df1cda1a9dc378b0af9c4fe` |
| Versionsdateien | `VERSION`, Frontend und Backend jeweils `1.5.35` |
| Datenprüfung | Code, DTOs, Reader, ADRs und vorhandene Tests; keine Nutzer-Datenbank oder Liveprovider geprüft |

## Ergebnis und Leseweg

Main besitzt **zwei Diagrammrenderer**: den historischen Positionskurs als
`PositionPricePlot` und den EOD-Marktvergleich als `TimeSeriesChart`. Absolutkurs,
Basis 100 und Prozentänderung sind drei Modi desselben EOD-Renderers. Performance
besitzt bereits zwei qualifizierte Berichte sowie vier Abschlussstatistiken,
aber noch keinen Performancechart. Zahlreiche weitere Informationen erscheinen
als Kennzahlenkarten, Quellenlisten und Tabellen. Backendprojektionen ohne
produktiven Frontendverbraucher sind unten ausdrücklich getrennt ausgewiesen.

Die Inventur erfasst die Diagramme und zusammengehörigen numerischen Anzeigen
für Trading, Positionen, Performance, Datenqualität, Analyse-/Planquellen und
Nachbeobachtung. Technische IDs, Versionsnummern und Eingabefelder werden als
Provenienz bzw. Eingaben geführt, nicht als zusätzliche Performancekennzahlen.
Ein vorhandener Rechenkern beweist weder einen aktiven Datenpfad noch echte
Datenabdeckung oder fachliche Betriebsabnahme.

Der [Visualisierungsvertrag](ux4-visualization-contract.md) definiert die
gemeinsamen Schutzregeln. Die [Qualifikation](../implementation/UX4_A_QUALIFICATION.md)
enthält Prüfmethodik, vorhandene Testanker, noch auszuführende Abnahmetests und
die Grenze dieses Dokumentations-PRs. Eigenständige Folgeaufträge:
[UX4-B](ux4-b-position-price-history-prompt.md),
[UX4-C](ux4-c-performance-visualization-prompt.md),
[UX4-D](ux4-d-quality-lifecycle-prompt.md).

## Koordination und aktueller Integrationsstand

Gelesen wurden insbesondere [README](../../README.md),
[Product Backlog](../planning/PRODUCT_BACKLOG.md),
[Roadmap](../foundation/ROADMAP.md),
[Modul-/Featurekatalog](../planning/MODULE_AND_FEATURE_CATALOG.md),
[Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md),
[Backendarchitektur](../architecture/BACKEND_ARCHITECTURE.md),
[Development Guide](../technical/DEVELOPMENT_GUIDE.md),
[Teststrategie](../reference/TEST_STRATEGY.md) und die fachlichen Quellen unten.
Der Backlog bleibt die maßgebliche Arbeitsstatusquelle. Eine frühere
„nicht im ersten Schnitt“-Aussage in einem ADR ist kein Beleg, dass später
integrierte Funktionalität heute fehlt.

Die während der Analyse veröffentlichten Master-Dokumente wurden am exakten
Head `2312abfe8834a1b652b100fc635c4d36172d5c32` von Draft #313 gelesen:
[Masterplan](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_MASTER_PLAN.md),
[Ownership](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_OWNERSHIP.md),
[Shared Contracts](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_SHARED_CONTRACTS.md),
[Abhängigkeiten](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_DEPENDENCIES.md) und
[Integrationsprotokoll](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_INTEGRATION_STATUS.md).
Sie liegen noch außerhalb Main. Keine `AGENTS.md` im Checkout.
**Offener Integrationsnachweis:** konkrete UX-2-Slots, öffentliche Importgrenze,
Readback und gemeinsame Regression; ein verfügbarer Draftvertrag belegt keine
abgenommene Einbindung. Dieser Draft baut keine gemeinsamen Workspace-Komponenten.

| Parallelstand, getrennt von Main | Gelesener Nachweis | Bedeutung für UX4 |
| --- | --- | --- |
| [MASTER, Draft #313](https://github.com/burckhju/trading-workspace/pull/313), Head `2312abfe8834a1b652b100fc635c4d36172d5c32` | Fünf oben verlinkte Koordinationsdokumente | Ein Owner je Schnittstelle; Integration Koordination → UX2-A → UX1 → UX3 → UX4, unabhängige Komponentenqualifikation parallel. Keine Mergefreigabe. |
| [UX-1, Draft #312](https://github.com/burckhju/trading-workspace/pull/312), Head `8f67442daac6879d7dfb28416f2171f67aead0e5` | [Feldmatrix und Qualifikation](https://github.com/burckhju/trading-workspace/blob/8f67442daac6879d7dfb28416f2171f67aead0e5/docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md), inkrementelles Delta zum zuerst geprüften `74d29bb8…` gelesen | Historische Währungsherkunft, gespeicherte Runs und Zeitzonenvorschlag. Zeitfeedback/Testkontext korrigiert; keine eigene UX4-Währungsauflösung/Defaultzone. |
| [UX-2, Draft #311](https://github.com/burckhju/trading-workspace/pull/311), Head `79e9b97e31d3bf80936fb5c026798bf8ebb10b33` | [Arbeitsbereichs-/Navigationsvertrag](https://github.com/burckhju/trading-workspace/blob/79e9b97e31d3bf80936fb5c026798bf8ebb10b33/docs/ui/ux2-trade-workspace.md) | Bestehende Kurskomponente, getrennte Readowner, exakte historische Pins; TradeManagementPage und gemeinsame Einbindung gehören UX-2. |
| [UX-3, Draft #314](https://github.com/burckhju/trading-workspace/pull/314), Head `52a24266dce1ec048b23360b4b75d5b3f54d746b` | [Hinweisvertrag](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/notice-contract.md), [Komponenten-/Aktionsvertrag](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/components-and-actions.md), [Integration](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/integration-and-rollout.md) | Dokumentations-/API-Vorschlag, keine produktive gemeinsame Hinweisschicht. Qualitätssprache bei UX-3; fachliche Codes bei den Domains, Achsen/Lücken/Tabelle bei UX-4. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205), alter Historienvorschlag | [Aktueller Positionshistorienvertrag](position-price-history.md) | Vorschlagsstatus von #205 nicht mit Main verwechseln: Umsetzung #302 und Ergänzung #306 sind integriert. |
| [#220](https://github.com/burckhju/trading-workspace/pull/220), [#197](https://github.com/burckhju/trading-workspace/pull/197) | Offene Quellenforschung / Forschungsabruf | Kein produktiver Historienfeed, keine tatsächliche Providerabdeckung aus Forschungsplänen ableiten. |
| [#187](https://github.com/burckhju/trading-workspace/pull/187), [#207](https://github.com/burckhju/trading-workspace/pull/207) | Offene Hebeltrader-Arbeiten; integrierter [Monitoringvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md) separat | Kein Übernehmen offener Regeln oder behaupteter Implementierung. Dokumentierter Vertrag ist keine Runtimeaktivierung. |

Diese Heads sind eine überprüfte Momentaufnahme. Folgeaufträge lesen Main und
die tatsächlichen parallelen Heads erneut; keine gegenseitigen Feature-Branch-Merges.
Ein Repositorylink ist eine prüfbare Übergabe, kein Empfangs- oder Freigabenachweis
in getrennten Chats. Die [UX4-A-Qualifikation](../implementation/UX4_A_QUALIFICATION.md)
liefert den vom Master angeforderten eigenen Dokumentationsübergabebericht.

## Diagrammmatrix

**Leseschlüssel:** „Vorhanden“ bezieht sich auf den oben genannten Main.
„Neu darstellbar“ heißt vorhandene fachliche Daten, noch keine Grafik.
„API/Kern“ bedeutet keine vorhandene produktive Chartanzeige. Quellenkürzel
verlinken die maßgeblichen Implementierungen. FE = `frontend/src/features/`,
BE = `backend/app/features/`. Jede Tabelle enthält dieselben neun Vertragsfelder.

### Kurse, Analyse, Planung und Produktauswahl

| Diagramm | Benutzerziel | Datenquelle | Berechnungs-Owner | Datenqualität | Vorhandene Komponente | Empfohlene Änderung | Schutzregel | Abhängigkeit zu anderen UX-Strängen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I01 · Positionskurs, vorhanden | Belegte Optionsscheinpreise und Lücken lesen | `/api/v1/trade-position/trades/{id}/price-history`, Samples + Retention [S01] · [S02] | Market Data `QuoteHistoryReader.prices` / `read_price_series`; TradePosition-Kontext | Originalzeit, Serienidentität, Ausschlüsse und Budget; reale Abdeckung unbekannt | `PositionPriceHistory`, `PositionPricePlot`, `PositionPriceHistoryEvidence` [F01] | UX4-B: Quellenwahl/Legende, Belegzugriff, mobile Dichte | Scatter ohne Linien; keine FX, synthetischen Punkte oder Basiswert-Ersatzkurse | UX1 Währungsbelege; UX2 Einbindung; UX3 Qualitätswörter |
| I02 · BUY-/SELL-Marker, vorhanden | Erfasste Ausführung von Marktkurs unterscheiden | `price-history.events` [S01] | Bestehende effektive Execution-/Currency-Resolver, `compose_price_history` | Nur `plottable`; Date-only/ungeklärte Währung bleiben ohne Marker | Derselbe Plot und Ereignisliste [F01] | Marker und zugänglichen Ereignisbeleg eindeutig zuordnen | Keine Mitternachts-/Nearest-Quote-Marker; keine ersetzten Buchungen als aktuell | UX1 Herkunft; UX2 Buchungslinks; UX3 Ausschlussgründe |
| I03 · EOD-Absolutkurs, vorhanden | Preisniveau von Aktie/ETF oder Index prüfen | `/api/v1/market-charts/series`, `daily_prices` [S03] · [S04] | Analysis `prepare_series`, Market/MarketData-Reader | EOD-Datum; CLOSE/ADJUSTED_CLOSE, Konflikt-/Limitgründe | `MarketChartsPage`, `TimeSeriesChart` [F02] | Einheit/Preisfeld/Identität und Datenlücken gut sichtbar halten | Eine absolute Serie; Indexpunkte ≠ Währung; kein Adjusted→Close-Fallback | UX3 Labels; UX2 Navigationskontext |
| I04 · EOD Basis 100 / Prozent, vorhanden | Beschreibender Markt-/Sektor-/Aktienvergleich | Dieselbe Antwort mit `normalized`, `change_percent` [S03] | `TIME_SERIES_COMPARISON/1.0.0`, `compare_series` | Max. vier Serien; gemeinsame reale Start-/Endtage, Statusguard | Zwei Modi desselben `TimeSeriesChart` | Definition, Zeitraum und native Währungen näher an den Vergleich | Nur READY; kein FX/Depotreturn; keine lokale Normalisierung oder Füllwerte | UX3 Qualität; Fachowner bei Semantikänderung |
| I05 · Sektor-Abdeckungsmatrix, vorhanden | Fehlende Referenzen, Proxies und Historie finden | `/market-charts/catalog`, Underlying-Kontext [S04] | Market-Identitätsauflösung, `TimeSeriesReader.coverage` | Counts/min/max beweisen Speicherbestand, keinen Handelskalender | Tabelle in `MarketChartsPage` [F02] | Bestehende Tabellenform mit klaren Status-/Quellenlabels | Kein Ranking-/Coverage-Prozent aus Anzahl gespeicherter Zeilen | UX1 sichere Verknüpfung; UX3 Status |
| I06 · FT-006-Kennzahlen/Kriterien, vorhanden | Versionierte Analyse nachvollziehen | Gespeicherter Analysis-Run und Snapshot [S05] | `calculator`, `calculator_v1_0_1`, `indicators` | Modell/Parameter/Hash/Quellen vorhanden; Rohkeys ohne Einheitenlexikon | `MarketAnalysisDetailPage.MetricTable` [F03] | Versionsbezogene Einheiten und Definitionen ergänzen | Bruch, Prozent und Preis unterscheiden; keine SMA-Zeitserie aus einer Endkennzahl | UX1 Metadaten; UX3 Qualität; Analysis-Owner |
| I07 · Candidate-/Top-down-Kriterien, vorhanden | Markt/Sektor/Basiswertqualifikation verstehen | Konkrete Kandidatenevaluation + Sources [S06] | Candidate-Orchestration, `calculate_relative_strength`, Qualification | Klassifikation vorhanden, numerische RS-/Rankingserie nicht im UI-Vertrag | `CandidatePage.EvaluationDetail` [F04] | Kriterien und historische Quellen verständlicher verknüpfen | Keine Erfolgswahrscheinlichkeit; RS-Preisgrundlage nicht mit Chartgrundlage gleichsetzen | UX1 Links; UX2 Navigation; UX3 Status |
| I08 · Produktvergleich, vorhanden | Bewertete Produkte und Quotebelege vergleichen | Gespeicherter ProductSelection-Run/Evaluation [S07] | `ProductSelectionService._quote_metrics` | Availability, unit, formula, source; historischer Run ≠ aktueller Quote | `ProductSelectionPage.EvaluationCard` [F05] | Absoluten Spread und Spread auf Mid präzise benennen | Kein aktueller Preis aus historischem Run; kein Ranking aus Sortierreihenfolge | UX1 Run/Planbindung; UX3 Qualität |
| I09 · Planpreise/-risiko, vorhanden | Ursprüngliche Annahmen und Marken lesen | Exakte `TradePlanVersion` [S08] | TradePlan speichert/validiert Nutzerannahmen | Historische Planwährung/Version; Risikoannahmen sind Text | `TradePlanVersionContent`, `TradePlanProvenance` [F06] | Einheit und Quellenbindung konsistent halten | Kein Position-Sizing-/CRV-Rechner; keine Stop-/Zielübertragung auf Produktpreisachse | UX1 Eingaben; UX2 Planlink; UX3 Herkunft |
| I10 · Buchungs-/Projektionswerte, vorhanden | Menge, Einstand, Kostenbasis und Korrekturen prüfen | PositionProjector / Timeline [S09] | TradePosition Average Cost / effektive History | Rohprojektion ohne Reportwährungsqualifikation | `TradeManagementPage`, `ExecutionDatesPanel`, `TradeTimelinePanel` [F07] | Buchungswert und qualifiziertes Ergebnis sprachlich trennen | Nicht als Performance-/EUR-Ersatz verwenden; keine zweite Timeline | UX1 Currency-Owner; UX2 Buchungsowner; UX3 Hinweise |

### Positionen und Performance

| Diagramm | Benutzerziel | Datenquelle | Berechnungs-Owner | Datenqualität | Vorhandene Komponente | Empfohlene Änderung | Schutzregel | Abhängigkeit zu anderen UX-Strängen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I11 · Aktueller Marktwert / unrealisierter G/V, vorhanden | Offenen Bestand bewerten | ProductPositionValuation / OperationalPosition [S10] | `ProductPositionValuationService`, `PositionValuationBasis` | Quotequalität und BUY-Kostenwährung separat; indikativ/retained möglich | `ProductValuationPanel`, `PositionDetails`, `OpenPositionsPanel` [F08] | Qualität, Einheit und Ursache direkt am Wert; Dopplung mit UX2 abstimmen | Kein PnL ohne ausdrückliches usable; nicht zu realisiertem Ergebnis addieren | UX1 Belege; UX2 Einbindung; UX3 Warnung |
| I12 · Offene Bestandssummen je Währung, vorhanden | Umfang verfügbarer Bewertungen verstehen | Gesamte geladene offene Positionsliste [F09] | Bestehendes `portfolioTotals`, exakte BigInt-Darstellungsaggregation | Getrennte Marktwert-/PnL-Abdeckung; ältester/unklarer Zeitpunkt | Aufklappbare Summen in `OpenPositionsPanel` | Teilabdeckung eng am Betrag, klarer Gesamtbestandsbezug | Keine Mischwährungssumme, keine neue Equityhistorie, Filter verändert Summenpopulation nicht | UX2 Scope; UX3 Qualität |
| I13 · SELL-Summe / Teilsumme, vorhanden | Realisierte Bruttobeiträge des Zeitraums verstehen | `/api/v1/performance/realized-gross`, `summary` [S11] | PositionProjector + Performance `report.py` | COMPLETE/PARTIAL/NOT_COMPUTABLE/EMPTY | `RealizedGrossReportView` [F10] | Summe/Teilsumme/Grundgesamtheit klar staffeln | Keine fehlenden Werte als null Euro; Kosten/Steuern nicht künstlich null | UX1 fachliche Daten; UX2 Platz; UX3 Status |
| I14 · SELL-Beiträge über Zeit, neu darstellbar | Einzelbeiträge und ihre Quellen zeitlich finden | Bereits gelieferte `items`, Zeitpräzision, Quellen [S11] | Gelieferter `realized_gross_pnl_delta` | Nur USABLE monetär; Datumpräzision separat | Berichtsliste/Quellen vorhanden; noch kein Chart [F10] | UX4-C: einzelne unverbundene Beiträge mit Quellenliste | Keine Tages-/Monatssumme, Kumulation, Interpolation oder Mitternachtsannahme | UX1 nur bei zusätzlichem Vertrag; UX2 Einbindung; UX3 Gründe |
| I15 · Volltradeergebnis / Abschlusssumme, vorhanden | Vollständige abgeschlossene Trades vergleichen | `/api/v1/performance/closed-trades` [S12] | Derselbe Projector + `closed_report.py` | Alle benötigten BUY-/SELL-Belege des Lebenszeitverlaufs | `ClosedTradeSummary`, `ClosedTradesReportView` [F11] | Ergebnis pro Trade und Abschlusszeitbezug präzisieren; später Einzelbalken möglich | Ein Trade einmal; frühere Teilverkäufe bleiben enthalten, keine Rekonstruktion aus Perioden-SELLs | UX1 Geldherkunft; UX2 Berichtskontext; UX3 Qualität |
| I16 · Trefferquote / Ø / Median / Profit-Faktor, vorhanden | Vollständige Abschlusskohorte beschreiben | `closed-trades.statistics` [S13] | `closed_statistics.py` | Nur COMPLETE und N>0; PF ohne Verluste undefiniert | Vier Karten `ClosedTradeStatistics` [F12] | Kurze Definition je Karte, N und Nichtberechenbarkeit sichtbar | Kein Browserrechner; kein Teilbestandsersatz; neutral gehört in N | UX1 Ownerwerte; UX3 Gründe; UX2 Platz |
| I17 · Abschlussabdeckung / Vorzeichenzähler, vorhanden | Ausschlüsse und ungeklärte Fälle verstehen | `closed-trades.counts` [S12] | `_group` / `_counts` | Acht disjunkte Gruppen; Vorzeichen sind Untergruppen | `ClosedTradeSummary` [F11] | Direkte beschriftete Zählerbalken optional, Tabelle erhalten | Untergruppen nicht doppelt zählen; fehlend ≠ neutral; keine Erfolgsquote bei PARTIAL | UX3 Farbsprache/Begriffe |
| I18 · SELL-Abdeckung, vorhanden | Perioden-/Währungsprobleme erkennen | `realized-gross.counts`, Ausschlüsse [S11] | Performance `report.py` | Überlappende Klassifikationen; cancelled zählt Trades | `RealizedGrossReportView` [F10] | Jeweils eine definierte Sicht mit Einheit zeigen | Kein Kreis-/100-%-Diagramm aus allen Zählern; SELLs und Trades getrennt | UX3 Qualität; UX4-D keine doppelte Gesamtampel |
| I19 · Einzeltradeergebnis in Quellenansicht, vorhanden | Bericht und exakte Quellen abgleichen | Neuer qualifizierter Abschlussreport mit ursprünglichen Filtern [S12] | Bestehender Performance-Owner | Eigenes Lesefenster/Basis; nicht historischer Reportstore | `ClosedTradeResult`, `ClosedTradeSources` [F13] | Wiederverwenden, Rückweg und Belegdetails erhalten | Kein Rohpositions-PnL als Ersatz; Fingerprint ist kein historischer Zustand | UX2 Pins/Navigation; UX1 Herkunft |

### Qualität, Risiko und Lebenszyklus

| Diagramm | Benutzerziel | Datenquelle | Berechnungs-Owner | Datenqualität | Vorhandene Komponente | Empfohlene Änderung | Schutzregel | Abhängigkeit zu anderen UX-Strängen |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I20 · Quoteabdeckung gehaltener Produkte, vorhanden | Quellen-/Kursprobleme je Produkt prüfen | `/api/v1/market-data/warrants/quote-coverage` [S14] | `QuoteCoverageService`, gespeicherte Routes/Quotes | Produkte, nicht offene Positionen; kein Liveabruf | `QuoteCoveragePanel` [F14] | Mobile Quellendetails und Zeit-/Scopekennzeichnung | Kein neues pauschales Qualitätsranking; Filter ist keine Gesamtquote | UX2 Platz; UX3 Status |
| I21 · Gebundene Positionsquelle, API vorhanden | Exakte gewählte Quelle je Position prüfen | `/api/v1/market-data/positions/quote-coverage` [S15] | `PositionQuoteCoverageService` | Mapping-/Listing-/Identitätsbindung; überlappende Summary | Kein produktiver Frontendconsumer gefunden | UX4-D: später absolute Zähler/Liste im abgestimmten Slot | Frische Alternativroute heilt nicht gewählte Route; kein Summieren aller Felder | UX1 Projektion; UX2 Slot; UX3 Status |
| I22 · Refresh-/Providerdiagnosen, vorhanden | Laufende und abgeschlossene Versuche unterscheiden | `/market-data/refresh/status` [S16] | RefreshRuntime / Diagnostics / Quality | Fünf Lanes; tri-state; `PROCESS_LOCAL`, kein Uptimearchiv | `MarketDataRefreshPanel`, `RefreshDiagnostics` [F15] | Hierarchie/Scope/Zeiten lesbar erhalten | AVAILABLE-Lauf ≠ vollständiger Providererfolg; kein SLA-/Uptimechart | UX3 Diagnosehierarchie; UX2 Platz |
| I23 · Monitoringlauf / Regelprüfungen, vorhanden | Letzten Lauf und Tradechecks verstehen | `/position-monitoring/runtime/status` [S17] | Runner und vorhandene Evaluatoren | Globale letzte abgeschlossene Zähler, gefilterte Tradechecks | `MonitoringRuntimePanel` [F16] | Globalen Scope vs Tradefilter sichtbar halten | Fehlerzähler nicht zu betroffenen Positionen addieren; kein Orderstatus | UX2 Einbindung; UX3 Warnungen |
| I24 · Basiswertfrische / Alerts / Zustellung, vorhanden | Fachlichen Hinweis von Daten-/Zustellproblem trennen | Trade-Health plus Alert-/Notificationreader [S17] | Health-, Alert- und Notification-Owner | Health kann EODHD aufrufen; Update-/Abrufzeit kein exakter Sessionclose | `TradeAlertsPanel` [F17] | Preisachse, Zeitbedeutung und Statusdimensionen benennen | OPEN-Alert ≠ zugestellte Nachricht ≠ Ausführung; kein neuer Healthread durch Diagramm | UX1 Zeitbeleg; UX3 Warnhierarchie |
| I25 · Historisches Erfassungsprotokoll, vorhanden | Was wurde wann von welcher Route erfasst? | `/market-data/warrants/{id}/quote-history` [S18] | `QuoteHistoryReader.report`, Samplingpolicy | Erster Capture je 5-Minuten-UTC-Slot; Fehler enthalten; nur 50 Detailitems | `WarrantQuoteHistory` [F18] | Segmentzähler und begrenzte Details kompakt darstellen | Erfassungszeit ≠ Originalkurszeit; Coverage-% bleibt unbekannt; kein Ausfallkalender | UX4-B Quellenbegriffe; UX3 Status; UX2 Einbindung |
| I26 · Positionsrisiko / Trend / RV / ATR, vorhanden | Vorhandene Risikohinweise erklären | Persistierte Risikoeingänge, GET-Vorschau [S19] | `PositionRiskService`, `risk_analytics`, `assess_risk` | Reale EOD-Fenster, Gap-/Adjustmentguards, nicht kalibrierte Schwellen | `PositionRiskSummary`, `PositionRiskPanel` [F19] | Summary/Details und Einheiten konsistent halten | RV ≠ IV; keine neue Schwelle/Entwarnung; Snapshots keine regelmäßige Serie | UX1 Ownerdaten; UX3 Warnungen |
| I27 · Basiswert-/Produktvergleich, bedingte Tabelle | Unterschiedliche Entwicklung nur bei Beleg vergleichen | `synchronized_pairs` im Riskvertrag [S20] | `product_comparison` | Produktiver Reader liefert keine synchronen Paare; fehlender EOD-Close-Instant | Bedingte Tabelle in `PositionRiskPanel`, keine Kurve | Als fachlich gesperrten Ausbau dokumentieren | Keine Paarbildung/Normalisierung im Browser, kein synthetisches Warrant-PnL | UX1/Fachowner Voraussetzung; UX2 Einbindung |
| I28 · IV-Datenverfügbarkeit, vorhanden | Fehlende IV-/Greekgrundlage verstehen | `IvReadiness`, `IV_READINESS_V2` [S21] | `assess_iv_readiness` | NOT_EVALUABLE; aktuelle IV/Greeks/Rank/Ereignisgrundlage fehlen | `IvRiskPanel`, sechs fehlende Kennzahlen [F20] | Ursachen kompakter, nachvollziehbar anzeigen | Keine Null-IV/Gauge „niedrig“, keine IV-Serie aus Risikosnapshots | UX1 Datenowner; UX3 Erklärung |
| I29 · Hypothetisches IV-Modelllabor, vorhanden | Explizite Modellannahmen untersuchen | Bestehendes `iv/model-preview` [F21] | Vorhandenes IV-Modell | Manuelle Hypothese, keine belegte Positionsbewertung | `IvModelCalculator`, Ergebnis-DL | Einheiten/%/Prozentpunkte und Modellcharakter erhalten | Isolierte Effekte nicht additiv stapeln; kein Kurs-/Performanceersatz | Fachowner; UX3 Modellhinweis |
| I30 · Produkt-/Bewertungsbelege, vorhanden | Dokumentidentität und Version prüfen | Product valuation-evidence [F22] | Product-Evidence-Owner | Manuell bestätigt, Terms-/Produktbindung; CURRENT ≠ Live-IV verfügbar | `WarrantValuationEvidence` | Bestehenden Status/Belegzugriff nutzen | Keine allgemeine Produkt-/Providerqualitätsfreigabe daraus ableiten | UX1 Editor; UX2 Einbindung; UX3 Status |
| I31 · Quellenkette / Lebenszyklus, Abschnitte vorhanden | Analyse bis Lesson anhand Belegen verfolgen | Fünf `/trade-position/trades/{id}/sources…`-Reads [S22] | TradePosition, TradePlan, PostTrade, Learning | Getrennte Lesefenster, genaue Pins; kein atomarer Gesamtstatus | `TradeSourcesView`, `ReadSection` [F23] | UX4-D: referenzierte vertikale Belegliste nach Einbindungsabstimmung | Kein „6/6 fertig“, latest-Fallback oder neue Quellenauflösung | UX1 Links; UX2 Owner/Navigation; UX3 Status |
| I32 · Plan-Kaufstatus, vorhanden | Buchungsstand konkreter Planversion erkennen | Planoverview-/Executionprojektion [F24] | TradePlan/TradePosition | OPEN/CLOSED/CANCELLED/UNKNOWN/NOT_STARTED | `PlanPurchaseStatus` | Planversion vs alle Versionen klar lassen | Planfreigabe ≠ Kauf; Storno ≠ Vollverkauf | UX1 Verknüpfung; UX2 Navigation |
| I33 · Nachbeobachtung / Actual / Counterfactual, vorhanden | Tatsächlichen Exit und reale Folgebeobachtungen getrennt prüfen | FT-011-Observation/Review [S23] | `observation_metrics`, PostTrade-Owner | 20 tatsächliche Basiswert-EODs; Missingcount kein Kalenderlückennachweis | `PostTradeReviewPage` [F25] | Preisart/Währung an Zahlen klären; Actual/Counterfactual sichtbar trennen | Keine hypothetische Optionsschein-PnL oder neue Trefferquote; keine künstlichen Tage | UX1 Provenienz; UX2 Einbindung; UX3 Grenzen |
| I34 · Journal / Evidence / Lesson, vorhanden | Historische Beziehung und jeweiligen Status erkennen | Learning-Readbacks, Handoff, Currentness [S24] | PostTrade/Learning | Draft, Finalisierung, Aktualität, Materialisierung, Lessonstatus unabhängig | `TradeJournalPanel`, `Ft011EvidenceHistory`, `JournalEvidenceOrigin`, `EvidenceSourceStatus` [F26] | Exakte Versionen/Relationen in Quellenliste übernehmen | Current materialized=false widerlegt alte Evidence nicht; keine automatische Anlage/Freigabe | UX1 sichere Links; UX2 Navigation; UX3 Status |
| I35 · Positionsanalytics / Phase / Score / Stop, API/Kern | Bestehende Modellprojektionen inventarisieren | Analytics-/Phase-/Scores-/Dynamic-stop-GETs [S25] | `PositionAwareAnalyticsService`, Phase-/Score-/Stop-Owner | Benötigt passenden Analysis-Run und `POSITION_ANALYTICS_V1`; kein produktiver Scorechart gefunden | Keine eigene aktive Chartanzeige | Datenpfad vor Anzeige qualifizieren; Policy-/Komponentenbeleg verlangen | Scorepunkte ≠ Wahrscheinlichkeit; Phase ≠ Trade-Lebenszyklus; kein Stopbefehl | UX1 Fachvertrag; UX2 Platz; UX3 Warnung |

## Kennzahlenlexikon: Definition, Einheit, Zustand

Die Formeln dokumentieren **bestehenden Code**. Sie sind kein Auftrag, sie im
Frontend oder in einem neuen Service nachzubauen. Je nach historischem Modell
sind dessen gespeicherte Parameter und Version maßgeblich.

### Kurse, Analyse, Planung und Position

| Kennzahl / Feldgruppe | Nachvollziehbare bestehende Definition | Einheit / fehlende Werte / Grenze | Quelle |
| --- | --- | --- | --- |
| BID, ASK, LAST_TRADE, PREVIOUS_CLOSE | Unveränderter Wert einer identifizierten Beobachtung, kein gemeinsamer Mischpreis | Handelswährung je Serie; `null` kein Punkt; Preisart erhalten | [S02] |
| EOD `value` | Gewähltes CLOSE oder ADJUSTED_CLOSE je Instrument und Handelstag | Wertpapierwährung bzw. Indexpunkte; Adjusted ohne Fallback | [S03] |
| Basis 100 / Veränderung % | `value/common_start_value×100` auf 8 Dezimalstellen HALF_EVEN; Prozentwert = normalisierter Wert − 100 | Basis 100 bzw. Prozent; nur zulässiges gemeinsames Fenster; native Währungen ohne FX | [S03] |
| History-Counts und Zeitgrenzen | Tatsächlich gespeicherte/gelesene Zeilen, erster/letzter belegter Zeitpunkt; jeweilige Population nennen | Anzahl, Datum/UTC; keine erwartete Marktzahl oder Abdeckungsquote | [S02] · [S04] · [S18] |
| FT-006 `latest_price`, `sma_W` | Letzter ausgewählter Preis; arithmetischer Mittelwert der letzten W Beobachtungen | Preiswährung/Preisfeld des Runs; Standardfenster 20/50/200, Runparameter maßgeblich | [S05] |
| FT-006 `distance_sma_W`, `momentum_W` | Preis/SMA−1; letzter Preis/Preis W Beobachtungen vorher−1 | **Brüche**, nicht bereits Prozent; fehlender Nenner/Fenster bleibt nicht berechenbar | [S05] |
| FT-006 `annualized_volatility` | Stichprobenstandardabweichung von Log-Renditen × Wurzel des Runannualisierungsfaktors | Bruch; Fenster/Faktor aus Run, übliche Defaults 20/252 nicht rückwirkend erzwingen | [S05] |
| FT-006 High/Low/Range-Position | Max high/min low über die letzten `range_window` OHLC-Beobachtungen des Runs (Default 52); `(latest−low)/(high−low)`, Flat-Range 0.5 | Preise bzw. Bruch; raw OHLC gegenüber ggf. adjusted latest ist vorhandene Ownersemantik, kein automatisch gleicher Chartmaßstab | [S05] |
| Relative Strength | Differenz der Subject-/Reference-Returns über W Beobachtungsschritte, benötigt W+1 gemeinsam datierte Preise; Standard W=60, also 61 Werte, Neutralzone 0.02 | Candidate zeigt Klassifikation; keine numerische Serie im UI-Vertrag. Backend nutzt adjusted close mit close-Fallback | [S06] · [S30] |
| Auswahl-Spread absolut / relativ | Ask−Bid; `(Ask−Bid)/((Ask+Bid)/2)×100` | Währung / Prozent auf **Mid**. Kurzkarte wählt erstes Spreadmetric (absolut); Details führen beide | [S07] · [F05] |
| Bewertungs-Spread absolut / relativ | Ask−Bid; `(Ask−Bid)/Bid×100` | Währung / Prozent auf **Bid**; nicht identisch zur Auswahlkennzahl | [S10] |
| Planentry/-range/-stop/-target | Gespeicherte Nutzerannahmen der exakten Planversion | Planwährung, keine Produktkurshistorie; `thesis_risk`/`max_loss_assumption` sind Text, keine Positionsgröße | [S08] · [F06] |
| Offene Menge / Kostenbasis / Average Entry | Bestehende effektive Average-Cost-Projektion; vor SELL durchschnittliche Kosten je Stück, Kostenbasis sinkt um verkaufte Menge × diesen Einstand | Stück / rohe Geld-/Preiswerte; Projektion selbst qualifiziert keine Berichtswährung | [S09] |
| Marktwert | Vorhandener Bewertungsowner multipliziert qualifizierten Referenzpreis mit offener Menge | Quote-Währung; Referenzart/Indikativstatus/Beobachtungszeit erhalten | [S10] |
| Nicht realisierter Brutto-G/V | Marktwert minus projizierte Kostenbasis nach belegter gleicher BUY-Kostenwährung | Nur bei ausdrücklichem usable; Marktwert kann vorhanden und G/V trotzdem unbekannt sein | [S10] · [F08] |
| Offene Bestandssumme | Bestehende `portfolioTotals` addiert passende Marktwerte/G/V separat je Währung über gesamten geladenen offenen Bestand | BigInt-Präsentationsaggregation, eigene Rundung; Marktwert-/PnL-Abdeckung getrennt | [F09] |

### Performance

| Kennzahl | Definition / Population | Fehlzustand und Präzision | Quelle |
| --- | --- | --- | --- |
| SELL-Bruttobeitrag | Verkaufte Menge × (SELL-Preis − Average Cost unmittelbar davor), qualifiziert aus vollständigem benötigtem Historypräfix | Nur USABLE und historisch passende Währungen; Decimal-Rohstring | [S09] · [S11] |
| Periodische SELL-Bruttosumme | Summe ungerundeter verwendbarer SELL-Beiträge im ausgewählten Zeitraum; offene Teilverkäufe enthalten | COMPLETE total; PARTIAL total=null und benannte subtotal; NOT_COMPUTABLE beide null; EMPTY explizite leere Summe 0 | [S11] |
| Vollständiges Trade-Bruttoergebnis | Gesamte wirksame Lebenszeit-SELL-Ergebnisse eines Trades; tatsächlicher Vollabschluss-SELL wählt die Periode | Nur QUALIFIED monetär; kein Teilbetrag des ungeklärten Trades als Vollergebnis | [S12] |
| Vollabschlusssumme | Summe vollständiger qualifizierter Tradeergebnisse | PARTIAL subtotal enthält nur vollständige qualifizierte Trades; keine Mischung mit SELL-Periodensumme | [S12] |
| Positiv / negativ / neutral | Rohwert >0 / <0 / exakt 0 je qualifiziertem Trade | `+0.004`/`−0.004` bleiben positiv/negativ trotz Anzeige 0.00; ungeklärt ohne Klassifikation | [S12] |
| Trefferquote | `positive / N ×100`; N = alle qualifizierten vollständigen Trades einschließlich neutral | Nur COMPLETE und N>0; Prozentanzeige HALF_EVEN, zwei Stellen | [S13] |
| Ø Bruttoergebnis | Bereits vorhandene ungerundete vollständige `summary.total / N` | Nur COMPLETE/N>0; bestehende Currency-Minor-Units/HALF_EVEN | [S13] |
| Median | Mittlerer Rohbetrag; bei geradem N Addition der beiden mittleren Beträge, dann /2 | Kein Median gerundeter Werte oder einzelner SELLs; COMPLETE/N>0 | [S13] |
| Profit-Faktor brutto | Positive Rohsumme / Absolutbetrag negativer Rohsumme | Keine Verluste ⇒ undefiniert/null; nur Verluste ⇒ gültige 0; dimensionslos, zwei Stellen HALF_EVEN | [S13] |
| Rundungsdifferenz | Gerundete Gesamtsumme minus Summe einzeln gerundeter Ergebnisse | Bestehender Backendbetrag; kein Zuschlag auf einen Trade/SELL | [S11] · [S12] |

`realized-gross-sell-v2`, `closed-trade-gross-v1` und
`closed-trade-statistics-v1` bleiben getrennte Definitionen. Die Oberfläche
verwendet EUR als **Filter**, ohne FX. Die Endpunkte qualifizieren historische
Ausführungswährungen; eine aktuelle EUR-Notierung genügt nicht. Bei PARTIAL
und NOT_COMPUTABLE sind alle vier Statistiken unavailable und N unbekannt;
EMPTY hat N=0, aber keine Statistikwerte. Geld ist brutto vor Kosten/Steuern.

Die acht Abschlussgruppen sind in Priorität disjunkt:
`CANCELLED`, `HISTORY_UNRESOLVED`, `OPEN`, `OUTSIDE_PERIOD`, `OTHER_CURRENCY`,
`PERIOD_UNRESOLVED`, `MONETARY_UNRESOLVED`, `QUALIFIED`.
`in_period`, `unresolved` und Vorzeichenzähler sind daraus abgeleitete
Teilgruppen, keine zusätzlichen Segmente. Im SELL-Bericht sind Perioden-
und Verwendbarkeitszähler verschiedene überlappende Sichten; `cancelled`
zählt Trades, `examined` wirksame SELLs. [S11] · [S12]

### Risiko, Qualität, Nachbeobachtung und vorhandene Modellkerne

| Kennzahl / Gruppe | Bestehende Definition | Einheit / fachliche Grenze | Quelle |
| --- | --- | --- | --- |
| Positions-RV / Vorfenster | 20 Log-Renditen aus 21 bereinigten abgeschlossenen Closes, Stichproben-SD × √252; Vorfenster ohne überlappende Renditen | Annualisierter Bruch, UI als Prozent; echte Window-/Gap-/Adjustmentguards; keine IV | [S19] · [F19] |
| SMA20-Abstand / -Änderung | `latest_adjusted_close/SMA20−1` bzw. `SMA20/previous_SMA20−1`, aus dem bestehenden RiskAnalytics-Fenster | Prozentdarstellung aus Ownerwerten; Trendstatus bleibt eigener Regelbefund | [S19] |
| ATR14 / ATR14 zum raw Close | Durchschnitt wahrer Spannen aus raw OHLC im 14er-Fenster; relativ zum zugehörigen raw Close | Preiswährung / Bruch; Faktorwechsel kann Nichtberechenbarkeit erzwingen | [S19] |
| Quotequalität im Risk-Owner | Vorhandener Midspread bei beiden Seiten, Frische-/Verfügbarkeitsgrenzen | LIMITED/NOT_EVALUABLE ist Qualitätsaussage, keine Richtung/Orderfreigabe | [S19] |
| Quotealter / Verzögerung | Bestehende Differenz aus nachgewiesener Kurszeit und Bewertungszeit bzw. Providerdelay | Sekunden; bei unbekannter Zeit/Zone unbekannt, nicht 0; Sessionpolicy vom Owner | [S10] · [S14] · [S15] |
| Slot-/Quellen-/Tageszähler | `sampled_slots`, `distinct_quote_evidence`, `observed_utc_days` zählen verschiedene Aspekte | `FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1`; `time_coverage_percent=null`; erste Fehlerprobe bleibt Fehlerprobe | [S18] |
| Provider-/Monitoringzähler | Bestehende fertige Läufe, Versuche, Fehlerfolgen, Positionen, Regeln, Alerts; Scope je Feld | PROCESS_LOCAL; Zustandsfelder teils tri-state; keine statistische Zuverlässigkeit | [S16] · [S17] |
| Post-Trade High/Low/Final Close | Höchstes High, niedrigstes Low, letzter Close tatsächlicher Basiswert-EOD-Beobachtungen nach dem Exitdatum; Exit-Tag ausgeschlossen | Basiswertpreis/-währung; keine fiktiven Optionsscheinwerte. Aktuelle UI zeigt Zahlen teils ohne Währung: offene Darstellungslücke | [S23] · [F25] |
| Post-Trade Beobachtungszahl / Kreuzungen | Reale Anzahl im Ziel von 20 Beobachtungen, vorhandene erste Schwellenkreuzungen/Datumsbelege | Kein verifizierter Handelssitzungs-/Datenlückenzähler; Actual und Counterfactual getrennt | [S23] |
| IV / IV-Änderung / Rank / Vega / Ereignis / Verlustszenario | Im Positionspfad ausdrücklich noch nicht qualifiziert verfügbar | NOT_EVALUABLE, keine Nullwerte; keine qualifizierte Historie oder synchronen Paare | [S21] |
| Hypothetische Modellpreise/-änderung/Vega | Bestehendes europäisches Vanilla-Modell mit expliziten Annahmen; Vega je Schein/Position pro IV-Prozentpunkt, kombinierte und isolierte Effekte | Modellwährung, Prozent und Prozentpunkte getrennt; isolierte Effekte nicht additiv; keine reale Position | [F21] |
| Sessions seit Einstieg / Highest High | `PositionAwareAnalyticsService` liest den gebundenen Analysesnapshot und tatsächlichen Einstieg | Gezählte Snapshotbeobachtungen strikt nach Einstiegstag und vor Auswertungstag; keine nachgewiesene vollständige Sitzungsabdeckung | [S25] |
| TrendScore | POSITION_SCORE_V1: fünf Komponenten à 20 (Reife ≥10 Sessions, Preis>SMA20, SMA20>SMA50, SMA50>SMA200, RSI≥50) | 0–100 **Punkte**; bei ungeeignetem Analysis-Run null, keine Wahrscheinlichkeit | [S26] |
| PeakScore | Vier Komponenten à 25: Trendstruktur, Reife ≥10, RSI≥70, Abstand zum Einstiegshoch zwischen 0 und 1 ATR | Punkte; keine Trendwendeprognose | [S26] |
| PositionPhase | POSITION_PHASE_V1: BUILDING/CONFIRMED/TREND/PEAK_PROTECTION anhand vorhandener Session-/SMA-/RSI-/ATR-Regeln | Klassifikation, keine gespeicherte Fortschrittsquote und kein Analyse→Lesson-Status | [S27] |
| Dynamic Stop / Abstand | DYNAMIC_STOP_V1: Highest High seit Einstieg − ATR14 × Policyfaktor; Abstand = letzter Preis − Kandidat. Faktoren 3/2.5/2/1.5 nach Phase, bedingtes Tightening 1.5/1 | Indikativer Kandidat aus dem Analysesnapshot, kein bestätigter Stop; DTO ohne explizite Währung/Listing/PriceBinding, daher kein qualifizierter Overlayvertrag; ungültige Abhängigkeiten/null verhindern Ergebnis | [S28] |

Der Kern `calculate_position_analytics` (ATR14/RSI14/highest_high20) existiert,
hat im geprüften `backend/app` aber keinen Runtimeaufrufer. Die darauf
angewiesenen APIprojektionen verlangen `indicator_set_version=POSITION_ANALYTICS_V1`.
Sie sind deshalb kein Nachweis einer bereits versorgten Score-/Phasenanzeige.
Von der tatsächlich verwendeten separaten RiskAnalytics-ATR-Berechnung unterscheiden.
Analytics/Phase/Score/DynamicStop können über Health mittelbar EODHD lesen;
read-only bedeutet dort keine Geschäftsmutation, nicht providerfrei. Eine
DynamicStop-Overlayanzeige benötigt zuerst einen expliziten Preisachsen- und
Währungsnachweis des Owners; gleiche Trade-ID oder aktuelles EUR genügt nicht.

## Datenquellen, Zeitstempel und Historiengrenzen

### Positionskurs und Erfassungsprotokoll

Die Historien-API liest in `REPEATABLE READ READ ONLY` mit Statementtimeout
10 Sekunden. Sie verwendet vorhandene Samples und letzten erfolgreichen
Retentionsbeleg, keinen Providerrefresh und keine aktuelle Produktbewertung.
Die jüngsten **10.000 Samples nach Erfassungsreihenfolge** werden zuerst
begrenzt, danach nach Originalzeit ausgewertet; Retention kommt gesondert hinzu.
`samples_available`, `samples_considered`, `sample_limit` und `truncated`
bleiben sichtbar. „Alle“ bedeutet keine unbegrenzte vollständige Historie. [S01] · [S02]

Serienidentität umfasst Provider, historischen identity_key, Listing, ISIN,
Währung, Preisart, Quellenmodus, Provider-Platzcode und MIC. Gleicher Preis zu
späterer Originalzeit ist eine neue Beobachtung; gleiche Zeit mit abweichendem
Preis wird nicht gemittelt. `observed_at` ist Kurszeit, `retrieved_at` Abrufzeit,
`captured_at` Speicherzeit. `collection_started_at` ist der erste gespeicherte
Samplezeitpunkt, kein Beginn vollständiger Marktversorgung. Das getrennte
Erfassungsprotokoll aggregiert Capture-Slots und zeigt nur 50 Detailitems;
es darf nicht in dieselbe Originalkurszeitreihe umgedeutet werden. [S02] · [S18]

### EOD-Chart, Analyseversion und historische Identität

EOD-Reader begrenzt auf 10.001 gelesene Zeilen als Guard; mehr als 10.000
Punkte führen zu `POINT_LIMIT_EXCEEDED`, nicht Downsampling. Fehlendes Adjusted,
unbrauchbare Qualität, ungültiger Preis oder Quellenkonflikt bleibt fehlend;
Währungs-/Datumsduplikatkonflikte können die Serie sperren. `gap_before`
bezeichnet eine konservative Wochentagslücke, keinen verifizierten
Handelskalender. Der erste gemeinsame tatsächliche Vergleichstag wird bei
ungültigem Wert nicht heimlich durch einen späteren ersetzt. [S03] · [S04]

`DailyPriceModel` speichert keine historische Provider-Exchange-/Mappingrevision.
Die `ChartIdentity.mapping_*`-/provider_identity-Angaben gehören zur gelesenen
Verwaltung und dürfen nicht als damalige Mappingbelege jedes historischen
Kurspunkts bezeichnet werden. Point-Provider/Symbol und bekannte Konflikte
bleiben maßgeblich. Versionierte FT-006-Snapshots sind dagegen konkrete
Analysebelege. Sie werden nicht durch einen heutigen Chart-GET ersetzt.
Details: [MARKET_CHARTS.md](../implementation/MARKET_CHARTS.md),
[ADR-CHARTS-001](../decisions/ADR-CHARTS-001-EOD-COMPARISON-AND-ETF-IDENTITY.md).

### Performance und Quellenansichten

Beide Performanceberichte verwenden denselben Snapshotreader und lesen je
Anfrage einen vollständigen lokalen Fakten-Snapshot. Getrennte Reportrequests
besitzen eigene Lesefenster. Die Grenzen sind: bis 2.000 Trades, 20.000
Executions, 40.000 Währungsbestätigungen, 10.000
CurrencyEvidence-Objekte und 100.000 Provenienzlinks. Überschreitung ergibt
`REPORT_RESOURCE_LIMIT`, keinen gekürzten Bericht. Zeitraum = Beginn Von-Tag
bis exklusiv Beginn des Tages nach Bis-Tag in der Berichtszone. Date-only-
Ausführungen behalten Originaldatum/-zone und mögliches Intervall; teilweise
Periodenüberlappung bleibt ungeklärt. [S11] · [S12] · [S29]

`basis.knowledge=CURRENT_EFFECTIVE_FACTS`: Ein Bericht über eine alte Periode
verwendet heute wirksame Korrekturen. `basis.id` ist ein gebundener Fingerprint,
keine wiederherstellbare historische Reportversion. Die fünf Tradequellen-
Reads besitzen dagegen **jeweils eigene** Read-only-Lesefenster. Ein gemeinsamer
Bildschirm macht diese Antworten nicht zu einem atomaren Gesamtstand. [S22] · [S29]

## Doppelte Darstellung und sinnvolle Wiederverwendung

| Bestand | Einordnung und Entscheidung |
| --- | --- |
| Positionshistorie in Workspace und Tradeverwaltung | Bereits dieselbe Komponente; keine zweite Chartengine bauen. Wiederholtes Öffnen kann neu lesen. Einbindung/Read-Lebensdauer entscheidet UX-2. |
| Markt-Absolut-, Normalisierungs- und Prozentansicht | Bereits Modi desselben Renderers; keine drei neuen Komponenten oder Berechnungen. |
| Marktwert/G/V in Übersicht, Details und ProductValuationPanel | Kontextdopplung, keine mehrfachen Positionen. Main liest im Bewertungsowner die Position nochmals; UX-2 koordiniert die mögliche Reduktion. |
| Rohpositions-PnL und qualifizierter Performancebericht | Ähnliche Begriffe, unterschiedliche Aussagequalität; nicht zu einem gemeinsamen Rechenwert zusammenlegen. |
| `RealizedGrossPage` / `ClosedTradesPage` | Dünne Wrapper um vorhandenen `PerformanceWorkspace`; getrennte Reportsemantik bleibt. |
| `ClosedTradeSources` in Liste und Einzeltradeergebnis | Sinnvolle Wiederverwendung; neue Quellenantwort kann jüngeren Readstand haben. |
| RiskSummary und RiskPanel | Bewusste Übersicht/Detailhierarchie, keine doppelte Risikoberechnung einführen. |
| Quote-/Frischehinweise in Bewertung, Coverage, Risk und Historie | Gemeinsame Wörter möglich, aber unterschiedliche Quellen-, Zeit- und Populationsbedeutung. Keine globale „aktuell“-Ampel. |
| TradeSources, PostTrade-/Journaleditor, Lessonhistorie | Lesender Herkunftsbezug und Bearbeitung bleiben eigene Owner. Ein Diagramm darf keinen Editor neu initialisieren. |
| Decimal-/Moneyformatter | `moneyText` lokalisiert Backend-HALF_EVEN; `positionsView.formatUnits` hat eigene BigInt-Anzeigerundung. Nicht ungeprüft als gemeinsamer Finanzformatter vereinheitlichen. |

## Fehlende fachliche Voraussetzungen und Grenzen

| Fehlender Nachweis / Vertrag | Auswirkung und zuständiger nächster Owner |
| --- | --- |
| Verifizierter Handelskalender und erwartete Frequenz je Historienfeed | Keine vollständige Zeitabdeckung, Ausfallquote oder garantierte Lückenzahl; Market Data/UX-1 |
| Historische EOD-Mapping-/Exchangeversion pro Punkt | Keine rückwirkend behauptete Listing-/Mappingidentität; Market Data/Market |
| Qualifizierte Bucket-/Kumulativzeitreihe | Keine Tages-/Monatssummen, Equity-/PnL-Kurve durch UX4; Performance-/TradePosition-Owner/UX-1 |
| Gebühren, Steuern, Cashflows, historische Equity, qualifizierte FX | Keine Netto-/Gesamtrendite, TWR/MWR, CAGR, Drawdown oder Sharpe; eigener Fachvertrag erforderlich |
| Synchrone Produkt-/Basiswertpreise und exakter EOD-Close-Instant | Keine relative Produktkurve aus unsynchronen Einzelquellen; Risk-/MarketData-Owner |
| Qualifizierte IV-/Greek-/Ereignisquellen und IV-Historie | Keine IV-Kurve, IV-Rank oder echte Vega-/Verlustanzeige; vorhandene Fehlgründe erhalten |
| Dauerhafte Providerdiagnosehistorie und Nenner | Kein Uptime-/SLA-Ranking aus PROCESS_LOCAL-Daten; Betriebs-/MarketData-Owner |
| Atomare Lebenszyklusprojektion / eindeutige zusätzliche Quellenauflösung | Nur getrennte referenzierte Belegabschnitte, keine globale Vollständigkeit; zuständige Source-/Learning-Owner/UX-1 |
| Abgestimmter Master-/UX-2-Einbindungsnachweis und UX-3-Terminologie | Keine neue gemeinsame Workspacekomponente; konkrete Slots/Props/Readowner zuerst abstimmen |
| Öffentlicher Refresh-/Coverage-Readtyp | Bestehende private `RefreshCheck`-/`RefreshStatus`- und Coverage-Typen nicht kopieren oder intern quer importieren; vor übergreifender Nutzung Market Data und UX-2 gemäß UX3 O3 einbeziehen |
| Nutzer-Datenbestand / lokale Installation nicht geprüft | Keine Aussage über tatsächliche instrumentbezogene Historie, Beträge oder Betriebsqualität; Codefähigkeit ≠ vorhandene reale Daten |

Zusätzlicher Owner-Prüfpunkt: `position_quote_coverage` verwendet an einer
Stelle `max_quote_age_seconds or 3600`; andere Qualitätswege unterscheiden
eine ausdrücklich gesetzte Nullsekundengrenze. Vor einer Behauptung identischer
Frischebewertungen ist dieser mögliche Policyunterschied beim Fachowner zu
qualifizieren. UX4-A ändert ihn nicht und führt keinen lokalen Ersatzschwellwert ein. [S15]

## Priorisierte Visualisierungsmöglichkeiten

| Priorität | Vorhaben | Konkreter Nutzen / Voraussetzung |
| --- | --- | --- |
| P0 | Gemeinsame Definitionen, Einheiten, Zeit-/Quellen- und Missingregeln | Schutz gegen fachlich falsche Zusammenführung; dieser Draftvertrag und UX1/2/3-Abgleich |
| P1 | UX4-B: vorhandenen Positionschart lesbarer machen | Quellenwahl nach exakter Serien-ID, eindeutige Symbole/Belege, Mobile/Tastatur; bestehender Datenvertrag reicht |
| P1 | UX4-C: bestehende vier Statistikfelder erklären und einzelne SELL-Beiträge zeigen | Sofort nutzbare Ownerwerte; keine neue Aggregation nötig; Einbindung mit UX-2 vereinbaren |
| P1 | UX4-D: vorhandene Qualitäts-/Erfassungsansichten verständlicher darstellen | Absolute Zahlen, Quelle/Zeit/Scope; keine globale Qualitätsquote |
| P2 | UX4-D: Positionsquellen-API und belegbasierte Lebenszyklusliste einbinden | Fachlich lokale Präsentation möglich; UX-2-Slot/Readowner, UX-3-Wörter und genaue Links vorher klären |
| P2 | Analyse-/Auswahl-/PostTrade-Einheiten verbessern | Konkrete Rohkey-, Spreadnenner- und Währungslesbarkeitslücken; eigener begrenzter Darstellungsumfang nach Ownerabgleich |
| Zurückgestellt | Neue Equity-/Kumulativ-/IV-/Uptime-/Scorehistorien | Fehlende Verträge oben; keine Frontendauffüllung oder zusätzliche Finanzrechnung |

## Quellenregister

Die Links zeigen auf den Code dieses Branches, dessen Runtime dem geprüften
Main entspricht. Für spätere Vergleiche ist die oben genannte Main-SHA
maßgeblich; der Qualifikationsnachweis prüft die unveränderten Runtimebäume.

[S01]: ../../backend/app/features/trade_position/api/price_history.py
[S02]: ../../backend/app/features/market_data/service/warrant_price_history.py
[S03]: ../../backend/app/features/analysis/domain/time_series.py
[S04]: ../../backend/app/features/market_data/persistence/time_series.py
[S05]: ../../backend/app/features/analysis/domain/calculator.py
[S06]: ../../backend/app/features/candidate/service/orchestration.py
[S07]: ../../backend/app/features/product_selection/service/application.py
[S08]: ../../backend/app/features/trade_plan/domain/models.py
[S09]: ../../backend/app/features/trade_position/domain/projector.py
[S10]: ../../backend/app/features/position_monitoring/service/product_valuation.py
[S11]: ../../backend/app/features/performance/domain/report.py
[S12]: ../../backend/app/features/performance/domain/closed_report.py
[S13]: ../../backend/app/features/performance/domain/closed_statistics.py
[S14]: ../../backend/app/features/market_data/service/quote_coverage.py
[S15]: ../../backend/app/features/market_data/service/position_quote_coverage.py
[S16]: ../../backend/app/features/market_data/service/refresh_diagnostics.py
[S17]: ../../backend/app/features/position_monitoring/service/health.py
[S18]: ../../backend/app/features/market_data/service/quote_history.py
[S19]: ../../backend/app/features/analysis/domain/risk_analytics.py
[S20]: ../../backend/app/features/position_monitoring/service/risk_inputs.py
[S21]: ../../backend/app/features/position_monitoring/service/iv_readiness.py
[S22]: ../../backend/app/features/trade_position/service/source_view.py
[S23]: ../../backend/app/features/post_trade/domain/observation_metrics.py
[S24]: ../../backend/app/features/learning/application/ft011_materialization_status_service.py
[S25]: ../../backend/app/features/position_monitoring/service/position_analytics.py
[S26]: ../../backend/app/features/position_monitoring/service/score_engine.py
[S27]: ../../backend/app/features/position_monitoring/service/phase_engine.py
[S28]: ../../backend/app/features/position_monitoring/service/dynamic_stop.py
[S29]: ../../backend/app/features/performance/service/reader.py
[S30]: ../../backend/app/features/analysis/domain/top_down.py
[F01]: ../../frontend/src/features/operational_workspace/components/PositionPriceHistory.tsx
[F02]: ../../frontend/src/features/analysis/components/TimeSeriesChart.tsx
[F03]: ../../frontend/src/features/analysis/pages/MarketAnalysisDetailPage.tsx
[F04]: ../../frontend/src/features/candidate/pages/CandidatePage.tsx
[F05]: ../../frontend/src/features/product_selection/pages/ProductSelectionPage.tsx
[F06]: ../../frontend/src/features/trade_plan/components/TradePlanVersionContent.tsx
[F07]: ../../frontend/src/features/trade/pages/TradeManagementPage.tsx
[F08]: ../../frontend/src/features/trade/components/ProductValuationPanel.tsx
[F09]: ../../frontend/src/features/operational_workspace/services/positionsView.ts
[F10]: ../../frontend/src/features/performance/components/RealizedGrossReportView.tsx
[F11]: ../../frontend/src/features/performance/components/ClosedTradeSummary.tsx
[F12]: ../../frontend/src/features/performance/components/ClosedTradeStatistics.tsx
[F13]: ../../frontend/src/features/performance/components/ClosedTradeResult.tsx
[F14]: ../../frontend/src/features/operational_workspace/pages/QuoteCoveragePanel.tsx
[F15]: ../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx
[F16]: ../../frontend/src/features/alert/components/MonitoringRuntimePanel.tsx
[F17]: ../../frontend/src/features/alert/components/TradeAlertsPanel.tsx
[F18]: ../../frontend/src/features/product/components/WarrantQuoteHistory.tsx
[F19]: ../../frontend/src/features/alert/components/PositionRiskPanel.tsx
[F20]: ../../frontend/src/features/alert/components/IvRiskPanel.tsx
[F21]: ../../frontend/src/features/alert/components/IvModelCalculator.tsx
[F22]: ../../frontend/src/features/product/components/WarrantValuationEvidence.tsx
[F23]: ../../frontend/src/features/trade/components/TradeSourcesView.tsx
[F24]: ../../frontend/src/features/trade_plan/components/PlanPurchaseStatus.tsx
[F25]: ../../frontend/src/features/post_trade/pages/PostTradeReviewPage.tsx
[F26]: ../../frontend/src/features/learning/components/Ft011EvidenceHistory.tsx

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | UX4-A: Main-Codeinventur, 35 Darstellungen/Quellenfähigkeiten, Kennzahlendefinitionen und Abhängigkeiten; keine Runtimeänderung |
