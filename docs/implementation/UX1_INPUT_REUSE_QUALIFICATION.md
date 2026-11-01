# UX-1: Eingaben wiederverwenden und Herkunft sichtbar machen

## Prüfgrundlage und abgegrenzter Umfang

Inventur vom 31.10.2026 vor der Implementierung, auf Main
`1883f7f330719453958f8be1dd51d48db816662e`, `VERSION`/Git-Tag `v1.5.35`.
Der Tag zeigt auf diesen Main-Commit. Das jüngste GitHub-Release-Objekt ist dagegen
`v1.0.0-product-selection`; Tagpublikation und Release-Objekt sind verschiedene Nachweise.
Diese Datei dokumentiert Befunde, Änderungen und Prüfnachweise; die maßgebliche
übergreifende Aufgabenstatusquelle bleibt [PRODUCT_BACKLOG.md](../planning/PRODUCT_BACKLOG.md).
Die Ausgangsinventur und ihre damaligen Nachweise bleiben erhalten. Die erneute
Fachregelprüfung vom 01.11.2026 und die öffentliche Erstkaufgrenze stehen im
[Fortsetzungsabschnitt](#fachregelprüfung-und-öffentliche-erstkaufgrenze--01112026).

Geprüft: README, Development Guide, Frontend-/Backend-Architektur,
ADR-S6-007, bestehender Trade-Capture-Vertrag, Währungsresolver und Tests.
Im Checkout existiert keine `AGENTS.md`. Das aktive Main-Ruleset verlangt einen PR,
aufgelöste Reviewthreads und die strengen Checks Backend / quality, Frontend / quality
und End-to-End / smoke; Force-Push und Löschen sind gesperrt. Die klassische
Branch-Protection-Detail-API ist für die Integration nicht lesbar (403); das
[Ruleset selbst](https://github.com/burckhju/trading-workspace/rules/20249841) ist lesbar.

Bestehende Main-CI (kein Nachweis für neue Änderungen):

- [Backend 41171213873](https://github.com/burckhju/trading-workspace/actions/runs/41171213873):
  3.830 Tests, Coverage 88,01 %, Ruff/Black/mypy erfolgreich.
- [Frontend 41171213875](https://github.com/burckhju/trading-workspace/actions/runs/41171213875):
  1.824 Tests / 158 Dateien, alle Qualitätsprüfungen erfolgreich.
- [E2E 41171214040](https://github.com/burckhju/trading-workspace/actions/runs/41171214040):
  Smoke 129 bestanden / 5 übersprungen; drei zusätzliche Owner-Jobs erfolgreich.
- [Tagpublikation 41172652775](https://github.com/burckhju/trading-workspace/actions/runs/41172652775):
  `v1.5.35` am 31.10.2026 um 06:27 Uhr Europe/Vienna auf dem geprüften Main publiziert.

#298, #302, #303, #305, #306, #307, #308, #309 und #310 sind integriert.
Offen sind #220, #207, #205, #197 und #187. #187 enthält Änderungen an
`TradePlanWorkflowPage.tsx` und ein Hebeltrader-Panel; daraus wird nichts übernommen.
#309 ist ausschließlich ein dokumentierter Monitoringvertrag, keine Runtimefreigabe.

Während der ersten Umsetzung wurde außerdem #311 (UX2-Navigation, damaliger Head
`6782bc7a`) eröffnet. Damals war `TradeManagementPage.tsx` die einzige gemeinsame
Änderungsdatei; sein Patch wurde auf UX1-Head `74d29bb8` konfliktfrei rein lesend
geprüft (`git apply --check`). Dieser historische Einzelbefund gilt nicht für den
inzwischen erweiterten UX2-Head. Die aktuelle Vier-Dateien-Grenze und der notwendige
gemeinsame Nachweis sind im Fortsetzungsabschnitt abgegrenzt. Aus #311 wurde nichts
übernommen.

## Feldmatrix des geprüften Main

Pfadkürzel: `FE` = `frontend/src/features`, `BE` = `backend/app/features`.
„Bereits“ bezeichnet den geprüften Main, nicht eine Leistung dieses Changesets.

| Feld | Aktuelle Eingabe | Vorhandene Quelle | Sichere Ableitung / Wiederverwendung | Nutzerentscheidung erforderlich? |
|---|---|---|---|---|
| Produkt / ISIN / WKN | Neuanlage einmal; vorhandenes Produkt wählen | FE/product/components/WarrantCreateForm.tsx, WarrantIdentifierCorrection.tsx; WarrantResponse | Bereits: vorhandene Produktidentität weiterreichen | Nur Neuanlage oder belegte Korrektur |
| Basiswertzuordnung | Auswahl, bei Selection-Reparatur schon vorbelegt | FE/product/services/selectionRepairContext.ts; WarrantCreateForm.tsx | Bereits: exakt geprüfter Selection-Basiswert | Nur ohne eindeutigen Ursprung |
| Emittent | Namen aus Stammdaten wählen | FE/product/pages/WarrantAdminPage.tsx; issuer_id | Bestehendes Produkt behält seinen Emittenten | Neues Produkt / Korrektur |
| Produkt-Handelsplatz | Erste Notierung im selben Produktformular | FE/product/components/WarrantListingFields.tsx; WarrantListingResponse | Bereits: konkrete Listing-ID wiederverwenden | Neue oder abweichende Notierung |
| Produkt-Handelswährung | Bei erster Notierung einmal erfassen | WarrantListingFields.tsx; initial_listing | Bereits: Produkt und erste Notierung atomar speichern | Neue Notierung; keine historische Ausführungsbestätigung |
| Produktart / Bedingungen | WARRANT fest; CALL/PUT und Bedingungen eingeben | FE/product/types/api.ts; WarrantTermsEditor.tsx | Bereits: bestehende Bedingungen und expected_version vorbelegen | Neue Bedingungen / Änderung; Konfliktentscheidung erhalten |
| Historische Währungsquelle | Quelle, Zeitraum, Belegbezug explizit prüfen | FE/product/components/CurrencyEvidenceEditor.tsx; BE/trade_position/domain/currency_evidence.py | Bereits: Korrektur übernimmt Facts mit Vorgänger-ID | Belegerfassung, Korrektur, Widerruf ausdrücklich |
| Analyse / Evaluationversion | Im Kandidatenkontext keine zweite Auswahl | FE/candidate/pages/CandidatePage.tsx; FE/trade_plan/services/originContext.ts | Bereits: exakte immutable Evaluation; kein latest-Ersatz | Nur fehlender / widersprüchlicher Kontext |
| Analysequellen / Modellversion | Keine erneute Eingabe | ADR-S6-007; TradePlanVersionContent.tsx | Bereits: transitiver historischer Ursprung ohne Datenkopie | Nein beim Lesen |
| Plan-Basiswert | Aus geprüftem Ursprung angezeigt | FE/trade_plan/services/originContext.ts | Bereits: gespeicherte underlying_id | Nur manueller Ursprung ohne Kontext |
| Plan / Planversion | Exakte Deep-Link-Version | FE/trade_plan/services/planViewContext.ts; FE/product_selection/services/planContext.ts | Bereits: historische Version bleibt trotz neuerem Draft gebunden | Ohne eindeutigen Kontext auswählen |
| Planannahmen / Einstieg / Ziel / Stopp / Risiko | Neu leer; Amendment vorbelegt | FE/trade_plan/forms/content.ts; ExistingTradePlanPage.tsx | Bereits: Inhalt exakt gewählter Basisversion in neuen Draft übernehmen | Neue Annahme, Änderungsgrund und Freigabe ausdrücklich |
| Planwährung | Neu manuell; Amendment aus Basisversion | TradePlanContentForm.tsx | Aktuelle Notierung wäre nur Vorschlag; keine sichere neue Automatik | Neuanlage weiterhin ja |
| Produktvorschläge / Bewertungslauf | Historische Runs laden, dann öffnen | FE/product_selection/pages/ProductSelectionPage.tsx | Lücke: genau ein vorhandener Run kann ohne zweiten Klick lesend geöffnet werden | Mehrere Runs auswählen; Neubewertung ausdrücklich |
| Bestätigtes Produkt | Run-Link übernimmt Auswahl | ProductSelectionPage.tsx; useSelectionReferenceData.ts | Bereits: exakte gespeicherte Selection und Evaluation | Keine erneute Auswahl bei gebundenem Run |
| Plan-Handelsplatz / Kursquelle | Gespeicherte Listing-ID / Evaluationdetails | BE/product_selection/service/application.py | Bereits: historischen Quote-Snapshot anzeigen | Neue Bewertung / Auswahl ausdrücklich |
| Kaufprodukt / Planbezug | Aus bestätigter Produktauswahl | ProductSelectionPage.tsx; InitialPurchaseRequest.product_selection_id | Bereits: Produkt, Plan und Version durch Backend auflösen | Nur tatsächlichen Kauf speichern |
| Nachkauf- / Verkaufsprodukt | Aus Trade-Kontext, keine Neueingabe | FE/trade/pages/TradeManagementPage.tsx; AdditionalPurchasePanel.tsx | Bereits: identischer Trade / Produktbezug | Anderer Trade durch bewusste Navigation |
| Verkaufsmenge | Teilverkauf leer, offene Menge als Maximalwert | PositionResponse.open_quantity; TradeManagementPage.tsx | Bereits: Begrenzung; expliziter Vollverkaufsbutton verwendet offene Menge | Teilmenge oder Vollverkauf ausdrücklich; niemals Auto-Buchung |
| Ausführungspreis | Leer für jeden Kauf / Verkauf | Tatsächliche Ausführung; aktuelle Quotes separat | Keine sichere Ableitung aus aktuellem Preis | Tatsächlichen Preis eingeben |
| Ausführungsdatum / Uhrzeit | Heute als editierbarer Vorschlag; Uhrzeit leer | FE/trade/services/capture.ts; ExecutionDateInput.tsx | Bereits: lokale Zone; Datum ohne erfundene Uhrzeit; Korrektur übernimmt Originalpräzision | Tatsächliches Datum / bekannte Uhrzeit |
| Erstkauf-Ausführungswährung | Sichtbares leeres Feld trotz möglicher historischer Quelle | ProductSelectionPage.tsx; BE/trade_position/domain/historical_currency_resolution.py | Lücke: vorhandenen Resolver vor Buchung lesend für Produkt und Datum auswerten; belegten Wert anzeigen | Nur ungeklärte / abweichende Währung explizit eingeben |
| Nachkauf- / Verkaufswährung | Kein Pflichtfeld; allgemeiner Wiederverwendungshinweis | ExecutionCurrencyOverride.tsx; BE/trade_position/domain/currency_resolution.py | Bereits: vollständig bestätigte frühere BUYs; Lücke: konkretes Ergebnis für Formulardatum vor Speichern sichtbar machen | Fehlende / widersprüchliche Quelle oder ausdrückliche Abweichung |
| Ausführungsbelege / Handelsplatz | Exakt zugeordnete Quellen; kein Quote-Default | CurrencyEvidence; historical_currency_resolution.py | Bereits: exakter Executionbeleg vor historischer Notierung; neue Buchung darf alten Einzelbeleg nicht erben | Neuer Beleg / eindeutiger Ausführungsplatz nur wenn tatsächlich belegt |
| Währung bei Korrektur | Optional abweichend; sonst vorhandener Resolver | ExecutionDatesPanel.tsx; currency_resolution.py | Bereits: bestätigter gleichseitiger Vorgänger; historische Quelle für neues Datum erneut prüfen | Korrektur bewusst; bei Quellenlücke gezielt bestätigen |
| Stornierung | Bestehende Vorschau plus Grund / Bestätigung | TradeCancellationPanel.tsx; cancellation.py | Bereits: Originaldaten anzeigen; keine Mengen-/Preis-Neueingabe | Storno ausdrücklich; Originale bleiben erhalten |
| Performance-Zeitraum | Monatserster bis heute vorgeschlagen | FE/performance/services/performanceReportContext.ts | Bereits: gültige URL-Filter haben Vorrang und bleiben beim Moduswechsel erhalten | Abweichenden Zeitraum wählen; Vorschlag durch Lesen nutzen |
| Berichtszeitzone | Europe/Berlin fest vorgeschlagen | report_timezone in URL; verfügbare Intl-Browserzone | Lücke: bekannte gültige Browserzone für Erstvorschlag; URL bleibt vorrangig | Abweichende Zone korrigieren; kein unbelegter Ausführungsbezug |
| Berichtswährung | EUR schreibgeschützt | FE/performance/components/PerformanceFilters.tsx | Bereits festgelegt; Nicht-EUR-Link wird nicht still ersetzt | Nein |
| Berichtsart / Grundgesamtheit | Verkäufe oder Vollabschlüsse wählen | FE/performance/pages/PerformanceWorkspace.tsx | Bereits: gleiche Filter, getrennte Abfragen und Definitionen | Fachliche Berichtsart wählen |
| Historische Buchungen / Kostenbasis | Keine Berichtsnacherfassung | BE/performance/service/reader.py; domain/report.py, closed_report.py | Bereits: vollständiger read-only Snapshot der wirksamen Fakten | Nur fehlerhafte Quellbuchung gezielt korrigieren |
| Performance-Daten-/Währungsherkunft | Automatisch mit Quelldetails | ReportSourceEntry.tsx; ExecutionCurrencySources.tsx; resolve_execution_currencies | Bereits: gleiche Provenienztypen, keine FX-/Null-Ersatzwerte | Ungeklärte Quellbelege klären |
| Journal-Trade / Version | Kontext / historischer Pin | FE/learning/components/useTradeJournal.ts; journalClient | Bereits: exakter Trade und Version, keine zweite Auswahl bei Refresh | Bewusster Kontext- / Versionswechsel |
| Journal-Plan / Analyse | Keine Neueingabe | BE/post_trade/application/read_adapters.py; Trade.trade_plan_version_id | Bereits: historisch gebundene Planversion und transitive Quellen | Fehlende Herkunft nicht durch aktuelle Analyse ersetzen |
| Journal-Ausführungsereignisse | Automatisch | SqlAlchemyTradeExitContextReader; effektive SELLs / Managementereignisse | Bereits: historische IDs, Preis, Menge, Datum und Präzision | Keine Zweiteingabe |
| Journal-Reviewquelle | History.handoff.source_exit_review_version_id | JournalService.history; TradeJournalPanel.tsx | Bereits: exakte Reviewquelle; neue Quelle wird nicht still eingebunden | Draft / Rebind / Finalisierung ausdrücklich |
| Vorhandene Journaltexte | Editor / Folgeversion vorbelegt | journalTexts; gespeicherte JournalVersion; CREATE_DRAFT | Bereits: persönliche Bestandstexte wiederverwenden | Bewertung und Interpretation bleiben Nutzereingabe |
| Evidence-/Lessonverknüpfungen | Automatisch aus gewähltem Evidence-Kontext | Ft011EvidenceHistory; JournalEvidenceOrigin; LessonDraftFromEvidence | Bereits: exakte historische Pins, vollständige Linksets | Lessoninhalt und Anlage ausdrücklich |
| Lesson-Folgeversion | Kategorie, Inhalt und Links vorbelegt | LessonReviewPanel.prepare | Bereits: SUPPORTS / CONTRADICTS / CONTEXTUAL erhalten | Änderungen, Begründung, Review und Freigabe ausdrücklich |

## Ableitungsregeln und Umsetzungsauswahl

Der bestehende Ausführungswährungsresolver bleibt allein maßgeblich. Seine Typen
`USER_CONFIRMED`, `EXECUTION_DOCUMENT`, `HISTORICAL_LISTING(S)`, `PRIOR_BUYS`,
`REPLACED_EXECUTION`, `UNKNOWN`, `MIXED` und `CONFLICT` bleiben erhalten.
Eine Anzeige im Formular erzeugt keine Bestätigung. Aktuelle Produkt-/Kursdaten
bleiben von historischen Ausführungsbelegen getrennt. Historische Quellen dürfen
nur innerhalb ihres nachgewiesenen Zeitraums gelten; sie begründen keine unbegrenzte
Vererbung auf spätere Buchungen. Eigene explizite Angaben werden nie durch eine
verspätete automatische Antwort überschrieben.

Reihenfolge der abgegrenzten Changesets:

1. UX1-A: Lesende Vorschau aus dem vorhandenen Resolver für Erstkauf, Nachkauf und
   Verkauf; bestehende Währungsformulare zeigen belegte Werte und aufklappbare
   Herkunft. Fehlende Angaben bleiben gezielt korrigierbar. Kein neuer Datenspeicher,
   keine Migration, keine implizite Währungsbestätigung oder Buchung.
2. UX1-B: Genau einen gespeicherten Bewertungslauf der exakten Planversion lesen;
   mehrere Läufe bleiben eine bewusste Auswahl. Keine neue Bewertung / Auswahl.
3. UX1-C: Browserbekannte gültige Berichtszeitzone als korrigierbarer Erstvorschlag;
   explizite URL-Filter und bestehende Lade-/Fehlerverträge bleiben vorrangig.
4. UX1-D: Vorhandene sichere Automatik dokumentieren; keine künstliche zusätzliche
   Ableitung, Bewertung oder Lesson erzeugen.

## Nachweise für den neuen Stand

### Implementierung und reproduzierbare Abläufe

| Ablauf | Neu implementierte Vereinfachung | Verbleibende Entscheidung / Herkunft | Regression |
|---|---|---|---|
| Erstkauf aus bestätigter Produktauswahl; passende geprüfte historische Quelle und tatsächliches Datum vorhanden | Währungs-Codefeld entfällt nach erfolgreicher Quellenprüfung; keine erneute Code-/Belegeingabe für dieselbe Herkunft | Menge, tatsächlicher Preis und Speichern bleiben ausdrücklich; Quelle mit Intervall und Zeitpunkt aufklappbar; POST enthält keine automatisch erzeugte currency_confirmation | ExecutionCurrencyPreview.test.tsx; ProductSelectionPage.test.tsx; test_currency_preview.py; neue PostgreSQL- und E2E-Fälle |
| Nachkauf / Verkauf bei einheitlich bestätigten vorherigen BUYs | Konkrete vorhandene Währung samt Herkunft wird schon im Formular angezeigt; kein Wechsel in die Buchungshistorie zur bloßen Herkunftskontrolle nötig | Die Wiederverwendung selbst war bereits Main-Funktion. Menge/Preis bleiben leer, Teil-/Vollverkauf ausdrücklich | AdditionalPurchasePanel.test.tsx; TradeManagementPage.test.tsx; bestehende Resolverfälle |
| Abweichende manuelle Währung während verspäteter Antwort | Einmal eingegebene Angabe und Notiz bleiben erhalten | Wird erst durch Speichern bestätigt; kein automatischer Wechsel zur Vorschauwährung | ExecutionCurrencyPreview.test.tsx |
| Fehlende / widersprüchliche historische Quelle | Konkrete Erklärung und Eingabemöglichkeit direkt am Währungsfeld | Keine willkürliche Quellenauswahl; ungeklärter Zustand bleibt zulässig und sichtbar | UNKNOWN/MIXED/CONFLICT-, Zeitgrenzen-, Fremdbeleg- und Current-EUR-Negativfälle |
| Quelle korrigieren und anschließend im selben Trade weiterarbeiten | Vorhandene erfolgreiche Read-Revision lädt die Herkunft neu, ohne den Verkaufsentwurf zu löschen | Originalquellen bleiben append-only; fehlgeschlagener Readback ist kein Erfolg | TradeManagementPriceHistory.test.tsx; PostgreSQL-Snapshotfall |
| Plan-/Versionslink mit genau einem gespeicherten Bewertungslauf | Ein zusätzlicher Klick auf denselben Historieneintrag entfällt; vorhandene Selection wird angezeigt | Mehrere Läufe erfordern Auswahl; keine Neubewertung, Produktauswahl oder Planfreigabe | Neun zusätzliche ProductSelectionPage.context.test.tsx-Fälle |
| Performance-Erststart mit gültiger Browserzone, etwa Europe/Vienna | Die Browserzone muss nicht erneut anstelle des bisherigen Berlin-Vorschlags eingegeben werden | Vorschlag bleibt bearbeitbar; explizite URL hat Vorrang; Datum im selben Zonenbezug, EUR unverändert | performanceReportContext.test.ts; PerformanceWorkspace.test.tsx |
| Journal / Lessons | Bestehende automatische Trade-/Review-/Plan-/Evidenceverknüpfungen bestätigt | Keine neue Bewertung, Interpretation oder Freigabe erzeugt | Vorhandene Journal-/Lesson-Suiten unverändert |

Die Währungsvorschau verwendet zwei alternative GET-Endpunkte für Produkt beziehungsweise Trade und den
vorhandenen `TradeSourceReader` samt schreibgeschütztem Repeatable-Read. Pro Faktenart
gilt dessen Grenze von 2.000 Einträgen, für die Resolververknüpfungen 100.000. Grenzen
führen zu einem erklärten Fehler statt zu abgeschnittener Herkunft. `side` und
explizite Zeit sind Pflicht; Menge, Preis und Bestätigung sind in diesem Vertrag
unzulässig. Details: [Trade-Capture-Vertrag](../trade-capture-safety.md#show-existing-currency-evidence-before-capture--ux1-a-2026-10-31).

### Tatsächlich lokale Prüfungen

- Backend: **427 bestanden, 3 übersprungen**, eine bestehende AnyIO-Warnung; gesamte
  TradePosition-Units, historische Performance-Währung und die neue Previewdatei.
  Enthalten sind **47 neue API-/Previewfälle**. Die drei übersprungenen Tests sind
  die neuen PostgreSQL-Integrationen, lokal ohne dedizierte Testdatenbank.
- Vollständiges Ruff- und Black-Gate: bestanden; mypy über **570 Quelldateien** bestanden.
- A/B: **103 gezielte Frontendtests** bestanden; zusätzlich die gesamte
  Readback-/Kursverlaufsdatei mit **8 Tests** einschließlich zweier neuer
  Preview-Readbackfälle. Diese Zahlen sind getrennte Läufe mit Überlappung.
- C: **155 Tests** in Performance-Kontext und Workspace bestanden.
- Ausführung mit Python 3.12.14 und der Repository-Toolchain **Node 22.16.0 / npm 10.9.2**.
  Vorherige lokale Node-24-Läufe waren wegen eines nachgewiesenen JSDOM-/AbortSignal-
  Konflikts nicht maßgeblich; keine Produkt-/Testumgehung oder Gateabsenkung vorgenommen.
- Neue E2E-Datei `tests/e2e/execution-currency-reuse.spec.ts`: durch Playwright
  erfolgreich entdeckt. Der tatsächliche Browser-/PostgreSQL-Ablauf läuft in der
  vorhandenen Wegwerf-CI mit `TRADE_E2E_WRITES_ALLOWED=1`; kein Zugriff auf echte Bestände.

Der erste PR-Testmerge `d5df27fe` qualifizierte bereits die neue Browserreise,
deckte aber zwei Regressionen auf: eine doppelte Datums-/Zeitfehlermeldung in der
Währungsvorschau sowie implizite Berlin-Annahmen in zwei Performance-Testdateien
auf dem UTC-Runner. Die Vorschau überlässt die präzise Zeitvalidierung wieder dem
Captureformular und bietet bei ungültiger Zeit keinen wirkungslosen Lese-Retry.
Die Performance-Tests wählen ihren Berichtskontext ausdrücklich; die fachliche
Antwortprüfung und Übernahme der Browserzone bleiben unverändert. Die bestehenden
DST-End-to-End-Prüfungen bleiben vollständig erhalten.

Das vollständige Frontend-Gate sowie exakte PR-Head-/Testmerge-/CI-Ergebnisse werden
im Integrations-PR nach tatsächlichem Lauf nachgewiesen. Die oben genannten Main-Läufe
qualifizieren keine UX-1-Änderung. Merge, Release, Deployment, PC-Installation und
fachliche Abnahme sind nicht Teil dieses autorisierten Implementierungsauftrags.

## Fachregelprüfung und öffentliche Erstkaufgrenze — 01.11.2026

### Ausgang und abgegrenzte Dateifläche

Erneut aufgelöst: Main `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35`, ursprünglicher
UX1-Head `8f67442daac6879d7dfb28416f2171f67aead0e5` und offener UX2-Head
`55072f8e90c00d309c3bd6ed6dd17f61ab33bd32`. Main enthält seit der ersten Prüfung
ausschließlich die fünf Koordinationsdokumente aus #313. `VERSION` bleibt 1.5.35;
der veröffentlichte Git-Tag v1.5.35 zeigt weiter auf `1883f7f3`, nicht auf den neuen
Dokumentations-Main. Die neue Mainbasis wird im UX1-Featurebranch erhalten.

Ausführender Lead dieses Teilschnitts ist UX1. Die integrierten
[Shared Contracts](../coordination/UX_SHARED_CONTRACTS.md#öffentliche-grenze-für-die-erstkaufvorschau)
geben die schmale öffentliche Erstkaufgrenze ausdrücklich vor. Reservierter und
bearbeiteter Produktumfang:

- `frontend/src/features/trade/public/InitialPurchaseCurrencyPreview.tsx`
- `frontend/src/features/trade/public/InitialPurchaseCurrencyPreview.test.tsx`
- `frontend/src/features/trade/index.ts`
- `frontend/src/features/product_selection/pages/ProductSelectionPage.tsx`, ausschließlich Previewimport und Aufruf

Hinzu kommen dieser bestehende Qualifikationsvertrag und
[trade-capture-safety.md](../trade-capture-safety.md#public-initial-purchase-preview-boundary--ux1-review-2026-11-01).
Die fünf MASTER-Dokumente werden unverändert aus Main übernommen. Keine eigene
Änderung an Hostnavigation, Performancehelper, Backend, Workflow, Version oder
fachlichem Backlogstatus ist Bestandteil dieser Fortsetzung.

### Öffentliche Grenze und fachliche Regelprüfung

`ProductSelectionPage` importiert `InitialPurchaseCurrencyPreview` aus `../../trade`.
Die öffentliche Grenze exportiert ausschließlich diesen Adapter und seinen Props-Typ.
Er nimmt `productId`, `date`, `time`, den vorhandenen kontrollierten Währungsentwurf
`value`/`onChange` mit `code`/`note` sowie optional `disabled` entgegen. Intern ist
der Kontext fest an das Produkt und `BUY` gebunden; die Props werden ausdrücklich
einzeln weitergereicht. Freie Side, Trade-ID, Preis, Menge und Read-/Writecallbacks
gehören nicht zum öffentlichen Vertrag. Trade behält den vorhandenen Previewread;
Produktauswahl behält den Entwurf und den ausdrücklichen Capture. Es gibt keine
kopierte Resolution, Finanzregel oder zweite Währungsauflösung.

Der vollständige ursprüngliche Backend-Diff und die Consumer wurden unabhängig
gegen die bestehenden TradePosition-/ProductSelection-Verträge geprüft. Befund:
kein konkreter fachlicher Fehler in den additiven Preview-GETs. Die fachlichen
Resolverfunktionen ändern gegenüber ihrer Basis ausschließlich den Scope-Parametertyp;
ihre Prioritäts-, Zeit- und Konfliktlogik bleibt unverändert.

| Geprüfte Grenze | Beobachteter Vertrag / vorhandener Gegenfall | Testbeleg |
|---|---|---|
| Erstkauf und aktuelle EUR-Notierung | Nur vollständige passende historische Produktquellen; andere Trades und aktuelle Listings begründen keinen Nachweis | `test_currency_preview.py`; `test_execution_currency_preview_postgres.py` |
| Bestätigung und Nachkauf/Teilverkäufe | Eigene gültige Executionbestätigung hat Vorrang; frühere BUYs bleiben abgeleitete Herkunft, spätere Käufe füllen keine früheren Lücken | Bestehende Currency-Resolverfälle; Preview- und Capturetests |
| Fehlend / gemischt / widersprüchlich | UNKNOWN, MIXED und CONFLICT bleiben erhalten; keine beliebige Quelle und kein EUR-Ersatz | Preview-, historische Resolver- und Performance-Währungsfälle |
| Datum, Zeitzone und DST | Date-only erfordert Abdeckung des ganzen möglichen lokalen Tages; halboffene Intervalle und Lücken bleiben erhalten; keine erfundene Uhrzeit | Historische Resolverfälle einschließlich 25-Stunden-Tag; unveränderter `trade-capture-dst.spec.ts` |
| Korrektur, Storno und Scope | Wirksame Korrekturhistorie, bestätigte Abstammung und neue Zeitbindung; stornierter Trade wird abgewiesen, fremde Quellen bleiben ausgeschlossen | Preview-, Korrektur-/Storno- und Scopefälle |
| Lesender Snapshot | Keine Capturefelder in GETs, keine Previewbestätigung oder persistierte Preview-ID; bounded Repeatable-Read bleibt READ ONLY | API-Negativfälle; PostgreSQL-Datenvergleich und gleichzeitige Bestätigungsänderung |
| Öffentliche BUY-Grenze | Nur freigegebene Props/Exports; feste BUY-Bindung auch bei fremden zusätzlichen Runtimeprops | `InitialPurchaseCurrencyPreview.test.tsx` |
| Manuelle Angaben und Kontextwechsel | Keine Draft-/Capturewrites durch Reads; Code/Notiz, Busy, Retry, A→B→A mit spätem Erfolg/Fehler und Unmount geschützt | Öffentliche Adaptertests und bestehende Preview-/Kontexttests |
| Bewusster Erstkauf | Angezeigte historische Währung erzeugt keine automatische `currency_confirmation`; erst der ausdrückliche Kauf speichert | `ProductSelectionPage.test.tsx`; `execution-currency-reuse.spec.ts` |

Dies ist eine technische Fachregelprüfung mit synthetischen Nachweisen. Sie ist
keine menschliche fachliche Abnahme und verändert keinen Abnahmestatus im Backlog.

### Neu ausgeführte lokale Nachweise und CI-Bindung

- Python 3.12.14: gesamte TradePosition-Units, historische Performance-Währung und
  Preview-PostgreSQLdatei erneut ausgeführt: **427 bestanden, 3 übersprungen**, eine
  bestehende AnyIO-Deprecation-Warnung, 8,51 Sekunden. Reale Datenbank-URLs waren für
  diesen lokalen Prozess entfernt; die drei PG-Fälle benötigen die isolierte CI.
- Node 22.16.0 / npm 10.9.2, `TZ=UTC`: **49 Tests in vier Dateien bestanden**:
  sieben öffentliche Adapterfälle sowie 5/33/4 bestehende ProductSelection-Seiten-,
  Kontext- und Repairfälle. TypeScript und gezielte Formatprüfung erfolgreich.
- Vollständiges Frontend-Gate derselben Toolchain/Zone: **1.869 Tests in 160 Dateien
  bestanden**, TypeScript, ESLint, Prettier und Build erfolgreich. Coverage:
  Statements/Lines **95,89 %**, Branches **90,22 %**, Functions **91,27 %**; bestehende
  Grenzen unverändert. Vier zunächst vom Lintgate beanstandete Async-Testcallbacks
  warten nun ausdrücklich auf ihre Deferred-Antworten; keine Regel oder Assertion
  wurde gelockert. Beide Dokumente und zwölf lokale Link-/Ankerziele sind geprüft.
- Alle normalen GitHub-Gates einschließlich echter PostgreSQL- und Browserreisen
  werden am neuen Head mit
  tatsächlich ausgechecktem Testmerge im [bestehenden PR #312](https://github.com/burckhju/trading-workspace/pull/312)
  nachgewiesen. Die grünen Läufe des ursprünglichen Heads gelten nicht automatisch
  für den Adapter oder einen später kombinierten UX1/UX2-Stand.

### Verbleibende Integrationsgrenze

Der unabhängig qualifizierbare Adapter schließt die öffentliche UX1-Importgrenze.
Die [festgelegte Integrationsreihenfolge](../coordination/UX_DEPENDENCIES.md#integrationsreihenfolge-phase-1)
bleibt bestehen: UX2 stellt den einmaligen Shared-Zeitzonenhelper bereit und führt
die Hostintegration; UX1 wird anschließend auf dem tatsächlich integrierten UX2-Main
neu qualifiziert. Gemeinsame Dateien sind weiterhin `TradeManagementPage.tsx`,
`performanceReportContext.ts`, `PerformanceWorkspace.test.tsx` und
`RealizedGrossPage.test.tsx`. Beide Funktionsumfänge bleiben zu erhalten.

Kein fremder Featurebranch wird übernommen. Erfolgreiche Einzel-PR-CI dieses
Adapters ist kein kombinierter Navigations-/Readbacknachweis. Der gemeinsame Stand
benötigt erfolgreiche Previewantworten, erhaltene manuelle Eingaben, konstante
Previewreads bei Hashwechseln, historische Pins und beide Berichtsrückwege sowie
die vollständigen normalen Gates. Mainintegration, Veröffentlichung, PC-Installation
und menschliche Fachabnahme bleiben eigene, hier nicht erteilte Freigaben.
