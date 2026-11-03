# UX3-B2/F4 — Ursachengetreue Hinweise in der Produktbewertung

## Auftrag und tatsächliche Ausgangsbasis — 02.11.2026

Der Nutzer hat die Fortsetzung beauftragt. Der erste B2/F4-Teilschnitt zu Q12
betrifft genau die vorhandene `ProductValuationPanel`-Fläche. Die bereits erteilte
Freigabe zum Merge bei grünen erforderlichen Prüfungen und zur PC-Bereitstellung
bleibt bestehen. Dieser Bericht dokumentiert Umfang und technische Nachweise;
Arbeits- und fachliche Abnahmestände führt ausschließlich der
[Product Backlog](../planning/PRODUCT_BACKLOG.md#operational-workspace).

| Ausgangsnachweis | Stand und Aussagegrenze |
| --- | --- |
| Ausgangs-Main dieses Schnitts | `3397399e7bf8364501437f9509a4fb18dbe32c08`; enthält den nachfolgenden UX4-B-Schnitt aus [#322](https://github.com/burckhju/trading-workspace/pull/322). |
| B1/F1 | [#320](https://github.com/burckhju/trading-workspace/pull/320) ist integriert. Seine historischen Draft-/Rücknahmephasen sind keine offenen B1-Implementierungsaufträge. |
| Veröffentlichte B1-Basis | Release-PR [#323](https://github.com/burckhju/trading-workspace/pull/323) und Tag `v1.5.38` auf `849a6d54eaeb5f5831754c6b15a41358c571f6da`; [Releaseumfang und PC-Weg](../releases/V1.5.38-UX3-CURRENCY-NOTICE.md). Der spätere UX4-B-Merge ist nicht in diesem Tag enthalten. |
| Qualifikation des nachfolgenden UX4-B-Mains | Frontend- und E2E-Main-Push-Prüfungen erfolgreich; wegen des bestehenden Pfadfilters kein Backend-Push-Lauf. Der erfolgreiche Backend-PR-Lauf bleibt ein getrennter Nachweis. Diese Ergebnisse qualifizieren noch keinen neuen B2-Head. |
| Zielinstallation und menschliche Abnahme | Aus Integration und Tag folgt keine tatsächlich ausgeführte PC-Installation oder menschliche Fach-/Screenreader-/Zoomabnahme. |

Der [kanonische Hinweisvertrag](../ui/ux-3/notice-contract.md), seine
[Abnahmefälle](../ui/ux-3/test-and-acceptance.md) und die bestehenden
[Ownergrenzen](../coordination/UX_OWNERSHIP.md) bleiben maßgeblich. Im geprüften
Repository und seinen zugänglichen Elternverzeichnissen wurde keine `AGENTS.md`
gefunden. Vor Veröffentlichung sind tatsächlicher Main und offene PR-Dateidiffs
erneut abzugleichen; fremde Änderungen bleiben erhalten.

## Enger Datei- und Ownerschnitt

| Datei | Erlaubter Umfang |
| --- | --- |
| `frontend/src/features/trade/components/ProductValuationPanel.tsx` | Einzige Runtimeänderung: Ursachen-/Wirkungstexte und begrenzte Darstellung auf der vorhandenen Bewertungsfläche. |
| `frontend/src/features/trade/components/ProductValuationPanel.notices.test.tsx` | Neue gezielte Gegenfälle zu Q12/TC-49, unbekannten Codes, gültigem Sitzungskurs und unveränderten Anzeige-/Lesegrenzen. |
| `frontend/src/features/trade/components/ProductValuationPanel.test.tsx` | Bestehende falsche LAST_AVAILABLE-Erwartung korrigieren; STALE-Gegenfall erhalten. |
| `frontend/src/features/trade/components/ProductValuationPanel.currency.test.tsx` | Einzelne Warntext-Assertion für die synthetische Kombination OUTDATED + INDICATIVE ohne bestätigten Altersgrenzbeleg anpassen; Werte, Fixtures und G/V-Qualifikation erhalten. |
| Dieser Bericht | Ausgangsbasis, begrenzter Umfang, tatsächliche Prüfbelege und verbleibende Arbeit. |
| `docs/ui/ux-3/integration-and-rollout.md` | Einstieg und Abschnitt 7: historischen B1-Abschluss, aktuellen ersten B2-Schnitt und getrennten verbleibenden PositionDetails-Auftrag einordnen. |

UX3 verantwortet die verständliche Darstellung in dieser bestehenden Fläche.
Der `position_monitoring`-Owner liefert Status, Reason, Kursqualität und
Verwendbarkeit im bestehenden
[ProductPositionValuationResponse](../../frontend/src/features/trade/types/api.ts).
`trade_position` behält Position, Kostenbasis und historische Währungsbelege.
Die vorhandene [G/V-Qualifikation](../../frontend/src/features/trade/services/valuationQualification.ts)
und die Backendberechnung werden nicht verändert. UX2 behält Host, Navigation,
Fokus und Readback; UX4 behält Kurshistorie, Quellenwahl und Originalbelegzugang.

`PositionDetails`, `TradeManagementPage`, UX1-Previews, UX4-Komponenten, Backend,
API-Typen, Abhängigkeiten, Versionen und Workflows gehören nicht zu diesem Diff.
F2/O1-Finanzqualifikation, F3/O3-Refreshvertrag und B3/B4/C/D werden nicht vorgezogen.

## Belegte Korrektur und erhaltene Semantik

Am Ausgangsstand fällt `ProductValuationPanel.warningText` für unbekannte
`analysis_warning`-Codes auf „Kursdaten veraltet“ zurück. Ein unbekannter Code
belegt diese Ursache nicht. Der neue Auffanghinweis bleibt neutral und benennt
die begrenzte Diagnose. Native Details zeigen den originalen `analysis_warning`
und `reason` ergänzend. `reasonText` und die bestehenden Primärursachen werden
nicht migriert; dieser Schnitt verschiebt nicht sämtliche Rohreasons in Details.
Ein unabhängig gelieferter Status oder belegter Nutzbarkeitswert bleibt sichtbar.

Auch `OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY` allein beweist keinen STALE-Status:
Der bestehende [Bewertungsowner](../../backend/app/features/position_monitoring/service/product_valuation.py)
liefert ihn sowohl bei `STALE` als auch bei `LAST_AVAILABLE` mit
`MARKET_CLOSED_LAST_AVAILABLE_QUOTE` und `valuation_usable=true`. Die Darstellung
berücksichtigt diese vorhandenen Fakten gemeinsam. Der echte STALE-Befund bleibt
eine Einschränkung; der zulässige letzte Sitzungskurs wird nicht pauschal veraltet
oder unbrauchbar genannt. Keine eigene Altersgrenze, Handelskalender- oder
Frischeklassifikation entsteht.

Der reguläre Ownerpfad `OUTDATED_QUOTE_INDICATIVE_ANALYSIS_ONLY` zusammen mit
`status=INDICATIVE`, `reason=REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS` und
`quote_age_limit_exceeded === true` belegt dagegen eine überschrittene
Altersgrenze des Referenzkurses. Die Anzeige lautet dafür „Referenzkurs
überschreitet die gemeldete Altersgrenze – indikative Analyse“. Sie übernimmt
das gelieferte Boolean und berechnet weder Alter noch Grenzwert; der Status
bleibt `INDICATIVE`. Bei `false` oder fehlendem Altersflag bleibt diese
Kombination hinsichtlich der Altersursache neutral. Ein verwendbarer
`LAST_AVAILABLE`-Sitzungskurs bleibt auch bei gesetztem Altersflag gemäß der
gelieferten Sitzungsklassifikation eingeordnet und wird nicht zu `STALE`.

`valuation_usable`, `analysis_usable`, beide G/V-Verwendbarkeitsflags und ihre
Reasons behalten ihre jeweilige Bedeutung. Ein brauchbarer Kurs oder Marktwert
beweist keinen berechenbaren G/V. Unbekannte Beträge bleiben unbekannt; echte
Nullwerte, Geldstrings, Währung, Quellenbezug und Originalzeiten bleiben erhalten.
MISSING/UNAVAILABLE/ERROR ohne nutzbaren Kurs begründen keinen verfügbaren
Referenzkurs. Nutzbarkeit wird nicht aus dem bloßen Vorhandensein einer Zahl
abgeleitet.

Die bestehenden Reads, ihre Auslöser und der Closed-Position-Guard bleiben
unverändert. Die Darstellung löst keine zusätzlichen Reads, Writes, Bestätigungen,
Providerrefreshes oder automatische Folgeaktionen aus. Es entstehen keine
Finanz-/FX-Berechnung, Währungsauflösung, Trading-/Planfreigabe- oder Recoveryregel.

## Begrenzung des B1-Präsentationskerns

Der vorhandene [NoticeCard-Vertrag](../../frontend/src/shared/notices/types.ts)
ist eine passive B1-Textprojektion mit obligatorischer Navigationsaktion.
Für die vorliegende Korrektur ist kein zusätzliches, belegtes Aktionsziel nötig.
Deshalb wird weder ein Link erfunden noch der Shared-Kern erweitert. Die lokale
Bewertungsfläche setzt den kanonischen semantischen Vertrag um; sie führt kein
zweites Statusmodell und keine generische Hinweisengine ein.

## Zielgerichtete Abnahme

| Fall | Erwarteter Nachweis |
| --- | --- |
| Unbekannter `analysis_warning` | Keine erfundene STALE-/Providerursache; begrenzte verständliche Diagnose, ergänzende Originalcodes in nativen Details. Bestehende Primärursachen bleiben erhalten. TC-43/49. |
| Verwendbarer LAST_AVAILABLE-Sitzungskurs mit OUTDATED-Code | Status/Reason/Usability bestimmen die Aussage, auch bei `quote_age_limit_exceeded=true`; kein pauschales „veraltet“ und keine Umklassifikation zu STALE. TC-15/49. |
| OUTDATED + INDICATIVE + REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS mit `quote_age_limit_exceeded=true` | Überschreitung der gemeldeten Referenzkurs-Altersgrenze ausdrücklich erklären; gelieferten Status, Zahlen und G/V-Qualifikation erhalten. Kein selbst berechnetes Alter. TC-49. |
| Dieselbe Referenzkurskombination mit Altersflag `false` oder fehlendem Flag | Hinsichtlich der Altersursache neutral; Warncode und Zahlen ersetzen keinen positiven Altersgrenzbeleg. TC-49. |
| Tatsächlicher STALE-Kurs | Belegte Einschränkung bleibt erhalten; indikative Analyse wird nicht zur aktuellen Depotbewertung. TC-49. |
| MISSING/UNAVAILABLE/ERROR ohne nutzbaren Kurs | Keine Behauptung eines verfügbaren Referenzkurses und kein Ersatzbetrag. TC-49. |
| Unabhängiger Marktwert und G/V | Unbekannte/gemischte/abweichende Kaufwährung unterdrückt nur den nicht qualifizierten G/V; positive, negative und echte Nullwerte bleiben korrekt. TC-05/49. |
| Zeit, Quelle und bekannter Abruffehler | Originalzeit, Abrufzeit, unbekannte Zeitzone und retained Quote bleiben getrennt; keine neue Provider-/Recoveryklassifikation. |
| Aufklappen und erneute Darstellung | Keine zusätzlichen Reads/Writes, keine neue Alarmregion, keine neue Pflichtentscheidung; Details bleiben per Tastatur bedienbar. Passende TC-41/44/46/47. |
| Geschlossene Position und bestehende Consumer | Bisheriger Verzicht auf Produktkursread bei geschlossener Position bleibt erhalten; keine Änderung anderer Bewertungsflächen. |

Vorhandene Regressionen:
[Produktbewertung](../../frontend/src/features/trade/components/ProductValuationPanel.test.tsx),
[Bewertungswährung](../../frontend/src/features/trade/components/ProductValuationPanel.currency.test.tsx)
und [Emittentenzeit](../../frontend/src/features/trade/components/ProductValuationPanel.issuer-time.test.tsx).
Die gezielten Fälle ergänzen die unveränderten Projektgates; sie ersetzen sie nicht.

## Lokale Vorprüfung am 02.11.2026

| Nachweis | Stand |
| --- | --- |
| Gezielte neue Hinweisfälle und bestehende Bewertungsregressionen | **35/35 Tests in vier Dateien bestanden**, darunter acht neue Gegenfälle; Node 22.16.0 und unverändertes Lockfile. Der STALE-Fall, die Währungsqualifikation und die Emittentenzeitregressionen bleiben erhalten. |
| Typecheck, Lint, Formatierung und Produktbuild | Vollständiger TypeScript-Buildcheck, ESLint und Prettier für die betroffenen Bewertungsdateien sowie Vite-Produktionsbuild erfolgreich, jeweils Exit 0. |
| Dateiabgleich | Die sechs vorgesehenen Dateien überschneiden sich mit keiner Datei der zum Abgleich offenen PRs #315, #220, #207, #205, #197 und #187. Die später integrierten UX4-B-Dateien bleiben erhalten. |
| Erforderliche reguläre PR-Gates | Werden zusätzlich auf dem tatsächlichen PR-Head qualifiziert; die lokale Auswahl und frühere B1-/UX4-Läufe ersetzen sie nicht. |
| B2-PR, finaler Head, aktuelle Basis, Testmerge/Tree, Run-/Jobbelege | Die PR-Übergabe bindet diese tatsächlichen Integrationsnachweise gesondert. Dieser lokale Bericht behauptet weder erfolgreiche Remote-CI noch Mainintegration oder Tagveröffentlichung allein aufgrund der Vorprüfung. |
| Menschliche fachliche/UI-Abnahme, Screenreader und echter Browserzoom | Nicht als erfolgt nachgewiesen; automatisierte Tests ersetzen diese Nachweise nicht. |

Dieser Bericht ist kein zweiter Arbeitsstatuskatalog. Der erste Produktschnitt
schließt Q12 nicht insgesamt ab: Der Auffangtext in `PositionDetails` bleibt
gesonderte Restarbeit. Dessen begrenzter Startprompt steht in
[Rollout Abschnitt 7](../ui/ux-3/integration-and-rollout.md#7-wichtigster-nächster-umsetzungsschritt).
