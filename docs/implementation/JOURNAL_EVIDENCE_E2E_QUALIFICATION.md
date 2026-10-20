# Journal und Review-Evidence: wiederholbare Gesamtqualifikation

Stand: 20.10.2026. Aufgabenstatus bleibt im [Product Backlog](../planning/PRODUCT_BACKLOG.md).
Basis: `main`/`v1.5.11`, Commit `5e9ede2dc29f52eaff601d30614df6bc9c25c426`,
Tree `303e56c078efd578e6e147edcf2ebac6accf6ba5`.

Dieser Schnitt ergänzt ausschließlich die wiederholbare Qualifikation der vorhandenen
FT-012-Journal-/Lesson- und FT-011-Evidence-Strecken. Die fachlichen Owner, API-Verträge,
Migrationen, Gate-Grenzen und der vorhandene Performance-Owner-Job bleiben unverändert.
Die historischen fachlichen Ergebnisse stehen in
[Journal](FT012_JOURNAL_WRITE_QUALIFICATION.md),
[Lesson-Review](FT012_LESSON_REVIEW_QUALIFICATION.md) und
[FT-011-Materialisierung](FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md).
Frühere dort dokumentierte Erfolge sind keine Ausführung dieses neuen Runners.

## Vorab festgelegter Testumfang

Es werden genau die folgenden **zwei bestehenden Fälle** im Projekt `chromium`
ausgeführt, je einmal, mit einem Worker und `--retries=0`:

| Datei unter `tests/e2e/` | Vollständiger Testtitel |
|---|---|
| `post-trade-journal-postgres.spec.ts` | `real PostgreSQL: captured full exit, review, journal, lesson and stale correction` |
| `post-trade-evidence-history-postgres.spec.ts` | `real PostgreSQL: FT011 history survives correction and opens the exact Lesson version` |

`scripts/check-journal-e2e-report.py` gleicht die Discovery gegen diese feste Datei-/Titelmenge
ab und schreibt vor dem Stackstart die tatsächlichen Playwright-IDs in `expected-tests.json`.
Der Ergebnisbericht muss dieselben IDs, Titel, Dateien und das Projekt enthalten. Jeder Fall
braucht genau einen tatsächlich bestandenen Versuch mit `retry=0` und `expectedStatus=passed`.
Globale Fehler, Skips, Flaky-Ergebnisse, erwartete Fehler, fehlende/zusätzliche Fälle und
geschönte Zähler werden abgewiesen. Ein grüner Upload oder ein leeres Testset genügt nicht.

Bestehende fachliche Assertions bleiben erhalten. Ergänzt sind die unabhängige Zielprüfung
vor dem ersten API-Schreibbefehl, die Browser-Sperre externer Requests und quellbezogene
Read-only-Nachweise. Der Journalfall prüft außerdem 19 vorhandene Beobachtungen als noch
unvollständig und erst die zwanzigste als vervollständigenden Datensatz. Der FT-011-Fall
prüft nach dem exakten historischen V1-Link/Reload zusätzlich eine unbekannte Versions-ID
ohne stillen Ersatz durch die aktuelle Lesson-Version. Das sind Erweiterungen derselben
zwei Fälle, keine zusätzlichen Tests oder Wiederholungen.

## Getrennter Sicherheitsvertrag

Einstieg ist `bash scripts/run-journal-evidence-e2e.sh` im Job
`End-to-End / journal and evidence owner` von `.github/workflows/e2e.yml`.
Der Runner verlangt einen tatsächlichen GitHub-Actions-Checkout, eine Run-ID, einen
sauberen getrackten Arbeitsbaum und den lokalen Unix-Docker-Socket. Er ist kein lokaler
Startbefehl für eine Nutzerinstallation. CI-Variablen dürfen nicht gesetzt werden, um
diesen äußeren Guard im Nutzerbetrieb zu umgehen.

- UUID-Projekt `tw-journal-evidence-e2e-<hex>`; neue Datenbank
  `trading_workspace_test_journal_<hex>` und eigenes `postgres-data`-Volume.
  Gefundene Namen oder Projektlabels führen vor Erstellung zum Abbruch. Kein alter
  Stack wird übernommen. Container, beide Netze und Volume tragen zusätzlich dieselbe
  Laufmarkierung `org.trading-workspace.e2e.run-id`.
