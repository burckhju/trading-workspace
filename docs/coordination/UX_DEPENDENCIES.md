# UX-Abhängigkeiten und Integrationsfolge

Diese Datei steuert technische Reihenfolge und Konfliktauflösung, keine fachlichen Aufgabenstände. Maßgeblich bleiben [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md), [Ownership](UX_OWNERSHIP.md) und [gemeinsame Verträge](UX_SHARED_CONTRACTS.md). Konkrete aktuelle Heads/CI: [Integrationsprotokoll](UX_INTEGRATION_STATUS.md).

## Gemeinsame Änderungsflächen

| Schnittstelle | Führender Owner | Abhängigkeit vor Integration |
|---|---|---|
| UX-1 / UX-2: `TradeManagementPage.tsx`, Formulare, Readback | UX-2 für Hostintegration | UX-1 liefert Preview-/Reload-Teilschnitt; beide prüfen Navigation, Entwurfserhalt und Invalidierung. |
| UX-1 / UX-2: Performancekontext und zwei gemeinsame Seitentests | UX-2 für Shared-/URL-Integration | Ein gemeinsamer `reportTimezoneError`; UX-1 erhält Browserableitung, Performanceowner die Finanzvalidierung. Beide Testumfänge erhalten. |
| UX-1 / UX-3: Validierung und Herkunft | UX-1 für Eingabefakten | UX-3 konsumiert vorhandene Feld-/Reason-/Quelleninformationen; Darstellung ändert keine Domainentscheidung. |
| UX-2 / UX-3: Hinweisposition und Fokus | UX-2 | UX-3-Hinweismuster vor Hosteinbindung abstimmen; relevante Blockierung bleibt sichtbar. |
| UX-2 / UX-4: Diagrammslot und Nachladen | UX-2 | UX-4 liefert vorhandenen lesenden Baustein; keine neue Positions-/Kursabfrage allein durch Hashnavigation. |
| UX-3 / UX-4: Qualitätsdarstellung | UX-3 | UX-4 konsumiert konsistente Erklärung; leer, Fehler, fehlend, veraltet und gekürzt bleiben unterscheidbar. |
| Alle: APIs und Domainmodelle | Jeweils genau der Domain-Owner aus der Ownership-Tabelle | Additive Felder/Reads und historische Bedeutung erst mit allen betroffenen Consumern klären. Kein gemeinsamer „UX-Domainowner“. |

## Integrationsreihenfolge Phase 1

Stand 01.11.2026: Alle sechs eingehenden PR-Heads sind einzeln gegen Main `1883f7f330719453958f8be1dd51d48db816662e` ohne Rückstand und mit neun erfolgreichen Prüfjobs qualifiziert; alle bleiben Draft. Dieser Einzelbefund ist keine fachliche Abnahme und keine Mergefreigabe. Änderungen an Heads oder Basis erfordern neue Nachweise.

