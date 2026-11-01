# UX3-B1/F1 — Währungsherkunft eines Verkaufsbeitrags

## Fortsetzungsauftrag und Dateischnitt vor Änderungen — 01.11.2026

Ausführender Rollenowner ist UX3. Der vorliegende Auftrag erlaubt Implementierung,
Tests und Fortsetzung des vorhandenen Draft-PRs; keine Merges, Releases,
Installationen oder produktiven Datenmutationen. Frühere Freigabeformulierungen
im Ausgangsdiff sind keine Freigabe dieses Auftrags.

Erneut geprüft: Main und v1.5.37 stehen auf
`bb49ffe781933270746b9f86f4aee99b6f8144c2`; #318 ist integriert.
Der bereits vorhandene Draft [#320](https://github.com/burckhju/trading-workspace/pull/320)
wird auf `feat/ux3-b1-currency-notice-20261101` fortgesetzt, Ausgangs-Head
`36522cdb8ca6a202950e459f07616483258927a8`, Tree
`a0d63b20972a12e7076fb3280487d6b5f476b692`. Sein damaliger Testmerge ist
`f251de0676af5399c027b5ce845329d5f64abcf3`, derselbe Tree. Kein zweiter Pilot.

Die acht sichtbaren offenen PRs #320, #319, #315, #220, #207, #205, #197 und
#187 wurden auf Überschneidungen geprüft. Nur PRODUCT_BACKLOG.md überschneidet
sich mit #319/#315. Der neue Produktschnitt lässt diese Datei sowie die
MASTER-Dateien auf Mainstand. Keine Kenntnis unveröffentlichter Chat-Arbeit;
vor dem Push werden Main und Branch-Head erneut aufgelöst. Der frisch geklonte
Checkout hatte nach dem Checkout keine lokalen Änderungen. Keine AGENTS.md
im Repository; README, Entwicklungs- und Architekturvorgaben gelten.

### Konkreter Producer-/Consumervertrag

| Producer / Owner | Consumer / erlaubter Schnitt | Unveränderte Grenze |
| --- | --- | --- |
| TradePosition: gespeicherte ExecutionCurrencyResolution, Confirmation und Evidence innerhalb report.sources | Performance-Featureadapter und quellengebundene Details | Resolverwert und Originalreason; keine Vorschau, neue Quelle, Bestätigung oder Zusatzabfrage |
| Performance: bereits akzeptierte RealizedGrossReport-Antwort, Item, summary und Kontext | buildRealizedCurrencyNotice und RealizedGrossSources | verifyRealizedReport, echte Itemmitgliedschaft, gleiche Trade-/Produkt-/Executionidentität; Status und Geldstrings bleiben Ownerfakten |
| UX1: Herkunftssemantik und manuelle Vorrangregel | Ausschließlich gespeicherte Herkunft im Pilot | ExecutionCurrencySources, Preview, Formulare und Capture unverändert |
| UX2: realizedTradeLink und geprüfter Berichtsrückkontext | Ein lesender Presenter-Link zu #execution-dates | Bereichsziel, bestehende Guards/Fokus-/Abort-/Generationsgrenzen; keine Routerparameter oder Requests hinzugefügt |
| UX3: geprüfte Texte und begrenzte Präsentationsprops | Reiner NoticeCard-Presenter mit nativen Details | Nur Information/Warnung und ein lesender Link; keine generische Status-, Retry-, Recovery- oder Alarmverwaltung |

### Reservierter enger Dateischnitt

Produkt und Tests:

- frontend/src/features/performance/components/RealizedGrossSources.tsx
- frontend/src/features/performance/components/RealizedGrossSources.test.tsx
- frontend/src/features/performance/components/ReportCurrencyEvidence.tsx
- frontend/src/features/performance/components/ReportSourceEntry.tsx
- frontend/src/features/performance/services/realizedCurrencyNotice.ts
- frontend/src/features/performance/services/realizedCurrencyNotice.test.ts
- frontend/src/shared/notices/types.ts
- frontend/src/shared/notices/NoticeCard.tsx
- frontend/src/shared/notices/NoticeCard.test.tsx
- frontend/src/shared/notices/index.ts
- frontend/src/features/performance/pages/RealizedGrossPage.test.tsx
- tests/e2e/ux3-currency-notice.spec.ts
- dieser vorhandene technische Qualifikationsbericht

Der optionale ReportSourceEntry-Slot wird nur für den Pilot präzisiert:
Resolution-null bleibt auch neben dem Preis unbekannt; der Default anderer
Consumer bleibt unverändert. Fremde mitgelieferte Confirmation-Detailobjekte
werden nicht als Beleg dieser Buchung angezeigt. Unabhängige Ursachen werden
nur optisch gruppiert, frühere SELLs nicht als gemeinsame BUY-Ursache benutzt.

Umfangskorrektur gegenüber dem Ausgangs-PR: VERSION, backend/pyproject.toml,
frontend/package.json, frontend/package-lock.json, PRODUCT_BACKLOG.md und die
sechs dort veränderten kanonischen UX3-Dokumente werden auf Mainstand gebracht;
die neue V1.5.38-Release-Notiz entfällt. Keine weiteren Produktflächen.
Das Dokumentationstypmodell bleibt Dokumentation und außerhalb des
Produktimportgraphen. Die normative Semantik aus #314 bleibt maßgeblich.

Gezielte neue Nachweise betreffen die gefundenen Herkunftslücken und den
synchronen Wechsel von Text/Details/Link. Bestehende Null-/Nullsummen-/PARTIAL-,
A→B→A-, Navigations-, Preview- und PostgreSQL-Ownerregressionen werden erhalten.
Alle normalen Workflows, Coverage- und Owner-Gates bleiben unverändert. Frühere
grüne Runs gelten nur für ihren damaligen Head; aktuelle Belege folgen nach
Umsetzung. Manuelle Fach-/Screenreader-/Zoomabnahme bleibt ausdrücklich offen.

## Umsetzung des begrenzten Pilots

### Rücknahme paralleler Releasevorbereitung — 01.11.2026

Nach Pilothead `06280ed5a59b49d56950b14ed9f1e42bfd0e130a` wurde der gemeinsame
Branch außerhalb dieser Fortsetzung weitergeschrieben: Main
`484143d33aa5f2d443da6b2edf097ae1cb5aee3a` mit den beiden UX1-Dokumenten aus #319,
Releasevorbereitung `71e971a67be7f1ca10192e04e3832f843b8099bd` und danach
Dokumentationsabgleich `90b72d85122bc33117c3db9a277b889573985660`.
Produktcode und Tests des Pilots blieben dabei unverändert.

Auf die konkrete Frage zur Rücknahme der fünf Release-Dateien antwortete der
Nutzer ausdrücklich „Zurücknehmen“. Die vier Versionsdateien VERSION,
backend/pyproject.toml, frontend/package.json und frontend/package-lock.json
werden auf den aktuellen Mainstand 1.5.37 zurückgeführt; die neue
V1.5.38-Release-Notiz wird entfernt. Der Folgecommit erhält die Git-Historie,
die integrierte UX1-Dokumentation sowie sämtliche Pilotänderungen.

Die inzwischen zusätzlich angepassten docs/ui/ux-3/README.md,
docs/ui/ux-3/components-and-actions.md und docs/ui/ux-3/integration-and-rollout.md
bleiben als Dokumentationsabgleich erhalten. Releaseverweise und Freigabeaussagen
werden an die Nutzerentscheidung angepasst. Dadurch umfasst der tatsächliche
PR-Diff die oben genannten 13 Dateien und diese drei Dokumentationsdateien.
Das Dokumenttypmodell contracts.ts, Fachverträge, Produkt- und Testschnitt sowie
alle Workflows bleiben unverändert. Der dokumentierte B2-Startprompt erteilt
keine Folgefreigabe und führt keine weitere Produktänderung aus.

Der PR bleibt Draft. Dieser Auftrag erlaubt keinen Merge, Release, keine
Installation und keine produktive Datenmutation. Aktueller Rücknahmehead,
Testmerge/Tree und reguläre CI-Ergebnisse werden im bestehenden PR gebunden;
abgebrochene frühere Läufe sind kein vollständiger Endnachweis.

Die aktive Umstellung erfolgt ausschließlich in RealizedGrossSources. Eine
statische Karte erklärt den ausgewählten Verkaufsbeitrag und die Qualifikation
der Berichtssumme. Der Performanceadapter nimmt item, report und context aus
der bereits akzeptierten Antwort; er nutzt verifyRealizedReport, prüft echte
Itemmitgliedschaft und eindeutige Executionidentität und verwendet die vorhandene
UX2-Navigation. Der reine Presenter erhält nur id, title, information/warning,
Textfelder für cause/impact/automatic/userNeed, Detailzeilen und einen Leselink.
Er importiert keine Featureinternas und keine Dokumentationstypen.

### Herkunft, Wirkung und Quellenbindung

- Resolverwert und Originalsource bleiben maßgeblich. EXECUTION_DOCUMENT,
  HISTORICAL_LISTING(S), PRIOR_BUYS und REPLACED_EXECUTION erklären die
  gelieferte automatische Herkunft; eine erneute Bestätigung wird nicht verlangt.
  USER_CONFIRMED bezeichnet ausschließlich eine vorhandene Bestätigung.
- UNKNOWN, MIXED und CONFLICT behalten ihren Originalreason. Ein unbekannter
  Reason oder Source erhält keine erfundene Diagnose. Fehlende Resolution wird
  auch neben dem Stückpreis nicht aus Confirmation rekonstruiert. Im Default
  anderer ReportSourceEntry-Consumer bleibt die bestehende Darstellung erhalten.
- Nur NOT_COMPUTABLE zusammen mit einem gelieferten Währungsreason begründet
  die entsprechende Beitragswarnung. EXCLUDED plus CURRENCY_UNKNOWN erzeugt
  keine zusätzliche Sperre der gewählten Summe. Ein eigener Satz übernimmt nur
  die bestehende report.summary-Qualifikation; die bereits vorhandene Anzeige
  von total/subtotal und ihren Originalstrings bleibt beim Bericht.
- null bleibt unbekannt, eine tatsächliche 0 bleibt 0. Der Pilot berechnet
  weder Kostenbasis noch Brutto-PnL, FX oder Summen und interpretiert keine
  Decimalstrings durch Number/Float neu.
- Der vorausgehende Executionprefix ist kein Nachweis gemeinsamer BUY-Ursachen.
  Frühere SELLs werden für die Währungszuordnung nicht zu Käufen umgedeutet.
  Quellen mit passender Trade-/Produktidentität, side und is_effective werden
  einzeln angezeigt; die Karte gruppiert sie ausschließlich optisch.
- Die Eindeutigkeit von Source-Execution-IDs wird über die gesamte Antwort vor
  der Trade-/Produktzuordnung geprüft. Fehlende, doppelte oder fremde Quellen
  werden nicht als Herkunft übernommen. Verschachtelte Confirmation-/History-
  Detailobjekte benötigen dieselbe Trade- und Execution-ID. Gültige gelieferte
  Resolverreferenzen bleiben auch ohne passendes Detailobjekt als Referenz sichtbar.
- IDs, Originalreferenz, Quellenversion, Resolverversion und tatsächlich gelieferte
  Fingerprints bleiben inspectierbar. source_reference wird als Text gerendert.
  Erfassungszeit, Ausführungspräzision und historische Gültigkeit bleiben getrennt;
  valid_to wird ausdrücklich als ausschließlich benannt. Der Produktname ist
  heutige Stammdatenanzeige, kein historischer Währungsbeleg.

### Navigation und zugängliche Darstellung

Die Hauptaussage und die belegte Einschränkung stehen außerhalb der Details.
Native details/summary und Linkelemente bleiben per Tastatur bedienbar. Der Link
„Buchungen und Währungsbestätigungen im Trade prüfen“ wird ausschließlich mit
realizedTradeLink gebildet; exakter Trade, Zeitraum, Berichtswährung, Zone, View,
Seite und Basis bleiben erhalten. #execution-dates bezeichnet den Buchungsbereich,
keine einzelne Ausführung und keinen neuen Routerparameter.

Titel, Originalgründe, Details und Aktion werden gemeinsam aus den aktuellen
Props ersetzt. Requestgeneration, Abort, A→B→A und Fokusführung bleiben bei den
vorhandenen Hosts. Eine neue basis.id oder ein Remount erzeugt weder eine neue
Ursache noch eine Recovery. Die Karte hat keine Alertrolle, Live-Region, Effekte,
Read-/Writecallbacks oder persistente Quittierungszustände. Aufklappen startet
keine Abfrage und erzeugt keine neue Bestätigung.

## Gezielte Prüfung und Nachweisgrenzen

Neue und erweiterte Tests prüfen sichtbares Verhalten und konkrete Quellen-
oder Kontextgrenzen. Unveränderte Ownerregressionen werden nicht durch neue
parallele Finanztests ersetzt.

| Anforderung / TC-Bezug | Konkreter Nachweisweg |
| --- | --- |
| Automatische historische Herkunft ohne Eingabe; PRIOR_BUYS ohne SELL-Bestätigung (TC-02/04) | realizedCurrencyNotice.test.ts, RealizedGrossSources.test.tsx; bestehende historische Resolver-/Berichttests |
| UNKNOWN/MIXED/CONFLICT, fehlende Resolution, unbekannter Reason/Source (TC-01/03/05) | Adapter-/Komponentengegenfälle; Resolver-null trotz vorhandener Confirmation bleibt auch in der Preiszeile unbekannt |
| EXCLUDED plus CURRENCY_UNKNOWN (TC-09) | Adapter und tatsächlicher Report-Consumer zeigen den ausgeschlossenen Beitrag bei unverändert vollständiger gewählter Summe |
| null, tatsächliche Null und PARTIAL-Teilbetrag (TC-06/07) | Bestehende RealizedGrossPage-Kette erweitert: unbekannter Beitrag, rohe 0.0040000000 bei angezeigter Teilsumme 0,00 EUR, tatsächliche vollständige Nullsumme; keine Umrechnung |
| Prefix mit früherem SELL und unabhängige Quellen (TC-59) | Bestehende synthetische Reportfixture und gezielte Adapter-/Komponentenfälle; weder frühere SELLs noch spätere/ersetzte Käufe werden zu gemeinsamer BUY-Ursache |
| Fehlende/fremde/doppelte Quellen und verschachtelte Confirmation (TC-08/35/44) | Globale Source-Eindeutigkeit, Trade-/Produktbindung, Confirmation-Trade-/Execution-Gegenfälle; fremde Payloads erscheinen nicht |
| Basis-/Filter-/Objektwechsel und alte Antworten (TC-33/35/58) | Erweiterte bestehende RealizedGrossPage-Fälle plus direkter Komponentenwechsel; bestehende PerformanceWorkspace-A→B→A- und UX1-Previewtests bleiben unverändert |
| Keine Zusatzreads/-writes und vollständiger Rückweg (TC-41/44) | Fetchspies in Komponententests; neuer Browserpilot erlaubt genau einen Report-GET; unveränderte trade-workspace-navigation-Journey prüft Klick, Reload, kopierte Quellen-URL und Rückkehr |
| 320/390/1280 px, lange Referenzen, Tastatur/Fokus, ruhige Remounts (TC-45/46/47) | ux3-currency-notice.spec.ts im regulären Smokejob: native Enter/Space, Tab/Shift+Tab, sichtbarer Fokus, Karten-/Quellen-/Dokumentbreite, keine Alerts und keine Zusatzrequests |
| Andere ReportSourceEntry-Consumer und UX1-Previews | Expliziter Default-Gegenfall sowie bestehende ClosedTradesPage-, ExecutionCurrencySources- und ExecutionCurrencyPreview-Suites |

TC-60/61 werden nicht als implementierte Create-/Berechtigungsfälle ausgegeben:
Dieser Pilot zeigt ausschließlich vorhandene, im Report gebundene Objekte.
Keine pauschale Backendupdate-Empfehlung, neue Pflichtentscheidung oder zusätzliche
Berichtsblockierung wird aus einem fehlenden optionalen Feld abgeleitet.

### Tatsächlich lokale Prüfungen dieser Fortsetzung

Laufzeit im isolierten Checkout: Node v24.22.1; keine lokale Installation von
Abhängigkeiten oder Browsern. Deshalb keine lokale Vitest-, TypeScript-Gesamt-,
Prettier-, Browser- oder PostgreSQL-Ausführung behauptet. Der reine
TypeScript-Syntaxstrip ist kein Typecheck.

- node docs/ui/ux-3/verify-docs.mjs: 10/10 bestanden; 818 lokale Dateilinks,
  24 Anker und 57 Tabellen; Dokumentation außerhalb des Produktimportgraphen.
- node --test .github/tests/version-tag.test.cjs: regulär Exit 0; Versionen
  wieder konsistent auf unverändertem Mainstand 1.5.37, kein Publisher ausgeführt.
- Syntaxprüfung der Adapter-/Typdateien über vorhandenes node:module:
  regulär Exit 0; ausdrücklich kein Ersatz für die reguläre TypeScript-Prüfung.
- git diff --check: regulär Exit 0; vollständiger finaler Dateischnitt oben.

Die regulären Frontend-, Backend-, PostgreSQL-, E2E-/Performance-/Journal-/
Governance-, Deployment- und Versionsschutzgates bleiben unverändert. Der neue
Browserspec liegt im bestehenden tests/e2e-Verzeichnis und läuft durch den
vorhandenen ungefilterten Smoke-Aufruf. Die unveränderte CI-Retrykonfiguration
wird nicht als retryfreier lokaler Browsernachweis ausgegeben.

Aktueller finaler Head, tatsächlich ausgecheckter Testmerge, Tree und konkrete
Run-/Jobergebnisse werden im fortgesetzten [Draft-PR #320](https://github.com/burckhju/trading-workspace/pull/320)
gebunden. Frühere grüne Runs am Ausgangs-Head 36522cdb qualifizieren den
geänderten Stand nicht. Die historischen lokalen Aussagen dieses Ausgangsdiffs
bleiben unter dessen Git-Commit nachvollziehbar und werden hier nicht als neu
ausgeführt fortgeschrieben.

## Verbleibende Abnahme

Technische Tests sind keine menschliche Fachabnahme. Offen bleiben die fachliche
Prüfung der konkreten Texte und Wirkung durch Performance/TradePosition und UX1,
die UI-Abnahme durch UX2/UX3, manuelle Desktop-/Mobile-Screenreaderprüfung
(TC-48) sowie echter 200-/400-%-Browserzoom. Automatische DOM-/Tastatur- und
Viewportprüfungen ersetzen diese Nachweise nicht.

Der Product Backlog bleibt einzige fachliche Statusquelle. Kein neuer FT-/PB-
Eintrag, kein zweiter Statuskatalog und keine MASTER-Statuspflege durch diesen
Schnitt. O1/O3 und UX3-F2–F8/UX4-B/C/D bleiben gesonderte Aufträge; O4 wird durch
den korrekt benannten vorhandenen Bereichslink nicht vorweggenommen.
