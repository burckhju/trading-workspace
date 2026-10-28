# Laufende Positionsbewertung — Währungsvertrag und Qualifikation

## Auftrag, Quellen und Abgrenzung

Der Auftrag vom 28.10.2026 verlangt, nicht realisiertes Brutto-PnL nur bei
belegter gleicher Währung von wirksamer Kaufkostenbasis und verwendeter Quote
als Geldbetrag auszugeben. Der enge Vertrag wurde vor der Implementierung
festgehalten; die tatsächlichen Prüfbelege sind im letzten Abschnitt ergänzt.
Arbeitsstatus steht ausschließlich in den bestehenden Einträgen
[PB-016 Positionen](../planning/PRODUCT_BACKLOG.md#pb-016-positions),
[PB-017 Brutto-PnL](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) und
[Operational Workspace](../planning/PRODUCT_BACKLOG.md#operational-workspace).

Die neu geprüfte Ausgangsbasis ist `main`
**`dc89dfa65758dfc1258a8fab657257f6598b0179`**, Softwareversion **1.5.29**.
Die historische Reviewreferenz `f3c067ecdfe99e46f3c8b63c37bb4d283cd5a568` /
1.5.28 bleibt eine frühere Basis. [PR #295](https://github.com/burckhju/trading-workspace/pull/295)
ist inzwischen integriert: Head `36e846cf9bcdaeb47981328597cb05335fe83d1f`,
Merge `13e8d5331abab32d4998118e83aaecbc231dea31` am 28.10.2026.
Der anschließende [Release-PR #296](https://github.com/burckhju/trading-workspace/pull/296)
führt zum genannten Main-Stand. Lesson- und Schedulerkorrekturen bleiben als
Bestandteile dieser Basis erhalten; sie werden nicht erneut implementiert.
Die historischen Prüfergebnisse dieser PRs qualifizieren den neuen Fix nicht.

Fachliche Grundlagen sind der bestehende
[FT-010-Projektionsvertrag](../features/FT-010_TRADE_MANAGEMENT.md),
[ADR-S10-002](../decisions/ADR-S10-002-EFFECTIVE-EXECUTION-HISTORY-AND-POSITION-PROJECTION.md),
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
und dessen [Kaufwährungs-Wiederverwendung](EXECUTION_CURRENCY_REUSE_QUALIFICATION.md).
Die strengere Qualifikation der bestehenden Performanceberichte dient als
Referenz. Ihre Perioden-, Vollabschluss- und Kennzahlenverträge werden nicht
geändert. Der Nutzerauftrag entscheidet die Anwendung der vorhandenen
Kaufbasisqualifikation auf laufende Bewertungen ausdrücklich; dafür bleibt keine
neue Finanzregel offen. Insbesondere werden weder FIFO/Lots noch FX,
Gebühren, Steuern, Nettoergebnisse oder eine neue Modellfamilie ergänzt.

## Ausgangsbefund und Verantwortlichkeit

Im geprüften Ausgangsstand multiplizierte `ProductPositionValuationService`
den Produktkurs mit dem offenen Bestand und zog danach die numerische
`position.cost_basis` ab. Die Währung der tatsächlichen Kaufkosten wurde dabei
nicht durch die vorhandenen Ausführungsbelege qualifiziert. Das betraf den
älteren Evaluationpfad und den Pfad mit ausdrücklich festgelegter Kursquelle
sowie die Analysevariante.
Die Quote kann dadurch eine Geldwährung auf einen nicht belegten Kostenabzug
übertragen. Zehn Stück, Kostenbasis 20 und Quote 2,50 EUR ergeben rechnerisch
25 EUR Marktwert und 5 EUR Differenz, auch wenn eine monetäre EUR-Aussage für
diese Differenz fachlich nicht zulässig ist.

FT-009/010 bleibt der einzige Owner von Executions, Währungsbestätigungen und
Position. `PositionProjector` liefert weiterhin Menge und Kostenbasis aus der
vollständigen effektiven Historie; `resolve_execution_currencies` liefert die
Währungsherkunft. Die Bewertung ergänzt eine Qualifikation dieser vorhandenen
Ergebnisse. Sie führt keine zweite Kostenbasis-/PnL-Projektion ein. Backend und
Frontend dürfen fehlende Währungsbelege nicht aus Listing, Plan, Quote oder
zuletzt bekannter Kaufwährung ersetzen.

## Definition `position-unrealized-gross-v1`

### Wirksame Kaufkostenbasis

Für eine offene Position werden alle effektiven BUYs des Trades in der
bestehenden Reihenfolge `(executed_at, recorded_at, id)` qualifiziert.
Nachkäufe und wirksame wirtschaftliche Korrekturen gehen durch den bestehenden
Projektor ein. Teilverkäufe verändern verbleibende Menge und Durchschnittskosten
nach dem bestehenden Average-Cost-Vertrag; ihre Erlöswährungen sind kein
Kaufkostenbeleg. Frühere SELL-Executions bleiben wegen ihrer Mengenwirkung in
der Herkunft. Ein vollständiger Abschluss kann im selben Trade nicht durch
einen neuen BUY wieder geöffnet werden. Es gibt daher keine neue Lot-Auswahl,
die einzelne frühere BUY-Währungen aus der offenen Durchschnittskostenbasis
entfernen dürfte.

Der vorhandene Resolver verwendet unverändert:

1. die aktuelle direkte Bestätigung der konkreten Execution;
2. andernfalls den bestätigten gleichseitigen Vorgänger entlang der wirksamen
   Korrekturherkunft;
3. andernfalls den vollständig vorhergehenden effektiven BUY-Präfix, wenn alle
   dort benötigten Währungen bekannt und gleich sind.

Ein später bestätigter Kauf bestätigt keinen früheren unbekannten Kauf.
Eine ausdrückliche Abweichung bleibt erhalten. Konkrete Execution- und
Bestätigungs-IDs belegen direkte, wiederverwendete und ersetzte Herkunft.
Unwirksame historische Executions werden nicht als zusätzliche effektive
Kostenbestandteile gerechnet.

### Unabhängige Aussagequalitäten

Marktwert und nicht realisiertes Brutto-PnL besitzen getrennte Qualifikationen.
Die vorhandenen Quote-Felder, Statuswerte und Nutzbarkeitsregeln bleiben erhalten,
einschließlich aktueller, indikativer, veralteter und zuletzt verfügbarer Kurse.
Ein unabhängiger gültiger Marktwert bleibt bei fehlendem PnL verfügbar.

| Kaufkostenbasis gegenüber der verwendeten Quote | PnL-Aussage |
|---|---|
| Mindestens eine erforderliche Kaufwährung unbekannt | Fehlender Betrag; `COST_BASIS_CURRENCY_UNKNOWN` |
| Erforderliche Kaufbasis enthält unterschiedliche belegte Währungen | Fehlender Betrag; `COST_BASIS_CURRENCY_MIXED` |
| Vollständig belegte einheitliche Kaufwährung weicht von der Quote ab | Fehlender Betrag; `COST_BASIS_CURRENCY_MISMATCH` |
| Vollständig belegte einheitliche Kaufwährung entspricht der Quote, Quote für die jeweilige Variante nutzbar | Berechenbarer Betrag; `COST_BASIS_CURRENCY_MATCHED` |
| Weder für aktuelle Bewertung noch Analyse ist eine Quote nutzbar | Fehlender Betrag mit dem vorhandenen Kurs-/Bewertungsgrund |

Sind bereits unterschiedliche belegte Kaufwährungen vorhanden, hat `MIXED`
Vorrang vor einer zusätzlich vorhandenen unbekannten Komponente. Andernfalls
bleibt eine unvollständig belegte Basis `UNKNOWN`. Erst eine vollständig
bekannte einheitliche Kaufbasis kann gegenüber der Quote als passend oder
abweichend qualifiziert werden.

Wenn eine Quote zumindest für Analyse nutzbar ist, wird die Währungsgrundlage
beider PnL-Felder qualifiziert. Eine vorhandene Währungslücke bleibt dann deren
Grund; die unabhängige Kursbegrenzung bleibt in `reason`, `analysis_warning`
und den bisherigen Quote-Flags sichtbar. Bei passender Währung und nur für
Analyse nutzbarer Quote behält das fehlende aktuelle PnL den ursprünglichen
Kursgrund. Das ist eine Priorisierung der Erläuterung, keine Lockerung der
Frische- oder Nutzbarkeitsgrenzen.

Die API ergänzt `unrealized_pnl_usable` und `unrealized_pnl_reason` für
`unrealized_gross_pnl` sowie `analysis_unrealized_pnl_usable` und
`analysis_unrealized_pnl_reason` für `analysis_unrealized_gross_pnl`.
Ein fehlender Betrag wird als `null` übertragen. Ein qualifiziertes exakt
neutrales Ergebnis bleibt ein gemessener Nullbetrag. Ein Quote-Status wie
`AVAILABLE` allein berechtigt keinen Consumer, PnL als nutzbar zu behandeln.

### Gemeinsame Lesebasis und Herkunft

Vor der ersten Fachabfrage beginnt eine kurze, eigene PostgreSQL-Transaktion
mit `REPEATABLE READ READ ONLY`. Sie materialisiert Trade, Positionsidentität,
vollständige Execution-/Korrekturhistorie, aktuelle Währungsbelege sowie die
vorhandenen Listing- und Kursquellenbindungen. Aus diesem Stand verwenden
Projektor und Währungsresolver dieselben effektiven Fakten. Die Transaktion
endet vor dem vorhandenen Quote-Provider-/Resolveraufruf. Globale Isolation,
Command-Sperren und Capture-Verhalten bleiben unverändert.

Der additive `position_basis`-Kontext bindet `definition_version`, einen
deterministischen `basis_id`, die projektierte Position, effektive
Execution-IDs und die Währungsauflösung je benötigtem BUY einschließlich
Quell-Execution-/Bestätigungs-IDs. Kaufkostenwährung und deren
Qualifikationsstatus bleiben getrennt von der Quote-Währung. Änderungen der
Ownerfakten oder Währungsbelege führen zu einem entsprechend anderen Basisbezug; der Hash
ist keine dauerhaft wiederherstellbare historische Berichtssitzung.

Die Depotantwort übernimmt Stückzahl und Kostenbasis dieser Bewertungsbasis.
Sie darf keine zuvor separat gelesene alte Position mit einer neueren
Bewertungs-/Währungsbasis kombinieren. Monitoring- und Alertinformationen
behalten ihre eigenen vorhandenen Lesebezüge; es wird kein globaler Snapshot
über fachfremde oder externe Daten behauptet. Kursherkunft, Preisbindung,
Zeitstempel, Mapping-/Auswahlversionen und Frischeinformationen bleiben erhalten.
Auch bei fehlendem Provider oder nicht verfügbarer festgelegter Kursquelle
bleibt die bereits materialisierte Positionsbasis in der Antwort erhalten.

Der Ablauf bleibt lesend: keine Bestätigung, kein Backfill, keine Änderung
historischer Buchungsfakten und kein zusätzlicher Provideraufruf zur vermeintlichen
Währungsreparatur. Die bestehenden erlaubten Quote-Lesewege bleiben bestehen.

## Consumervertrag

Depotzeile und Positionsdetails, Trade-Management und indikative Analysewerte
übernehmen ausschließlich das zur Variante gehörende qualifizierte PnL.
Fehlende Berechenbarkeit wird mit verständlichem Grund angezeigt. Gewinn- und
Verlustfilter, Vorzeichenfarbe und Geldsortierung behandeln einen solchen Wert
als fehlend. Fehlende Werte bleiben auch bei umgekehrter Sortierung zuletzt.
Die vorhandene Workspace-Aktionsliste nennt dieselbe Währungslücke; eine
indikativ nutzbare Quote begründet dort keine pauschale Zusage verfügbarer
PnL-Überwachung.

PnL-Summen und ihre Abdeckungszähler verwenden ausschließlich qualifizierte
PnL-Beiträge. Marktwertsummen und deren Abdeckung werden unabhängig weitergeführt.
Eine Position mit gültigem EUR-Marktwert und unqualifiziertem PnL erhöht die
Marktwertabdeckung, aber weder EUR-PnL-Summe noch PnL-Abdeckung. Bestehende
exakte Aggregation, Währungsgruppierung und Kursqualitäts-/Zeitangaben bleiben
erhalten. Keine neue Finanzberechnung ist im Frontend erforderlich.

## Vorab festgelegte Regressionen

Die folgenden Sollkriterien wurden vor der Implementierung festgelegt. Ihre
tatsächlichen Code-/Testbezüge und Ergebnisse stehen im Prüfabschnitt unten:

- Unbekannte Kaufwährung, bestätigter USD-BUY bei EUR-Quote sowie gemischte
  EUR-/USD-BUYs: Marktwert 25 EUR bei zehn Stück und Quote 2,50 EUR bleibt
  erhalten; beide PnL-Varianten fehlen mit verständlichem Grund.
- Vollständig belegtes EUR bei gleicher Quote: positiver, negativer und exakt
  neutraler Wert bleiben qualifiziert und unterscheiden sich von fehlend.
- Ein bestätigter Erstkauf qualifiziert zulässige Nachkäufe über den bestehenden
  Resolver; ein später bestätigter Kauf heilt keinen früheren unbekannten Kauf.
- Teilverkäufe sowie Preis-, Mengen-, Datums- und Währungskorrekturen verwenden
  effektive Historie, unveränderte Ownerarithmetik und genaue Herkunft. Eine
  abweichende frühere SELL-Erlöswährung vergiftet die verbleibenden Kaufkosten nicht.
- Evaluationpfad und festgelegte Kursquelle, indikative und zuletzt verfügbare
  Quotes sowie vorhandene Stale-/Missing-Grenzen bleiben ausdrücklich abgedeckt.
- Backend-/API-/UI-Nachweis bis zu Filtern, Sortierung, Farbe, Summen und
  getrennten Abdeckungszählern. Mindestens ein durchgängiger Fall belegt, dass
  ein unqualifiziertes PnL nicht zur EUR-Gewinnsumme beiträgt, während der
  gültige Marktwert sichtbar bleibt.
- Eine während des Lesens committed Ownerkorrektur erzeugt keine gemischte
  Antwort. Lesen erzeugt keine Bestätigungen und keine zusätzlichen externen
  Aufrufe zur Währungsreparatur.

Schreibende Prüfungen verwenden ausschließlich eindeutig identifizierte
Wegwerfumgebungen, synthetische Daten und abgefangene externe Aufrufe.
Python 3.12, Node 22.16.0 und npm 10.9.2 sowie die bestehenden Backend-,
Frontend-, Integrations- und Browsergates bleiben maßgeblich. Es werden keine
Coverage-Grenzen, Assertions oder Sicherheitsvoraussetzungen abgesenkt.
Fehler, Skips und nicht ausführbare Gates werden mit exaktem Commit-/Treebezug
getrennt von erfolgreichen Nachweisen ausgewiesen.

## Prüfbelege vom 28.10.2026

### Exakte lokale und veröffentlichte Stände

Die folgenden lokalen Commits binden die tatsächlich geprüften Dateien. Für die
Veröffentlichung über die GitHub-Git-Data-Schnittstelle wurden neue Commitobjekte
mit **jeweils identischem vollständigem Git-Baum** erzeugt. Damit werden keine
lokalen Läufe nachträglich als Ausführung auf einem anderen Commit ausgegeben.
Die Zuordnung ist vor Veröffentlichung geprüft; die PR-CI bleibt ein eigener
Nachweis am jeweiligen Remote-Head.

| Zweck | Lokaler Commit | Veröffentlichtes Commitobjekt | Gemeinsamer vollständiger Tree |
|---|---|---|---|
| Vertrag vor Implementierung | `b16b2dd15e64e5572c0732b57535833408c0a3c9` | `02b3a91044f7fb302faa473cb28bd0f7c355654c` | `382cc9ff43cec32a737cd7d4fc917554ce1787ec` |
| Implementierung und neue Regressionen | `567a0f3ed1654e76169b9ec2f549c1f2d6fe01f6` | `59ab5203cd41c2ec012b199e253727194f34ec9c` | `4f96a9b03f89c72e6333543de4c88c381b7afba0` |
| Import-/Runnerkonventionen der Tests | `d06287759ac1d6f4b50131dd773482b3b1e41d67` | `7a556b30d36ab650a95b7a29e2e5984da57d8424` | `ab7af4ab08538ee85e2e4eff43c3b11e630c8c39` |
| Exakte Ownerroute im Browserfixture | `52643868ee8f4d82dbb1778a2fb39e4afbbb73f3` | `7a7adacec3657806b208237fc9e2253e6fa403c1` | `98dd12a93404a445c4204b7cb0494e5819349a35` |

Der Backend-Gesamtlauf gehört zu `d0628775`; bis `52643868` änderte sich nur
`tests/e2e/position-currency-qualification.spec.ts`. Der vollständige
Frontendlauf prüft die Produktions-/Unit-Dateien von `567a0f3e`; diese bleiben
in den beiden folgenden Testcommits unverändert. Die abschließenden Browserläufe
gehören zu `52643868`. Nachfolgende reine Dokumentationsänderungen erweitern
diesen Softwareprüfumfang nicht.

[PR #297](https://github.com/burckhju/trading-workspace/pull/297) wurde als Draft
mit Remote-Head `7a7adacec3657806b208237fc9e2253e6fa403c1` eröffnet. Die aktuellen
headgebundenen CI-Ergebnisse, der endgültige Dokumentationshead und die
Reviewbereitschaft werden dort getrennt festgehalten. Zum Zeitpunkt der
PR-Eröffnung am 28.10.2026 waren die neuen CI-Läufe noch nicht abgeschlossen;
dies ist ein historischer Zwischenstand, keine Aussage über spätere Läufe.

### Ursprünglicher Fehler und gezielte Korrekturbelege

Auf der alten Bewertung scheiterten **alle 32 neuen Währungsfälle**:
Unbekannter Kauf, USD-Kauf, gemischte Käufe und unbekannter früherer Kauf mit
späterer EUR-Bestätigung, jeweils über Evaluation/festgelegte Quelle und
aktuelle/indikative/veraltete/zuletzt verfügbare Quote. Bei jeweils 25 EUR
Analysemarktwert entstand das fachlich unzulässige **+5 EUR** statt fehlendem
PnL. Eine zusätzliche Projektionsregression scheiterte, weil die alte
materialisierte Kostenbasis 20 statt der wirksamen Projektorkosten 24 verwendet
wurde. Die ursprünglichen Frontendregressionen endeten mit **17 Fehlern und vier
bestandenen Fällen**; sie zeigten die Weitergabe unqualifizierter Werte.

Mit dem Fix bestehen dieselben Assertions in den aktuellen Gesamtprüfungen.
Eine unbekannte Währung wird nicht bestätigt; das Ergebnis bleibt fehlend.
Belegte gleiche Währungen liefern weiterhin positive, negative und exakt
neutrale Beträge. Die unabhängige Codeprüfung schloss zusätzlich zwei konkrete
Restlücken: Die schon materialisierte `position_basis` bleibt auch bei frühen
Rückgaben wegen fehlender Quelle/Provider erhalten; die Workspace-Aktionsliste
verspricht bei bloßer Quote-Nutzbarkeit keine unqualifizierte PnL-Überwachung.

| Vertragsnachweis | Konkrete Regression und Grenze |
|---|---|
| Beide Bewertungswege, vier Kursvarianten, unbekannt/abweichend/gemischt/späterer BUY | [Bewertungsregressionen](../../tests/unit/backend/features/position_monitoring/test_product_valuation_currency.py), `test_unproven_costs_never_become_monetary_pnl` mit 32 Fällen; Positiv-/Negativ-/Nullmatrix und zwei Ownerhistorien zusätzlich. |
| Tatsächliche Owner-Captures, Korrekturen, Bestätigungsherkunft und unveränderte Tabellen | [Neue PostgreSQL-Integration](../../tests/integration/backend/test_position_valuation_currency_postgres.py), acht Fälle im vollständigen Backendlauf. `test_additions_partial_sales_and_corrections_keep_exact_cost_evidence` prüft Nachkauf, Teilverkauf, gleichseitige Ersatzherkunft und Datumsverschiebung; frühere USD-Verkaufserlöse vergiften EUR-Kaufkosten nicht. |
| Ein konsistenter Stand trotz unabhängig committed Writer | Drei Varianten von `test_repeatable_read_preserves_old_basis_while_owner_correction_commits`: Preis, Menge, Währungsbestätigung. Tatsächliches PostgreSQL `REPEATABLE READ READ ONLY`; der Writer beendet seinen Commit bei noch offenem Reader, die nächste Antwort erhält eine neue Basis. Der Quoteaufruf erfolgt nach Ende der Basistransaktion. |
| Depotmenge/Kosten passen zur Bewertung auch bei fehlender Quelle | Drei Varianten von `test_depot_replaces_earlier_quantity_with_its_actual_valuation_basis`: verfügbarer Kurs, fehlender Provider, nicht erlaubte Quelle. Der initial gelesene Bestand 10 wird nach zwischenzeitlicher Ownerkorrektur mit der Bewertungsbasis 20/40 konsistent ausgegeben. |
| Filter, Sortierung, Farbe, getrennte Summen und Abdeckung | [View-Regressionen](../../frontend/src/features/operational_workspace/services/positionsView.currency.test.ts), [Depotkomponente](../../frontend/src/features/operational_workspace/pages/OpenPositionsPanel.currency.test.tsx), [Tradebewertung](../../frontend/src/features/trade/components/ProductValuationPanel.currency.test.tsx) und [Herkunftsdetails](../../frontend/src/features/trade/components/PositionValuationBasisDetails.test.tsx). Fehlende Flags fallen ebenfalls geschlossen aus; gemessenes wissenschaftlich notiertes `0E-10` bleibt neutral nutzbar. |
| Durchgängige Backend-/Browserbindung | `test_owner_to_depot_preserves_market_value_and_excludes_unqualified_pnl` erzeugt tatsächliche Antworten von Bewertungs- und Depot-API; vollständiger Vergleich mit der [gemeinsamen Fixture](../../tests/fixtures/position_currency_qualification.json). Die [zwei Chromium-Journeys](../../tests/e2e/position-currency-qualification.spec.ts) verwenden genau diese Antworten bis zu EUR-Summe/Abdeckung und nach Navigation ins Trade-Management. |
| Wahrheitsgemäße Workspace-Aktionen | [Priorisierungsregressionen](../../tests/unit/backend/features/operational_workspace/test_prioritization.py) qualifizieren Währungsgründe auch bei nutzbaren indikativen Quotes. |

Der durchgängige Sechs-Positionen-Fall behält **135 EUR Marktwert / 6 von 6
bewertet**. Nur Gewinn +5, Verlust −5 und gemessene Null sind PnL-Beiträge:
**0 EUR / 3 von 6 PnL verfügbar**. Unbekannte, gemischte und abweichende
Kaufwährungen tragen jeweils einen gültigen Marktwert von 25 EUR bei, aber kein
PnL und keine Gewinn-/Verlustfarbe oder Filterzugehörigkeit. Die Fixture
normalisiert ausschließlich zufällige UUIDs, opake Basisidentitäten und den
Antwortzeitpunkt; finanzielle Werte, Gründe, Flags und Quellenrelationen werden
nicht nachgebaut. Die Browserfälle verwenden abgefangenes HTTP, kein zweites
live angebundenes Backend; die unabhängige native PostgreSQL-Prüfung erzwingt
stattdessen die vollständige Gleichheit dieser API-Antworten. Beide Ebenen
prüfen ausdrücklich fehlende Schreib-/externe Aufrufe.

### Ausgeführte reguläre Prüfungen

Laufzeiten: **Python 3.12.14, Node 22.16.0, npm 10.9.2, Playwright 1.55.0,
Chromium 140.0.7339.16 (Build 1187)**. Die nativen PostgreSQL-17.11-Stacks sind
ausschließlich für diesen Auftrag erstellt und nur über Loopback erreichbar;
Checksummen, `fsync`, `synchronous_commit` und `full_page_writes` bleiben aktiv.
Der vorhandene Integrationsguard verlangt die Basisdatenbank
`trading_workspace_test`; die neuen Integrationstests erzeugen und entfernen
ihre eigenen zufällig benannten `tw_currency_ref_test_*`-Datenbanken. Native
Browserfälle verwenden jeweils eine frische markierte
`tw_realized_report_e2e_<uuid>`-Datenbank mit ihrem bestehenden Guard.
Bestehende Migrationen bis `20261017_0047`, synthetische Ownerdaten,
abgeschalteter Scheduler/Versand und abgefangene externe Transporte bleiben
maßgeblich. Die Browserumgebung beobachtete keine ausgehenden HTTP-/Nichtloopback-
Versuche; deren Wegwerfdatenbanken und Prozesse wurden nach der Prüfung entfernt.

| Prüfung | Tatsächliches Ergebnis / Bindung |
|---|---|
| Unverändert `bash scripts/check-backend.sh` | **3.463 bestanden, keine Fehler oder Skips**, 875,24 s, eine bestehende Starlette-DeprecationWarning. Coverage **87,66 %** bei unverändertem **85-%-Gate**. Ruff, Black über 1.000 Dateien und mypy über 560 Dateien erfolgreich. Lokaler Commit `d0628775`. |
| Unverändert `bash scripts/check-frontend.sh` | **1.726 Tests / 149 Dateien bestanden**, 81,02 s. Typecheck, ESLint, Prettier und Produktionsbuild erfolgreich. Coverage **95,72 %** Lines/Statements, **90,73 %** Functions, **89,88 %** Branches; unveränderte Grenzen **80/80/80/70**. Produktions-/Unit-Dateien von `567a0f3e`. |
| Gezielter tatsächlicher Chromium-Lauf am Produktionsbuild | **11/11 bestanden**, keine Skips, Flaky-Ergebnisse oder Retries; einschließlich der neuen Backendfixture-Journeys. Stand `52643868`. |
| Vollständige allgemeine Browser-Smoke-Suite | **115 bestanden, fünf reguläre native Skips**, 134,81 s, keine Retries/Flakiness. Stand `52643868`, echte lokale App-/API-Ursprünge 8080/8000 und synthetische Daten. Diese fünf Skips sind nicht als Erfolge gezählt. |
| Nativer SELL-Periodenbericht | [Bestehende Journey](../../tests/e2e/realized-gross-report-postgres.spec.ts), **1 bestanden**, 69,05 s, keine Skips/Retries, Stand `567a0f3e`. Der vorhandene `check-performance-e2e-report.py` bestätigt den exakten erwarteten Test. Separat von den allgemeinen Smoke-Skips. |
| Nativer Vollabschlussbericht | [Bestehende Journey](../../tests/e2e/closed-trades-report-postgres.spec.ts), **1 bestanden**, 50,98 s, keine Skips/Retries, Stand `d0628775`, ebenfalls mit geschlossenem Report-Validator. Keine neue Performancefunktion oder Erweiterung der Fachdefinition. |
| Diff und Versionsgrenze | `git diff --check` erfolgreich; keine Migration, Abhängigkeitsänderung, Gate-Absenkung, neue Versionsnummer oder Änderung der integrierten Lesson-/Schedulerkorrekturen. |

Alle Browserläufe verwenden tatsächliches Chromium mit einem Worker und
`--retries=0`. Die beiden nativen Performancefälle verwenden den vorgesehenen
expliziten `REPORT_E2E_WRITES_ALLOWED=1`-Guard, eine eigene Run-UUID und den
bestehenden JSON-Report-Validator. Der temporäre lokale App-/Static-Wrapper
serviert die unveränderte Anwendung und den Produktionsbuild; dies ist kein
Compose-Nachweis.

Docker ist lokal nicht vorhanden; `scripts/run-e2e.sh` ist lokal **nicht als
bestanden** qualifiziert. Die drei nativen
[Candidate](../../tests/e2e/candidate-governance-journey-postgres.spec.ts)-,
[Journal](../../tests/e2e/post-trade-journal-postgres.spec.ts)- und
[FT011](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts)-Fälle
verlangen außerdem echte GitHub-Actions-Identität in ihren bestehenden Guards.
Sie wurden lokal nicht ausgeführt; diese Identität wurde nicht vorgetäuscht.
Die drei Fälle bleiben zusammen mit den Docker-Image-/Renderer-Prüfungen
Bestandteil der regulären headgebundenen PR-CI. Ein erfolgreicher lokaler
Smoke-Lauf ersetzt diese Nachweise nicht.

### Fehlgeschlagene Vorbereitungsläufe und Nachbesserungen

Frühere Versuche werden nicht als grüne Gates angerechnet:

- Ein Backend-Sandboxlauf wurde mit Exit 143 beendet. Ein erster betroffener
  Lauf meldete 616 Erfolge und sieben Fehler: zwei Dokumenttests wurden aus dem
  falschen Arbeitsverzeichnis gestartet; eine Routingfixture enthielt nicht die
  vollständigen Trade-Metadaten für den Owner-Mapper; vier Frankfurtfälle
  änderten nur die alte Positionszeile auf 2.000 Stück / 1.020 Kosten, während
  ihr neuer synthetischer BUY noch 10 Stück / 20 Kosten repräsentierte. Der BUY
  wurde auf 2.000 Stück zu 0,51 angepasst. Sämtliche fachlichen Preis-, Zeit- und
  Quellenassertions blieben erhalten. Der korrekte Nachlauf aus `backend/`
  bestand mit 632 Tests; das vollständige Gate bestand anschließend wie oben.
- Der erste Backend-Gatestart fand eine Importreihenfolge im neuen Test unter
  der tatsächlichen `backend/`-Konfiguration. Die Sortierung wurde korrigiert;
  keine Qualitätsgrenze oder Testassertion wurde verändert.
- Der erste Frontend-Gesamtlauf hatte 20 Fehler wegen der unpassenden API-Origin
  in der Testumgebung. Nach der Umgebungskorrektur bestand das vollständige
  unveränderte Gate. Neue Browserfixtures wurden an die vorhandene
  CommonJS-Ladekonvention und die exakte Ownerroute gebunden. Der erste allgemeine
  Browserversuch an Port 38080 wurde beendet; der vollständige erfolgreiche
  Nachweis verwendet die bestehenden Ursprünge 8080/8000.
- Beim erstmaligen Erzeugen der gemeinsamen API-Fixture bestanden bereits alle
  sechs Fachfälle und die vollständigen Tabellen-Nichtmutationsassertions;
  anschließend fehlte die noch nicht angelegte Vergleichsdatei. Erst der
  Wiederholungslauf mit dem tatsächlichen erzeugten Artefakt zählt als bestandene
  Gleichheitsprüfung. Es wurde kein gewünschter Geldwert von Hand eingesetzt.

## Übergabegrenze

Die Implementierung und die genannten lokalen Prüfungen sind abgeschlossen.
Aktuelle headgebundene CI-Ergebnisse und Reviewbereitschaft stehen in
[PR #297](https://github.com/burckhju/trading-workspace/pull/297); sie bleiben
von den lokalen Nachweisen und der fachlichen Abnahme getrennt. Der maßgebliche
Arbeitsstatus ist **Technical Review** in den bestehenden Backlogeinträgen,
keine neue zweite Aufgabenliste. Eine menschliche
Fachabnahme des Ergebnisses sowie tatsächliche Quellenabdeckung und beobachteter
Nutzerbetrieb sind nicht belegt.

Der aktuelle Auftrag umfasst Implementierung, Tests, Dokumentation und einen
überprüfbaren Pull Request. Er erlaubt keinen Merge, Release, Tag, Deployment
oder Installation. Frühere Freigaben zu PR #295/#296 übertragen sich nicht auf
#297. Reale Nutzerbestände wurden nicht geprüft oder verändert.
