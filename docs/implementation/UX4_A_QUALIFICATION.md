# UX4-A — Prüfbasis, Vertragsreview und Testplanung

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Qualifikationsnachweis für einen Dokumentations-Draft, 0.1 |
| Datum / Status | 31.10.2026, Europe/Vienna / Draft |
| Geprüfter Main | `1883f7f330719453958f8be1dd51d48db816662e` |
| Main-Tree / Version | `e90aa341805c71362df1cda1a9dc378b0af9c4fe` / `1.5.35` |
| Auftrag | Diagramm-/Kennzahleninventur, konsolidierter Visualisierungsvertrag und Startprompts UX4-B/C/D |
| Verantwortlicher Lead / Branch | UX-4 / `docs/ux4-a-visualization-inventory-contract` |
| Implementierungsstand | Eigener Dokumentationshead im PR-Text; kein UX4-B/C/D-Produktimplementierungshead |
| Freigabegrenze | Eigenständiger Draft-PR; kein Merge, Release, Deployment oder PC-Update |

## Lieferumfang

1. [Vollständige Inventur und Diagrammmatrix](../ui/ux4-visualization-inventory.md)
   mit 35 Darstellungen bzw. getrennt gekennzeichneten API-/Kernfähigkeiten,
   Kennzahlendefinitionen, Datenquellen, Dopplungen und fehlenden Voraussetzungen.
2. [Konsolidierter Visualisierungsvertrag](../ui/ux4-visualization-contract.md)
   mit Regeln V01–V14 für Owner, Identität, Einheiten, Zeiten, Datenlücken,
   Grundgesamtheiten, Lebenszyklus und zugängliche Bedienung.
3. Unabhängige Startprompts für [UX4-B](../ui/ux4-b-position-price-history-prompt.md),
   [UX4-C](../ui/ux4-c-performance-visualization-prompt.md) und
   [UX4-D](../ui/ux4-d-quality-lifecycle-prompt.md).

Nur diese sechs neuen Markdown-Dateien gehören zum PR. Runtime, Datenmodelle,
Finanzberechnungen, Provider, Konfiguration, Abhängigkeiten, Tests, CI-Gates,
Versionsdateien und bestehende Koordinationsdokumente bleiben unverändert.
Die Dokumente enthalten keine privaten Trades, Providerantworten, historischen
Kursreihen oder Zugangsdaten. Fachliche Beispielbeträge sind ausdrücklich
vorhandene synthetische Testreferenzen, keine Nutzerergebnisse.

## Tatsächlich durchgeführte Analyse

- Repository frisch geklont, Arbeitsstand und Main-SHA per GitHub und lokal
  verglichen; Git-Tag `v1.5.35` auf denselben Commit aufgelöst. Drei
  Versionsangaben (`VERSION`, Frontend, Backend) stimmen überein.
- Main-Dateibaum auf `AGENTS.md`, Master-/UX-Koordination und relevante
  Dokumente geprüft. 295 Remote-Refs einschließlich symbolischem `origin/HEAD`
  nach UX1–UX4-/Master-/Koordinations-Dokumentpfaden durchsucht. Zunächst waren
  nur UX1-/UX2-Dokumente auffindbar; der abschließende GitHub-Abgleich fand
  zusätzlich die inzwischen veröffentlichten Drafts #313 und #314.
- Alle fünf Master-Koordinationsdokumente aus #313 am Head `2312abfe…` gelesen;
  UX-3-Hinweis-, Komponenten-/Aktions- und Integrationsvertrag aus #314 am Head
  `52a24266…` abgeglichen. Vollständige SHAs und Dokumentlinks stehen in der
  [Koordinationsinventur](../ui/ux4-visualization-inventory.md).
- UX1 #312 bis `8f67442d…` einschließlich tatsächlichem Fünf-Dateien-Delta
  zum ersten Prüfstand und UX2 #311 bis `79e9b97e…` berücksichtigt. Die
  Implementierungen bleiben getrennt vom Main-Iststand; ältere Forschungs-/
  Vorschlags-PRs wurden nicht übernommen. Keine fremden Testresultate werden
  als Nachweis dieses Dokumentationsheads ausgegeben.
