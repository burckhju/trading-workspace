# Basisstatistiken abgeschlossener Trades — V1-Vertrag und Qualifikation

## Begrenzte Entscheidung vom 25.10.2026

Der neue Nutzerauftrag **„Basisstatistiken für abgeschlossene Trades als
unabhängigen Parallelstrang umsetzen“** autorisiert Trefferquote, Durchschnitt,
Median und Profit-Faktor brutto bis zu einem qualifizierten Draft-PR. Diese
Kennzahlen waren in
[ADR-S10-009](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md)
ausdrücklich noch nicht enthalten. Die heutige Entscheidung ergänzt diesen
engen Umfang; sie stellt keine frühere Freigabe rückwirkend anders dar.
Merge, Version, Tag, Veröffentlichung, PC-Update und fachliche Gesamtabnahme
bleiben getrennt. Die frühere Freigabe für PR #278 gilt nicht für diesen PR.

Zuordnung: bestehendes **PB-019 / FT-012**, Lieferziel C. Der Arbeitsstatus
bleibt im [zentralen Backlog](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics).
Keine neue Feature-ID und kein Abschluss des vollständigen M8-Umfangs.

Anfangsbasis: Main `b49e87e8e254a82cdcded0f7a606c61d1edc0c76`, Tree
`5717bb34b3efd4a4b8f2b7a336fe1bace1d49aba`, `VERSION` 1.5.18.
Der getrennte Tag `v1.5.18` zeigte beim Arbeitsbeginn auf
`3b8c59e54445dc39f9f84c8eeab2b11137bdde6c`. Kein offener Statistik-PR;
der parallele Release-PR #281 wird vor Übergabe erneut geprüft.
Eigener Branch: `feat/closed-trade-basic-statistics`.

## Fachvertrag `closed-trade-statistics-v1`

Die Population und Geldregeln von `closed-trade-gross-v1` bleiben unverändert:
genau ein vollständiges qualifiziertes Ergebnis je stabiler Trade-ID; der
wirksame tatsächliche Abschluss-SELL bestimmt den Zeitraum; sämtliche
wirksamen Lebenszeitverkäufe liefern das Tradeergebnis. Die bestehenden acht
disjunkten Coveragegruppen, Währungsbelege und Korrekturverträge gelten weiter.
Journal, Review, Lesson, FT-006 und Modellaktivierung sind keine Voraussetzungen.

Berechnung ausschließlich bei `summary.status = COMPLETE` und
`counts.qualified > 0`. Dann ist **N** die Zahl aller qualifizierten Trades des
gesamten abgerufenen Berichts, einschließlich exakt neutraler Trades.

| Kennzahl | Ungerundete Berechnung |
|---|---|
| Trefferquote | Exakt positive Tradeergebnisse / N × 100. Neutrale Ergebnisse sind im Nenner enthalten. |
| Ø Bruttoergebnis je Trade | Die bereits bestehende vollständige ungerundete `summary.total` / N; keine zweite Rekonstruktion der Geldsumme. |
| Median des Bruttoergebnisses | Mittlerer ungerundeter Tradebetrag; bei geradem N arithmetischer Mittelwert der beiden mittleren Beträge. |
| Profit-Faktor brutto | Summe positiver Rohbeträge / Absolutbetrag der Summe negativer Rohbeträge. |

`PARTIAL` und `NOT_COMPUTABLE` liefern für alle vier Kennzahlen `raw = null`,
`display = null`, Grund **„Berichtsgrundlage unvollständig“**. `EMPTY` liefert
ebenfalls vier Nullwerte, Grund **„Keine abgeschlossenen Trades in der
Auswahl“**. Die bestehende leere Gesamtsumme `0`, zulässige Teilsummen,
Vorzeichenzähler und Abdeckung behalten ihre Bedeutung. Keine alternativen
Kennzahlen des bekannten Teilbestands.

Ein Verlustnenner ungleich null und keine Gewinne ergeben Profit-Faktor `0`.
Ohne Verlustbeträge bleibt er `null`, Grund **„Nicht definiert: keine
Verlusttrades“**. Es gibt kein Infinity, NaN, Ersatznull oder Qualitätsurteil.