- Bereinigte Umgebung und eigenes leeres Docker-Konfigurationsverzeichnis; explizit
  `unix:///var/run/docker.sock`; eigene leere Env-Datei und leerer Read-only-Bind-Mount.
  Private `.env`, Credentials, Consent-Zustände und Remote-Docker-Ziele werden nicht geladen.
- Die Compose-Konfiguration wird vor Erstellung geprüft. Nach dem Datenbankstart werden
  tatsächliche Container-, Netz-, Port- und Volumeidentitäten vor Migration/Markierung
  geprüft; danach erneut alle drei gesunden Dienste und der tatsächliche Backend-DB-URL.
  Die DB erhält den exakten Kommentar `synthetic journal-evidence browser <run-id>`.
- Backend ausschließlich im internen Netz, ohne veröffentlichte Ports. Nur Datenbank
  und Frontend gehören zusätzlich zum eigenen Ingress-Netz; DB-Port `127.0.0.1:25432`,
  Frontend-Port `127.0.0.1:8080`. Provider, Refresh, Monitoring und Telegram sind deaktiviert.
  Das interne Backend-Netz sperrt externe API-Ausgänge; Browserrequests außerhalb des
  kanonischen Ursprungs werden abgefangen und machen den Test rot. Die separate
  APIRequestContext-Strecke prüft den Ursprung vor jedem GET/POST und setzt
  `maxRedirects: 0`; lokale Antworten können dadurch keine externen Weiterleitungen
  auslösen. Service Worker sind in diesen beiden Fällen blockiert.
- Der vorhandene Browserursprung bleibt `http://localhost:8080`, der Testbuild verwendet
  `http://localhost:8080/api`. Nginx entfernt ein `/api/`; der tatsächliche API-Pfad bleibt
  deshalb `http://localhost:8080/api/api/v1`. Keine Produktions-CORS- oder Proxyänderung.
- Der unabhängige Host-DB-Guard verlangt eine Verbindung zu genau `127.0.0.1:25432`, dem
  laufgebundenen Datenbanknamen und Benutzer `tw_journal_e2e`, identische konfigurierte
  Test-/App-Ziele, passenden DB-Kommentar, PostgreSQL 17 und genau Head `20261017_0047`.
  Die tatsächliche `workspaces`-Menge muss genau den vorhandenen synthetischen Workspace
  `00000000-0000-4000-8000-000000000001` enthalten; sämtliche gefundenen `workspace_id`-
  Spalten müssen ebenfalls zu ihm gehören. Der erste Laufbestand enthält
  keine Trades, Executions, Journale, Evidence oder Lessons. Ein Container-Healthcheck
  allein ersetzt weder diesen Host-Verbindungsnachweis noch den Host-API-Readiness-Aufruf.

Erst nach den tatsächlichen Stackprüfungen setzt der Runner die beiden expliziten
Schreibflags für seine Guard-/Browserprozesse. Beide Browserfälle und der Preis-Seed
prüfen den DB-Marker nochmals unabhängig. Der bestehende synthetische Preis-Helper
wird mit seinem erlaubten Testnamen-Präfix weiterverwendet. Es werden ausschließlich
klar bezeichnete Preisbeobachtungen geseedet; tatsächliche BUY/SELL, Korrekturen, Review,
Journal, Evidence und Lesson entstehen über die vorhandenen Owner-APIs. Die bestehenden
EXTERNAL-Captures sind eigene ausdrücklich erfasste Ausführungen; keine SQL-Umschreibung
einer Herkunft und keine neue Performancepflicht für den Lernweg.

## Artefakte und Cleanup

Der neue Job archiviert unter `frontend/test-results/journal-evidence-<run>/`:

- tatsächlichen Checkout, Tree, Workflow-SHA/-Run sowie Projekt-/DB-/Laufidentität;
- geprüfte Konfiguration und tatsächliche Netz-/Container-/Volume-/Loopbackportidentitäten;
- Migrationslog, unabhängigen initialen Host-DB-Nachweis und Host-API-Readiness;
- vorherige Test-Discovery, festgelegte IDs, vollständigen JSON-Report und dessen Prüfung;
- Erfolgstraces und Screenshots an den jeweiligen `testInfo.outputPath`-Pfaden;
- synthetische Journal-/Evidence-/Lesson-Antworten mit exakten Quell-IDs und DB-Fingerprints;
- Containerlog, Cleanup-Log, maschinenlesbares `cleanup.json`, Ergebniscode und `SHA256SUMS`.

