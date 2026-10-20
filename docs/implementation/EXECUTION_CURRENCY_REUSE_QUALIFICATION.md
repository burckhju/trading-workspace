# Kaufwährung wiederverwenden — Vertrag und Qualifikation

## Auftrag und Prüfgrundlage

Ausgangspunkt ist `main` **`254fe35b76027b72cd989715e17bd0ae55af55eb`**,
Version **1.5.9**, am 20.10.2026 erneut gelesen. Der saubere Aufgabenbranch ist
`fix/execution-currency-reuse-20261020`. Die vorherige
[Berichtsqualifikation](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) bleibt ein
historischer Nachweis für V1; sie ist kein Test der hier geänderten Semantik.
Arbeitsstatus ausschließlich im [Product Backlog](../planning/PRODUCT_BACKLOG.md),
insbesondere PB-017 Brutto-PnL und PB-019 Performancekennzahlen/Periodenauswertungen.

Am 20.10.2026 hat der Nutzer ausdrücklich festgelegt: Die beim Kauf angegebene
Währung gilt auch beim Verkauf; vorhandene Eingaben sollen wiederverwendet und
zusätzliche Eingaben auf das notwendige Minimum begrenzt werden. Damit entfällt
die vorherige Pflicht zur separaten Währungsbestätigung jedes SELL und jedes
gleichartigen Ausführungsersatzes. Die bereits erteilte Anweisung, nach grünen
Prüfungen zu mergen und für den PC bereitzustellen, bleibt bestehen. Dies ist
keine Behauptung einer fertigen Fachabnahme oder einer neuen PC-Installation.

## Begrenztes Quelleninventar

| Benötigte Information | Owner / Speicherort | Historische Bindung und Änderbarkeit | Read-Contract / Consumer | Befund und erforderliche Änderung |
|---|---|---|---|---|
| Tatsächliche Kaufpreiswährung | FT-009/010; `execution_currency_confirmations` | Konkrete Workspace-, Trade- und BUY-ID, Bestätigungs-ID und Actor/Zeit; append-only, Korrektur durch Nachfolger | `ExecutionCurrencyConfirmationService`, Capture-Response, Timeline und Report-Snapshot | Qualifizierte vorhandene Quelle wiederverwenden. Keine Kopie als angeblich neue SELL-Bestätigung. |
| Tatsächlicher eingegebener Kaufcode | `ProductSelectionPage`, `ExecutionCurrencyInput`, `executionCurrencyDeclaration` | Der Code wird erst durch den Capture-Request zur gespeicherten Erklärung | Bestehender BUY-Command | V1.5.9 ließ einen getippten Code bei fehlendem Zusatzhaken aus dem Request weg. Speichern der tatsächlichen Buchung bestätigt künftig den eingegebenen Code; nichtleere ungültige Eingaben werden abgelehnt. Ein früher nicht gespeicherter Wert ist nicht rekonstruierbar. |
| Wirksame Reihenfolge, Korrektur und vollständige Kaufbasis | `execution_records`, `PositionProjector`, Owner-Repositories | Unveränderte Fakten und exakte Supersession-IDs; `(executed_at, recorded_at, id)` | Owner-Timeline und vollständiger Report-Snapshot | Dieselbe Reihenfolge für die reine Währungsableitung nutzen. Keine neue Average-Cost-Schleife. |
| Historischer TradePlan-Währungscode | FT-007 `TradePlanVersion.entry_currency` | Konkrete Planversion, aber produktneutraler Underlying-Kontext | TradePlan-Entry; FT-007 / ADR-S6-006 | Kein Beleg für den tatsächlichen Optionsscheinpreis. Nicht übernehmen. |
| Listing-, Quote-, Strike- und Beobachtungswährungen | Product-, Market- und Learning-Owner; Listings, Evaluation-Metriken, Quote-Source-Evidence, externe Rohbeobachtung | Je nach Quelle heutige Stammdaten oder historischer Bewertungs-/Beobachtungskontext | Bewertung, Quellenwahl, Monitoring, Learning-Import | Keine zusätzliche qualifizierte historische Kaufwährungsquelle gefunden. WORKSPACE_SELECTION und eigene EXTERNAL-Trades verwenden denselben Execution-Vertrag. Reine Beobachtungen bleiben ausgeschlossen. |
| Herkunft im Bericht | Reiner Report-Reader und gemeinsame Owner-Ableitung | Gesamte Antwort im vorhandenen kurzen Repeatable-Read-Snapshot; Definition und Quellen im Basis-Hash | `/performance/realized-gross`, Quellen-Drill-down | Aufgelöste Währung und konkrete Ursprungs-IDs zusätzlich ausgeben; bestehende direkte Bestätigungen unverändert erhalten. |

