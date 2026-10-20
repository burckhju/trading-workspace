# Abschlussübersicht — Quellen, Umsetzung und Qualifikation

Entwicklungsbasis: `main` / `v1.5.11`
`5e9ede2dc29f52eaff601d30614df6bc9c25c426`. Die Fortsetzung erweitert
[PR #270](https://github.com/burckhju/trading-workspace/pull/270) auf dem
vorhandenen Branch `docs/closed-trade-report-readiness`; ursprünglicher reiner
Proposal-Head: `59d9de576b7ec53bed4f6ef7eeeef64324b1b426`.

Der Nutzer hat nach Erläuterung der Auswirkungen mit **„ok, umsetzen“** die drei
konkreten Regeln bestätigt. Maßgeblich sind
[ADR-S10-009](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md)
und die vor der Implementierung festgelegten
[Readiness-/Referenzfälle](CLOSED_TRADES_READINESS.md).
Der Arbeitsstatus bleibt im
[zentralen Backlog](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics).

## Sichtbares Ergebnis und bestehende Zuständigkeiten

Die Navigation unterscheidet „Verkäufe im Zeitraum“ von
„Trades mit Vollabschluss im Zeitraum“. Der neue Bericht besitzt eine eigene
Definition `closed-trade-gross-v1`, einen GET
`/api/v1/performance/closed-trades` und die UI-Route
`/performance/closed-trades`. Die vier expliziten Filter bleiben inklusive
Kalendertage, Berichtswährung und IANA-Zone.

| Quelle / Schnitt | Aufgabe |
|---|---|
| [PositionProjector](../../backend/app/features/trade_position/domain/projector.py) | Unveränderte einzige Average-Cost-Rechnung; vollständiger wirksamer Trace und kumuliertes Owner-Bruttoergebnis. |
| [Execution-Währungsresolver](../../backend/app/features/trade_position/domain/currency_resolution.py) | Unveränderte direkte / gleichseitige Vorgänger- / frühere BUY-Herkunft mit exakten Quellen- und Bestätigungs-IDs. |
| [Snapshotreader](../../backend/app/features/performance/service/reader.py) | Unveränderte kurze `REPEATABLE READ READ ONLY`-Transaktion, vollständige begrenzte materialisierte Fakten und aktueller Währungsreferenzstand. |
| [Neuer Tradebericht](../../backend/app/features/performance/domain/closed_report.py) und [DTO](../../backend/app/features/performance/domain/closed_models.py) | Gültige tatsächliche Abschluss-SELL-Quelle, Vollqualifikation aller erforderlichen Käufe und aller wirksamen Verkäufe, disjunkte Tradegruppen, exaktes Vorzeichen und nachvollziehbare Summen. |
| [Service](../../backend/app/features/performance/service/application.py) und [Router](../../backend/app/features/performance/api/router.py) | Ein Snapshot pro Anfrage; Fehler statt abgeschnittener Historie; kompatible bestehende SELL-Route. |
| [Abschlussseite](../../frontend/src/features/performance/pages/ClosedTradesPage.tsx), [Abdeckung](../../frontend/src/features/performance/components/ClosedTradeSummary.tsx), [Tradequellen](../../frontend/src/features/performance/components/ClosedTradeSources.tsx) | Lesende Auswahl, ein Eintrag je Trade-ID, Serverbeträge/-klassifikation, lokale Seiten und Quellen desselben Antwortstands. |
| [Gemeinsame Quellenanzeige](../../frontend/src/features/performance/components/ReportSourceEntry.tsx) | Bestehende Anzeige von Executions, Präzision, Original-/Korrekturbezügen und Währungshistorie wird auch vom unveränderten SELL-Quellendetail benutzt. |

Die neue Auswahl summiert keine bereits auf den Monat zugeschnittenen
SELL-Berichtszeilen. Sie qualifiziert die vollständige Owner-Projektion und
übernimmt deren ungerundetes Ergebnis. Ein früherer fremdwähriger SELL kann
deshalb einen Gesamttrade ungeklärt machen, obwohl ein späterer EUR-SELL im
bestehenden Bericht einzeln verwendbar ist.

Fehlende Position, fehlende/ungültige Historie und mehrdeutige
Supersession-Verknüpfungen beweisen keinen Vollabschluss. Storno bleibt ein
Ausschluss. Gültig offene Trades mit Teilverkäufen bleiben offen. Jede stabile
Trade-ID zählt einmal, auch bei gleichem Produkt oder mehrfachen Lernrelationen.

## Vollständigkeit, Geldpräzision und Quellen

Die acht disjunkten Zähler heißen in Prioritätsreihenfolge
`cancelled`, `history_unresolved`, `open`, `outside_period`, `other_currency`,
`period_unresolved`, `monetary_unresolved`, `qualified`. Ihre Summe ist
`examined`. Zusätzlich gilt:

- `qualified = positive + negative + neutral`.
- `in_period = monetary_unresolved + qualified` bezeichnet sicher zugeordnete
  Abschlüsse innerhalb der Währungsauswahl.
- `unresolved = history_unresolved + period_unresolved + monetary_unresolved`.

`COMPLETE` enthält die vollständige Summe; `PARTIAL` nur die klar bezeichnete
Teilsumme vollständig qualifizierter Trades. `NOT_COMPUTABLE` liefert keine
künstliche Null. `EMPTY` bezeichnet eine geprüfte leere Auswahl und enthält
explizit `0`. Ein bekannter Teilbetrag eines ungeklärten Trades wird niemals in
die Trade-Teilsumme oder einen Vorzeichenzähler übernommen.

`+0.004`, `-0.004` und exakt `0` bleiben unterschiedliche Klassifikationen.
Bei Anzeige mit zwei Nachkommastellen wird der Unterschied erklärt; Rohwerte
sind in den Quellen zugänglich. Die Währungsreferenz bestimmt die tatsächliche
Anzahl der Nachkommastellen. Owner-Decimalreihenfolge und Abschlussrest bleiben
sichtbar; Backend-Anzeige verwendet `ROUND_HALF_EVEN`. Das Frontend berechnet
weder Geldbeträge noch Vorzeichen erneut.

Alle wirksamen SELL-Beiträge behalten ihr eigenes Ausführungsdatum, ihre
Periodenzugehörigkeit, Kostenbasis, Menge und Provenienz. Ein früherer Beitrag
wird nicht als Verkauf des Abschlussmonats bezeichnet. Date-only bleibt ohne
Uhrzeit; historische ersetzte Ausführungen und Währungsbestätigungen bleiben
einsehbar. Aktuelle Produktnamen sind Anzeige, keine historische Identität oder
Währungsquelle.

Filterwechsel, neue Abfrage und Unmount entwerten ausstehende Antworten. Ein
abweichender Definition-/Filter-/Währungsstand wird zurückgewiesen. Ein neuer
Fingerprint ersetzt Ergebnis, Zähler und Quellen gemeinsam und wird erklärt.
Die lokalen 20-Zeilen-Seiten und Zeilenfilter ändern keine Gesamtbeträge und
führen keinen weiteren GET aus.

## Unabhängige Sollwerte und zugehörige Prüfungen

| Fall | Festgelegte Erwartung | Konkreter Nachweis im Code |
|---|---|---|
| T1 vor Vollabschluss | Offen; September-SELL-Bericht weiterhin +10 EUR; keine Abschlussklassifikation. | Report-Unit, tatsächlicher Browser-/Ownerablauf. |
| T1 vollständig | Oktober einmal +50 EUR; September-Abschlussauswahl `EMPTY`; September-SELLs +10 EUR, Oktober-SELL +30 EUR. | Unit, API, PostgreSQL und neuer Browserfall. |
| September-SELL-Preiskorrektur auf 3,00 | T1 +70 EUR; September-SELLs +30 EUR; Oktober-SELL unverändert +30 EUR; alte Quelle erhalten. | Unit, native PostgreSQL-Korrektur und Browserquellen. |
| T1/T2/T3 | Drei Trades, 1 positiv / 1 negativ / 1 neutral; vollständige +40 EUR, nach T1-Korrektur +60 EUR. | Unabhängige Unit-, PostgreSQL- und Browser-Assertions. |
| T4 ohne Herkunft | Keine Betrag-/Vorzeichenklassifikation; gemeinsam mit T1/T2/T3 ausschließlich +40 / +60 EUR Teilsumme. | Unit, API-Zustände, PostgreSQL, UI und Browser. |
| T5 USD / T6 noch offen | Getrennte sichere Ausschlüsse; keine Änderung der EUR-Abschlusszähler. | Unit, PostgreSQL und Browser. |
| Nur unbekannt / nur exakte Null / leer | `NOT_COMPUTABLE` / `COMPLETE` mit Null / `EMPTY` bleiben unterscheidbar. | Unit, UI, PostgreSQL und Browser mit getrennten Perioden. |
| Datum, Menge oder Währung korrigiert | Ganze Abschlussperiode wechselt / verbleibende Einheit entfernt den Abschluss / gemischte frühere Erlöse machen Gesamttrade ungeklärt. | Unit und vier parametrisierte native Writer-Races einschließlich Preiskorrektur. |
| Präzision und Randfälle | Datum ohne erfundene Uhrzeit, DST-/Monatsgrenzen, ±0.004, exakte Null, Owner-Decimalrest, Ressourcenüberschreitung und konservative Historielücken. | Neue Domain-/API-Units; vorhandene Perioden-/Owner-Regressionsfälle bleiben bestehen. |
| Identität und unabhängiges Lernen | Gleicher Produktname vervielfacht keine Trade-ID; fremder Workspace und Beobachtungen sind keine eigenen Trades; Lernbezüge verändern keinen Finanzreport. | Domain-Units, bestehender gescopter Reader und erweiterte native Lernunabhängigkeit. |
| Bedienung und Antwortwechsel | Tastaturbedienung, Quellen, alte Antwort/Fehler, neue Basis, lokale Seiten; 27 tatsächliche Trades im Browser. | Frontend-Units und neuer nativer Browserfall. |

Prüfdateien:

- [Neue Domain-Units](../../tests/unit/backend/features/performance/test_closed_report.py)
  und [API-/Service-Units](../../tests/unit/backend/features/performance/test_closed_api.py).
- [Native PostgreSQL-Prüfung](../../tests/integration/backend/test_closed_trades_report_postgres.py)
  und [Lernunabhängigkeit](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py).
- [Frontend-Regressionen](../../frontend/src/features/performance/pages/ClosedTradesPage.test.tsx),
  vorhandene SELL-Seiten-/Quellentests und Client-/Navigationsprüfungen.
- [Neuer nativer Browserfall](../../tests/e2e/closed-trades-report-postgres.spec.ts)
  sowie der erhaltene [SELL-Ownerfall](../../tests/e2e/realized-gross-report-postgres.spec.ts).

Die PostgreSQL-Races pausieren die Produktionseinlesung nach ihrem bereits
begonnenen Snapshot mit Events, lassen einen unabhängigen Owner-Writer committen
und setzen dann den Read fort. Die Antwort muss vollständig zum alten Stand
passen; eine folgende Anfrage zeigt vollständig den neuen. Kein Sleep errät
den Snapshotbeginn. Normale Folge-Verbindungen behalten `read committed` und
Schreibfähigkeit; die Isolation wird nicht global verändert.

## Native Browserqualifikation und Belegbindung

Der bestehende [End-to-End-Workflow](../../.github/workflows/e2e.yml) führt über
den [CI-Runner](../../scripts/run-realized-gross-e2e.sh) zwei explizite
Qualifikationen aus: den vorhandenen SELL-Bericht und die neue Abschlussübersicht.
Jeder Aufruf erzeugt und entfernt seinen eigenen frischen UUID-Compose-Stack.
Die zweite Qualifikation übernimmt keine Finanzdaten aus der ersten.

Der Runner bleibt an den echten GitHub-Actions-Checkout gebunden. UUID-Projekt
und -Datenbank, lokaler Docker-Socket, leere Compose-Umgebung, bestätigte
Container-/Netz-/Portidentität, Schema 0047 und PostgreSQL 17 werden geprüft.
Der Backenddienst hat ausschließlich das interne Netz und keinen veröffentlichten
Port; Datenbank und Frontend sind nur an Loopback veröffentlicht. Provider und
Zustellungen sind deaktiviert. Der Browser blockiert fremde Ursprünge und
Service Worker; API-Aufrufe erlauben keine Redirects.

Alle synthetischen Finanzbuchungen und Korrekturen laufen über Owner-Befehle.
GETs, Quellenansicht und lokale Pagination werden in abgegrenzten Lesefenstern
gegen Fingerprints der fachlichen Tabellen geprüft. Beabsichtigte Capture- oder
Korrekturbefehle liegen außerhalb dieser Vergleiche. Desktop- und Mobilbilder,
Trace, echte API-Antworten und Datenbanknachweise werden als Artefakte erhalten.

Der [exakte Reportprüfer](../../scripts/check-performance-e2e-report.py) akzeptiert
pro Aufruf nur die erwartete Datei, Titel, Test-ID und das Chromium-Projekt mit
genau einem erfolgreichen Versuch: kein Skip, Flaky, Retry oder globaler Fehler.
[Negative Verifier-Tests](../../tests/unit/backend/test_closed_report_e2e_contracts.py)
verhindern den Austausch durch den jeweils anderen oder unvollständigen Fall.
Cleanup muss eigene Container, Volumes und Netze vollständig entfernen; das
Artefaktmanifest enthält auch versteckte Dateien.

| Qualifikation | Exakte Datei / Test-ID |
|---|---|
| `realized-gross` — purchase currency once, inherited sales, sources and correction | `realized-gross-report-postgres.spec.ts` · `bafadc4ef6213b62375d-e7b379ddd7f6cba6769e` |
| `closed-trades` — full-close cohort, lifetime result, gaps and current correction | `closed-trades-report-postgres.spec.ts` · `2dd5a78c1f224eb1b623-d0bfb041223e2b8fca72` |

Am 20.10.2026 bestanden lokal **191 gezielte Backendtests** ohne Fehler/Skip:
68 neue Domain-/API-Fälle sowie die bestehenden Owner-Trace-, Währungsresolver-
und Performance-Fälle. **33 gezielte Frontendfälle** bestanden, darunter
16 neue Abschlussseitenfälle und die bestehenden SELL-/Client-/Layoutregressionen.
Die **26 Reportprüfer-Tests** bestanden ebenfalls. Die native Sammlung bestätigt
acht betroffene PostgreSQL-Fälle (sieben neue und die erweiterte Lernunabhängigkeit)
und beide Browseridentitäten; Sammlung bedeutet keine Datenbankausführung.
Ruff/Black nach dem tatsächlichen Backend-Prüfeinstieg sowie mypy über alle
554 Anwendungsquelldateien bestanden. Lokale vollständige und native CI-Gates
bleiben davon getrennte, an ihre Ausführung gebundene Nachweise.

Anschließend bestand lokal der unveränderte Einstieg
`bash scripts/check-frontend.sh`: Typecheck, ESLint ohne Warnungen,
Prettier-Prüfung, **593 Tests in 112 Dateien**, Coverage und Produktionsbuild.
Coverage: Statements/Zeilen **93,15 %**, Branches **84,82 %**, Funktionen
**85,48 %** bei unveränderten Mindestgrenzen. Vite meldet weiterhin eine
informative Warnung über große Build-Chunks; der Build bestand, die Grenze
wurde nicht erhöht. Backend-Ruff und Black bestanden über Anwendung und beide
Testsammlungen (972 Pythondateien). Die native Backend-Vollprüfung erfolgt im
vorgesehenen PostgreSQL-CI-Job.

**Die tatsächliche Head-/Checkout-/Tree-Bindung, ausgeführten Gates, Run-Links,
Artefakthashes und gesichteten Bilder werden in der Übergabe von
[PR #270](https://github.com/burckhju/trading-workspace/pull/270) festgehalten.**
Testcode oder frühere grüne Proposal-Läufe sind kein Nachweis einer neuen nativen
Ausführung. Lokale Tests verwenden Python 3.12 sowie Node 22.16.0/npm 10.9.2.
Native Datenbank-/Containerprüfungen erfordern den vorgesehenen echten CI-Stack;
CI-Flags werden lokal nicht gefälscht. Die vorgeschriebenen vollständigen Backend-,
Frontend- und Smoke-Gates werden unverändert auf dem tatsächlich übergebenen
Stand ausgewertet.

## Grenzen

Keine Migration, neue Trade-Währung, Gebühren-/FX-Annahme oder neue Pflichtangabe.
Keine Änderung der Execution-, Journal-, Review-, Lern- oder Provider-Commands.
Der bestehende SELL-Bericht bleibt `realized-gross-sell-v2`.
Trefferquote, Durchschnitt, Median, Profit-Faktor, Export, weitergehende
Dashboards und ursprüngliche M8-Anforderungen bleiben eigenständige Umfänge.
Synthetische Nachweise bestätigen keine realen Nutzerwährungen. Entwicklungs-PR,
fachliche Abnahme, Merge, Release, PC-Installation und beobachteter Betrieb sind
getrennte Aussagen; diese Umsetzung nimmt die letzten Schritte nicht vorweg.