- Produktiven Frontendcode nach Recharts, SVG/Canvas, Chart-/Kennzahlen-/
  G/V-/Qualitätsdarstellungen durchsucht. Zwei Diagrammrenderer bestätigt;
  Modi, Karten, Tabellen und Backend-only-Fähigkeiten getrennt inventarisiert.
- Drei unabhängige Fachprüfungen: Kurs-/Analyse-/Auswahlpfade,
  Performance-/Geldsemantik sowie Qualität/Risiko/Lebenszyklus. DTOs,
  Domainservices, Persistenzreader, Consumer und vorhandene Testfälle gelesen.
- Konsolidierten Vertrag unabhängig gegengeprüft. Präzisierungen zu
  historischem EOD-Mapping, Beobachtungs-/Tageseinheiten, vollständigem
  Tradeergebnis, PF-Summen, DATE_ONLY, tatsächlichen Lessonlinkfeldern und
  getrennten Currentness-/Materialisierungsachsen übernommen.
- Kein Benutzerdepot, kein laufender Scheduler/Monitoringcommand und kein
  Liveprovider wurde für diese Inventur aufgerufen. Keine Aussage über
  tatsächlich gespeicherte instrumentbezogene Historie auf dem Nutzer-PC.

## Dokumentprüfung dieses PRs

Die abschließende Dokumentprüfung umfasst UTF-8, abschließenden Zeilenumbruch,
geschlossene Codeblöcke, auflösbare lokale Markdown-Verweise, tatsächlich
vorhandene Code-/Testdateien, Matrixfelder und `git diff --check`.
Der gezielt gestagte Tree darf außerhalb der sechs Dokumente keine Änderung
enthalten. Backend-/Frontend-/Test-/Workflow-Teilbäume müssen mit Main identisch
sein; der veröffentlichte Git-Tree wird gegen den lokalen Indexbaum gelesen.

**Lokale Anwendungstests wurden für UX4-A nicht ausgeführt.** Es wurden keine
Runtime- oder Testdateien geändert. Die unten aufgeführten Testfälle sind
Planung für die späteren Implementierungen, keine behaupteten UX4-B/C/D-Erfolge.
Die reguläre unveränderte GitHub-CI prüft den tatsächlichen Draft-Head/Testmerge.
Konkrete Commit-, Tree-, Run-/Job-URLs und die abschließend gelesenen Ergebnisse
stehen im PR-Text, damit die Dokumentation nicht durch bloße CI-Nummern erneut
einen anderen ungeprüften Head erzeugt. Ein übersprungener Job zählt nicht als
bestandener Test; alte Main-/UX1-/UX2-Läufe qualifizieren diesen PR nicht.

## Prüfmatrix für die spätere Implementierung

Alle Fälle erwarten vorhandene finanzielle Ergebnisse unverändert. Neue
Tests prüfen Benutzerergebnisse und konkrete Schutzregeln, keine bloßen
JSX-Kopien. Kürzel B/C/D nennen den zuständigen Folgeauftrag; Quellenverweise
stehen im anschließenden Testregister.