Der historische Vergleich mit `e9aac2bf` zeigt für die damaligen tatsächlichen
BUY-DTOs und den Produktauswahl-Capture nur Menge, Stückpreis und Ausführungsdatum,
keine Execution-Währung. Ein früherer Plan- oder Produktwährungseintrag ersetzt
diese fehlende Speicherung nicht. Weder der Berichtswährungsfilter noch ein
vermeintlicher EUR-Standard bestätigt vorhandene Buchungen.

## Definition of Ready und freigegebener Vertrag

**Für diesen begrenzten Schnitt erfüllt:** Die eindeutige Kaufbestätigung ist
bereits gespeichert, der Nutzer hat die Wiederverwendung ausdrücklich
entschieden, und der vorhandene Owner/Snapshot liefert die vollständige
Execution-/Korrekturherkunft. Für Buchungen ohne irgendeine qualifizierte
Kaufquelle bleibt die Währung unbekannt. Diese Datenlücke wird durch keine
Migration oder Annahme verdeckt.

Die gemeinsame reine Auflösung liegt beim Execution-Owner. Vorrang:

1. Die aktuelle direkte Bestätigung der konkreten Execution gilt unverändert.
2. Fehlt diese, darf die nächste tatsächlich bestätigte Vorgänger-Execution
   entlang der lückenlosen Korrekturkette **derselben Seite** verwendet werden.
   Ein Seitenwechsel beendet diese Ableitung. Preis-, Mengen- oder
   Datumsersatz allein verlangt keine erneute Währungseingabe.
3. Fehlt auch eine solche Quelle, darf ein SELL oder Nachkauf die Währung des
   vollständig davor liegenden, wirksamen BUY-Präfixes verwenden, wenn dessen
   aufgelöste Währungen sämtlich bekannt und gleich sind. Spätere Käufe heilen
   keine früheren unbekannten Käufe. Frühere SELL-Erlöswährungen sind weiterhin
   kein Kaufkostenbeleg.

Eine ausdrücklich abweichende SELL-Währung bleibt erhalten. Verschiedene
Währungen innerhalb der erforderlichen Kaufkosten und Erlöse bleiben ohne
freigegebenen FX-Vertrag nicht berechenbar. Ein aus BUYs abgeleiteter SELL wird
nicht als eigene neue `USER_CONFIRMED`-Bestätigung ausgegeben oder gespeichert.

Die additive `currency_resolution` enthält `currency_code`, `source`
(`USER_CONFIRMED`, `PRIOR_BUYS`, `REPLACED_EXECUTION`, `UNKNOWN`, `MIXED`),
`source_execution_ids` und `confirmation_ids`. Das bestehende
`currency_confirmation` bezeichnet weiterhin ausschließlich die direkte
Erklärung zur jeweiligen Execution. Die vorhandene Quelle kann auch bereits
gespeicherte Verkäufe qualifizieren, ohne diese zu verändern.

Die Berichtsdefinition wird **`realized-gross-sell-v2`**. Rechenformel,
Periodenzuordnung, Decimal-Präzision, Summen-/Lückenzustände, Limits und Snapshot
bleiben erhalten. Nachträgliche Kauf- oder Währungskorrekturen können den nächsten
Bericht ändern; Basis und Quellen zeigen den neuen Stand. Keine damalige
Wissenslage oder dauerhaft eingefrorene Berichtssitzung wird behauptet.

Im normalen Verkauf, Nachkauf und gleichartigen Ausführungsersatz wird keine
Währung erneut eingegeben. Eine tatsächliche Abweichung bleibt bewusst
bearbeitbar. Ein gültiger, ausdrücklich eingegebener Kaufcode wird zusammen mit
der tatsächlichen Buchung gespeichert; ein zusätzlicher Bestätigungshaken ist
nicht erforderlich. Es gibt keine Vorbelegung aus heutigen Listings oder Plänen.

## Vorab festgelegte Abnahmefälle

- Einmal bestätigter BUY, danach sämtliche Teilverkäufe und Nachkauf ohne
  Währungseingabe: unabhängiger Referenzfall September **10 EUR**, insgesamt
  **50 EUR**; SELL-Korrektur ebenfalls ohne Währungseingabe ergibt **30 / 70 EUR**.
- Die Zahl gespeicherter Währungsbestätigungen steigt durch Ableitung nicht.
  Capture-Response, Timeline, Report-Quellen und UI unterscheiden eigene
  Erklärung und wiederverwendete Herkunft.
- Unbekannter Erstkauf bleibt unbekannt; später bestätigter Kauf heilt ihn
  nicht rückwärts. Explizite Mischwährung oder widersprüchlicher SELL bleibt
  sichtbar, ohne falsche Geldsumme oder stille Überschreibung.
