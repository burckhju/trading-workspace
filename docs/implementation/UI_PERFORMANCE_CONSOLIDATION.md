# Performance-Berichte mit gemeinsamer Zeitraumsteuerung

## Auftrag und geprüfte Grundlage

UI8 bezeichnet den begrenzten Umsetzungsschritt zur gemeinsamen Bedienung der beiden vorhandenen Performance-Berichte. Es ist keine neue FT-/PB-Nummer und keine zusätzliche Lifecycle-Statusquelle. Maßgeblich bleibt [PB-019 im Product Backlog](../planning/PRODUCT_BACKLOG.md); dieses Dokument beschreibt Implementierung, Verträge und technische Nachweise.

Vor Beginn am 27.10.2026 geprüft:

- `main`: `eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4`, Tree `a864274c4c050698e1fc61134a98dfb03dcf1441`, Version `1.5.23`.
- Arbeitsbranch: `refactor/performance-report-workspace` auf diesem `main`; integrierte UI1–UI5 sind damit enthalten.
- UI6/Journal: [Draft-PR #289](https://github.com/burckhju/trading-workspace/pull/289), Head `bfb18e9de5f04c7eea0763583c75dd6d785cec02`, weiterhin offen und nicht integriert. UI6 ist keine Voraussetzung für diese Änderung.
- Die offenen PR-Dateilisten enthalten keine Performance-Anwendungsdateien. `PRODUCT_BACKLOG.md` und `TRACEABILITY.md` überschneiden sich unter anderem mit #289 und [#268](https://github.com/burckhju/trading-workspace/pull/268). Performance-Ergänzungen bleiben auf den betroffenen Abschnitt begrenzt; vor einer späteren Integration sind die tatsächlichen aktuellen Diffs erneut zu prüfen.
- Berücksichtigt wurden [README](../../README.md), [Development Guide](../technical/DEVELOPMENT_GUIDE.md), [Coding Standards](../technical/CODING_STANDARDS.md), [Roadmap, Lieferziel C](../foundation/ROADMAP.md) sowie die unten verlinkten Berichtsqualifikationen. Im Checkout wurde keine zusätzliche `AGENTS.md` gefunden.

Implementierung und Tests sind auf [Commit `35356d7c4e824c29b9fb92b9a86b6e78a0e7a901`](https://github.com/burckhju/trading-workspace/commit/35356d7c4e824c29b9fb92b9a86b6e78a0e7a901), Tree `2d69f8932753814c629fcb8e787738e5b4929950`, gebunden. [Draft-PR #290](https://github.com/burckhju/trading-workspace/pull/290) trägt den Titel **refactor(performance): Zeitraumsteuerung und Berichtsansichten konsolidieren**. Die nachfolgenden Prüftabellen unterscheiden das lokale vollständige Frontend-Gate, die tatsächlichen CI-/PostgreSQL-Läufe und den abschließenden Dokumentationsstand.

Der anschließende [Testabgleich `cf419d4f27d5ad5b682f5a739ddb563c91d99309`](https://github.com/burckhju/trading-workspace/commit/cf419d4f27d5ad5b682f5a739ddb563c91d99309), Tree `e5eb08e03f69587dd78df644716a184f43ec12e9`, ändert ausschließlich drei Quellenhinweis-Textassertions in den beiden nativen Performance-Journeys. Anwendung, finanzielle Assertions, Testidentitäten, Runner und Workflows bleiben gegenüber dem Implementierungscommit identisch. Anlass und neue native Qualifikation sind unten ausdrücklich getrennt ausgewiesen.

Der Auftrag endet mit einem geprüften Draft-PR. Merge, Versionsanhebung, Veröffentlichung, PC-Installation und menschliche fachliche Abnahme sind gesonderte Schritte.

## Bedienweg vorher und nachher

Vorher besaßen Abschluss- und Verkaufsbericht jeweils ein eigenes Formular. Der Abschlussbericht konnte einen angewendeten URL-Kontext wiederherstellen, sein Link zum Verkaufsbericht übertrug aber keinen Zeitraum und keine Berichtszone. Der Verkaufsbericht führte die Auswahl nur lokal. Wechsel und Reload konnten dadurch eine erneute Eingabe derselben Werte erfordern.

Die Hauptnavigation besitzt jetzt einen Einstieg **Performance**. `/performance` führt zur bestehenden Verkaufsroute; beide bestehenden direkten Routen bleiben erhalten. [PerformanceWorkspace](../../frontend/src/features/performance/pages/PerformanceWorkspace.tsx) stellt die Berichtsart, genau ein [Filterformular](../../frontend/src/features/performance/components/PerformanceFilters.tsx) und genau eine aktive Berichtsansicht bereit:

1. **Verkäufe im Zeitraum** oder **Trades mit Vollabschluss im Zeitraum** wählen.
2. **Von**, **Bis** und **Berichtszeitzone (IANA)** prüfen oder bearbeiten. Die Berichtswährung ist sichtbar und schreibgeschützt **EUR**.
3. **Bericht lesen** übernimmt die gültige Auswahl und liest den ausgewählten Endpoint.
4. Der bewusste Wechsel zur anderen Berichtsart übernimmt dieselben sichtbaren gültigen Filter und liest ausschließlich den Zielbericht. Zeitraum und Zeitzone werden nicht erneut eingegeben.

Die aktive Berichtsart erscheint in der Seitenüberschrift und über `aria-pressed` an den beiden normalen, per Tastatur bedienbaren Auswahlbuttons. Das gemeinsame Formular besitzt eindeutige Labels, Feldfehler mit `aria-invalid`/`aria-describedby` und Fokus auf dem ersten fehlerhaften Feld. Umschalter und Formular können in schmalen Ansichten umbrechen. Der gemeinsame Rahmen zeigt keine zweite Summe oder zusätzliche identische Zusammenfassung.

[ClosedTradesPage](../../frontend/src/features/performance/pages/ClosedTradesPage.tsx) und [RealizedGrossPage](../../frontend/src/features/performance/pages/RealizedGrossPage.tsx) bleiben dünne Einstiegskomponenten desselben Rahmens. Die vorhandenen Ergebnis-, Datenabdeckungs- und Herkunftsanzeigen liegen in [ClosedTradesReportView](../../frontend/src/features/performance/components/ClosedTradesReportView.tsx) beziehungsweise [RealizedGrossReportView](../../frontend/src/features/performance/components/RealizedGrossReportView.tsx). Es entsteht keine zweite konkurrierende Berichtsstrecke.

## Gemeinsame Auswahl, getrennte finanzielle Bedeutung

| Berichtsart | Unveränderte Grundgesamtheit | Definition und Endpoint |
|---|---|---|
| Verkäufe im Zeitraum | Wirksame SELL-Ausführungen innerhalb der Periode; einschließlich Teilverkäufen weiterhin offener Trades. Die Kostenbasis kann frühere Ausführungen benötigen. | `realized-gross-sell-v2`, `GET /api/v1/performance/realized-gross` |
| Trades mit Vollabschluss im Zeitraum | Trades mit wirksamem vollständigem Abschluss innerhalb der Periode; je Trade das gesamte Bruttoergebnis einschließlich früherer Teilverkäufe. | `closed-trade-gross-v1`, `GET /api/v1/performance/closed-trades` |

Die gemeinsamen Filter sind `from_date`, `to_date`, `report_currency` und `report_timezone`. Die Oberfläche bleibt bei EUR, ohne den vorhandenen Backend-Währungsvertrag einzuschränken. EUR ist eine Berichtsauswahl: Sie bestätigt keine Buchungswährung und löst keine Umrechnung aus.

Die bestehende September-/Oktober-Referenz wird wiederverwendet: September enthält SELL-Beiträge von insgesamt `10,00 EUR`, aber keinen Vollabschluss; Oktober enthält einen SELL-Beitrag von `30,00 EUR`, während das vollständige Ergebnis desselben Trades `50,00 EUR` beträgt. Diese Erwartungswerte stammen aus den vorhandenen Backendfixtures und -regressionen. Die Frontendfixtures liefern fertige Antwortwerte und rechnen keine neue finanzielle Erwartung aus. Das im Auftrag erläuterte Januar-/Februar-/März-Beispiel mit `30,00`/`140,00`/`170,00 EUR` beschreibt dieselbe fachliche Unterscheidung; es wird hier nicht als eigens ausgeführter zusätzlicher Seed-Nachweis ausgegeben.

Es gibt keine Summe über beide Berichte und keine Ableitung eines Berichts aus den Zeilen des anderen. Abschlussstatistiken bleiben allein beim Abschlussbericht. Rohwerte und gerundete Geldtexte stammen aus der jeweiligen vollständigen Backendantwort; lokale Zeilen oder Seiten werden nicht zur Geldberechnung verwendet. Gebühren, Nettoergebnis, FX-Umrechnung und Depot-Equity werden nicht ergänzt.

Einschließliche Kalendertage und Berichtszone werden weiterhin im Backend in Periodengrenzen übersetzt. Die Frontendvalidierung prüft Kalenderdaten und bekannte Zonen, berechnet aber keine eigenen UTC-/Sommerzeitgrenzen. Datumgenaue und zeitlich unklare Ausführungen behalten ihre bisherige Darstellung und Einordnung.

Maßgebliche bestehende Verträge:

- [SELL-Berichtsqualifikation](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
- [Abschlussberichtsqualifikation](CLOSED_TRADES_REPORT_QUALIFICATION.md)
- [Abschlussquellenintegration](CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md)
- [Abschlussstatistiken V1](CLOSED_TRADE_STATISTICS_V1.md)
- [Backend-Router](../../backend/app/features/performance/api/router.py), [Snapshot-Reader](../../backend/app/features/performance/service/reader.py), [Frontend-Client](../../frontend/src/features/performance/services/client.ts) und [Antworttypen](../../frontend/src/features/performance/types/api.ts)

## URL-Vertrag und Wiederherstellung

| Bestandteil | Verkaufsbericht | Abschlussbericht |
|---|---|---|
| Route | `/performance/realized-gross` | `/performance/closed-trades` |
| `report_context` | `realized-gross` | `closed-trades` |
| Erforderliche Filter | `from_date`, `to_date`, `report_currency`, `report_timezone` | dieselben vier Filter |
| `report_view` | `candidates`, `usable`, `unresolved`, `excluded`, `all` | `candidates`, `qualified`, `unresolved`, `excluded`, `all` |
| Standardansicht | `candidates` | `candidates` |
| `report_page` | `1` bis `1000` | `1` bis `100` |
| Seitengröße | 20 Zeilen | 20 Zeilen |
| `report_basis` | optionaler Fingerprint aus 64 kleinen Hexadezimalzeichen | gleicher syntaktischer Fingerprintvertrag, ausschließlich für den Abschlussbericht |

Die Seitenobergrenzen folgen den vorhandenen Ressourcenverträgen des Readers: maximal 20.000 Executions beim SELL-Bericht und maximal 2.000 Trades beim Abschlussbericht. Der neue [SELL-Kontexthelper](../../frontend/src/features/performance/services/performanceReportContext.ts) übernimmt deshalb nicht unverändert die 100-Seiten-Grenze des Abschlussparsers. Intern bleiben Seiten nullbasiert; die URL ist einsbasiert. Fehlende optionale Zeilen-/Seitenwerte bedeuten Standardansicht und erste Seite; ausdrücklich leere Werte sind ungültig.

Ohne ausdrücklichen Berichtskontext werden der aktuelle Monat bis heute und EUR lediglich vorgeschlagen. UX1-C verwendet dafür die bereits bekannte gültige IANA-Zeitzone des Browsers; beide Kalenderdaten werden in genau dieser Zone gebildet. Nur wenn der Browser keine gültige Zone liefert, bleibt `Europe/Berlin` der korrigierbare Vorschlag. Die vorhandene IANA-Feldvalidierung prüft auch diesen Vorschlag; reine UTC-Offsets werden nicht übernommen. Es erfolgt kein automatischer Report-GET. Ein gültiger vollständiger direkter URL-Kontext hat vor dem Browservorschlag Vorrang, stellt seine genaue Auswahl her und liest den zu dieser Route gehörenden Bericht. Die aufklappbare „Herkunft der Berichtsauswahl“ erklärt Linkkontext, Browservorschlag und Rückfall; manuelle Änderungen bleiben erhalten. Es entsteht weder Browser-Storage noch eine neue fachliche Provenienz- oder Bestätigungstabelle.

Doppelte Werte, leere oder unvollständige Pflichtparameter, ungültige Kalenderdaten, Von nach Bis, unbekannte Zeitzonen, ungültige Seiten/Fingerprints sowie eine zur Route unpassende Berichtsart führen zu einem verständlichen Kontextfehler. Es gibt keinen Ersatzread mit Standardwerten. Eindeutige vorhandene Eingaben können als Entwurf sichtbar bleiben; mehrdeutige Werte werden nicht durch Auswahl eines der Duplikate repariert. Ein fehlerhafter expliziter Link bleibt auch nach Bearbeitung oder Berichtswechsel fehlerhaft, bis **Bericht lesen** die neue gültige Auswahl ausdrücklich übernimmt.

Feste Offsetangaben wie `+01:00`, `-0230`, `+01` oder `+0100` erfüllen den IANA-Vertrag nicht. Moderne `Intl.DateTimeFormat`-Implementierungen können solche Werte akzeptieren, während der Backendvertrag einen Zonennamen benötigt. Die gemeinsame Feldvalidierung und die zusätzlichen Eingangsprüfungen beider Workspace-Routen weisen diese Werte deshalb vor jedem GET zurück. Die benannte Zone `Etc/GMT+1` bleibt gültig. Der veröffentlichte Abschlussparser selbst bleibt unverändert; die zusätzliche Prüfung liegt am gemeinsamen Performance-Einstieg.

Ein formal gültiger Nicht-EUR-Link bleibt als solcher erkennbar und erhält den erklärten Währungsfehler. Er wird nicht beim Laden oder Moduswechsel automatisch als EUR-Bericht gelesen. Die fest angezeigte EUR-Auswahl kann nach Prüfung von Zeitraum und Zone ausdrücklich als neue Auswahl übernommen werden.

Beim Berichtswechsel werden ausschließlich die gemeinsamen gültigen Filter übertragen. Der Zielbericht startet mit `report_view=candidates`, `report_page=1` und ohne `report_basis`. Der vorherige vollständige URL-Kontext bleibt in der Browserhistorie verfügbar. Reload sowie Zurück/Vor folgen dem React-Router-Kontext einschließlich Berichtsart; nicht angewendete Zwischenwerte werden bei dieser bewussten Navigation durch die URL-Auswahl ersetzt. Es gibt weder eine einmalige Auswertung von `window.location.search` noch Browser-Storage als konkurrierende Quelle.

Zeilenfilter und Pagination ändern die URL lokal und verwenden dieselbe vollständige Antwort. Quellenaufklappen liest bereits enthaltene Herkunft. Ist eine angeforderte Seite nach einem neuen Read nicht mehr vorhanden, zeigt die Ansicht die letzte verfügbare Seite und erklärt den begrenzten Seitenwechsel, ohne die alte Seite als wiederhergestellt auszugeben.

## Filterentwurf, angewendete Auswahl und Antwort

Der gemeinsame Rahmen hält drei Zustände auseinander:

| Zustand | Bedeutung | Änderung |
|---|---|---|
| Filterentwurf | Sichtbare, gerade bearbeitete Feldwerte; auch unvollständige Zwischenwerte | Feldänderung, ausdrückliche Übernahme oder Router-Navigation |
| Angewendeter Kontext | Gültige Berichtsart und Filter aus der URL, ergänzt um lokale Zeilen-/Seitenwahl und optionalen Vergleichsfingerprint | `Bericht lesen`, gültiger Berichtswechsel, lokale Navigation oder Browserhistorie |
| Antwort | Vollständige validierte Antwort eines konkreten Reads mit eigener Berichtsart und Quellenbasis | Nur ein erfolgreicher, noch aktueller Request |

Schon eine Feldänderung entwertet einen laufenden Request und entfernt das zuvor gezeigte Ergebnis. Sie erzeugt selbst keinen neuen GET. Dadurch erscheint eine frühere Summe nicht unter neuen, noch nicht angewendeten Eingaben als passend.

Validierungsfehler erhalten den Entwurf und setzen einen Feldfehler. Lesefehler erhalten die angeforderten Eingaben, zeigen aber keine frühere Summe. Ein anschließender bewusster Wechsel mit gültigen Filtern ist möglich, solange kein noch ungeklärter expliziter URL-Kontext vorliegt. Neue gültige URL-Kontexte werden ausschließlich durch den Routereffekt gelesen; das erneute Lesen einer identischen angewendeten URL wird direkt ausgelöst. Submit und URL-Synchronisierung erzeugen damit keinen doppelten aktuellen GET.

## Request-, Antwort- und Quellenisolation

Vor jedem neuen Read werden der vorherige `AbortController` abgebrochen und seine Generation entwertet. Feldänderung, Routerwechsel und Unmount entwerten ebenfalls. Nach Auflösung eines Requests werden Abbruchsignal und Generation geprüft, bevor Daten oder Fehler übernommen werden. Das schützt auch A→B→A: Eine verspätete Antwort des ersten A darf den später erneut gewählten A-Kontext nicht ersetzen.

Die Identität umfasst immer **Berichtsart plus alle vier Filter**. Ein Moduswechsel lädt nur den gewählten Endpoint. Es gibt kein vorsorgliches paralleles Laden beider Berichte und keinen gemeinsamen Antwortcache. Der lokale Vergleich zuletzt gelesener Fingerprints wird nach derselben vollständigen Identität geführt.

Jede Antwort wird vor Anzeige gegen ihre Definition, Filter und Währung geprüft. Beim Abschlussbericht gelten zusätzlich unverändert:

```text
statistics.definition_version = closed-trade-statistics-v1
statistics.report_basis_id = report.basis.id
statistics.report_status = report.summary.status
```

Eine falsche Berichtsdefinition oder Statistikbindung verwirft die vollständige Antwort. Erneutes Lesen ersetzt Ergebnis, Zähler, Zeilen, Herkunft und gegebenenfalls Abschlussstatistiken gemeinsam; alte Quelldetails werden dabei geschlossen.

Jeder Endpoint liest seinen eigenen konsistenten Snapshot. Zwei GETs bilden keinen gemeinsamen atomaren Quellenstand. Eine `basis.id` wird weder beim Moduswechsel übertragen noch berichtsübergreifend verglichen. Ein mitgegebener Fingerprint dient nur dem Vergleich mit dem aktuellen Read; er ist kein gespeicherter historischer Bericht und erlaubt keine Rekonstruktion eines damaligen Wissensstands. Der Quellenhinweis benennt ehrlich den **mitgegebenen oder zuletzt gelesenen Stand dieser Auswahl** als Vergleichsgrundlage. Er behauptet bei einem erstmalig geöffneten Link keinen bereits erfolgten eigenen Read und schreibt eine Änderung keinem bestimmten geöffneten Trade unbelegt zu.

Die bisherigen Zustände `EMPTY`, `COMPLETE`, `PARTIAL` und `NOT_COMPUTABLE` bleiben erhalten. Fehlend ist nicht Null; ein bekannter Teilbetrag ersetzt keine unbekannte Gesamtsumme. `REPORT_INPUT_INVALID`, `REPORT_RESOURCE_LIMIT` und `REPORT_READ_UNAVAILABLE` behalten ihre verständlichen Fehlermeldungen. Nach einem Validierungs-, Antwortidentitäts- oder Lesefehler wird kein altes Ergebnis der neuen Auswahl zugeschrieben.

## Kompatible Quellenaufrufe

[closedReportContext.ts](../../frontend/src/features/performance/services/closedReportContext.ts) bleibt unverändert. Seine veröffentlichten Funktionen `parseClosedContext`, `closedContextQuery`, `closedListUrl`, `closedTradeSourceLink`, `preserveClosedContext`, `verifyClosedReport` und `verifyClosedStatistics` behalten ihre Semantik. Insbesondere akzeptiert der Abschlussparser keinen SELL-Kontext, und `preserveClosedContext` erhält auch ungültige Mehrfachparameter als ungültig.

Die bestehende Strecke Abschlussliste → `/trade-management?trade_id=…&view=sources` → Abschlussliste erhält die genaue Filterauswahl, Zeilenansicht und Seite. Historische Plan-, Review-, Journal- und sonstige Quellenpins bleiben bei ihrer bisherigen Navigation. Die Rückkehr liest aktuelle Daten und kann eine geänderte Quellenbasis melden; sie verspricht keinen unveränderten früheren Bericht. [ClosedTradeSourceJourney.test.tsx](../../frontend/src/features/performance/pages/ClosedTradeSourceJourney.test.tsx) prüft die tatsächlichen Listen-/Quellenkomponenten einschließlich Rückkehr, Zurück und Reload.

SELL-Quellenlinks behalten den bisherigen Weg zu `#execution-dates`. Ein neuer SELL→Tradequellen→SELL-Rücksprungvertrag gehört nicht zu UI8. URLs transportieren keine vertrauenswürdigen Geldwerte, freie Workspace-Identität oder beliebige Rücksprungziele.

Lesen, Filtern, Umschalten und Navigation erzeugen keine Ausführung, Währungsbestätigung, Review-/Journalaktion, Lesson oder Provideraktualisierung.

## Prüfzuordnung der 18 Abnahmekriterien

Die folgende Matrix ordnet Anforderungen den konkreten Prüfstellen zu. Tatsächlich abgeschlossene Ergebnisse und ihre Aussagegrenzen stehen im anschließenden Abschnitt. Die Matrix ist kein zusätzlicher Aufgabenstatus.

| Nr. | Abnahmekriterium | Konkrete Prüfstellen |
|---:|---|---|
| 1 | Ein Filterbereich und ein sichtbarer Bericht | `PerformanceWorkspace.test.tsx`: beide Direkteinstiege und Moduswechsel mit tatsächlichen Berichtsansichten; `performance-workspace-ui.spec.ts`: einmaliges Formular und aktive Anzeige; beide erweiterten nativen Journeys. |
| 2 | Zeitraum/Zone werden in beide Richtungen übernommen | Workspace-Test `switches from %s using the visible valid draft, with only target defaults and one active report` für beide Modi; UI-Browserfall mit `Asia/Tokyo`; zusätzliche Wechsel in beiden nativen Journeys. |
| 3 | Zwischenwerte bleiben bei Fehler/Wechsel erhalten; Browsernavigation folgt der URL | Workspace-Fälle zu ungültigen Entwürfen, Lesefehlern und gleichbleibendem Filterkontext bei POP; UI-Browserfall zu Feldwerten und Fehlerfokus. |
| 4 | Beide Routen, Reload und Zurück/Vor | Workspace-Test mit `createMemoryRouter`/`RouterProvider`, Zurück/Vor und frischer Routerinstanz; tatsächlicher Browserfall; bestehende Abschlussquellenjourney. |
| 5 | Fehlerhafter Kontext erzeugt keinen Ersatzread | Parametrisierte Workspace-Kontextfälle, beide Kontexthelper-Testdateien und explizite ungültige Browserlinks, einschließlich reiner UTC-Offsets. |
| 6 | EUR bleibt fest, Nicht-EUR wird nicht umgedeutet | Workspace- und bestehende Abschlussseitentests zu USD-Links, Helpertest zur unveränderten USD-Erkennung, UI-Browserfall zur ausdrücklichen neuen EUR-Auswahl. |
| 7 | SELL- und Vollabschlussbedeutung bleiben unterscheidbar | Workspace-September-/Oktober-Referenz, unveränderte Backendtests `test_report.py` und `test_closed_report.py`; unabhängige native Antwortassertions in beiden Ownerjourneys. |
| 8 | Statistik ausschließlich an vollständiger passender Abschlussantwort | Workspace-Fälle für falsche Statistikdefinition/-basis/-status und Moduswechsel; `ClosedTradesPage.test.tsx`; unveränderte Backendstatistik- und Closed-API-Tests. |
| 9 | Request/Antwort an Berichtsart, Definition und Filter gebunden | Workspace-Fälle mit fremder Definition; `performanceReportContext.test.ts`, bestehende Seiten- und Clienttests, unveränderte Backend-API-Tests. |
| 10 | Wechsel überträgt keine fremde Basis/Seite/Zeilenansicht | Workspace-Wechseltests mit modusspezifischer Zeilenauswahl, nicht erster Seite und Fingerprint; URL-Assertions in beiden nativen Journeys. |
| 11 | Verspätete Antworten einschließlich A→B→A bleiben wirkungslos | Workspace-Tests mit kontrolliert verzögertem Erfolg/Fehler bei Modus- und Filterrennen; bestehende Seitentests zu Filteränderung und Unmount. |
| 12 | Lokale Seite/Zeilenwahl/Quellen ändern keine Summen und lesen nicht neu | Workspace-Fälle für SELL-Seite 101 und Abschlussseite 2; bestehende Seitentests; Browserfall und erhaltene native GET-Zählungen. |
| 13 | SELL-Seiten oberhalb 100 | Helpertests für 101/999/1000 und Ablehnung von 1001; Workspace mit 2.001 Antwortzeilen und Seite 101; separater UI-Browserfall mit kürzerem Folgeread. |
| 14 | Quellenpins und Abschlussrücksprung funktionieren | Unveränderter Abschlusshelper und dessen Tests; `ClosedTradeSourceJourney.test.tsx`; erhaltene native Abschlussquellenstrecke samt Seitengrenzhinweis. |
| 15 | Datenlücke/Null/Teilbetrag/Gesamtsumme/Fehler bleiben verschieden | Bestehende SELL-/Abschlussseitentests; Backendreport-/API-/Statistikregressionen; alle bisherigen nativen fachlichen Assertions. |
| 16 | Keine fachlichen Mutationen oder Providerabrufe | Workspace-Prüfung gegen fremde Netzwerkzugriffe; Clienttests für GET-Vertrag; isolierte Browser-Aufzeichnung; native Schreib-/Provider-Schutzprüfungen und Read-only-Snapshots. |
| 17 | Tastatur, Fokus, schmale Ansicht und Navigation | `ApplicationLayout.test.tsx`, `Application.test.tsx`, Workspace-Fokusassertions; `performance-workspace-ui.spec.ts` mit Tastatur und visuell geprüfter 390-px-Ansicht. |
| 18 | Beide nativen Identitäten unverändert erfolgreich; UI6/UI7-Dateigrenzen | Unveränderter Owner-Reportchecker, Discovery der zwei gebundenen Identitäten, tatsächliche Ownerläufe in der regulären CI sowie finaler Dateidiff; lokale Runnerablehnung ist kein Erfolgsnachweis. |

Testquellen: [gemeinsame Routerintegration](../../frontend/src/features/performance/pages/PerformanceWorkspace.test.tsx), [neuer Kontexthelper](../../frontend/src/features/performance/services/performanceReportContext.test.ts), [bestehender Abschlusskontext](../../frontend/src/features/performance/services/closedReportContext.test.ts), [SELL-Seite](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx), [Abschlussseite](../../frontend/src/features/performance/pages/ClosedTradesPage.test.tsx), [Client](../../frontend/src/features/performance/services/client.test.ts), [Abschlussergebnis](../../frontend/src/features/performance/components/ClosedTradeResult.test.tsx), [isolierte Browserfälle](../../tests/e2e/performance-workspace-ui.spec.ts).

## Tatsächlich ausgeführte Prüfungen und Bindung

### Lokale Prüfung

| Prüfung | Tatsächliches Ergebnis | Aussagegrenze |
|---|---|---|
| Unverändertes vollständiges `bash scripts/check-frontend.sh` | Auf Commit `35356d7c4e824c29b9fb92b9a86b6e78a0e7a901` **138 Dateien / 1.372 Tests bestanden**, Exit 0. Typecheck, ESLint, Prettier, vollständige Coverage und Produktionsbuild erfolgreich. Coverage: Statements/Lines **95,21 %**, Branches **88,91 %**, Functions **89,64 %**. Node 22.16.0, npm 10.9.2. | Vollständiges lokales Frontend-Gate mit unveränderten Schwellen 80/80/80/70; Mock-/Routertests und Build, kein echter PostgreSQL-Lauf. |
| Neue SELL-/gemeinsame Kontexthelper und bestehender Abschlusskontext | 2 Dateien, **112 Tests bestanden**, Exit 0: 83 neue und 29 bestehende Tests. Abschließender Lauf mit Node 22.16.0; Formatierung und ESLint erfolgreich. Abschlusshelper bytegleich. | Synthetische Unit-Tests; kein Browser-/PostgreSQL-Nachweis. |
| Gemeinsame Routerintegration | **59 Tests bestanden**, einschließlich beider tatsächlicher Berichtsansichten, kompletter URL-Navigation, Requestrennen, Seiten und Antwortbindung. | `createMemoryRouter`/`RouterProvider` mit kontrollierten API-Antworten; kein PostgreSQL-Lauf. |
| Bestehende Performance-/Quellen-/Navigationstests | **63 Tests bestanden** im gezielten Regressionslauf. | Bewahrt vorhandene Seiten-, Quellen-, Client- und Anwendungsnavigation; ersetzt nicht das vollständige Frontend-Gate. |
| Unveränderte Performance-Backendregression | **178 Tests bestanden**: API 12, Closed-API 17, Closed-Report 55, Closed-Statistik 24, Perioden 33, SELL-Report 37. | Domain- und ASGI-API-Tests mit kontrollierten Fixtures; kein echter Datenbanklauf. |
| Unveränderter Owner-Reportchecker und Sourceview-Seed-Schutz | **32 Tests bestanden**: Reportchecker 26, Seed-Schutz 6. Mit den Performance-Tests insgesamt **210 Tests**, Exit 0, 1,69 s, keine Skips/Warnungen. | Prüft unter anderem Ablehnung falscher Identitäten, Skips/Retry und unzulässiger Seedziele; qualifiziert keinen ausgeführten Ownerlauf. |
| Isolierte UI-Browserfälle | **3/3 bestanden**, finaler Lauf **4,1 s**, ein Worker, kein Retry. Tastatur/Fokus, Wechsel/History, ungültige Links/Offsets und SELL-Seite 101 geprüft; 390-px-Ansicht zusätzlich visuell geprüft. | Echte Oberfläche in Chromium mit synthetischen HTTP-Antworten; kein Browser→API→PostgreSQL-Nachweis. |
| Gepinnte Browserlaufzeit | Node-Playwright 1.55.0; Chromium 140.0.7339.16 / Build 1187 installiert und erfolgreich gestartet. | Laufzeit der isolierten UI-Prüfung. |
| Beide lokalen nativen Owneraufrufe | Der unveränderte Runner verweigert beide Starts: `This runner requires its disposable GitHub Actions checkout.` | **Nicht ausgeführt / nicht erfolgreich qualifiziert.** Kein lokaler Docker-/PostgreSQL-Nachweis; CI-Identität wurde nicht vorgetäuscht und der Guard nicht verändert. |

Die Backendprüfung lief mit Python 3.12.14, pytest 9.0.2 und unverändertem `requirements-dev.txt` in einer isolierten Umgebung. Externe EODHD-, Stuttgart- und Telegram-Dienste waren ausdrücklich deaktiviert. Ein erster eingeschränkter Helpertestlauf erreichte grüne Einzeldateien, aber keinen Runnerabschluss; er wurde beendet und wird nicht gezählt. Die angegebenen Helpertests stammen aus vollständig abgeschlossenen Läufen mit Exit 0.

Die Review fand einen tatsächlichen IANA-Vertragsfehler: feste Offsets wurden durch modernes `Intl` akzeptiert. **Sechs gezielte Routerfälle waren vor der Korrektur rot und danach grün**; zwei positive Fälle erhalten `Etc/GMT+1` auf beiden Routen. Ergänzend prüfen die Helpertests vier Offsetschreibweisen und die gültige benannte Zone. Der gemeinsame Guard korrigiert die neue Oberfläche, ohne den veröffentlichten Abschlusshelper umzuschreiben. Der Quellenhinweis wurde außerdem auf die tatsächliche mitgegebene oder zuletzt gelesene Vergleichsbasis präzisiert.

Die genannten lokalen Teilprüfungen beziehen sich auf die Implementierung und Tests des oben gebundenen Implementierungscommits `35356d7c4e824c29b9fb92b9a86b6e78a0e7a901`. Nach Wiederherstellung des identischen GitHub-Trees wurde das vollständige Frontend-Gate erneut vollständig ausgeführt und mit Exit 0 abgeschlossen. Verlorene lokale Laufdateien werden nicht als rekonstruierte Originalnachweise ausgegeben; der abschließende lokale Gesamtnachweis stammt aus diesem tatsächlichen neuen Lauf. Der anschließende Textabgleich ändert ausschließlich die unten beschriebenen drei nativen Assertions. Der nachfolgende reine Dokumentationsschnitt verändert keine Anwendungs- oder Testdatei des zuletzt nativ qualifizierten Heads `cf419d4f27d5ad5b682f5a739ddb563c91d99309`.

### Reguläre CI: Erstlauf auf dem Implementierungsstand

Die regulären PR-Läufe prüfen Head `35356d7c4e824c29b9fb92b9a86b6e78a0e7a901` über den tatsächlich ausgecheckten Testmerge `d4ee338fda97fd93466b4853736d38f5ecb6f52a`. Dessen Tree ist identisch mit dem Implementierungstree `2d69f8932753814c629fcb8e787738e5b4929950`. Die Joblogs bestätigen diesen Checkout; erfolgreiche Läufe anderer PRs werden nicht als UI8-Nachweis verwendet.

| Regulärer Workflow / Prüfung | Tatsächliches Ergebnis |
|---|---|
| [Frontend, Lauf 40533878172](https://github.com/burckhju/trading-workspace/actions/runs/40533878172) | Erfolgreich: unverändertes Gate, **138 Dateien / 1.372 Tests**, Typecheck, ESLint, Prettier, Coverage und Build. Coverage entspricht dem lokalen Gesamtlauf. |
| [Backend, Lauf 40533878209](https://github.com/burckhju/trading-workspace/actions/runs/40533878209) | Alle drei Jobs erfolgreich: Backend-Qualität sowie die beiden bestehenden Imageprüfungen. **3.405 Tests bestanden, 0 Skips**, 562,29 s; eine bestehende Starlette/anyio-Deprecation-Warnung. Coverage **87,58 %** bei unverändertem 85-%-Gate; Ruff, Black und mypy für 559 Quelldateien erfolgreich. |
| Echte PostgreSQL-Regressionsbestände im Backend-Qualitätsjob | PostgreSQL **17.11**: `test_closed_trades_report_postgres.py` **7/7**, `test_realized_gross_report_postgres.py` **6/6**, `test_realized_gross_learning_independence_postgres.py` **1/1** und `test_trade_source_view_postgres.py` **5/5** bestanden. Diese API-/Datenbankregressionen werden von den nativen Browserjourneys getrennt ausgewiesen. |
| [End-to-End, Lauf 40533878021](https://github.com/burckhju/trading-workspace/actions/runs/40533878021), Smoke-Job | **102 Browserfälle bestanden**, fünf erwartete Owner-Skips; kein Flaky-Ergebnis. Die gesonderten Ownerprüfungen ersetzen diese Skips mit ihrer eigenen gebundenen Qualifikation. |
| Derselbe End-to-End-Lauf, bereits abgeschlossene andere Owner | Candidate-Governance **1/1** sowie Journal/Evidence **2/2** erfolgreich auf ihren jeweiligen Wegwerfstacks. |
| Derselbe End-to-End-Lauf, Performance-Owner | **Fehlgeschlagen:** ein veralteter Wortlaut-Locator im SELL-Fall; die anschließende Vollabschlussqualifikation wurde nicht ausgeführt. Dieser Erstlauf qualifiziert die nativen Performance-Journeys nicht. |
| [Version tag, Lauf 40533878229](https://github.com/burckhju/trading-workspace/actions/runs/40533878229) | Erfolgreich; **9 Versionstests** bestanden. Keine Version geändert und kein Release-Tag erzeugt. |

Der erste native SELL-Lauf stoppte an `getByText(/Der Quellenstand hat sich seit dem letzten Lesen/)`. [Fehlerartefakt 12749330435](https://github.com/burckhju/trading-workspace/actions/runs/40533878021/artifacts/12749330435), Fehlerscreenshot und `error-context.md` zeigen den tatsächlich sichtbaren neuen Quellenhinweis sowie das erwartete Ergebnis `30,00 EUR`. Der UI-Text erklärt bereits präzise den Vergleich mit dem mitgegebenen oder zuletzt gelesenen Quellenstand; die alte Textprüfung war beim Abgleich übersehen worden. Der Testcommit passt genau eine SELL- und zwei Abschlussassertions auf den vollständigen neuen Wortlaut mit `exact: true` an und erhält alle Sichtbarkeits-, Betrags-, Quellen-, Fingerprint- und Schutzprüfungen. Beide bestehenden IDs/Titel wurden per Discovery erneut gegen das unveränderte `CASES`-Mapping bestätigt. Auch beim fehlgeschlagenen Lauf entfernte das Cleanup sämtliche Container, Netzwerke und Volumes; es gab keinen Retry und keine Gateänderung.

### Erfolgreiche native Qualifikation nach dem Textabgleich

Der [Performance-Owner im neuen Lauf 40536721132](https://github.com/burckhju/trading-workspace/actions/runs/40536721132/job/122303843800) hat beide bestehenden Browser→API→PostgreSQL-Journeys erfolgreich abgeschlossen. Geprüft wurde Head `cf419d4f27d5ad5b682f5a739ddb563c91d99309` über Testmerge `5048042f98f2ce3550a816a947e5ff4d3749da2e`; Head- und Testmerge-Tree sind beide `e5eb08e03f69587dd78df644716a184f43ec12e9`. Die beiden `code-and-stack.txt` bestätigen den tatsächlichen Checkout. Die zugehörige [Frontend-CI 40536720516](https://github.com/burckhju/trading-workspace/actions/runs/40536720516) ist ebenfalls erfolgreich mit 138 Dateien / 1.372 Tests und unveränderten Coveragewerten.

| Qualification | Tatsächlicher Browsernachweis | Getrennter Wegwerfstack / Cleanup |
|---|---|---|
| `realized-gross` | **1/1 bestanden**, Chromium, Testdauer **46,495 s**, genau ein Versuch, Retry 0, keine Skips und keine Flaky-Fälle. | Run-ID `03e8811a-3288-4b8f-82cc-745727ba9778`; eigener Stack und eigene Datenbank; Cleanup Exit 0, keine verbliebenen Container, Netzwerke oder Volumes. |
| `closed-trades` | **1/1 bestanden**, Chromium, Testdauer **58,549 s**, genau ein Versuch, Retry 0, keine Skips und keine Flaky-Fälle. | Run-ID `7dd29d77-293e-4909-b6d0-eaa287cf73cb`; anschließend frischer eigener Stack und eigene Datenbank; Cleanup Exit 0, keine verbliebenen Container, Netzwerke oder Volumes. |

Das [native Artefakt 12747538712](https://github.com/burckhju/trading-workspace/actions/runs/40536721132/artifacts/12747538712) wurde heruntergeladen und ausgewertet. Beide `results.json`, `verified-native-journey.json`, `code-and-stack.txt` und `cleanup.json` stimmen mit den exakten Identitäten der folgenden Tabelle überein. ZIP-Prüfsumme gegen die GitHub-Metadaten bestätigt: `sha256:6c0a90032c846a487207d24d59c2b368702c0e9b337e09d6b6843bea199e7ed6`. Die beiden Qualifikationen liefen im selben Ownerjob nacheinander; die festen Hostports wurden nicht gleichzeitig verwendet.

Zusätzlich wurden alle 38 Einträge der beiden nativen Manifestdateien gegen Dateigröße und SHA256 geprüft. Fünf tatsächliche Screenshots dieses erfolgreichen Laufs wurden visuell kontrolliert: `september-desktop.png`, `september-corrected-mobile.png`, `closed-statistics-complete-desktop.png`, `closed-statistics-corrected-mobile.png` und `closed-partial-corrected-mobile.png`. Desktop- und 390-px-Ansichten zeigen einen gemeinsamen Filterblock, eine aktive Berichtszusammenfassung und lesbare Quellenhinweise ohne sichtbare Doppelanzeige oder horizontales Überlaufen. SELL zeigt keine Abschlussstatistiken; PARTIAL trennt die nicht berechenbare Gesamtsumme von der ausdrücklich bezeichneten Teilsumme und den nicht verfügbaren Kennzahlen.

### Abschließender Dokumentationsstand und Aussagegrenzen

Der nachfolgende reine Dokumentationscommit ergänzt dieses Dokument sowie ausschließlich den betroffenen PB-019-Abschnitt und eine aktuelle Traceability-Zeile. Er verändert keine Anwendungs- oder Testdatei des zuletzt nativ qualifizierten Heads. Für den finalen Gesamtstand sind die vier regulären Checks des aktuellen [Draft-PR #290](https://github.com/burckhju/trading-workspace/pull/290) maßgeblich; dessen Beschreibung bindet den endgültigen Head, Dokumentationstree, tatsächlichen Testmerge und die zugehörigen Workflowläufe. Die Ergebnisse der hier einzeln gebundenen Läufe werden dadurch nicht rückwirkend einem anderen Commit zugeschrieben.

Der lokale vollständige Frontendnachweis, kontrollierte Unit-/Routertests, isolierte UI-Browserfälle, echte Backend-PostgreSQL-Regressionen und beide nativen Browserjourneys sind oben getrennt aufgeführt. Der lokale Start der nativen Runner blieb am unveränderten Guard blockiert; die erfolgreichen nativen Nachweise stammen aus den tatsächlichen GitHub-Actions-Wegwerfstacks. Beobachteter PC-Betrieb und menschliche fachliche Abnahme sind nicht Bestandteil dieses Auftrags und nicht nachgewiesen.

### Unveränderte native Testidentitäten

Die Erweiterungen ergänzen Auswahlübernahme, URL-/History-Verhalten und einmalige Anzeige in den bestehenden Journeys. Sie ändern weder deren Titel noch die Ownerzuordnung. Alle bisherigen fachlichen Assertions und Schutzprüfungen bleiben erhalten.

| Qualification | Datei | Gebundene Test-ID / Titel |
|---|---|---|
| `realized-gross` | [realized-gross-report-postgres.spec.ts](../../tests/e2e/realized-gross-report-postgres.spec.ts) | `bafadc4ef6213b62375d-e7b379ddd7f6cba6769e` — `real PostgreSQL: purchase currency once, inherited sales, sources and correction` |
| `closed-trades` | [closed-trades-report-postgres.spec.ts](../../tests/e2e/closed-trades-report-postgres.spec.ts) | `2dd5a78c1f224eb1b623-d0bfb041223e2b8fca72` — `real PostgreSQL: full-close cohort, lifetime result, gaps and current correction` |

[run-realized-gross-e2e.sh](../../scripts/run-realized-gross-e2e.sh) und [check-performance-e2e-report.py](../../scripts/check-performance-e2e-report.py) bleiben unverändert. Pro Qualification ist genau die vorhandene eine Identität zulässig. Die beiden Owner verwenden feste Hostports 35432/38080 und müssen auf demselben Host nacheinander oder auf getrennten Runnern laufen. Es werden ausschließlich synthetische Daten auf zugelassenen Wegwerfstacks verwendet.

## Umfangsgrenzen

Die Änderung betrifft den Performance-Rahmen, die bestehenden Ansichten, kleine Filter-/Kontexthelfer, minimale Router-/Navigationsanbindung, zugehörige Tests und diese Dokumentation. UI6-Journal, Lesson-/Reviewadapter, UI7-`ExecutionDatesPanel` und dessen Korrekturhelper werden nicht umgebaut. Bestehende Trade-Quellenconsumer bleiben Regressionen ihres veröffentlichten Vertrags.

Es gibt keine neuen Backend-APIs, Migrationen, Finanzdefinitionen, Kennzahlen, globalen Guardverträge, Runner, CI-Workflows, Abhängigkeiten oder Versionsänderungen. Die Lieferung weist Mock-/Routertests, synthetische Browsertests, echten PostgreSQL-Nachweis, reguläre CI und PC-Betrieb getrennt aus.