| ID / Thema | Erwartung und konkrete Grenzfälle | Zuständig / vorhandene Testanker |
| --- | --- | --- |
| Q01 · Einheiten/Währungen | EUR/USD/CHF getrennt; Indexpunkte, Basis100, Prozent, Brüche, Stück, Scores und Zeiten korrekt; aktuelle EUR-Quote belegt keine historische BUY-Währung | B/C/D; T01–T06, T11 |
| Q02 · Historische Identität | Provider-, Listing-, ISIN-, Mapping-, Preisart-, Quellenmodus- und MIC-Wechsel nur nach tatsächlichen Belegen; EOD ohne historische Mappingrevision nicht rückwirkend anreichern | B/D; T01, T02, T03 |
| Q03 · Original-/Abrufzeit | `observed_at` gegen `retrieved_at`, `captured_at`, `assessed_at`; Retention darf ihren echten Originalpunkt liefern, wiederholter Read/Abrufzeit erzeugt keinen zusätzlichen Originalpunkt oder Frischenachweis; unbekannte Zone bleibt unbekannt | B/D; T01, T02, T09 |
| Q04 · EOD und Kalender | Handelstag bleibt Datum; Wochenende allein kein Gap, unbeobachteter Wochentag bleibt ohne Kalender unbestimmt (Feiertag oder Lücke); kein EOD-Intradaytimestamp; Kalender-/Beobachtungszahl nicht gleichsetzen | B/D; T03, T11 |
| Q05 · DATE_ONLY / DST | Kein Mitternachtsmarker; Originaldatum/-zone bzw. mögliches Intervall. 23-/25-Stundentage, fremde Originalzone und teilweise Periodenüberdeckung bleiben korrekt; kein neuer Tagesbucket | B/C; T02, T04, T05 |
| Q06 · Lücken/fehlende Werte | Ein Punkt, keine Punkte, null, echte 0, nicht berechenbar und Fehler getrennt. Keine Linie über gemeldete Lücke, keine Datenauffüllung oder versteckte Filterung | B/C/D; T01–T05, T09 |
| Q07 · Quellenkonflikt | Zwei Preise zur selben Zeit nicht mitteln; Identitäts-/Währungs-/Providersymbolkonflikt erhalten; andere frische Route heilt gewählte fehlerhafte Route nicht | B/D; T01, T03, T09 |
| Q08 · BUY/SELL/Korrektur | Formen und Texte unterscheidbar; Menge/Preis/Originalzeit/Beleg erreichbar; ersetzte Ausführung nicht doppelt; gleichzeitige Ereignisse einzeln; Storno kein SELL | B/C; T02, T04, T05, T12 |
| Q09 · Historienlimits | 10.000-Samplebudget und begrenzte Retention-/Captureansichten ausdrücklich anzeigen; „Alle“ nicht Vollhistorie; EOD-Punktlimit liefert leere Serie mit POINT_LIMIT_EXCEEDED / SERIES_UNAVAILABLE im regulären Report, keine stille Kurve und nicht zwingend einen HTTP-Fehler | B/D; T01, T03, T09 |
| Q10 · Getrennte Performancepopulationen | Offener Teilverkauf im SELL-Bericht; genau ein Lifetime-Ergebnis pro vollständig abgeschlossenem Trade; frühere Teilverkäufe bleiben Quellen des Volltradeergebnisses | C; T04–T06, T13 |
| Q11 · Bestehende Statistikgoldens | Synthetische bestehende Referenz `100,-50,0,200`: N4, Trefferquote 50.00 %, Ø62.50 EUR, Median50.00 EUR, PF6.00. Grafik übernimmt Ownerwerte unverändert | C; T05 |
| Q12 · PF und Fehlzustände | Gewinne ohne Verluste ⇒ undefiniert; nur Verluste ⇒ 0; alle neutral ⇒ PF undefiniert. EMPTY, COMPLETE, PARTIAL, NOT_COMPUTABLE mit unterschiedlichen Geld-/N-/Statistikzuständen | C; T04, T05 |
| Q13 · Vorzeichen/Rundung | ±0.004 behalten Rohvorzeichen; HALF_EVEN, Minor Units und Rundungsdifferenz des Reportowners bleiben erhalten; kein Moneyformatter-Austausch | C; T05, T06 |
| Q14 · Überlappende Zähler | Abschlussgruppen disjunkt, deren Untergruppen nicht doppelt. SELLs ≠ stornierte Trades; gehaltene Produkte ≠ Positionen; Positionscoverage-Summary nicht pauschal stapeln | C/D; T04, T05, T09 |
| Q15 · Scope/Seite/Filter | N, Summe, Statistik und Berichtsbasis ändern sich nicht durch lokale Seiten, Legende oder Ausschnitte; vollständiger Scope und Darstellungsfilter klar bezeichnet | B/C; T06, T07, T08 |
| Q16 · Antwort-/Kontextisolation | A→B→A, verspäteter Erfolg/Fehler, Modus-/Zeitraumwechsel, reloadToken und bestätigter Readback: keine fremden/alten Werte oder verlorenen Entwürfe. Bloßer Hash-/Bereichswechsel desselben Trades ohne zusätzliche Trade-/Positions-/Timeline-Reads | B/C/D; T02, T06, T08, T10 |
| Q17 · Vollständige Readgrenzen | Report-Ressourcenlimit/Source-Limit ergibt erklärten Fehler, keine abgeschnittene Summe oder „keine Quellen“. Resultate aus einem Reportbasisstand ersetzen sich zusammen | C/D; T06, T10, T13 |
| Q18 · Prozessscope/Recovery | Restart, kein fertiger Lauf, retained/cache/deferred, laufender vs fertiger Versuch: kein Uptimebeleg, kein künstlicher Erfolg oder Rücksetzen von Diagnosefehlern | D; T09 |
| Q19 · Lebenszyklus/Pins | Externer Trade/manueller Plan ohne Analyse ist zulässig; fehlend, nicht lesbar, nicht auflösbar getrennt. Exakte Review-/Journal-/Lessonpins, Relation und separate Readfenster erhalten | D; T10, T12 |
| Q20 · Currentness/Materialisierung | Draft aktuell ≠ final; final stale ≠ current; aktuelle Materialisierung false trotz alter Evidence. Keine Lessonreview-/Freigabeinformation aus bloßem Link erfinden | D; T10, T12 |
| Q21 · Risiko-/IV-Grenzen | RV nicht IV; fehlende IV/Paare/Greeks kein 0-/niedrig-Signal; raw ATR und Adjusted-SMA nicht ungeprüft überlagern. Modelllabor hypothetisch, isolierte Effekte nicht additiv | D; T11 |
| Q22 · Finanz-/Buchungsinvarianz | Backend-Finanzownerdateien unverändert; vorhandene Average-Cost-, effektive History-, Währungs-, Vollabschluss- und Statistikregressionen weiter grün | B/C/D; T02, T04–T06, T13 |
| Q23 · Read-/Providergrenzen | Öffnen, Fokus, Legende und Filtern lösen keine zusätzliche Mutation, Providerabfrage, Journal-/Lessonanlage oder Aktivierung aus. Bestehende Health-GETs nicht pauschal als providerfrei behandeln | B/C/D; T02, T09–T13; Request-/DB-Guards |
| Q24 · Mobile/Zoom | 320/390/1280 CSS-Pixel, 200 % Zoom und Hinweisflächen zusätzlich 400 %, lange Quellnamen/Währungen, >6 und >12 Serien, mehrere gleiche Punkte: kein Dokumentoverflow, erreichbare Legenden/Details/Einheiten | B/C/D; T07, T08, T12; tatsächliche Browserfälle ergänzen |
| Q25 · Tastatur/Fokus | Tab/Shift-Tab, Enter/Space, vorhandene Pfeiltasten, Fokus nach Auswahl/Retry/Navigation; kein Hover-only-Zugriff und keine tausendfach nötige Tabfolge | B/C/D; T07, T08, T12; neue Grafikfälle ergänzen |
| Q26 · Semantische Alternative/Kontrast | Name, Wert, Einheit, Originalzeit, Quelle und Grund über Tabelle/Liste verfügbar; Farbe plus Form/Text; sichtbarer Fokus; keine Doppel-/Daueransage unveränderter Hinweise. Screenreader-/Kontrastnachweis nur nach realer Prüfung behaupten | B/C/D; T07, T08, T12; gesonderte manuelle Abnahme |

