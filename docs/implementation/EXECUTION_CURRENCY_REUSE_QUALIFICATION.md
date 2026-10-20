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

## Zuordnung zu Akzeptanzkriterien 1–10

Die Zuordnung gilt für den Teststand `a31551733bb86ff3cfda1cee5beb20eb6d1e6759`
(derselbe Tree wie PR #266, Head `7737f29b`). Die unten dokumentierten **2690
Backend-Unit- und 558 Frontend-Tests sind lokal bestanden**. Die tatsächlichen
CI-Ergebnisse, ihre exakten Commitbezüge und die anschließend präzisierte
Smoke-Assertion stehen im Prüfabschnitt; die Existenz eines Tests allein ist
kein bestandener Lauf.

| Nr. / ursprüngliches Kriterium | Konkrete Zuordnung und Prüfgrenze |
|---|---|
| **1. Referenz und Korrektur** | [Owner-Trace](../../tests/unit/backend/features/trade_position/test_projector_trace.py): `test_reference_contributions_and_full_cost_basis_provenance` und `test_explicit_effective_correction_preserves_original_and_changes_only_current_trace`. [PG-Wiederverwendung](../../tests/integration/backend/test_execution_currency_reuse_postgres.py): `test_one_confirmed_purchase_qualifies_sales_additional_purchase_and_price_correction` prüft **10/50 → 30/70 EUR**, einmal bestätigten BUY, Nachkauf und SELL-Korrektur ohne zusätzliche Erklärung. Browserzuordnung unter Nr. 9. |
| **2. Offene Position, BUY und Ausschlüsse** | [Owner-Trace](../../tests/unit/backend/features/trade_position/test_projector_trace.py): `test_reference_september_sales_already_exist_while_trade_is_open`, `test_buy_only_has_no_sell_contributions`. [Report-Units](../../tests/unit/backend/features/performance/test_report.py): `test_completely_examined_empty_selection_is_explicit` mit `buy_only`/`cancelled`. Eigene EXTERNAL-Ausführungen werden in den PG-Fällen erfasst. Reine externe Beobachtungen sind durch die [Reader-Quellen](../../backend/app/features/performance/service/reader.py) ausgeschlossen; dafür besteht kein eigener isolierter negativer Berichtstest. |
| **3. Belegte Währung und Herkunft** | [Resolver-Units](../../tests/unit/backend/features/trade_position/test_currency_resolution.py): `test_later_buy_cannot_fill_earlier_unknown_costs_or_seed_an_incomplete_prefix`, `test_same_side_correction_chain_preserves_exact_nearest_confirmed_ancestor` sowie Scope-/Mischwährungsfälle. [PG-Report](../../tests/integration/backend/test_realized_gross_report_postgres.py): `test_legacy_unknown_listing_changes_and_one_explicit_purchase_confirmation`. [Report-Units](../../tests/unit/backend/features/performance/test_report.py): `test_eur_and_usd_are_explicit_separate_selections_without_fx`, `test_previous_sale_revenue_currency_does_not_poison_later_cost_basis`. Der Browserfall verwendet USD-Listing/Strike bei tatsächlicher EUR-Kaufbestätigung. |
| **4. Leer, unbekannt, Null und Teilbetrag** | [Report-Units](../../tests/unit/backend/features/performance/test_report.py): `test_unconfirmed_real_facts_are_not_a_zero_or_an_empty_selection`, `test_partial_known_zero_and_complete_zero_remain_measured_results`. [PG-Wiederverwendung](../../tests/integration/backend/test_execution_currency_reuse_postgres.py): `test_mixed_costs_and_explicit_conflicting_sales_preserve_facts_and_partial_coverage`. [UI](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx): `keeps an empty reviewed set distinct from entirely unresolved facts and from a measured rounded zero`. |
| **5. Datum, Zeitzone und Korrektur** | [Perioden-Units](../../tests/unit/backend/features/performance/test_periods.py): `test_calendar_days_use_separate_local_boundaries`, `test_precise_instants_obey_half_open_month`, `test_date_only_possible_day_is_preserved` und ungültige Quellenzeiten. Konkret Berlin **29.03.2026 (23 Stunden)**, **25.10.2026 (25 Stunden)**, Jahresgrenze, beide Herbst-Offsets sowie Date-only-Überlappungen aus Tokyo/New York. Die [Referenzfixtures](../../tests/unit/backend/features/performance/fixtures.py) erfassen wirtschaftliche Fakten von 2026 erst 2031. [PG-Report](../../tests/integration/backend/test_realized_gross_report_postgres.py): `test_repeatable_read_allows_committed_owner_corrections_without_mixed_response[date]`. DST ist hier ein Domain-Nachweis, keine behauptete vollständige Browser-DST-Abdeckung. |
| **6. Gemeinsame Basis, Zähler und UI-Rennen** | [API-Units](../../tests/unit/backend/features/performance/test_api.py): `test_service_uses_only_one_snapshot_and_validates_first`. [Report-Units](../../tests/unit/backend/features/performance/test_report.py): `test_sort_and_source_fingerprint_are_stable_between_unchanged_reads` und Rundungsdifferenzen. [UI](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx): `does not derive totals from the visible page or convert high-precision money through a float`; `invalidates visible results immediately and ignores older success and failure responses after filter changes`; gesonderter Test für falsche Filter und markierten Basiswechsel. PG-Report prüft Zählidentitäten und vollständige Quellen. |
| **7. Konkurrierende Korrektur** | [PG-Report](../../tests/integration/backend/test_realized_gross_report_postgres.py): `test_repeatable_read_allows_committed_owner_corrections_without_mixed_response`, parametrisiert mit `price`, `date`, `currency`. [PG-Wiederverwendung](../../tests/integration/backend/test_execution_currency_reuse_postgres.py): `test_repeatable_read_keeps_all_inherited_currencies_on_one_committed_basis`. Tatsächlicher Writer-Commit zwischen Reader-Abfragen, vollständiger Alt-/Neustand und Writer-Fortschritt; keine globale Serializable-Zusage. |
| **8. Lernen unabhängig, GET ohne Nebenwirkungen** | [PG-Report](../../tests/integration/backend/test_realized_gross_report_postgres.py): `test_real_captures_qualified_report_complete_sources_and_no_get_side_effects` prüft Tabellen-Fingerprints und abgefangene externe Transporte. [PG-Lernunabhängigkeit](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py): `test_report_ignores_persisted_incomplete_observation_and_stale_review`. Tatsächlich gespeichertes `ACTIVE` mit `ready=False`/`POST_TRADE_OBSERVATION_INCOMPLETE`, danach gespeichertes `STALE` mit `EXIT_REVIEW_STALE`; kein erfundenes persistiertes `NOT_READY`-Enum. Lerninhalte bleiben durch den Bericht unverändert. |
| **9. Backend-Owner und echter Browserweg** | [API-Units](../../tests/unit/backend/features/performance/test_api.py): `test_response_transmits_complete_exact_strings_sources_and_definition`. [Echter Browserfall](../../tests/e2e/realized-gross-report-postgres.spec.ts): `real PostgreSQL: purchase currency once, inherited sales, sources and correction` verbindet Workspace-Selection, BUY/SELL über UI, Bericht, Einzelbeiträge, Herkunft, Korrektur und einmalige historische BUY-Bestätigung mit Owner-API und PostgreSQL. Der bestandene echte CI-Lauf ist unten dokumentiert; UI-Mocks ersetzen ihn nicht. |
| **10. Gates und begrenzter Abschluss** | Unverändert: [Backend-Gate](../../scripts/check-backend.sh), [Frontend-Gate](../../scripts/check-frontend.sh), [E2E-Gate](../../scripts/run-e2e.sh) und [Owner-Browserrunner](../../scripts/run-realized-gross-e2e.sh). Vertrags-/Backlogkonsistenz wird durch Dokumentreview geprüft, nicht durch einen einzelnen Unit-Test bewiesen. Vollständige aktuelle CI-Ergebnisse werden unten ergänzt. |

`PositionProjector` und Snapshotreader sind gegenüber dem Ausgangscommit
unverändert. Ein Snapshot gilt für eine vollständige Antwort; ein neuer GET darf
eine neue, sichtbar markierte Basis liefern. Unbekannte frühere BUY-Währungen,
gemischte Kosten und ausdrücklich widersprüchliche Erlöswährungen bleiben echte
Datenlücken. **Reale Nutzerbestandsabdeckung, PC-Installation und PC-Abnahme sind
nicht beobachtet.** Weder diese Zuordnung noch ein später grüner CI-Lauf erklärt
den gesamten ursprünglichen M8-Umfang für abgeschlossen.

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

### Lokale Werkzeuggrenze und tatsächlicher CI-Nachweis

Lokal fehlen Docker und PostgreSQL-Werkzeuge. Der vorhandene Vorprüfbefehl
`bash scripts/verify-release-readiness.sh` meldet deshalb mit Exit 1
`FEHLT IM PATH: docker`. Das vollständige `bash scripts/check-backend.sh` mit
PostgreSQL/Coverage und die Docker-Browsergates wurden hier nicht als bestanden
gewertet. Sie müssen im unveränderten CI-Teststack mit PostgreSQL 17 und
synthetischen Daten erfolgreich sein. Der separate Owner-Browserrunner prüft
weiterhin genau einen bestandenen Test, keine Skips, Flaky-Ergebnisse oder
Retries, keine externen Browseraufrufe und die begrenzte Stackbereinigung.

Der veröffentlichte Umsetzungskommit ist
**`7737f29b35b9a1f8dc1a68c0a88a684ed73aafc4`** in
[PR #266](https://github.com/burckhju/trading-workspace/pull/266). Der lokale
Commit `a31551733bb86ff3cfda1cee5beb20eb6d1e6759` und der tatsächliche
CI-Merge-Commit **`a124fa73e0aeba3e01a5c25405db3c332579e786`** besitzen denselben
vollständigen Tree **`116dce899c6bdc65b84a6dbe845dead9b30eed98`**. Damit sind
lokale und CI-Codebasis exakt gebunden.

| CI-Prüfung auf diesem Code | Ergebnis und Nachweis |
|---|---|
| Erster vollständiger Backend-Lauf einschließlich PostgreSQL | **2886 bestanden, 3 fehlgeschlagen**, eine bestehende Warnung, 830,73 s; Coverage **87,30 %** bei unverändertem Minimum 85 %. Ruff, Black, Mypy und Migration bestanden; **kein grünes Gesamtgate**. [Job 118476943159](https://github.com/burckhju/trading-workspace/actions/runs/39376893297/job/118476943159). Die drei Testkorrekturen sind unten getrennt benannt. |
| Frontend | **558 Tests / 111 Dateien bestanden**, Coverage und Build erfolgreich; [Run 39376893203](https://github.com/burckhju/trading-workspace/actions/runs/39376893203). |
| Owner-Browser auf echtem PostgreSQL | **1 bestanden, 0 übersprungen, 0 flaky, 0 Retries**, 6,0 s; [Job 118476943101](https://github.com/burckhju/trading-workspace/actions/runs/39376893295/job/118476943101). |
| Produktionsimage und Renderer | `Backend / restrictive-umask image` und `Backend / issuer renderer sandbox` bestanden; [Backend-Run](https://github.com/burckhju/trading-workspace/actions/runs/39376893297). |
| Veröffentlichungsgrenzen | bestanden; [Run 39376893286](https://github.com/burckhju/trading-workspace/actions/runs/39376893286). Der Tag-Job ist auf einem PR absichtlich nicht ausgeführt. |
| Erster allgemeiner Smoke-Lauf | **54 bestanden, 1 fehlgeschlagen, 3 bestehende Sicherheits-Skips**; kein grüner Gesamt-E2E-Nachweis. Die einzige fehlgeschlagene Assertion und die erforderliche Wiederholung sind nachfolgend erklärt. |

Das Owner-Artefakt `realized-gross-owner-e2e`, ID **12243423173**, wurde
heruntergeladen und gegen SHA-256
`f0871200fa2df103cae00074c7444d97bf45843e13bd72260bd96ee100f1fe21` geprüft.
Es belegt PostgreSQL **17.11**, Schema **`20261017_0047`**, den nur für diesen
Lauf erzeugten Compose-/Datenbanknamen und unveränderte Fingerprints aller
**103 öffentlichen Tabellen** während des Lesens. Sechs Ausführungen benötigen
nur **eine** tatsächliche Kaufwährungsbestätigung. Die beigefügten API-Antworten
unterscheiden **10 EUR**, korrigierte **30 EUR**, `NOT_COMPUTABLE` mit
`total=null`, einen gemessenen Nullbeitrag und `EMPTY`. Die Desktop-/Mobilbilder
wurden gelesen; Quellenanzeige und markierter Basiswechsel stimmen mit diesen
Antworten überein. Die Bereinigung entfernte ausschließlich den eigenen
UUID-Stack samt Test-Volume und Netzwerken.

### Gezielte Testkorrekturen und Freigabegrenze

Der erste vollständige PostgreSQL-Lauf fand drei Fehler im Testaufbau bzw.
in bestehenden exakten Response-Erwartungen:

- Der Legacy-Journal-Migrationstest verwendete die aktuelle Capture-API erst
  nach einem Downgrade auf Schema 0045. Die neue reine Herkunftsableitung liest
  dann eine absichtlich noch nicht vorhandene 0047-Tabelle. Die wirtschaftliche
  Buchung wird deshalb vor dem Downgrade auf aktuellem Schema durch ihren Owner
  erfasst. Nach geschlossenem Client wird der leere neue Journal-/Currency-Stand
  zurückgenommen; der alte FINAL-Fakt wird weiterhin auf 0045 angelegt und
  anschließend vorwärts migriert. Die Herkunft bleibt unbekannt und alle
  bisherigen Integritätsassertions bleiben bestehen. Kein Produktionsfallback
  auf ein veraltetes Schema und kein `alembic stamp`.
- Eine weitere vollständige Currency-History-GET-Erwartung enthielt nur
  `current`/`history`. Die zusätzliche `currency_resolution` wird nun ebenfalls
  exakt geprüft, einschließlich tatsächlicher Execution-/Confirmation-IDs.
- Der neue Mixed-/Conflict-Test legte seinen zweiten Trade über einen zweiten
  Produktaufbau mit demselben Test-Ticker an und scheiterte bereits an der
  bestehenden Listing-Eindeutigkeit. Der Testaufbau verwendet ein gemeinsames
  Underlying/Listing und drei ausdrücklich getrennte Owner-Produkte; die
  Trade-, Mischwährungs- und
  Teilabdeckungsassertions bleiben erhalten. Der Constraint bleibt unverändert.

Der erste Smoke-Lauf verglich in
[`trade-execution-dates.spec.ts`](../../tests/e2e/trade-execution-dates.spec.ts)
die komplette alte SELL-Timelinezeile vor/nach Ersetzung. Die neu hinzugefügte
`currency_resolution` ist jedoch eine aktuelle Ableitung: Ein wirksamer,
unbekannter SELL nennt den vorherigen BUY als ungeklärte Quelle; ein ersetzter
historischer SELL erhält ausdrücklich keinen erfundenen früheren BUY-Präfix.
Alle gespeicherten Ausführungsfakten blieben gleich.

Der Test prüft nun den exakten unbekannten BUY-Präfix vor der Korrektur, die
**vollständige** alte Zeile mit ausdrücklich leerer historischer Ableitung und
den richtigen Präfix am neuen wirksamen SELL. Menge, Preis, Datum, Bestände,
Ergebnis und Supersession bleiben ausdrücklich geprüft. Keine Assertion wurde
gestrichen, kein Skip hinzugefügt und kein Runner/Gate geändert. Der geänderte
E2E-Teilbaum ist **`85b2d129284cf2df5e01963fec6ab463a604ded7`**. Anwendung,
Frontend und Backend-Unit-Testbaum bleiben exakt wie oben. Die drei beschriebenen
PostgreSQL-Testkorrekturen verändern ausschließlich ihren Integrationstestbaum.
Dieser ist nun **`3b5f9d1ff6629d77c9346e7911a899f0a6a09035`**.
Ruff, Black, gezielte Collection und Diffprüfung wurden erneut bestanden;
Collection ist weiterhin kein PostgreSQL-Pass.

Die drei vorhandenen Smoke-Skips betreffen die eigens abgesicherten Journal-,
FT-011-Historien- und Realisations-Browserfälle. Der hier erforderliche
Realisationsfall wird im getrennten Owner-Job tatsächlich ausgeführt und darf
dort nicht übersprungen werden. Die beiden Lernprozess-Browserfälle sind durch
diesen Auftrag nicht neu qualifiziert; ihre Backend-Gates bleiben enthalten.

Nach diesen Testkorrekturen müssen **sämtliche Gates auf dem aktuellen
PR-Head erneut erfolgreich sein**. Die exakten abschließenden Run-/Headbezüge
und danach der tatsächlich veröffentlichte main-/Tag-Commit werden im
[PR #266](https://github.com/burckhju/trading-workspace/pull/266) festgehalten.
Nur dieser erfolgreiche aktuelle Stand erlaubt den bereits autorisierten
normalen Merge. Der bestehende Version-Workflow veröffentlicht `v1.5.10` erst
nach grünen Backend-, Frontend- und End-to-End-Push-Läufen auf genau dem
aktuellen main-Commit. Vorhandene grüne V1.5.9-Läufe gelten nicht als Nachweis
dieser Änderung. Ein Tag ist weiterhin kein Nachweis einer PC-Installation.