Fingerprints entstehen in kurzen `REPEATABLE READ READ ONLY`-Transaktionen. Verglichen
werden ausschließlich die dedizierten lesenden Journal-/Evidence-/Lesson-API-Fenster am
Ende der Fälle. Absichtliche Owner-Buchungen, Korrekturen und Preisfixtures liegen außerhalb
dieser Fenster. Ein gleicher Fingerprint behauptet weder globale Serialisierbarkeit des
Lernbereichs noch einen unveränderlichen Gesamtbestand über bewusste Schreibaktionen hinweg.

Cleanup läuft auch nach Fehlern. Vor Löschung muss jede gefundene Projektressource die
exakte Laufmarkierung besitzen. Anschließend entfernt ausschließlich das eigene Compose-
Projekt seine Ressourcen. Container-, Netz- und Volumelisten werden erneut abgefragt;
verbleibende Ressourcen oder Abfrage-/Cleanupfehler verhindern ein grünes Ergebnis.
Es gibt keinen globalen Prune und kein Entfernen fremder Volumes.
Bei Auswertung heruntergeladener Artefakte sind ZIP-Digest und `SHA256SUMS` zu prüfen,
Report und Cleanup inhaltlich zu lesen und die Screenshots tatsächlich anzusehen.

## Trigger und aktuelle Nachweisgrenze

Der neue Job ergänzt bestehende PR-Prüfungen und später passende Main-Push-Prüfungen.
Neue Runner-/Verifier-/Guardtest-Pfade sind ausdrücklich im Main-Push-Filter enthalten;
`tests/e2e/**` erfasst beide Fälle und ihre Helfer. Bestehender Smoke und Performance-Job
behalten ihre Gates und Schreibgrenzen. Ein PR ist noch keine Workflow-Auslieferung auf Main.

Lokal auf Python 3.12.14 wurden **57 gezielte Guard-/Reporttests** erfolgreich ausgeführt,
einschließlich negativer Laufidentitäts-, Port-, Netz-, Credential- und Ergebnisfälle.
Diese Unitfälle simulieren Konfiguration und Reportdaten; die tatsächlichen SQL-Marker-,
Schema- und Workspace-Prüfungen benötigen weiterhin den nativen Job.
Ruff 0.15.1, Black 26.1.0, Bash-Syntax und `git diff --check` wurden gezielt geprüft.
Mit Node 22.16.0/npm 10.9.2 und unverändertem Lockfile wurden beide tatsächlichen
Playwright-Testidentitäten erfolgreich entdeckt und durch den Verifier gepinnt;
**9 separate Node-Unitfälle** prüfen den API-Origin-Guard und deaktivierte Redirects.
Das ist ein Discovery-Nachweis, keine Browserausführung. Ein vorheriger lokaler Aufruf
scheiterte an einer unvollständigen Tool-Runtime vor Testbeginn; die reparierte, verifizierte
Runtime wurde für den genannten erfolgreichen Discovery-Lauf verwendet.

**Der native Gesamtabschluss dieses neuen Jobs ist noch nicht nachgewiesen.** Lokal fehlen
Docker/PostgreSQL. Bis ein konkreter CI-Lauf beide Fälle ohne Skip/Flaky/Retry sowie
erfolgreichen Cleanup belegt, bleibt Paket 3 in technischer Qualifikation. Die alten
Journal-/FT-011-Erfolge und die neuen Unit-Erfolge werden nicht als neue Gesamtzahl addiert.
Auch vollständige aktuelle Backend-/Frontend-/Smoke-Gates sind getrennt nachzuweisen.

Der statische `execute-as-trade`-Hinweis aus PB-016 wurde nicht durch zwei reale
PostgreSQL-Sessions reproduziert. Der Service hält Trade/Execution/Währung/Link/Receipt
atomar in einer UOW; der mögliche erstmalige Unique-Constraint-Konkurrenzfall bleibt ein
eigenständiger Reproduktionsauftrag. In diesem CI-Schnitt erfolgt dafür kein Produktfix.
Keine neue Migration, Releaseversion, Modellaktivierung, Providerfreigabe, echte Nachricht,
PC-Installation oder Änderung realer Nutzerbestände.