Alle Berechnungen erfolgen im Backend mit `Decimal` in einer lokalen Kopie des
bereits im Berichtsfingerprint gebundenen Decimal-Kontexts. Der globale Kontext
wird durch die Statistik nicht verändert. Der reguläre Owner-Kontext hat
Präzision 28 und `ROUND_HALF_EVEN`; ein abweichender geerbter Präzisions- oder
Rundungsstand bleibt im bestehenden Fingerprint gebunden. Die Quote rechnet
`positive / N * 100` in dieser Reihenfolge. Positive und negative Summen folgen
der bestehenden kanonischen Trade-ID-Reihenfolge. Nur die Medianwerte werden
sortiert; bei geradem N folgt die Addition der beiden Mittelwerte vor `/ 2`.
Die vom PositionProjector berechneten Rohwerte bleiben
maßgeblich; fehlende Beträge werden niemals zu null Euro umgedeutet.
Geldanzeige: bestehende Währungsreferenz, Minor Units und `ROUND_HALF_EVEN`.
Trefferquote und Profit-Faktor: zwei Nachkommastellen, `ROUND_HALF_EVEN`.
`+0.004` / `-0.004` bleiben positiv / negativ trotz gerundeter Nullanzeige.

## Additiver Antwort- und Herkunftsvertrag

Der vorhandene GET `/api/v1/performance/closed-trades` erhält `statistics`:

- `definition_version`: `closed-trade-statistics-v1`.
- `report_basis_id`: exakt die bestehende `report.basis.id`.
- `report_status`: derselbe Status wie `summary.status`.
- `population`: bei `COMPLETE` die positive Zahl `counts.qualified`, bei
  `EMPTY` null Trades (`0`), bei `PARTIAL` / `NOT_COMPUTABLE` unbekannt (`null`).
  Die vorhandenen qualifizierten Teilbestandszähler bleiben separat erhalten.
- `win_rate`, `average_gross_pnl`, `median_gross_pnl`, `gross_profit_factor`:
  jeweils getrennte `raw`, `display` und `reason` (Strings oder `null`).

Statistikdefinition und Berichtsbasis bilden gemeinsam die Provenienz. Die
Statistikdefinition versioniert Berechnungs- und Anzeigepräzisionsregeln.
Der bestehende Finanz-/Quellenfingerprint bleibt unverändert; eine zusätzliche
Anzeige erzeugt keine scheinbare Quellenänderung. Es gibt weiterhin genau
einen vorhandenen Snapshotreaderaufruf, keinen zweiten Owner, Datenbankread,
Provideraufruf oder persistierten Statistikdatensatz.

Die Oberfläche zeigt die Backendwerte und Gründe für den gesamten gewählten
Bericht. Lokale Tabellenfilter und Seiten verändern die Statistik nicht und
lösen keinen Request aus. Auswahlwechsel entwerten alte Antworten samt
Statistik; feste EUR-Formulare, Quellenlinks und Filter-/Seitenrückkehr gelten
weiter. Brutto bedeutet vor Kosten und Steuern. Ergebnisse beweisen weder
gute Einzelentscheidungen noch zukünftige Ergebnisse.

## Vor Implementierung festgelegte Referenzerwartungen

Diese Sollwerte wurden aus den ausdrücklich vorgegebenen Tradebeträgen
festgelegt, bevor produktiver Statistikcode geschrieben wurde. Der Test darf
die Erwartung nicht aus dem zu prüfenden Ergebnis selbst ableiten.

| Rohbeträge | N / positiv / negativ / neutral | Summe | Trefferquote (Anzeige) | Ø / Median (EUR-Anzeige) | Profit-Faktor (Anzeige) |
|---|---|---|---|---|---|
| `100, -50, 0, 200` | 4 / 2 / 1 / 1 | 250 | 50.00 | 62.50 / 50.00 | 6.00 |
| Nach wirksamer Korrektur `200 → 50` | 4 / 2 / 1 / 1 | 100 | 50.00 | 25.00 / 25.00 | 3.00 |
| `10, -4, 0` | 3 / 1 / 1 / 1 | 6 | 33.33 | 2.00 / 0.00 | 2.50 |
| `1.005` | 1 / 1 / 0 / 0 | 1.005 | 100.00 | 1.00 / 1.00 | null, keine Verlusttrades |
| `-2, -4` | 2 / 0 / 2 / 0 | -6 | 0.00 | -3.00 / -3.00 | 0.00 |
| `0, 0, 0` | 3 / 0 / 0 / 3 | 0 | 0.00 | 0.00 / 0.00 | null, keine Verlusttrades |
| `0.004, -0.004` | 2 / 1 / 1 / 0 | 0 | 50.00 | 0.00 / 0.00 | 1.00 |