| Reihenfolge | Schnitt | Entscheidung, Risiko und notwendiges Folgegate |
|---|---|---|
| 1 | **Korrigierter Koordinations-PR #313** | Eigene fünf Dokumente; keine Dateiüberschneidung mit #311/#312/#314/#315/#316, keine Produkt-/Finanz-/Backlogstatusänderung. Der alte Head war grün, der korrigierte benötigt seine eigene aktuelle CI. Gemeinsame Owner-/Hinweisentscheidung zuerst zur ausdrücklichen Integration vorlegen. |
| 2 | **UX4-A #316 als Dokumentationsvertrag** | Sechs neue Markdown-Dateien, Runtime identisch zu Main, keine gemeinsame Datei mit #313/#311/#312. Auch ohne #313 technisch integrierbar: Koordinationsquellen sind commitgepinnt, keine fehlenden lokalen Dateien. Organisatorisch nach #313; nach dessen Integration neuen Mainbezug/Testmerge erneut prüfen. Kein Vorziehen von UX4-B/C/D-Produktcode. |
| 3 | **Ein konsolidierter UX3-Dokumentationsvertrag auf #314** | Zuerst UX3-K-Auftrag und vier Typpräzisierungen erfüllen; Pflichtübernahmen aus #315 nachweisen. Aktuelle #314-/#315-CI qualifiziert noch keinen konsolidierten Vertrag. Stabile gemeinsame Begriffe/Typen vor abhängigen Hinweisoberflächen. #315 nicht zusätzlich integrieren. |
| 4 | **UX2-A #311 mit kleinem additivem Shared-Helper-Schnitt** | Navigation, Plan-/Lesson-/Berichtsrückwege und Shared-Grenze sind bereits implementiert. Nur die belegte gemeinsame Helperlücke schließen; normale CI und betroffene Navigation-/Performancefälle auf neuem Head prüfen. UX2 bleibt Hostintegrator. |
| 5 | **UX1 #312 auf dem tatsächlich integrierten UX2-Mainstand** | Öffentlichen BUY-Preview-Adapter qualifizieren; Helper importieren; gezielt Host-/Testhunks erhalten. Dreiwegekonflikt bewusst lösen, keinen Featurebranch blind übernehmen. Neuer kombinierter Head/Testmerge/Tree mit vollständigen normalen Gates und gemeinsamer Regressionsmatrix erforderlich. |

Nach diesen Vertrags- und Codeintegrationen folgen getrennte Produktaufträge: genau ein UX3-B1/F1-Pilot in `RealizedGrossSources`, danach die davon abhängigen UX4-Darstellungsschnitte. Unabhängige lokale Diagramm-/Quellenanalyse kann parallel erfolgen; gemeinsame Hoständerungen bleiben seriell bei UX2. Diese Folgeaufträge sind keine bereits integrierten Bestandteile von #314/#315/#316.

#313 und #316 benötigen keinen Produktmerge voneinander oder von #311/#312. Ihre Dokumentation lässt sich unabhängig beurteilen; die gewählte Reihenfolge macht den Mastervertrag zum gemeinsamen Ausgangspunkt. Der konsolidierte UX3-Dokumentationsschnitt kann ebenfalls ohne vorgezogenen Hinweisrenderer fertiggestellt werden. Die technische Leadabstimmung benötigt keine Merges, um jetzt zu beginnen.

#311 und #312 stammen von derselben Mainbasis. Erst der kleine vereinbarte Helperexport erzeugt eine bewusste additive Integrationsabhängigkeit. Die Reihenfolge UX2 vor UX1 folgt Host-/Navigationsownership und der Vermeidung einer zweiten Parserfassung. Kein früherer grüner Einzel-PR, kein sauberer Textmerge und keine unveränderte Versionsnummer ersetzt den gemeinsamen Laufzeitnachweis.

Die Alt-PRs #187, #197, #205, #207 und #220 sind keine Voraussetzung dieser Folge. Ihre ursprünglichen Diffs, überholten Basen und inzwischen vorhandene Main-Implementierung müssen separat mit dem jeweiligen Fachowner abgeglichen werden. Insbesondere #205 liefert keine fehlende aktuelle Chartfunktion; #207 enthält am geprüften Head lediglich einen Entwicklungsworkflow. Keine eigenmächtige Übernahme oder Schließung.

## Konfliktmatrix #311/#312

Vollständig verglichen: **#311 `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` (47 Dateien)** und **#312 `8f67442daac6879d7dfb28416f2171f67aead0e5` (33 Dateien)** gegen denselben Main. Genau vier gemeinsame Dateien. Der lokale rechnerische Dreiwegevergleich meldet **einen** Textkonflikt, im Performance-Service. Er verändert keine Branchreferenz und ist kein getesteter kombinierter Produktstand.