## Vorhandenes Testregister

Die Dateien existieren auf der angegebenen Prüfbasis. Gruppenbezeichnungen
sind nur Verweise dieser Dokumentation, keine neue Test-/Featurearchitektur.

| ID | Bestehende Dateien / prüfbarer Schwerpunkt |
| --- | --- |
| T01 | [test_warrant_price_history.py](../../tests/unit/backend/features/market_data/test_warrant_price_history.py): Historienidentität, Originalzeit, Retention, Budget, Ausschlüsse |
| T02 | [test_position_price_history.py](../../tests/unit/backend/features/trade_position/test_position_price_history.py), [PostgreSQL-Historie](../../tests/integration/backend/database/test_position_price_history_postgres.py): effektive Buchungen/Währungen, Date-only, Storno, Read-only |
| T03 | [test_time_series.py](../../tests/unit/backend/features/analysis/test_time_series.py), [test_chart_service.py](../../tests/unit/backend/features/analysis/test_chart_service.py), [PostgreSQL-Marktcharts](../../tests/integration/backend/database/test_market_charts_postgres.py): EOD-Vergleich, Lücken, Grenzen, Renditebasis |
| T04 | [test_report.py](../../tests/unit/backend/features/performance/test_report.py), [test_periods.py](../../tests/unit/backend/features/performance/test_periods.py): SELL-Population, Geld-/Periodenzustände, DST |
| T05 | [test_closed_report.py](../../tests/unit/backend/features/performance/test_closed_report.py), [test_closed_statistics.py](../../tests/unit/backend/features/performance/test_closed_statistics.py): Lifetime-Kohorte, acht Gruppen, unabhängige Goldens, Präzision |
| T06 | [test_historical_currency_reports.py](../../tests/unit/backend/features/performance/test_historical_currency_reports.py), [PerformanceWorkspace.test.tsx](../../frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx), [ClosedTradesPage.test.tsx](../../frontend/src/features/performance/pages/ClosedTradesPage.test.tsx), [RealizedGrossPage.test.tsx](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx): Herkunft, Filter/Seite, Antwortbindung |
| T07 | [PositionPriceHistory.test.tsx](../../frontend/src/features/operational_workspace/components/PositionPriceHistory.test.tsx), [priceHistoryPresentation.test.ts](../../frontend/src/features/operational_workspace/services/priceHistoryPresentation.test.ts), [position-price-history.spec.ts](../../tests/e2e/position-price-history.spec.ts): vorhandene Grafik/Evidenz/Mobile; neue Serien-/Markerinteraktion ergänzen |
| T08 | [TimeSeriesChart.test.tsx](../../frontend/src/features/analysis/components/TimeSeriesChart.test.tsx), [MarketChartsPage.test.tsx](../../frontend/src/features/analysis/pages/MarketChartsPage.test.tsx), [market-charts.spec.ts](../../tests/e2e/market-charts.spec.ts), [performance-workspace-ui.spec.ts](../../tests/e2e/performance-workspace-ui.spec.ts): Einheiten, Legende, Kontext, echte Browsernavigation |
| T09 | [test_position_quote_coverage.py](../../tests/unit/backend/features/market_data/test_position_quote_coverage.py), [test_quote_coverage.py](../../tests/unit/backend/features/market_data/test_quote_coverage.py), [test_quote_history.py](../../tests/unit/backend/features/market_data/test_quote_history.py), [test_refresh_quality_diagnostics.py](../../tests/unit/backend/features/market_data/test_refresh_quality_diagnostics.py), [test_refresh_identity_evidence.py](../../tests/unit/backend/features/market_data/test_refresh_identity_evidence.py): Scope, Capture/Recovery, Quellidentität |
| T10 | [test_source_view.py](../../tests/unit/backend/features/trade_position/test_source_view.py), [test_trade_source_view_postgres.py](../../tests/integration/backend/test_trade_source_view_postgres.py), [TradeSourcesView.test.tsx](../../frontend/src/features/trade/components/TradeSourcesView.test.tsx): getrennte Reads, Pins, Fehler und Quellenlimits |
| T11 | [test_risk_signals.py](../../tests/unit/backend/features/position_monitoring/test_risk_signals.py), [test_risk_readers.py](../../tests/unit/backend/features/position_monitoring/test_risk_readers.py), [test_iv_readiness.py](../../tests/unit/backend/features/position_monitoring/test_iv_readiness.py), [PositionRiskPanel.test.tsx](../../frontend/src/features/alert/components/PositionRiskPanel.test.tsx), [IvRiskPanel.test.tsx](../../frontend/src/features/alert/components/IvRiskPanel.test.tsx), [position-risk.spec.ts](../../tests/e2e/position-risk.spec.ts): Ownerqualifikation und Modellgrenzen |
| T12 | [test_ft011_materialization_status_service.py](../../tests/unit/backend/features/learning/test_ft011_materialization_status_service.py), [test_ft011_evidence_history.py](../../tests/unit/backend/features/learning/test_ft011_evidence_history.py), [post-trade-handoff-pin.spec.ts](../../tests/e2e/post-trade-handoff-pin.spec.ts), [quote-coverage.spec.ts](../../tests/e2e/quote-coverage.spec.ts): historische Evidence, Pins und Browserqualität |
| T13 | [test_realized_gross_learning_independence_postgres.py](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py), [realized-gross-report-postgres.spec.ts](../../tests/e2e/realized-gross-report-postgres.spec.ts), [closed-trades-report-postgres.spec.ts](../../tests/e2e/closed-trades-report-postgres.spec.ts): native Ownerabläufe, Finanz-/Learningtrennung und bestehende DB-Guards |