Zusätzlich gezielt zu prüfen: alle vier Berichtsstatus, fehlende und
widersprüchliche Währungsbelege, Kontext-/Rundungsregeln, unveränderte
Berichtsbasis bei identischen Fakten, ein Snapshot, wirksame Korrektur mit
erhaltener Historie, lokale Seiten/Filter und überholte Antworten.

Der vorhandene native Abschlussberichtfall wird unter identischer Fall-ID
und mit sämtlichen bisherigen Assertions um unabhängige Kennzahlensollwerte
aus seinen eigenen Seedfakten ergänzt. Vorhandene isolierte CI-Stacks, Guards,
Gates, Coveragegrenzen und die übrigen nativen Fälle bleiben erhalten.

Vor der Implementierung separat aus den nativen Seedfakten abgeleitet:

| Native Auswahl | Unabhängige Erwartung |
|---|---|
| T1 mit Lebenszeitbeiträgen `10, 30, -20, 30` | N = 1, Summe 50, Quote 100.00, Ø 50.00, Median 50.00, Profit-Faktor null. |
| T1/T2/T3 mit Ergebnissen `50, -10, 0` | N = 3, Summe 40, Quote 33.33, Ø 13.33, Median 0.00, Profit-Faktor 5.00. |
| Septemberkorrektur erhöht T1 auf 70; T4 ohne Währung bleibt relevant | PARTIAL mit bestehender Teilsumme 60; alle vier Kennzahlen null. |
| Korrigierter T1, vollständige Tagesauswahl 03.10.2026 | N = 1, Summe 70, Quote 100.00, Ø 70.00, Median 70.00, Profit-Faktor null; T4 vom 04.10. ist außerhalb. |
| Ein neutraler Junitrade | N = 1, Quote 0.00, Ø 0.00, Median 0.00, Profit-Faktor null. |
| Juli ungeklärt / Mai leer | NOT_COMPUTABLE / EMPTY mit jeweils vier null und unterschiedlichen Gründen. |

21 zusätzliche offene Trades ändern die Statistik nicht. Der vollständige
Tagesbericht enthält weiterhin sämtliche 27 untersuchten Trades, verteilt auf
lokale Seiten; Filter/Seiten müssen dieselben Kennzahlen ohne erneuten GET und
ohne Datenmutation erhalten.

## Qualifikationsstand und Integrationsübergabe

| Umsetzung / Prüfung | Datei und nachgewiesene Grenze |
|---|---|
| Reine Berechnung / additiver DTO | [closed_statistics.py](../../backend/app/features/performance/domain/closed_statistics.py), [closed_models.py](../../backend/app/features/performance/domain/closed_models.py), [Reportintegration](../../backend/app/features/performance/domain/closed_report.py). Summary und Counts entstehen einmal, Statistik folgt ohne neuen Read. |
| Domain-Referenzen | [test_closed_statistics.py](../../tests/unit/backend/features/performance/test_closed_statistics.py): zentrale Korrektur, Nullzustände, Währungsbelege, Minor Units, HALF_EVEN, Kontextisolation und identische Provenienz. |
| API / ein Snapshot | [test_closed_api.py](../../tests/unit/backend/features/performance/test_closed_api.py): additive Decimalstrings, Zustand und genaue Basisbindung; Reader weiterhin genau einmal pro Bericht. |
| Anzeige / Antwortschutz | [ClosedTradeStatistics.tsx](../../frontend/src/features/performance/components/ClosedTradeStatistics.tsx), [Seitentests](../../frontend/src/features/performance/pages/ClosedTradesPage.test.tsx): vier Backendanzeigen, Rohwerte, Nullgründe, lokale Ansichten/Seiten und veraltete Antworten. Der neue Statistikguard wird nur von der Abschlussseite verwendet; der bestehende Finanz-/Quellenvalidator bleibt unverändert. |
| Native Qualifikation | [Bestehender Abschlussberichtfall](../../tests/e2e/closed-trades-report-postgres.spec.ts): identischer Titel und Fall-ID `2dd5a78c1f224eb1b623-d0bfb041223e2b8fca72`; neue Kennzahlenassertions, Desktop-/Mobilbilder und Read-only-Fenster ergänzen alle alten Nachweise. |