| Gemeinsamer exakter Pfad | #311 | #312 | Konflikt / verbindliche Auflösung | Integrator |
|---|---|---|---|---|
| `frontend/src/features/trade/pages/TradeManagementPage.tsx` | Shared-Navigation, Bereiche/Anker, `tradeLookupQuery`, historische Pins und Berichtsrückkontext | `ExecutionCurrencyPreview` statt bisherigem Override, `historyReloadToken` für SELL und Nachkauf | Textuell konfliktfrei. Beide Hunks erhalten: Navigation/Anker plus kontrollierter Preview-/Reload-Teilschnitt. Identität, Dirty/Busy, manuelle Werte und bestehende Readbackgrenze gemeinsam prüfen. | UX2; UX1 prüft Eingabeverhalten |
| `frontend/src/features/performance/services/performanceReportContext.ts` | Reine URL-/Filterfunktionen nach `shared/trade-workspace-navigation/realizedReportNavigation.ts` verschoben, kompatible Featureexporte | `reportTimezoneError` extrahiert; Browserzone in `initialPerformanceFilters` verwendet | Echter Textkonflikt: verschobene Funktion versus Änderung am alten Ort. UX2 exportiert den vorhandenen reinen Helper einmal in Shared, `reportFiltersErrors` nutzt ihn dort. UX1 importiert ihn; Browserableitung bleibt im Feature, Finanzvalidatoren unverändert. | UX2; Performanceowner prüft Vertragsgleichheit |
| `frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx` | Genauere SELL-Rücklinkassertionen mit Kontext einschließlich Seite 101 | Explizite Berichtszonenwahl und abweichende Browserzone | Textuell konfliktfrei; beide Assertionsätze erhalten, Fixturekontext und Zeitzonenmocks gemeinsam qualifizieren. | UX2 für kombinierte Datei; UX1 für Zonenfälle |
| `frontend/src/features/performance/pages/RealizedGrossPage.test.tsx` | Genaue Trade-/Quellen-/Berichtsrückwege | UTC-feste Auswahl-/Fixtureannahmen | Textuell konfliktfrei; keine Rücknahme der genauen URLs oder von URL-Vorrang/negativen Kontextfällen. | UX2 für kombinierte Datei; UX1 für Zonenfälle |

Weitere semantisch gemeinsame Flächen sind keine zusätzlichen Textkonfliktdateien:

| Fläche | Belegter Zustand / Grenze | Verbleibender Auftrag |
|---|---|---|
| Öffentliche Navigation | In #311 bereits tatsächlich unter `shared/trade-workspace-navigation` implementiert; Lesson-Consumer korrigiert. | Erhalten, keine erneute Entwicklung. Closed-/SELL-Parser, Limits 100/1000 Seiten, Definitions-/Basisvalidatoren nicht zusammenziehen. |
| Erstkaufvorschau | #312 führt neue interne `trade/components`-Imports in `ProductSelectionPage.tsx` ein. Die korrigierte Navigationsgrenze löst das nicht. | UX1: exakt den schmalen [öffentlichen BUY-Adapter](UX_SHARED_CONTRACTS.md#öffentliche-grenze-für-die-erstkaufvorschau) mit vorhandenen kontrollierten Draftprops umsetzen; Domainowner prüfen. |
| Validierung / Quellen / Währung | Bestehende historische Resolver und Read-only-Preview-GETs in #312, erneute Captureprüfung; UNKNOWN/MIXED/CONFLICT bleiben unterscheidbar. | Inputformat-/DST-Feedback beim Formular; Preview keine Bestätigung und keine neue Finanz-/FX-/Währungsregel. Keine ungesicherte Umdeutung heutiger Stammdaten. |
| URL- und Trade-Kontext | #311 bewahrt exakte Plan-/Review-/Journal-/Lessonpins sowie typgerechten Reportkontext; echter Tradewechsel entfernt fremde Pins. | Kontext-/Duplikatvalidatoren und Generation-/Abortschutz erhalten; Hash nicht in Preview-/Chartreadschlüssel aufnehmen. |
| Entwürfe / Readback | #311 schützt Navigation; #312 bringt Previewreads und Invalidierung hinzu. | Zwei gleichzeitige Entwürfe, Busy, bestätigtes Verwerfen, erfolgreicher Write mit fehlgeschlagenem Readback und spätes A→B→A gemeinsam nachweisen. |
| Browserfixture / Preview | `tests/e2e/trade-workspace-navigation.spec.ts` aus #311 kennt die neuen Preview-GETs noch nicht; unbekannte API-Pfade liefern den generischen 503-Fallback. | UX2 ergänzt mit UX1 eine erfolgreiche Previewantwort und explizite GET-Zählung. Ein grüner Navigationstest nur im Preview-Fehlerfallback ist kein gemeinsamer Herkunftsnachweis. |
| Performance / Charts / Hinweise | Neue Rückwege in `RealizedGrossSources` betreffen den späteren UX3-Piloten. UX4-Charts nutzen bereits vorhandenen Hostslot. | Erst aktuellen Code-/Vertragsstand konsumieren; keine parallelen Host-/Hinweis-/Finanzmodelle. |

