# UX-Masterplan

## Auftrag und gemeinsame Basis

MASTER-LEAD koordiniert Architektur, Zuständigkeiten, Abhängigkeiten, technische Prüfung und Integration der vier UX-Stränge. Dieser Dokumentationsschnitt implementiert keine Produktfunktion.

Geprüfte Ausgangsbasis: [Main `1883f7f330719453958f8be1dd51d48db816662e`](https://github.com/burckhju/trading-workspace/commit/1883f7f330719453958f8be1dd51d48db816662e), 31.10.2026. Der veröffentlichte Tag `v1.5.35` zeigt auf diesen Commit. Vor jedem neuen Arbeitslauf Main, Tag, offene PRs und die tatsächlich geänderten Dateien neu auflösen; diese Basis nicht ungeprüft fortschreiben.

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

## Übergabepaket UX-1 — Eingaben und Herkunft

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Belegte Eingaben und historische Herkunft wiederverwenden; den vorhandenen Schnitt #312 für Integration qualifizieren. |
| Nicht-Ziele | Neue Finanzlogik, automatische Buchung oder Bestätigung, neue Navigation, heutige Währung als historischen Beleg verwenden. |
| Ausgangscommit | Gemeinsame Main-Basis oben; geprüfter [#312-Head](https://github.com/burckhju/trading-workspace/commit/8f67442daac6879d7dfb28416f2171f67aead0e5) `8f67442daac6879d7dfb28416f2171f67aead0e5`. |
| Komponenten / Dateien | `frontend/src/features/trade/components/ExecutionCurrencyPreview.tsx`, `AdditionalPurchasePanel.tsx`, `trade/services/client.ts`, `trade/types/api.ts`; `product_selection/pages/ProductSelectionPage.tsx`; `performance/services/performanceReportContext.ts`; `backend/app/features/trade_position/{api,domain,service}`. Gemeinsame `TradeManagementPage.tsx` nur mit UX-2. Vollständige Dateiliste im PR. |
| Vorhandene Implementierung | Bestehende Währungsresolver und schreibgeschützter `TradeSourceReader`; #312 ergänzt Vorschau vor BUY/SELL, Wiederöffnung eines eindeutigen gespeicherten Auswahlruns und editierbare Berichtszeitzone. Journal-/Lessonverknüpfung ist dort Bestandsaufnahme. |
| Schnittstellen / Abhängigkeiten | TradePosition besitzt Resolver/DTO/GET-Vertrag; UX-2 integriert Formularslots und Readback-Invalidierung; UX-3 besitzt Hinweismuster. Neue featureübergreifende Previewimporte benötigen eine geklärte gemeinsame Grenze. |
| Testanforderungen | Vorhandene Preview-Unit-/PostgreSQL-/Browserfälle, UNKNOWN/MIXED/CONFLICT, historische Zeitbindung, keine Preview-Writes, manuelle Eingaben, späte Antworten und A→B→A; gemeinsame Navigation/Readback-Regression mit #311. Fehlerkorrekturen am aktuellen Head vollständig qualifizieren. |
| Erlaubte Änderungen | Im eigenen Implementierungsauftrag: eigene Eingabebausteine, bestehende Clients, additive lesende API nur mit Domain-Owner-Prüfung; keine alleinige Änderung der Hostnavigation oder Domainprioritäten. MASTER ändert diese Dateien nicht. |
| Abschlusskriterien | Quellenbindung und manuelle Vorrangregel belegt; lesender API-Vertrag fachlich geprüft; gemeinsame Import-/Dateigrenze geklärt; aktuelle CI und gemeinsame Regression erfolgreich; Restabnahme getrennt benannt. |

Vorhandene Übergabe: [UX1_INPUT_REUSE_QUALIFICATION am geprüften Head](https://github.com/burckhju/trading-workspace/blob/8f67442daac6879d7dfb28416f2171f67aead0e5/docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md). Fachliche Zuordnung: [PB-016 Eröffnung](../planning/PRODUCT_BACKLOG.md#pb-016-opening), [PB-015 Vergleich](../planning/PRODUCT_BACKLOG.md#pb-015-comparison), [PB-019 Auswertungen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations).

## Übergabepaket UX-2 — Trade-/Positionsarbeitsbereich

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Einen vorhandenen Trade zwischen Position, Buchungen, Quellen und Lernen verfolgen, ohne Kontext, historische Pins oder ungespeicherte Eingaben zu verlieren. |
| Nicht-Ziele | Zweite Trade-/Positionshaltung, neue Fachberechnung, neue Freigabe/Lifecycleentscheidung, unbelegte Beziehungen zwischen Plan, Run, Analyse und Journal. |
| Ausgangscommit | Gemeinsame Main-Basis; geprüfter [#311-Head](https://github.com/burckhju/trading-workspace/commit/79e9b97e31d3bf80936fb5c026798bf8ebb10b33) `79e9b97e31d3bf80936fb5c026798bf8ebb10b33`; gegenüber dem zuerst geprüften `6782bc7a…` nur zwei E2E-Testdateien korrigiert. |
| Komponenten / Dateien | `frontend/src/features/trade/pages/TradeManagementPage.tsx`, `trade/pages/index.ts`, `trade/components/TradeSourcesView.tsx`, neue Navigation/Linkhelper; `post_trade/pages/PostTradeLearningPage.tsx` und betroffene Journal-/Lessonconsumer. Vollständige Dateiliste im PR. |
| Vorhandene Implementierung | Kontext-/Dirty-/Busy-Guards, Abort-/Generationsschutz, ein Timelineowner, Sources und historische Journal-/Lessonversionen. #311 liefert UX2-A Navigation; UX2-B/C/D sind lediglich vorbereitet. Die bestehende zusätzliche Positionsabfrage des Bewertungsbausteins ist noch nicht konsolidiert. |
| Schnittstellen / Abhängigkeiten | Einziger Integrationsowner der gemeinsamen Hostseite; UX-1-Formularverhalten, UX-3-Hinweisplatzierung und UX-4-Charts konsumieren. Öffentliche Navigationsgrenze gemäß Shared Contracts herstellen. |
| Testanforderungen | Kontext/Pins/Rückwege, Tastatur/Fokus, 390/1280-px-Ansichten, keine Zusatzreads bei Hashnavigation, zwei parallele Entwürfe, A→B→A, geschlossen/storniert/fehlend; gemeinsame #311/#312-Regression und bestehende Journal-/Performance-Gates. |
| Erlaubte Änderungen | Im eigenen Implementierungsauftrag: Navigation, darstellende Komposition, schmale Link-/Slotverträge und Tests; Hoständerung für andere Stränge abgestimmt übernehmen. Keine Domain- oder Formeländerung. |
| Abschlusskriterien | Korrigierte E2E-Consumer erfolgreich am neuen Head qualifiziert; gemeinsame Importgrenze und Dateiabstimmung erledigt; Pins/Guards/Readback erhalten; gemeinsamer Laufzeitnachweis. Keine Vollständigkeitsbehauptung für UX2-B/C/D. |

Vorhandene Übergabe: [ux2-trade-workspace am geprüften Head](https://github.com/burckhju/trading-workspace/blob/79e9b97e31d3bf80936fb5c026798bf8ebb10b33/docs/ui/ux2-trade-workspace.md). Fachliche Zuordnung: [PB-016 Positionen](../planning/PRODUCT_BACKLOG.md#pb-016-positions), [PB-017 Historie](../planning/PRODUCT_BACKLOG.md#pb-017-history), [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) und [Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).

## Übergabepaket UX-3 — Hinweise und sichere Folgeaktionen

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Vorhandene Hinweise konsistent als Feststellung, Ursache, Auswirkung und bewussten nächsten Benutzerweg darstellen. Zunächst eigenen Repositoryübergabebericht mit konkretem Umfang liefern. |
| Nicht-Ziele | Neue Alert-/Notificationengine, neue fachliche Prioritätsberechnung, pauschale Risikoampel, automatischer Refresh/Write/Trade oder Aktivierung. |
| Ausgangscommit | Gemeinsame Main-Basis; kein eigener veröffentlichter UX-3-Programmhead im Prüflauf nachgewiesen. Lead liefert tatsächliche Basis und Head oder ausdrücklich „noch kein Implementierungshead“. |
| Komponenten / Dateien | `frontend/src/features/alert/components/{TradeAlertsPanel,MonitoringRuntimePanel,PositionRiskPanel,PositionRiskSummary}.tsx`; vorhandene `ErrorNotice`/`LoadingNotice` in `features/market/components/ApiFeedback.tsx`; zugehörige Tests. Gemeinsame Hostseite bleibt bei UX-2. |
| Vorhandene Implementierung | Getrennte Alert-, Runtime-, Risiko- und Zustellzustände, Quellen-/Zeitangaben und explizite Aktionen; keine belegte neue appweite UX-3-Vereinheitlichung. |
| Schnittstellen / Abhängigkeiten | UX-1 liefert Validierungs-/Herkunftsfakten; UX-2 Platzierung/Fokus; UX-4 konsumiert Qualitätsmuster. Fachliche Bedeutung und Blockierungen bleiben beim jeweiligen Domain-Owner. |
| Testanforderungen | Fehlend/veraltet/Fehler nie als gesund; Alert versus Zustellung versus Scheduler unterscheiden; keine Mutation durch Rendering oder Link; Retry nur für den benannten Read; Tastatur, Fokus, Live-Region und schmale Ansicht. |
| Erlaubte Änderungen | Erst eine abgegrenzte Präsentationsaufgabe und Dateireservierung vereinbaren. Danach im eigenen Auftrag vorhandene Renderer/Tests; keine Regel-/API-/Schreibänderung ohne gesonderte Domainprüfung. |
| Abschlusskriterien | Repositoryübergabe mit Pflichtfeldern und konkreten Diff-/Testbelegen; Ursache/Auswirkung/Handlungsgrenze verständlich; vorhandene Statusbedeutung erhalten; gemeinsame Qualitäts-/Platzierungsprüfung; fachliche Abnahme separat. |

Fachliche Zuordnung: [Monitoringregeln](../planning/PRODUCT_BACKLOG.md#monitoring-rules), [Zustellung](../planning/PRODUCT_BACKLOG.md#notification-delivery), [Datenqualität](../planning/PRODUCT_BACKLOG.md#market-data-quality), [PB-017 Stop](../planning/PRODUCT_BACKLOG.md#pb-017-stop).

## Übergabepaket UX-4 — Diagramme und Kennzahlen

| Pflichtfeld | Arbeitsauftrag |
|---|---|
| Fachliches Ziel | Bestehende Diagramme/Kennzahlen lesbar, zugänglich und hinsichtlich Herkunft, Zeitraum und Datenlücken nachvollziehbar darstellen. Zunächst eigenen Repositoryübergabebericht liefern. |
| Nicht-Ziele | Zweite Kursspeicherung, Backfill/Providerabruf beim Anzeigen, neue Finanzformel, eigene Normalisierung, erfundene Netto-/FX-/Equitywerte. |
| Ausgangscommit | Gemeinsame Main-Basis; kein eigener veröffentlichter UX-4-Programmhead im Prüflauf nachgewiesen. Tatsächlichen Head oder fehlenden Implementierungshead benennen. |
| Komponenten / Dateien | `frontend/src/features/operational_workspace/components/{PositionPriceHistory,PositionPricePlot,PositionPriceHistoryEvidence}.tsx`, zugehörige Präsentationshelper; `analysis/components/TimeSeriesChart.tsx`; `performance/components/ClosedTradeStatistics.tsx`; passende Tests. |
| Vorhandene Implementierung | Lesender Positionsverlauf mit Scatterpunkten und Evidenztabelle, Marktcharts mit Backendnormalisierung und Lücken, serverseitige Abschlussstatistik mit Nenner/Definitionsversion. #205 ist keine aktuelle Implementierungsvoraussetzung. |
| Schnittstellen / Abhängigkeiten | UX-2 integriert Charts; UX-3 liefert Qualitätsmuster; Market Data, TradePosition, Analysis und Performance behalten ihre einzelnen Daten-/Berechnungsverträge. |
| Testanforderungen | Quelle/Währung/Preisart getrennt; Originaldezimalwerte; fehlend ungleich Null; leer/Fehler/Kürzung unterscheiden; date-only nicht als präzisen Zeitpunkt plotten; verspätete Antworten; Tabelle/Keyboard/Mobilansicht; keine Mutation beim Öffnen. |
| Erlaubte Änderungen | Nach konkreter Dateiabstimmung im eigenen Auftrag bestehende Darstellungs-/Evidenzkomponenten und Tests; Hostnavigation nur über UX-2. Ownerantworten unverändert konsumieren. |
| Abschlusskriterien | Übergabe mit konkretem Diff; Einheiten, Quellen und Lücken erhalten; zugängliche Alternative und gemeinsame Qualitätsprüfung belegt; aktuelle CI; weitergehende Performancefunktionen und Abnahme ausdrücklich abgegrenzt. |

Fachliche Zuordnung: [Marktübersicht](../planning/PRODUCT_BACKLOG.md#pb-013-overview), [Kennzahlen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics), [Statistiken](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics), [Dashboards](../planning/PRODUCT_BACKLOG.md#pb-019-performance-dashboards).

## Übergabe zwischen getrennten Chats

Alle vier Leads erhalten dieselbe Main-Basis, diese fünf Dokumente und den exakten Koordinations-PR-Head als Einstieg. Ein Link im Repository ist ein überprüfbares Übergabeangebot; er belegt keinen automatischen Empfang in einem anderen Chat.

Jeder Folgeauftrag ergänzt vor Änderungen: Ziel/Nicht-Ziele, Ausgangs-SHA, vollständige Dateiliste, bereits vorhandenen Code, Owner/Consumer, Abhängigkeiten, Tests, erlaubte Änderungen und Abschlusskriterien. Die Übergabe nennt anschließend Branch, PR, Head-/Testmerge-SHA, tatsächlichen Diff, CI-Run-/Joblinks, offene Konflikte und getrennte Fach-/Release-/PC-Nachweise. Für UX-3 und UX-4 wird dieser Bericht ausdrücklich angefordert; unsichtbare Chatstände werden nicht geschätzt.

Erlaubnis dieses MASTER-Laufs: Analyse, technische Koordinationsdokumentation, eigener Dokumentationsbranch und Draft-PR. Merges, Releases, Tags, PC-Updates, produktive Änderungen und PR-Schließungen benötigen ausdrückliche gesonderte Freigabe.
