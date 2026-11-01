# UX3-B1/F1 — Währungsherkunft eines Verkaufsbeitrags

## Auftrag und geprüfte Grundlage

Der Nutzerauftrag „Nächster Schritt umsetzen ggf. mit separatem Startprompt“
konkretisiert den ersten Produktdurchstich nach UX3-K. Die bereits erteilte
Autorisierung für Merge bei grünen erforderlichen Prüfungen und Bereitstellung
für den PC bleibt erhalten. Technische Prüfung, Main-Integration, veröffentlichter
Tag, PC-Installation und menschliche Fachabnahme sind getrennte Nachweise.

Ausgangsbasis ist Main
[`bb49ffe781933270746b9f86f4aee99b6f8144c2`](https://github.com/burckhju/trading-workspace/commit/bb49ffe781933270746b9f86f4aee99b6f8144c2),
veröffentlicht als v1.5.37. Der Stand enthält den kanonischen Vertrag aus
[#314](https://github.com/burckhju/trading-workspace/pull/314) und die qualifizierte
UX1/UX2-Integration aus
[#318](https://github.com/burckhju/trading-workspace/pull/318).
Der Quellentwurf #315 bleibt unangetastet. Maßgeblich sind der
[Hinweisvertrag](../ui/ux-3/notice-contract.md), die
[Masterentscheidung](../coordination/UX_SHARED_CONTRACTS.md) und der
[begrenzte Rollout](../ui/ux-3/integration-and-rollout.md).

## Ergebnis und Dateigrenze

Beim Öffnen der Herkunft eines realisierten Verkaufsbeitrags zeigt genau eine
Karte den betroffenen Gegenstand, die belegte Währungsursache, ihre Auswirkung,
eine bereits vorhandene automatische Zuordnung und den verbleibenden optionalen
Prüfweg. Primär stehen Produktname beziehungsweise ein ehrlicher Ersatz sowie
Verkaufsdatum und Berichtszeitzone. Technische Identitäten stehen in Details.

| Fläche / Owner | Konkrete Änderung | Erhaltene Grenze |
| --- | --- | --- |
| [Shared-Präsentation](../../frontend/src/shared/notices/index.ts) / UX3 | `NoticeView`, `NoticeCard`, `NoticeDetails`, `ContextActionLink`; sichtbare Statuslabels, native Details, interne Links und sichtbarer Fokus | Keine Featureimporte, Requests, Callbacks, Commands, Effekte, Live-Regionen, globale Priorisierung oder Recoveryverwaltung |
| [Performance-Mapper](../../frontend/src/features/performance/services/realizedCurrencyNotice.ts) / Performance | `buildRealizedCurrencyNotice(item, report, context)` erklärt vorhandene Item-/Quellenfakten; `currencyResolutionLabel` benennt deren Herkunft | Kein Währungsresolver, Finanzalgorithmus, neues Domainenum oder neue fachliche Zulässigkeitsprüfung |
| [RealizedGrossSources](../../frontend/src/features/performance/components/RealizedGrossSources.tsx) / bestehender Performance-Host | Eine Karte, genau ein bestehender Trade-Buchungslink, eindeutige Quellenzuordnung und ruhige Quellenabschnitte | Vorhandene Berichtsauswahl, Generationen, Rückkontext, Zahlen und Finanzstatus bleiben erhalten |
| [ReportCurrencyEvidence](../../frontend/src/features/performance/components/ReportCurrencyEvidence.tsx) / Performance | Bereits gelesene Bestätigung, historische Belege, Resolverreferenzen und Bestätigungshistorie aufklappbar | Keine zusätzliche Warnung pro Quelle; keine neue Qualifikation, kein Quellenabruf |
| [ReportSourceEntry](../../frontend/src/features/performance/components/ReportSourceEntry.tsx) / Performance | Optionaler Präsentationsslot ausschließlich für den Realized-Piloten | Der bestehende Default einschließlich Closed-Trade-Verbrauchern bleibt erhalten; kein globaler Umbau von `ExecutionCurrencySources` |
| [Vollständiger Dokumentvertrag](../ui/ux-3/contracts.ts) / UX3 | Importiert und erweitert dieselbe Shared-Projektion | Die 42 bestehenden Typgegenfälle sowie zusätzliche Kontext-/Evidence-/Lifecyclebindungen bleiben erhalten; Produktcode importiert keine Dokumentation |

Der Pilot ändert keine Trade-/Produktauswahlformulare, UX1-Vorschau, UX2-Navigation,
Backendantworten, Provider, Tradingregeln oder Planfreigaben. B2–D und weitere
Berichtspopulationen sind keine implizite Folge dieses Diffs.

## Fachliche Entscheidungen

### Status und Auswirkung bleiben beim Bericht

Eine Warnung entsteht nur aus `item.status === NOT_COMPUTABLE` zusammen mit einem
gelieferten Währungsreason (`CURRENCY_UNKNOWN`, `CURRENCY_CONFLICT` oder
`CURRENCY_MIXED`). Der Mapper erfindet weder eine Operationssperre noch einen
Gesamtstatus. `EXCLUDED` bleibt ein neutral erklärter Ausschluss, auch wenn dort
zusätzlich ein Währungsreason steht. Nutzbare, unbekannte und echte Nullbeträge
bleiben unverändert; keine Berechnung und keine Umdeutung von `null` in `0`.

Unbekannte Reasons bleiben mit Originalcode in den Details sichtbar. Die
Hauptaussage begrenzt dann die Erklärbarkeit. `DOCUMENT_CONFLICT` kann Währung
oder Handelsplatz betreffen; mehrere historische Listingwährungen werden nicht
pauschal als widersprüchliche Kaufwährungen bezeichnet.

### Die tatsächlichen Quellen bestimmen den Bezug

Die Karte verwendet wirksame BUY-Quellen aus dem vom Owner gelieferten
Kostenbasispräfix und den ausgewählten SELL. Frühere SELLs erklären die
Bestandsentwicklung, aber keine Kaufkostenwährung. Spätere und ersetzte
Buchungen bleiben in der unverändert zugänglichen Historie. Eine bestätigte
Verkaufswährung schließt eine unbekannte Kaufwährung nicht aus.

Quellenidentitäten werden über die gesamte Antwort auf Eindeutigkeit geprüft;
erst danach werden Trade und Produkt zugeordnet. Fehlende, doppelte, fremde,
ersetzte oder falschseitige Quellen erzeugen keine erfundene Auflösung. Fremde
Payloads gelangen nicht in die Quellenanzeige. Fehlt das optionale
`currency_resolution`, wird es nicht aus einer Bestätigung rekonstruiert.

Originalbestätigungen, Autoren, Notizen, Bestätigungshistorie, Evidenceversionen,
Quellenreferenzen, Fingerprints und Resolverversionen bleiben prüfbar. Quellen-
und Evidence-IDs dienen der Rückverfolgbarkeit. Originalreferenzen sind Text,
keine ungeprüften externen Links. Das Ende eines Gültigkeitsintervalls wird
ausdrücklich als ausschließlich bezeichnet.

### Eine gemeinsame Projektion, kein zweiter Vertrag

Die reinen Darstellungstypen werden aus dem Dokumentvertrag einmalig nach Shared
übernommen. `NoticeView` enthält seine vorhandenen Felder und erhält insbesondere
die Korrelation von Darstellungsart und Nutzerbedarf. Der vollständige Typ
`Notice<TFacts>` ergänzt dieselbe Projektion um Ownerfakten und Kontext;
`ExistingDestination` ergänzt `NoticeDestination` um `NoticeContext`.

Der vorhandene Host liefert keinen vollständigen generischen Workspacekontext an
diesen Quellenabschnitt. Deshalb werden keine `workspaceKey`-/Generationswerte
erfunden. Der Mapper prüft tatsächliche Itemmitgliedschaft, eindeutige Identität,
Berichtsdefinition, Filter, Währung und Basis über die bestehenden Ownerhelper.
`PerformanceWorkspace` behält Requestgeneration und Abortschutz. Die Karte wird
bei neuen Props unmittelbar aus der neuen Antwort aufgebaut.

Die Ursachenidentität enthält fachlichen Bezugsraum und konkrete Quellenidentität.
Eine neue Berichtsbasis, Lesezeit oder Darstellung allein ändert sie nicht.
Deutsche Meldungstexte sind keine Identitätsbausteine. Unabhängige Quellen bleiben
unterscheidbar; dies ist keine berichtsweite Ursachenzählung und kein Deduplizierungs-
oder Recoverystore.

### Zeiten und Aktionen behalten ihre Bedeutung

`read_started_at` und `read_completed_at` stehen unter „Bericht gelesen“,
`calculated_at` unter „Bericht berechnet“. Sie werden nicht als Ausführungszeit,
Quellenprüfung oder Behebungszeit ausgegeben. Nicht gelieferte allgemeine
Beobachtungs-/Prüfzeiten bleiben `null`; historische Gültigkeit bleibt am Beleg.

Der einzige primäre Link lautet „Buchungen und Währungsbestätigungen im Trade
prüfen“. Er nutzt den vorhandenen `realizedTradeLink` und erhält Zeitraum,
Berichtswährung, Zeitzone, Basis, Trade-ID und `#execution-dates`. Der Anker
bezeichnet den Buchungsbereich, keine vorgetäuschte individuelle Zeilenfokussierung.
Die Shared-Komponente aktiviert ausschließlich absolute interne Apppfade;
ungeeignete Ziele bleiben Text. Eine spätere Bestätigung bleibt eine bewusste
Aktion im vorhandenen Fachformular.

Statische Karten besitzen keine Live-Region oder Alertrolle. Aufklappen,
Rerendern, neue Props und Remounts erzeugen keine automatische Ansage, zusätzliche
Reads, Writes oder Entwarnung. Die fünf Darstellungsarten tragen sichtbare
Textlabels; Farbe allein vermittelt keine Bedeutung.

## Prüfungen und Aussagegrenzen

Die lokalen Prüfungen vom 01.11.2026 verwendeten Node 22.16.0, TypeScript 5.8.3,
Vitest 3.2.0 und `TZ=UTC`; die Produktfixture behält ihre ausdrückliche
Berichtszeitzone Europe/Berlin. Alle unten als bestanden genannten Prozesse
beendeten sich regulär mit Exit 0. Der PR-Abschluss bindet zusätzlich den
tatsächlichen Head, Mainbasis, Testmerge/Tree und die erforderlichen CI-Run-/Jobbelege.

| Prüfung | Tatsächlicher lokaler Nachweis |
| --- | --- |
| Vollständige Frontend-Suite | Alle 167 Testdateien erfolgreich; enthalten sind 48 Mapper-, 25 Shared- und 9 neue Hostfälle sowie die bestehenden Performance-/Closed-/Trade-Regressionen |
| Coverage | Statements/Lines 96,00 %, Functions 91,49 %, Branches 90,33 %; unveränderte Gates 80/80/80/70 % |
| Frontend-Qualität | Vollständiger TypeScript-Buildcheck, ESLint ohne Warnungen, Prettier und Produktionsbuild erfolgreich; vorhandener Vite-Hinweis auf große Chunks bleibt bestehen |
| Neuer Browserpilot | 3/3 bei 320/390/1280 CSS px, Playwright 1.55.0 mit Chromium 140.0.7339.16, ein Worker und keine Retries; genau ein Report-GET, null unerwartete Requests/Mutationen und keine Pageerrors je Fall |
| Bestehender geklickter Berichtsrückweg | 1/1 unverändert bei 390 px: SELL → Buchungslink → Fokus `#execution-dates` → Reload → kopierte Quellen-URL → Reload → exakter Berichtsrückweg; null Writes/Browserfehler und keine zusätzlichen Performance-/Closed-Reads während des Trade-/Quellenwegs |
| Dokumentvertrag | 10/10 bestehende Dokumentchecks; strict/noEmit mit allen 42 unveränderten erwarteten Typfehlern und positiven Beispielen erfolgreich |
| Veröffentlichungsschutz | 9/9 vorhandene Version-/Publisherguards erfolgreich; Versionswerte konsistent für die vorbereitete v1.5.38 |

Die ersten Einzeltestläufe innerhalb der eingeschränkten Prozessumgebung meldeten
bestandene Fälle, schlossen aber nicht regulär ab. Gewertet wird der danach
außerhalb dieser Umgebung abgeschlossene Gesamtlauf. Der erste Browserstart
erreichte wegen fehlender Ausführbarkeit der temporären Chromium-Datei keine
Appprüfung; nach Korrektur des Dateimodus bestand derselbe unveränderte Spec.
Keine Test-, Timeout-, Retry- oder Coveragegrenze wurde gelockert.

Backend-/PostgreSQL-/Deploymentläufe sind keine lokalen B1-Nachweise. Die
unveränderten erforderlichen Projektgates werden vollständig in der PR-CI
ausgeführt; frühere Ergebnisse qualifizieren diesen Diff nicht.

Der gezielte Testschnitt umfasst Shared-Darstellung, Quellenadapter,
Hostintegration und einen Browserweg mit synthetischer Berichtsantwort bei
320/390/1280 CSS px. Er prüft unter anderem unbekannten BUY bei bestätigtem SELL,
automatische historische Zuordnung, Ausschluss, echte Nullwerte, fehlende und
mehrdeutige Quellen, neue Props/Basis, genaue interne Ziele, native Tastatur-
bedienung, Fokus und lange Texte. Vorhandene Performance-, Closed- und
Trade-Navigationsregressionen bleiben Teil der regulären Gates.

Die Browserfixture erlaubt genau den vorhandenen Report-GET und blockiert andere
APIs, Provideraufrufe sowie Mutationen vor einem echten Dienst. Native
Tastatur-/Geometrieprüfungen sind kein Ersatz für die manuelle Desktop- und
Mobile-Screenreaderabnahme TC-48 oder echten 200-/400-%-Browserzoom aus TC-45.
Diese manuellen Nachweise bleiben offen. Der Produktpilot führt auch keine
fachfremden Alert-/Journal-/Governanceabnahmen aus.

## Nächster getrennter Auftrag

Nach qualifizierter B1/F1-Integration kann der folgende Startauftrag für B2/F4
übernommen werden. Er ist hier vorbereitet, nicht bereits umgesetzt:

> Implementiere UX3-B2/F4 auf dem tatsächlichen aktuellen Main von
> `burckhju/trading-workspace`. Prüfe den kanonischen UX3-Vertrag und Befund Q12.
> Grenze mit dem bestehenden Bewertungsowner genau die betroffene Fläche in
> `ProductValuationPanel` beziehungsweise `PositionDetails` ab. Ersetze dort eine
> unbelegte allgemeine Providerursache durch eine verständliche Erklärung aus
> den vorhandenen Bewertungsfakten. Erhalte Geldwerte, Usability, Originalzeiten,
> vorhandene sichere Ziele und fachliche Statusmodelle. Nutze den B1/F1-Kern,
> soweit er diese eine Darstellung ohne neue Domainfelder trägt. Prüfe TC-49
> und die vorhandenen Bewertungsregressionen; liefere einen eigenen kleinen PR
> mit genauem Scope, Tests und noch offenen fachlichen Abnahmen. Keine neue
> Providerqualifikation, Frischepolicy, Finanzrechnung, automatische Aktion oder
> globale Hostmigration. Die erteilte Merge-/Bereitstellungsautorisierung gilt
> nur nach grünen erforderlichen Prüfungen und innerhalb dieses Auftrags.

Der [Product Backlog](../planning/PRODUCT_BACKLOG.md) bleibt die einzige fachliche
Statusquelle. Dieses Dokument protokolliert den technischen Schnitt und seine
Belege; es erteilt keine zusätzliche fachliche Plan-, Handels- oder Modellfreigabe.