## Reproduzierbare Prüfeinstiege für Folge-PRs

Vor Ausführung die im Repository festgelegte Toolchain bereitstellen:
Python 3.12 und Node 22.16.0/npm 10.9.2 sowie gepinnte Abhängigkeiten. Synthetische
Fixtures bleiben als Testdaten erkennbar. PostgreSQL-/E2E-Schreibtests laufen
ausschließlich im vorhandenen Wegwerf-Stack mit den bestehenden Guards, nie
gegen persönliche Daten. Die folgenden Befehle sind **geplant, hier nicht
ausgeführt**; betroffene Suiten nach tatsächlichem Delta auswählen.

```bash
PYTHONPATH=backend:. python -m pytest -c backend/pyproject.toml tests/unit/backend/features/market_data/test_warrant_price_history.py tests/unit/backend/features/trade_position/test_position_price_history.py tests/unit/backend/features/performance -q
npm --prefix frontend run test -- src/features/operational_workspace/components/PositionPriceHistory.test.tsx src/features/performance
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run format
npm --prefix frontend run build
git diff --check
```

Die unveränderten Workflows
[Backend](../../.github/workflows/backend.yml),
[Frontend](../../.github/workflows/frontend.yml) und
[End-to-End](../../.github/workflows/e2e.yml) sind die verbindlichen vollständigen
Gates. Backend-Coverage bleibt 85 %; Frontend Lines/Functions/Statements jeweils
80 %, Branches 70 %. Gezielte lokale Suiten ersetzen diese Gates nicht. Es
werden keine Tests, Assertions, Provider-/DB-Guards oder Limits abgeschwächt.