- Bestätigter BUY und seine lückenlose gleichseitige Korrektur bleiben
  nachvollziehbar verknüpft. Fremde Workspace-/Trade-/Produktquellen und
  Seitenwechsel dürfen keine Währung vererben.
- Reale PostgreSQL-Owner-Requests, Preis-/Datum-/Währungsänderung und parallele
  Kaufwährungsbestätigung qualifizieren dieselbe Snapshotgrenze wie der Bericht.
  GET/Drill-down verändert keine Tabellen und ruft keine Provider auf.
- Browserweg auf dem vorhandenen abgeschotteten Wegwerfstack: Kaufcode ohne
  Zusatzhaken, Verkauf ohne Währungseingabe, Ergebnis, Herkunft und Korrektur.
  Bestehende Race-, Retry-, Abbruch- und Herkunftsgates bleiben bestehen.

## Prüfungen und Auslieferung

### Lokale Qualifikation am 20.10.2026

Prüfbasis ist der Aufgabenbranch auf dem oben genannten Ausgangscommit, mit
Python **3.12.14**, Node **22.16.0** und npm **10.9.2** aus den bestehenden
Manifest-/Lockverträgen. Folgende Git-Teilbäume binden den tatsächlich geprüften
Code; spätere Dokumentation ändert diese Prüfbasis nicht:

| Teilbaum | Git-Tree-SHA |
|---|---|
| `backend/app` | `bd846fb056974074e062506be84005439dc19bc4` |
| `frontend/src` | `aaf0e331af4c0b42e7a806518eee6ddc050f0a96` |
| `tests/unit/backend` | `a2652fa8f009f8814e61a0b6794a33aea367a203` |
| `tests/integration/backend` | `eec114d332a4706f33e256a62ed7bbdb426e27c8` |
| `tests/e2e` | `23a74b0e088c4f5de0669be616e111f1266a070c` |

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Ruff und Black über Anwendung, Backend-Unit- und Integrationstests | bestanden |
| Mypy | bestanden, 552 Quelldateien |
| Vollständige Backend-Unit-Suite, aus `backend/`: `.venv/bin/python -m pytest -c pyproject.toml ../tests/unit/backend -q` | **2690 bestanden**, keine Skips, 142,97 s; bestehende Starlette/AnyIO-DeprecationWarning |
| Unverändert `bash scripts/check-frontend.sh` | Exit 0: Typecheck, ESLint, Prettier, **558 Tests in 111 Dateien**, keine Skips; Produktionsbuild erfolgreich |
| Frontend-Coverage | Statements/Lines 92,85 %, Branches 84,60 %, Functions 85,19 %; bestehende Mindestwerte unverändert |
| `node --test .github/tests/version-tag.test.cjs` | **9 bestanden**, keine Skips |
| `git diff --check` | bestanden |
| Gezielte PostgreSQL-Testsammlung | 16 Fälle erkannt, davon 6 neu; **nur Collection, kein Datenbank-Pass** |

Die Ausführung verwendete isolierte Entwicklungsabhängigkeiten und synthetische
Fixtures mit abgeschalteten externen Daten-/Benachrichtigungspfaden. Ein
vorheriger Backend-Aufruf vom Repositoryroot scheiterte an zwei relativen
Dokumentpfaden; der korrekte Aufruf aus `backend/` bestand unverändert. Ein
erster Frontend-Gatelauf fand vier Lintfehler im neuen Testcode; diese sind
behoben und das vollständige Gate wurde danach bestanden. Hängende
Standard-Sandbox-Versuche wurden abgebrochen und zählen nicht als Nachweis.

### Noch erforderlicher vollständiger Integrationsnachweis

Lokal fehlen Docker und PostgreSQL-Werkzeuge. Der vorhandene Vorprüfbefehl
`bash scripts/verify-release-readiness.sh` meldet deshalb mit Exit 1
`FEHLT IM PATH: docker`. Das vollständige `bash scripts/check-backend.sh` mit
PostgreSQL/Coverage und die Docker-Browsergates wurden hier nicht als bestanden
gewertet. Sie müssen im unveränderten CI-Teststack mit PostgreSQL 17 und
synthetischen Daten erfolgreich sein. Der separate Owner-Browserrunner prüft
weiterhin genau einen bestandenen Test, keine Skips, Flaky-Ergebnisse oder
Retries, keine externen Browseraufrufe und die begrenzte Stackbereinigung.

Der endgültige PR-/Commitbezug und diese aktuellen CI-Ergebnisse werden nach
Ausführung ergänzt. Vorhandene grüne V1.5.9-Läufe gelten nicht als Nachweis
dieser Änderung. Keine Schemaänderung oder automatische Änderung vorhandener
Bestände ist nötig. Ein veröffentlichter Tag ist weiterhin kein Nachweis einer
aktualisierten PC-Installation.
