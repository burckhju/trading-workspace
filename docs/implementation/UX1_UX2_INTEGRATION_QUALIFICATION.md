# Gemeinsame Qualifikation von UX1 und UX2-A

## Umfang und nachvollziehbare Ausgangspunkte

Der Nutzer hat am 01.11.2026 die Umsetzung, den Merge bei grünen Prüfungen und
die Freigabe für den vorhandenen PC-Updater ausdrücklich beauftragt. Eine
Installation auf dem PC oder eine fachliche Abnahme wird damit nicht behauptet.

Dieser kontrollierte Integrationsschnitt führt folgende geprüfte Featurestände
zusammen, ohne deren Branches gegenseitig zu überschreiben:

| Quelle | Commit | Beitrag |
| --- | --- | --- |
| UX2-A, [#311](https://github.com/burckhju/trading-workspace/pull/311) | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Gemeinsame Trade-Navigation, vorhandene Bereichsowner, historische Pins, Plan-/Lesson- und getrennte Berichtsrückwege |
| UX1, [#312](https://github.com/burckhju/trading-workspace/pull/312) | `b1df1c1000815786a6623d35bf3f8631661a9543` | Belegte Währungsvorschau für explizite Käufe/Verkäufe, manuelle Overrides, Zeitzonenvorschlag und öffentlicher BUY-Adapter |
| Koordination, Main bei Beginn | `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` | Verbindliche [Shared Contracts](../coordination/UX_SHARED_CONTRACTS.md) und [Abhängigkeiten](../coordination/UX_DEPENDENCIES.md) |
| Main nach #317, erste Integrationsbasis | `28c03f939eb24e3c79dee235c28dadf3fd299f54` | v1.5.36, inzwischen durch den automatischen Publisher veröffentlicht |
| Main nach #316, zweiter Basisstand | `5f2e12667759bfb54eb14f39c6d8426c9cd8080f` | Sechs zusätzliche UX4-Dokumente; kein Produktcode-, Test-, Workflow- oder Versionswechsel |
| Main nach #314, aktuelle Integrationsbasis | `d80bd45d84d845aa920a7eac5b19a7fe6cd63307` | Kanonischer UX3-Dokumentationsvertrag; beide getrennten UX2-/UX3-Backloghunks bleiben erhalten |

Die eigenständige Koordinationsveröffentlichung v1.5.36 aus #317 wird zuerst
abgeschlossen. Der gemeinsame Produktstand erhält v1.5.37 auf dem dann aktuellen
Main. Der erste Integrationscommit erhält Main als ersten Parent und beide genannten
Featureheads als weitere Parents. Die spätere Mainaktualisierung erhält diesen
Integrationscommit als zusätzlichen Parent. Der PR dokumentiert tatsächlichen Head,
Mainbasis, von GitHub ausgecheckten Testmerge und dessen Tree. Alte einzelne
Feature-CI ersetzt diese gemeinsame Qualifikation nicht.

Während der gemeinsamen CI wurde #316 parallel gemergt. Der kontrollierte
Mainabgleich übernimmt alle sechs Dokumente vollständig; Produktcode, Tests und
Workflows stimmen weiterhin mit dem ursprünglichen Integrationshead
`5fe89ab1f3db171ef42366ac45193ce045de2caf` überein. Die strikte Branchregel
verlangt trotzdem neue reguläre Prüfungen am aktualisierten Head/Testmerge.
Die vorherigen grünen Frontend-/E2E-Ergebnisse werden nicht als Nachweis dieser
neuen Mainbasis ausgegeben.

Während dieses zweiten Laufs wurde außerdem #314 in Main integriert. Der erneute
konfliktfreie Abgleich erhält dessen 13 Dokumentdateien, einschließlich isolierter
Dokumentationstypprüfungen, vollständig. Der Produktbacklog enthält danach die
UX2-Navigationseinträge und die fachlich getrennten UX3-Vertragseinträge.
Anwendung, fachliche Tests, Workflows und Versionen bleiben gegenüber dem ersten
gemeinsamen Integrationshead identisch. Maßgeblich ist die erneut gestartete CI
auf der jetzt aktuellen Mainbasis; ältere Läufe werden getrennt dokumentiert.

Die vollständige Navigations-/Komponentenmatrix und die getrennte Vorbereitung
von UX2-B bis UX2-D stehen weiterhin in
[UX2 Trade-Arbeitsbereich](../ui/ux2-trade-workspace.md). Deren umfangreichere
Darstellungsänderungen sind nicht Bestandteil dieses Schnitts. UX3-/UX4-Entwürfe
und andere offene Produkt-PRs werden nicht vorgezogen.

## Kleine gemeinsame Integrationsänderungen

### Eine gemeinsame Zeitzonenprüfung

Der einzige textuelle Zusammenführungskonflikt lag in
`performance/services/performanceReportContext.ts`. Die vorhandene UX1-Funktion
`reportTimezoneError` liegt jetzt einmalig in
`shared/trade-workspace-navigation/realizedReportNavigation.ts` und wird über
den öffentlichen Shared-Index exportiert. `reportFiltersErrors` verwendet genau
dieselbe Funktion. Funktionskörper, Fehlertexte, zulässige IANA-Zonen und
Ablehnung fester Offsets bleiben unverändert.

`initialPerformanceFilters` und der Zugriff auf die Browserzone bleiben im
Performance-Feature. Eine gültige explizite URL-Auswahl hat Vorrang; ungültige
oder doppelte Parameter werden nicht still durch Browserwerte ersetzt.
Finanzielle Antwortprüfungen bleiben beim Performance-Owner. Shared importiert
kein Feature und ermittelt selbst keine Browserzone.

### Öffentliche Erstkaufgrenze

`trade/public/InitialPurchaseCurrencyPreview.tsx` ist der schmale öffentliche
BUY-Adapter. Die Props sind ausschließlich Produkt-ID, Datum, Uhrzeit,
kontrollierter Währungsentwurf, dessen Änderungscallback und optional `disabled`.
Der Adapter setzt intern BUY fest und delegiert an die bestehende Preview.
Er besitzt keinen eigenen State, Reader, Resolver oder Schreibpfad.

UX1 hat diese Grenze während der gemeinsamen Vorbereitung auf seinem eigenen
Branch nachgeliefert. Übernommen werden dessen kanonischer Adapter, sieben
öffentliche Tests, Consumer und Capture-Vertrag. Eine parallel vorbereitete
gleichwertige Adapterfassung wurde dadurch ersetzt, nicht zusätzlich integriert.

ProductSelection importiert den Adapter über `../../trade`. Entwurf und
bewusste Kaufbuchung bleiben dort; der Trade-Owner besitzt Herkunftsread,
Abortschutz und Retry. Die bestehende Capture-Payload bleibt unverändert:
Eine erfolgreiche Vorschau erzeugt keine `currency_confirmation` und trägt
keinen Währungscode in den manuellen Entwurf ein.

### Gemeinsamer Host

Die automatisch zusammengeführte `TradeManagementPage` erhält sowohl UX2s
Navigation/Anker als auch UX1s Preview-/Reloadhunks. Die Produktionskomponenten
für Erstkauf, Nachkauf, Verkauf, Korrektur und Storno behalten ihre fachliche
Semantik. Es wird kein zusätzlicher Positions- oder Timeline-Owner eingeführt.

`historyReloadToken` steigt erst nach erfolgreichem, aktuellem und
identitätsgeprüftem Parent-Readback. Daneben behält die Vorschau ihre vorhandene
Invalidierung durch bestätigte `trade-timeline-changed`-Events nach Writes.
Diese eigenen Evidence-Reads verändern keine manuellen Eingaben. Hashwechsel
erzeugen weder dieses Event noch einen Readbacktoken.

## Reproduzierbare gemeinsame Nutzerwege

| Nutzerweg | Nachweis und erwartetes Verhalten |
| --- | --- |
| Trade auswählen, SELL und Kaufkorrektur gleichzeitig bearbeiten | `trade-workspace-navigation.spec.ts`: 390 und 1280 CSS-Pixel, Datum/Menge/Preis, manueller CHF-Code und Beleg bleiben über vier per Tastatur bediente Bereichswechsel erhalten |
| Herkunft lesen, ohne Währung erneut einzugeben | Erfolgreiche EUR-Vorschau und historische Quelle sichtbar; manueller Code zunächst nicht vorbelegt; anschließend bewusst eingegebene Werte bleiben vorrangig |
| Bereich wechseln | Exakte Query einschließlich historischer Pins und kodierter Trade-ID bleibt erhalten; Fokus folgt dem Bereich; die vollständige Liste aller GETs bleibt unverändert, einschließlich Preview |
| Quellen-/Journalseite verlassen und Reload | Ein bestehender zentraler Verwerfguard; Escape/Hier bleiben erhält Entwurf, native Reloadwarnung bleibt wirksam |
| Preview-Quelle nicht erreichbar | Eigener 503-Fall zeigt Readfehler, keine erfundene Währung; manueller Entwurf bleibt über Bereichswechsel und ausdrücklich ausgelösten Retry erhalten |
| Datum A → B → A, alte Antwort kommt zuletzt | Je ein Browserfall für alten Erfolg und Fehler; nur neueste EUR-Herkunft sichtbar, keine alte USD-/GBP-Anzeige und keine überschriebenen manuellen Werte |
| Produkt/Trade wechseln, späte Antworten | Bestehende Preview-/Hosttests plus neuer Public-Adaptertest prüfen Scope, Abort und A → B → A; der Adapter besitzt keine zusätzliche Lebensdauerverwaltung |
| Gebundene historische Planversion öffnen | Bestehender Browserpfad liest freigegebene P1 trotz neuerem Entwurf P2; kopierte URL, Reload und Rückweg erhalten Trade-/Review-/Journalbezüge |
| Performance → Buchungen → Quellen → Bericht | Vorhandener SELL-Rundweg erhält Filter, Seite und Basis; Abschluss-/SELL-Kontexte und ihre Validierungen bleiben getrennt |
| Readback und Busy | Bestehende Host-/PriceHistory-/Capturetests prüfen parallele Drafts, Busy, bestätigte Writes mit fehlgeschlagenem Readback und Ausschluss überholter Antworten |
| Tatsächliche Buchungskette | `execution-currency-reuse.spec.ts` muss im regulären PostgreSQL-E2E-Job Erstkauf → Nachkauf → Teilverkauf und Quellenkorrektur ausführen; lokale abgefangene Reads sind dafür kein Ersatz |

Die Navigationstests intercepten jeden API-Request, lassen nur GET zu und
protokollieren unerwartete Writes als Fehler. Ihre synthetischen Belege sind
Browserfixtures, kein Nachweis echter Providerqualität. Initiale Mountreads
werden nicht mit zusätzlichen Reads bei Bereichswechseln verwechselt. Gezielt
geänderte Previewreads werden zusätzlich anhand Endpoint, Trade-ID, SELL,
Berlin-Zone und Datum geprüft.

## Lokale Prüfungen und verpflichtende CI

Lokale Laufzeit: Node 22.16.0, npm 10.9.2, Python 3.12.14; Frontendtests unter
UTC, Browserfälle ausdrücklich unter Europe/Berlin. Chromium entspricht dem
festgeschriebenen Playwright 1.55.0.

| Prüfung | Lokaler Nachweis |
| --- | --- |
| Gesamte Frontend-Suite mit CI-Coveragegrenzen | 1.978 Tests in 164 Dateien am kanonischen UX1-Adapterstand; 95,95 % Statements/Lines, 90,31 % Branches, 91,35 % Functions |
| Gemeinsame Navigation im Browser | 13 Fälle, darunter erfolgreiche Vorschau auf beiden Breiten, separater Fehler/Retry und zwei verspätete Antworten |
| Gesamte TradePosition-Unit-Suite | 406 Tests; eine bestehende Starlette/AnyIO-DeprecationWarning |
| Helper-/Performance-Grenze | 210 gezielte Tests; zusätzlich in der Gesamtsuite enthalten |
| Öffentlicher BUY-Adapter und ProductSelection | Alle sieben öffentlichen Owner-Adaptertests und die bestehenden ProductSelection-Kontext-/Capturefälle in der Gesamtsuite erfolgreich |
| Frontend-Qualität | TypeScript, ESLint ohne Warnungen, Prettier und Produktionsbuild erfolgreich; vorhandener Vite-Hinweis auf große Chunks bleibt unverändert |
| Backend-Qualität | Ruff erfolgreich, Black prüft 1.027 Dateien, mypy prüft 570 Quelldateien ohne Befund |
| Veröffentlichungsschutz | 9/9 bestehende JavaScript-Tests bestanden, keine Skips |

Die 13 Browserfälle wurden zusätzlich mit dem API-Präfix der CI ausgeführt.
Die Endpointprüfung toleriert dessen äußeren Proxy-Prefix, prüft aber weiterhin
den exakten Trade-Endpunkt, SELL, die Berlin-Zone und das Ausführungsdatum.

Reproduzierbare Befehle aus `frontend`:

```sh
npm ci
npm run typecheck
npm run lint
npm run format
npm run test:coverage -- --coverage.thresholds.lines=80 --coverage.thresholds.functions=80 --coverage.thresholds.statements=80 --coverage.thresholds.branches=70
npm run build
npm run e2e -- ../tests/e2e/trade-workspace-navigation.spec.ts --workers=2
```

Der Browserbefehl erwartet die bestehende Testoberfläche unter
`PLAYWRIGHT_BASE_URL` (Standard `http://127.0.0.1:8080`) sowie den installierten
Projektbrowser. Lokal kann der vorhandene Vite-Server mit vollständig
abgefangenen API-Fixtures verwendet werden.

Backend aus `backend`:

```sh
python -m pip install --requirement requirements-dev.txt
PYTHONPATH=.:.. pytest -c pyproject.toml ../tests/unit/backend/features/trade_position
ruff check app ../tests/unit/backend ../tests/integration/backend
black --check --config pyproject.toml app ../tests/unit/backend ../tests/integration/backend
mypy app
```

Lokal steht kein Docker-/PostgreSQL-Dienst zur Verfügung. Deshalb bleiben die
vollständigen regulären GitHub-Jobs verpflichtend: Backend mit 85-%-Grenze und
allen drei PostgreSQL-Previewtests, Frontend, E2E-Smoke, Performance- und
Journal/Evidence-Owner-Jobs, Candidate-Governance-Owner-Job, restriktives Image,
Renderersandbox und Veröffentlichungsschutz. Workflow, Auswahlregeln und
Qualitätsgrenzen werden nicht verändert. Exakte Lauf-IDs und Testmergebelege
werden nach Abschluss im Integrations-PR nachgetragen.

## Fachliche Schutzregeln und Freigabestufen

BUY-/SELL-Verarbeitung, Mengen, Average Cost, realisierter Bruttobeitrag,
Korrekturen und Storno bleiben unverändert. Die Vorschau verwendet vorhandene
Resolver in einer lesenden Transaktion; aktuelle Produktnotierungen bestätigen
keine historische Ausführungswährung. Unbekannte oder widersprüchliche Quellen
bleiben entsprechend gekennzeichnet. Keine neue Pflichtangabe, Migration,
Planfreigabe, Journalentscheidung, Provideraktivierung oder Handelsentscheidung.

Die Source-, Report- und Previewreads bleiben eigenständige Ownerreads und
bilden durch die gemeinsame Anzeige keinen atomaren Finanzsnapshot. Charts
verwenden weiterhin ausschließlich vorhandene Kursbeobachtungen und deren
qualifizierte Ereigniszuordnung.

Implementierung, lokale Prüfung, PR-Qualifikation, Main-Merge, veröffentlichter
Tag, PC-Installation und fachliche Abnahme werden getrennt nachgewiesen.
Main-Push-CI und automatischer Tag müssen nach dem autorisierten Merge noch
auf genau dem aktuellen Releasecommit erfolgreich sein. Der PC erhält erst
danach einen Updatebefehl mit vollständigem, verifiziertem SHA.