## Integrationsübergabe und nächster Schritt

| Verantwortlich | Konkrete Übergabe / offener Nachweis |
| --- | --- |
| UX-1 / Fachowner | Bestehende Werte/Provenienz verwenden; fehlende Buckets, historische Identität oder zusätzliche Quellenauflösung nur separat qualifizieren |
| UX-2 | Genaue Einbindungsstellen, Props, öffentliche Importgrenze, Readowner, Invalidierung, Anker und konkurrierende Dateien für B/C/D bestätigen |
| UX-3 | Hinweisvertrag #314 gemeinsam konkretisieren: Begriffe und Präsentationspriorität; fachliche Schwere/Blockierung bleibt beim bestehenden Domain-Owner |
| UX-4 | Diagrammgestaltung, Kennzahlenerklärung, Datenlücken sowie nachgewiesene Mobile-/Tastaturbedienung |
| Master-Lead | Eigene UX4-Übergabe mit den fünf Dokumenten aus #313 abgleichen; konkrete Dateiabstimmung und Integrationsfolge koordinieren; keine Freigabe hier vorweggenommen |

Diese sechs Dokumente bilden die vom Master angeforderte eigenständige
Leadübergabe: Ziel/Nicht-Ziele und Ausgangscommit oben; vollständige Dateiliste
im Lieferumfang und PR; Bestandskomponenten/Daten-/Berechnungsowner in der
Inventur; Schnittstellen, Änderungsgrenzen und Abschlusskriterien im Vertrag
und den drei Startprompts; tatsächliche Prüfung hier und an Head/Testmerge/CI
gebunden im PR-Text. Fachliche Statusänderungen gehören ausschließlich in den
bestehenden Backlog. Die Prompts reservieren keine gemeinsamen Dateien und
geben weder fremde Branches noch Produktintegration frei.

**Ein nächster Schritt:** Den dokumentierten UX4-B-Schnitt samt bestehender
`PositionPriceHistory`-Einbindung mit UX-2 abstimmen. Danach kann der
eigenständige B-Startprompt auf dem dann aktuellen Main ausgeführt werden.
UX4-C und UX4-D bleiben unabhängig vorbereitete Aufträge mit ihren jeweiligen
Daten- und Einbindungsvoraussetzungen.

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | UX4-A-Codeaudit, unabhängiger Vertragsreview und 26 Fälle für die spätere Implementierungsabnahme; keine Runtimeänderung |
