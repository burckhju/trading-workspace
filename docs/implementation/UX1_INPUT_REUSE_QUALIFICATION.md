# UX-1: Eingaben wiederverwenden und Herkunft sichtbar machen

## Prüfgrundlage und abgegrenzter Umfang

Inventur vom 31.10.2026 vor der Implementierung, auf Main
`1883f7f330719453958f8be1dd51d48db816662e`, `VERSION`/Git-Tag `v1.5.35`.
Der Tag zeigt auf diesen Main-Commit. Das jüngste GitHub-Release-Objekt ist dagegen
`v1.0.0-product-selection`; Tagpublikation und Release-Objekt sind verschiedene Nachweise.
Diese Datei dokumentiert Befunde, Änderungen und Prüfnachweise; die maßgebliche
übergreifende Aufgabenstatusquelle bleibt [PRODUCT_BACKLOG.md](../planning/PRODUCT_BACKLOG.md).

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

Während der Umsetzung wurde außerdem #311 (UX2-Navigation, Head `6782bc7a`)
eröffnet. Gemeinsame Änderungsdatei ist `TradeManagementPage.tsx`; sein Patch lässt
sich auf UX1-Head `74d29bb8` konfliktfrei rein lesend prüfen (`git apply --check`).
Bei einer späteren gemeinsamen Integration müssen Währungsvorschau und
`historyReloadToken` erhalten sowie die Navigationsjourneys gemeinsam geprüft
werden. Aus #311 wurde nichts übernommen.

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

Die Währungsvorschau verwendet zwei GETs für Produkt beziehungsweise Trade und den
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