Der exakte gemeinsame Vertrag steht in [UX_SHARED_CONTRACTS](UX_SHARED_CONTRACTS.md#exakter-integrationsvertrag-ux1ux2). MASTER entwickelt den erforderlichen Produktpatch nicht selbst und führt keinen gegenseitigen Featurebranch-Merge aus.

## Gemeinsame Regressionen

| Bereich | Erforderlicher beobachtbarer Nachweis |
|---|---|
| Kontext / Navigation / Eingaben | Ungespeicherter SELL- und Korrekturentwurf gleichzeitig über Bereichswechsel erhalten; echte Pfad-/Query-/Tradewechsel korrekt geschützt; Busy blockiert Verwerfen; A→B→A und verspätete Erfolge/Fehler einschließlich Unmount isoliert. |
| Reads / Wiederverwendung | Bereichswechsel löst keine zusätzlichen Trade-/Positions-/Timeline-/Preview-Reads aus. Erfolgreicher qualifizierter Buchungs-/Quellenreadback aktualisiert Preview und Historie, ohne manuelle Eingaben zu löschen. Fehlgeschlagener oder überholter Readback ist kein qualifizierter neuer Stand und macht einen bestätigten Write nicht ungeschehen. |
| Historische Quellen | Plan-, Review-, Journal- und Lessonpins bleiben exakt. Ungültige/mehrfache Pins werden nicht still auf aktuell umgebogen; fremde Quelle erzeugt keine gültige Anzeige. |
| Währung / Formulare | Vorhandene Resolver und UNKNOWN/MIXED/CONFLICT erhalten; Preview erzeugt weder `currency_confirmation` noch Draftänderung; Capture prüft erneut. Produkt-/Tradewechsel, Quellenkorrektur, Zeit-/DST-/DATE_ONLY-Fälle und manuelle Code-/Notizwerte prüfen. Berichtszone unter UTC und abweichender Browserzone, gültige URL mit Vorrang, ungültige/mehrfache URL ohne stillen Ersatz; fehlende Browserzone mit bestehendem Fallback. |
| Journal / Lessons | Neue Lesson-URLs mit Query/Hash korrekt konsumieren: ID über URL-Pfad lesen; Trade-/Versions-/Rückkontext ausdrücklich prüfen. Schreibanzahl, Currentness, Korrektur und lokale API-Grenze erhalten. |
| Hinweise / Aktionen | Fachliches Risiko, Datenqualität, Scheduler und Zustellung getrennt; Rendering/Navigation ohne Mutation; Fehler nicht als leer oder gesund behandeln. |
| Charts / Statistik | Originalwerte, Währung, Preisart, Quelle, Lücke und Zeitgenauigkeit erhalten; Tabellenfallback, Kürzung und Fehler sichtbar; Gesamtkohorte statt sichtbarer Seite. |
| Responsivität / Barrierefreiheit | Kleine und große Viewports, Zoom, Keyboard, Fokus nach Navigation, Live-Regionen und alternative Datentabelle. Automatisierte Fälle und noch fehlende manuelle Abnahme getrennt dokumentieren. |

Vorhandene gezielte Suites: `TradeManagementPage`, `TradeManagementPriceHistory`, `TradeWorkspaceNavigation`, `ExecutionCurrencyPreview`, Performance-Seiten, `TradeAlertsPanel`, `MonitoringRuntimePanel`, `PositionPriceHistory`, `TimeSeriesChart`; Browserpfade `trade-workspace-navigation`, `execution-currency-reuse`, `post-trade-handoff-pin`, `post-trade-journal-postgres`, `position-price-history`. Neue Dateien aus offenen PRs sind vor deren Integration noch nicht Main-Bestand.

Für UX1/UX2 zusätzlich `TradeManagementContext`, `AdditionalPurchasePanel`, ProductSelection-Kontextfälle, `reportReturn`, `workspaceNavigation`, `performanceReportContext`, `ClosedTradeResult` und die vollständigen realisierten/abgeschlossenen Performanceberichte ausführen. Im Browser die bestehenden Guards in `trade-capture-safety`, `trade-capture-dst`, `trade-execution-consolidation` sowie beide Report-/Quellenrundwege erhalten. Die unveränderten PostgreSQL-Owner-Jobs für Performance und Journal/Evidence bleiben erforderlich; lokal abgefangene Reads beweisen keinen echten Write-/Datenbankpfad.

Die kombinierte Navigationsfixture muss erfolgreiche Währungsvorschau und sichtbare Herkunft, manuelle Code-/Notizwerte, unveränderte Preview-GET-Zahl bei Hashwechsel und späte Antworten ausdrücklich prüfen. Ebenso einen getrennten Fehlerfall erhalten; den vorhandenen 503-Fallback weder als Erfolg zählen noch durch eine generische immer-grüne Antwort verdecken.

Nachweise immer mit Main-SHA, Implementierungshead, tatsächlich ausgechecktem Testmerge und Tree, Befehl, Toolchain/Zeitzone, Lauf-/Jobnummer, Ergebnis sowie regulären Skips binden. Der neue kombinierte Zustand benötigt alle normalen CI-Gates; gezielte lokale Tests ergänzen sie. Ändert sich ein Head oder Main, wird nur der konkret betroffene Nachweis erneuert, bevor eine Integration entschieden wird.

## Präzise Folgeaufträge

Die folgenden Rollenaufträge sind in diesem Koordinations-PR dokumentiert. Sie erfinden keine GitHub-Assignees und belegen keinen Empfang in einem anderen Chat. Jeder Lead bindet seine Rückmeldung an den eigenen tatsächlichen neuen Head; keine Änderung fremder Featurebranches durch MASTER.

### UX2 — Gemeinsamen Helper und Hostintegration führen

- Ausgang: #311 `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32`, #312 `8f67442daac6879d7dfb28416f2171f67aead0e5`, aktuelle Mainbasis erneut prüfen.
- **Erster kleiner Quellschnitt:** `shared/trade-workspace-navigation/realizedReportNavigation.ts`, dessen öffentlicher `index.ts` und gezielte Tests. Vorhandenen UX1-`reportTimezoneError` semantisch unverändert übernehmen, genau einmal exportieren und in `reportFiltersErrors` verwenden. Kein Browserzugriff in Shared und keine Finanzvalidatorverschiebung. #311 bleibt ohne UX1-Preview ausführbar und rückwärtskompatibel.
- **Spätere Hostintegration:** gemeinsame Konfliktauflösung in den vier Matrixdateien mit UX1 gezielt durchführen; UX2-Navigation plus UX1-Preview-/Reloadhunks erhalten. Die dazu nötigen Regressionen einschließlich `tests/e2e/trade-workspace-navigation.spec.ts` ergänzen. Kein neues Draft-/Timeline-/Readbackmodell. Aktuelle Hostslots für UX3/UX4 explizit bestätigen.
- Abschluss: vollständiger Diff, Gegenüberstellung beider erhaltenen Funktionsumfänge, aktueller Head/Testmerge/Tree, unveränderte CI und gemeinsame Regressionsnachweise. Vorher keine kombinierte Mergefähigkeit behaupten.

### UX1 — Eingabeumfang erhalten und öffentliche Previewgrenze schließen

- Ausgang: #312 `8f67442daac6879d7dfb28416f2171f67aead0e5`; später auf dem tatsächlich integrierten UX2-Stand neu qualifizieren. Keine Übernahme eines ungeprüften gesamten #311-Featurebranches.
- **Unabhängig vorbereitbar:** `trade/public/InitialPurchaseCurrencyPreview.tsx`, `trade/index.ts`, der Previewconsumer in `product_selection/pages/ProductSelectionPage.tsx`, öffentliche Adaptertests und bestehender Capture-/Qualifikationsvertrag. Exakte schmale Props und BUY-Bindung aus Shared Contracts; kein Resolver-/Command-/Vorbelegungsduplikat.
- **Nach UX2-Helper:** `performanceReportContext.ts` importiert denselben Shared-Helper; `initialPerformanceFilters`, Browserfallback, URL-Vorrang und sämtliche bisherigen Performanceprüfungen bleiben erhalten. Hosthunks und die beiden Testdateien an UX2 übergeben; eigene SELL-/Nachkauf-/Erstkauf-, Quellen-, DST- und Asyncregressionen durchführen.
- TradePosition-Owner prüft die bereits implementierten additiven Preview-DTOs/GETs/Resolverwiederverwendung; ProductSelection-Owner den öffentlichen Consumer und unveränderte explizite Kaufbuchung. Abschluss erst mit neuem kombinierten Code-/CI-Nachweis, ohne automatische Bestätigung oder neue Finanzregeln.

### UX3 — #314 konsolidieren, danach genau einen lesenden Piloten liefern

- Ausgang: #314 `52a24266dce1ec048b23360b4b75d5b3f54d746b`, #315 `d9d85f1af3159c4356c8773d076decbf1dc604e4`; alle zehn plus fünf Diffdateien sind verglichen.
- **UX3-K ist ein Dokumentationsauftrag:** kanonische Dateien unter `docs/ui/ux-3/`, genau ein Typmodell, vier Typpräzisierungen und vollständige Pflichtübernahmematrix aus Shared Contracts. Inventur-/Test-/Rolloutzeilen auf einen Katalog abbilden, T04/TC-01 präzisieren. Nur belegte kanonische Verweise in `workspace-statusmeldungen.md`/`PRODUCT_BACKLOG.md`; kein neuer fachlicher Status oder Produktabschluss.
- #315 als Quellreview referenzieren, nicht blind mergen und nicht schließen. Keine zweite normative Vertragsdatei oder parallele B/C/D-Gesamtmigration. Bestehende 48/24 Abnahmefälle eindeutig zuordnen; zusätzliche Typgegenfälle ergänzen.
- Abschluss UX3-K: Dokumentprüfung, strict/noEmit-Typcheck, vollständiger Übernahmebeleg, neuer Main-/Head-/Treebezug und aktuelle PR-CI. Runtime, Workflows und Finanzverträge bleiben außerhalb dieses Auftrags.
- Erst danach **B1/F1**: `RealizedGrossSources` im dann aktuellen #311/#312-Gesamtstand; gespeicherte Fakten und bestehender Buchungslink, kein neuer Read/Write. Performanceowner prüft Wirkung, UX1 Herkunft/Previewgrenze, UX2 Kontext/Guard/Fokus, UX3 Sprache/Dedupe/Ansage. Geplante Abnahmefälle sind erst nach Ausführung Produktnachweise.

### UX4 — Vorhandenen Chartslot und kanonischen Hinweisvertrag konsumieren

- Ausgang: #316 `ae8c792f3e3ad74994894fac581cb4cf81ba5de7` bleibt ein unabhängig qualifizierter Dokumentationsschnitt; keine belegte Änderung an seinem Branch durch MASTER nötig.
- Vor UX4-B aktuellen Main, konsolidierten UX3-Head und UX2-Host neu binden. Vorhandenen Slot `#position-price-history`, Props `tradeId`/`positionId`/`reloadToken`, Readowner und Shared-Navigation bestätigen; alte Vertrags-Snapshots nicht zum zweiten Hinweis-API-Modell machen.
- Änderungen auf vorhandene `PositionPriceHistory`, `PositionPricePlot`, `PositionPriceHistoryEvidence` und Präsentationshelper/-tests begrenzen: Quellenwahl, Belegzugriff, Mobile/Tastatur. Keine neue Historie, Finanzrechnung, Timelineabfrage oder Notice-Engine.
- Abschluss: keine Mehrreads bei Hash/Fokus, erhaltene Drafts, korrekte erfolgreiche/gescheiterte Readbacks, A→B→A mit alten Erfolgen/Fehlern, sichtbare Lücken, DATE_ONLY-/Währungs-/Preisartgrenzen, 320/390/1280 CSS-Pixel, Zoom/Tastatur und zugängliche Evidenz. C/D behalten getrennte Reportpopulationen bzw. getrennte Lifecycle-/Readerachsen; spätere Produktprüfung bleibt gesondert.

## Integrationsprüfung für jeden PR

MASTER prüft jeweils:

1. Vollständigen tatsächlichen Diff und Ursprungsschnitt; implementiert, vorbereitet und behauptet unterscheiden.
2. Unabhängigkeit oder exakte vorgelagerte Commit-/Vertragsabhängigkeit; vorhandene Funktionen nicht erneut liefern.
3. Einhaltung der Shared Contracts sowie des einzelnen API-/Domainowners.
4. Aktuelle GitHub-Run- und Jobergebnisse am richtigen Head; Testmerge und Eltern/Tree prüfen. Fehlend, abgebrochen und übersprungen sind kein erfolgreicher Test.
5. Erneut aufgelösten Main und Datei-/Semantikkonflikte; nach Änderungen am Head oder an der Basis betroffene Prüfung erneuern.
6. Gemeinsame Regressionen am tatsächlich vorgesehenen Gesamtstand, nicht nur isolierte Branchtests.
7. Verbleibende Domainentscheidungen, Fachabnahme, Review und ausdrückliche Mergeberechtigung.

Die bestehenden [Backend](../../.github/workflows/backend.yml)-, [Frontend](../../.github/workflows/frontend.yml)-, [E2E](../../.github/workflows/e2e.yml)- und [Publikationswächter](../../.github/workflows/version-tag.yml)-Gates bleiben unverändert. Tests mit Schreibzugriff nur in identifizierter Wegwerfumgebung mit synthetischen Daten und abgefangenen externen Aufrufen. Keine Sicherheits-/Ergebnis-/Coverageprüfung lockern, um neue UX-Consumer grün zu bekommen.

Implementierung, erfolgreicher PR-Test, Main-Integration, Tagveröffentlichung, PC-Installation und menschliche Fachabnahme sind sechs getrennte Nachweise. Dieser Koordinationsauftrag gestattet Analyse, eigene Dokumentkorrekturen/Draft-PR, Tests und präzise Folgeaufträge. Kein Merge, keine PR-Schließung, kein Release/Tag, kein Workflow-Neustart und kein PC-/Produktivupdate ohne ausdrückliche Freigabe.