Besonders empfindliche Präzisionsreferenz: Bei Ownerwerten
`[999, -999, 0.4]` und Präzision 3 ist die vorhandene Gesamtsumme `0.4`, der
Durchschnitt `0.133` (Anzeige `0.13`). Eine unzulässige Neusumme nach Sortierung
der Medianwerte wäre null. Ein vor Implementierung festgehaltener Fingerprint
der bestehenden Standardfixture bleibt exakt
`ffb7c92a677b6d6f685388638257aa0a433c12dd9b523f99742b080ead9668b5`.
Auch eine isoliert andere Statistikdefinition ändert keine Finanzquellen-ID.

Am 25.10.2026 lokal tatsächlich ausgeführt:

- **219 Backendtests bestanden**: gesamter Performance-Bereich einschließlich
  24 neuer Statistikfälle und vier zusätzlicher API-Statusfälle sowie bestehende
  Projectortrace- und Währungsresolverprüfungen; Python 3.12.14, unveränderte
  gepinnte Testabhängigkeiten und deaktivierte Provider-/Telegramflags.
- **26 bestehende Abschlussbericht-Verifier-Tests bestanden**. Echte
  Playwright-Sammlung bestätigt genau einen Chromium-Fall mit identischer ID,
  einem Worker und null Retries. Sammlung ist keine native Ausführung.
- Globale Backendprüfungen: Ruff, Black (997 Dateien) und mypy
  (559 Anwendungsdateien) erfolgreich.
- Frontend: Typecheck, vollständiger ESLint-/Prettier-Lauf und Produktionsbuild
  erfolgreich. Die unveränderte Vite-Chunkwarnung ist informativ.
- **78 von 79 gezielten Frontendtests bestanden** unter lokalem Node 24.22.1;
  alle neuen Statistikfälle sind darunter. Der vorhandene Nicht-EUR-Routerfall
  scheitert vor dem API-Aufruf an Node24/Undici/jsdom-`AbortSignal`-Inkompatibilität.
  Derselbe Fehler wurde auf unverändertem Main `b49e87e8` reproduziert
  (16 von 17 ursprünglichen Pagefällen erfolgreich). Die zusätzliche
  Node-22-Binary war lokal nicht lauffähig. Keine Produkt-/Test-/Runneränderung,
  Skip oder Assertionlockerung zur Umgehung; die reguläre Node-22-CI ist der
  erforderliche vollständige Frontendnachweis.

Ein erster eingeschränkter API-Testprozess blockierte im lokalen Sandboxkontext
und wurde beendet; der identische Befehl bestand im genehmigten Kontext. Auch
der lokale Vitest-Prozess wurde für einen sauberen Abschluss im regulären
Kontext ausgeführt. Diese Umgebungsdiagnosen sind keine erfolgreichen Testläufe.

Neu gelesen wurden zu Arbeitsbeginn die tatsächlichen Main-Push-Läufe auf
`b49e87e8`: [Backend 40201534207](https://github.com/burckhju/trading-workspace/actions/runs/40201534207),
[Frontend 40201534202](https://github.com/burckhju/trading-workspace/actions/runs/40201534202),
[End-to-End 40201534220](https://github.com/burckhju/trading-workspace/actions/runs/40201534220),
jeweils erfolgreich. Diese Basisnachweise ersetzen keine neue Statistikprüfung.

Die vollständigen neuen regulären CI-Ergebnisse, tatsächlichen Head-/Tree-/
Testmerge-Bezüge, Artefakte und Bildsichtung werden im Draft-PR dieses Branchs
geführt. Der native Runner verlangt den echten isolierten GitHub-Actions-Stack;
CI-Flags werden lokal nicht gefälscht. Keine Runner-, Gate- oder
Quellenregistrierungsänderung ist erforderlich: bestehende Docker-COPYs nehmen
die neuen Quelldateien mit, Artefaktmanifeste erfassen neue Belege rekursiv.

**Integration:** Main und offene PRs vor Übergabe erneut lesen; zwischenzeitliche
Basisänderungen regulär erhalten und den kombinierten Head qualifizieren.
Gemeinsame PB-019-Dokumentationsstellen mit paralleler Backlogarbeit additiv
zusammenführen. Der Main-/Release-Strang benötigt für diesen neuen PR eine
eigene Mergefreigabe und nach Integration die Prüfungen des tatsächlichen Main.
Version, Tag und PC-Update werden separat koordiniert. Breitere Dashboards,
Export, vollständiges M8 und fachliche Bedienabnahme bleiben offen.
