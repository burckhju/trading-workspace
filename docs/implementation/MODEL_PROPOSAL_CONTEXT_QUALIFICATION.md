# Strang B — Proposal-Kontextintegrität

Technischer Qualifikationsnachweis vom **24. Oktober 2026, Europe/Berlin**.
Dies ist kein zweites Backlog. Aufgabenstatus bleiben ausschließlich in
[PB-020 Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance) und der
[bestehenden Candidate-Familie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family).

## Ausgangspunkt und Umfang

- Repository: `burckhju/trading-workspace`.
- Verifizierter Main: `2887d39b7a54117d362fdc9d3dacd76f35980878`.
- Vollständiger Basistree: `215f17c359976d818dee73e463fb0f3f6af16013`.
- Unveränderte Versionswerte: `1.5.13`.
- Eigener Branch: `fix/model-proposal-context-isolation`, separater Clone und
  zusätzlicher unveränderter Baseline-Worktree. Kein fremder Branch als Grundlage.
- Die aktuelle Suche unter allen offenen PRs fand keinen passenden
  Proposal-Isolationsnachfolger. PR #204 gehört weiterhin zu Strang A.
- Im aktuellen Checkout wurden keine anwendbaren `AGENTS.md` gefunden.

Produktionsänderung ausschließlich in
`frontend/src/features/model/components/HypothesisProposalPanel.tsx`.
Der Parent, globale Router-/Layoutdateien, `frontend/src/features/market/`,
`Application.test.tsx`, gemeinsame `ApiFeedback`-Hilfen, Backend-Produktionscode,
Migrationen, Dependencies, Lockfiles, Versionsdateien und Workflows bleiben
unverändert. Die bestehenden fünf Candidate-Komponententests bleiben unverändert.

Zusätzliche Testdateien:

1. `frontend/src/features/model/components/HypothesisProposalPanel.isolation.test.tsx`
2. `tests/e2e/model-proposal-isolation.spec.ts`
3. `tests/integration/backend/learning/test_ft020_proposal_context.py`

Dokumentation: dieser Bericht, der passende FT-020-Kontextabschnitt, ausschließlich
die Test-/Commitfelder der beiden oben verlinkten PB-020-Einträge sowie ein klar
bezeichneter Strang-B-Nachtrag in `TRACEABILITY.md`. Die markierte historische
Traceability-Baseline und alle Lifecycle-/Arbeitsstatusfelder werden erhalten.

## Befund und rote Reproduktion

Die neuen Componenttests wurden mit exakt demselben Testinhalt zunächst gegen die
unveränderte Baseline ausgeführt. Der tatsächliche Source-Blob des alten Panels ist
`1ed2d3dbff1e7329fe2d33e3115816c0b4f67852`; er stimmt mit dem Blob aus Main überein.

Die entscheidenden Abweichungen sind beobachtet, nicht nur aus Code vermutet:

- Nach vollständigem H1/M1/B1 und Wechsel zu M2 mit offenem Versionsread sendet ein
  programmatischer Submit **M2 zusammen mit B1 und der alten Rationale**. Das gilt
  auch bei unmittelbar aufeinanderfolgenden Events vor dem nächsten Render.
- Ein verspäteter erfolgreicher M1-Read überschreibt die bereits geladene M2-Basis.
  Auch M1→M2→M1 und eine vor Abort bereits erfüllte Promise benötigen Besuchsbindung.
- Zwei synchrone Submit-Events senden auf Main zwei gleiche POSTs.
- Synthetische H-Propwechsel derselben Component können alte Reads/Saves übernehmen.
  Diese Experimente werden ausdrücklich vom tatsächlichen keyed Parent getrennt.
- Fehlerhafte/fehlende/vermischte Basisantworten, fehlende IDs und unerwartete
  Create-Response-Identitäten werden durch den alten Eventhandler nicht vollständig
  gesperrt. Reine Button-/HTML-required-Prüfungen reichen nicht aus.

Die Browserreproduktion verwendet den bestehenden Weg
`/lessons/:lessonId` → `LessonDetail` → `LessonHypothesisPanel` → Proposal-Dialog.
Desktop und Mobil zeigen denselben M2/B1-Payload. Im Screenshot stehen neues
Modelllabel, alte Basis, alte Definition und alte Rationale gleichzeitig im
speichernden Dialog. Alle HTTP-Antworten sind synthetisch; der gehaltene POST ist
**kein Nachweis beschädigter persistierter Nutzerdaten**.

### Bereits funktionierende Grenzen

14 der 46 neuen Componentfälle bestehen bereits auf Main: alter Versionsfehler
einschließlich Finally, Erhalt des Drafts bei aktuellem Savefehler mit bewusster
Wiederholung, kein automatischer POST nach unklarem Abschluss mit Readback bei
Rückkehr, ungültige JSON-Syntax, acht Candidate-Fachfälle sowie beide Fälle mit
altem Save nach echtem keyed Parent-Unmount.

Der tatsächliche Lesson-Router bindet `LessonDetail` an Lesson/Version; der Parent
bindet Hypothesenartikel an `hypothesis.id`. Ein alter H1-Save übernimmt dadurch
schon auf Main weder H2-Eingaben noch dessen Fehlerzustand. Die beiden umfassenderen
Browserfälle scheitern auf Main erst an einem erneuten programmatischen Submit
während des noch laufenden H2-Saves. Aus der Parentprüfung entsteht **kein
zusätzlicher Parent-/Router-Reparaturauftrag**.

## Enger Fix und bewusste Bedienentscheidung

| Bindung | Umsetzung und Zweck |
|---|---|
| Hypothesenbesuch | Intern keyed Form; Layout-Cleanup entwertet die Instanz vor passivem Cleanup. Ein zurückgekehrtes H1 erhält keine Schreibberechtigung einer früheren H1-Operation. StrictMode-Reads bleiben getrennt. |
| Modell-/Versionsladung und Basisdraft | Jede echte Modellauswahl erhält synchron eine neue Objektidentität. Basis, Versionen, Definition, Policy und Rationale werden sofort entkoppelt. Ein eigener Basisdraft schützt auch Basiswechsel vor dem nächsten Render. |
| Bewusster Submit | Vollständiger Handler-Guard, einmaliger Payload-Snapshot und synchrone `saveRef`-Sperre vor dem ersten `await`. Erfolg, Fehler und Finally gehören genau dieser Operation. |

Eine Basis ist erst verwendbar, wenn die aktuelle Initial- und Versionsladung
erfolgreich ist, das Modell im geladenen Katalog existiert und die ausgewählte
Version zur aktuellen Auswahl gehört, eine nichtleere ID besitzt und APPROVED ist.
Eine Versionsliste mit fremdem Modellbezug oder doppeldeutigen IDs wird insgesamt
abgewiesen. Leere Listen oder Ladefehler erzeugen keine Ersatzbasis. Die bestehende
Auswahlkonvention `approved.at(-1)` bleibt erhalten; sie ist keine Aussage über die
aktive Runtime-Version und kein Aktivierungsbefehl.

**Resetstrategie:** Ein echter Modell-/Basiswechsel leert gebundene Eingaben; der
Dialog erklärt das sichtbar. Ein normales Rerender oder eine äquivalente Auswahl
erhält Rationale und Definition. Es gibt keinen globalen Draftstore.

**Savestrategie:** Modell, Basis und Draftfelder sind während des Saves gesperrt,
auch in ihren Handlern. Ein echter Seiten-/Hypothesenwechsel bleibt möglich. Der
alte Request kann serverseitig trotzdem abschließen; er wird nicht als storniert
bezeichnet. Seine Antwort verändert keinen neuen Dialog und entsperrt keinen
neueren Save. IDs und DRAFT-Status der aktuellen Create-Response werden vor
Anzeige und Übergabe an `ProposalValidationPanel` geprüft.

Aktuelle Fehler behalten die Eingaben. Es gibt keine automatische POST-Wiederholung
und keinen erfundenen Idempotency-Key. Das bewusste Wiederöffnen/Neuladen der
bestehenden Lesson-Seite liest vorhandene Proposals zurück. Die UI-Sperre ist keine
serverweite Exactly-once-Zusage über Tabs, Reloads oder Netzwerkabbrüche.

## Erhaltener Fachvertrag und native Grenze

Pflichtquellen wurden in ihrem aktuellen Zusammenhang gelesen: FT-013, FT-019,
FT-020, Proposal-/Hypothesenclients und Typen, tatsächliche Lesson-Seite,
`requestJson`/Abortverhalten, Proposal-API, `ModelGovernanceService`,
`RuntimeActivationService`, Candidate-Runtimeadapter sowie
[ADR-FT019-001](../decisions/ADR-FT019-001-CANDIDATE-DEFINITION-SEMANTIC-VERSIONING.md).
Die historische FT-013-V1-Aussage ohne Aktivierungs-API wird nicht auf den späteren
FT-019/020-Vertrag übertragen: APPROVED und explizite Runtime-Aktivierung bleiben
getrennt.

- V1 wird weder verändert noch umgedeutet. Unterstützte Policyänderungen erzeugen
  ausschließlich explizites `TOP_DOWN_CANDIDATE/2.0`, LONG, mit den zwei bestehenden
  Policies. Beide V2-Richtungen und V1→V2 sind als vollständige Create-Payloads geprüft.
- No-op, unbekannter Schlüssel, fehlender Parameter, unbekanntes Schema und
  nicht unterstützte Richtung bleiben im spezialisierten Editor gesperrt.
- Allgemeine Nicht-Candidate-Erfassung behält JSON-Objekte bei; `null`, Arrays,
  Syntaxfehler und leere Rationale erzeugen keinen POST. Keine neue JSON-Engine oder
  Ausführung von Ausdrücken, Python, SQL, URLs oder Befehlen.
- Preview beschreibt ausschließlich das vorhandene Kriterium. Keine Rendite-,
  Backtest- oder Überlegenheitsaussage.
- Create bleibt DRAFT. Browserfixtures behandeln jeden unerwarteten Request,
  insbesondere Validation-/Approval-/Activation-Schreibaufrufe, als Fehler.

Der bestehende `create_proposal()` prüft Workspace/Modell, genaue Modell/Basis-
Zuordnung, APPROVED und gültige nicht geschlossene Hypothese vor dem ersten Insert
oder Hypothesenstatuswechsel. Ein M2/B1-UI-Kommando wird daher schon serverseitig
abgewiesen. Die Suche fand gültige native FT-013-/FT-019-Ketten, aber keinen direkten
Fehlzuordnungs-/Partial-Persistenznachweis. Die neue PostgreSQL-Regression ergänzt
ausschließlich diesen Nachweis auf unveränderter Produktionslogik:

`test_foreign_proposal_base_is_rejected_without_partial_governance_facts`

Zwei synthetische Modelle mit verschiedenen Fachschlüsseln und genehmigten Basen;
falsches Paar → ValueError, unveränderte Versions-/Proposal-/Validation-/Approval-/
Activationfakten und Hypothese OPEN. Anschließend gültiger Create → genau ein DRAFT
mit denselben gebundenen IDs/Definition/Rationale, Hypothese PROPOSED, unveränderte
Basen und keine zusätzliche Validation/Freigabe/Aktivierung.

## Tatsächlich ausgeführte lokale Prüfungen

Node **22.16.0**, npm **10.9.2**, Vitest **3.2.0**, Playwright **1.55.0** /
Chromium **140.0.7339.16 (build 1187)**. Python **3.12.14**, Ruff **0.15.1**,
Black **26.1.0** für den neuen nativen Test. Pins, Assertions, Coveragegrenzen,
Retries und Timeouts im Repository unverändert.

| Prüfung | Ergebnis |
|---|---|
| Neue Componentfälle gegen unveränderten Main | 46: **32 rot, 14 bereits grün**, 0 übersprungen |
| Dieselben Fälle plus fünf unveränderte Candidatefälle mit Fix | **51/51 grün**, 0 übersprungen |
| Browser gegen Baseline, Desktop/Mobil/echter Router | 7: **5 rot, 2 bereits grün**, 0 Skip/Flaky/Retry |
| Exakt dieselben Browserfälle mit Fix | **7/7 grün**, 0 Skip/Flaky/Retry |
| Vollständiges `bash scripts/check-frontend.sh` | **716/716 Tests in 117 Dateien**; TypeScript, ESLint, Prettier, unverändertes Coverage-Gate und Build erfolgreich |
| Frontend-Coverage Statements / Lines / Functions / Branches | **93,43 / 93,43 / 86,18 / 85,43 %** |
| Neuer nativer Test, statische Prüfung | Python-AST, gepinnter Ruff und Black erfolgreich |
| `git diff --check` | Erfolgreich |

Alle sieben Browser-API-Verträge verwenden den tatsächlichen Build-Präfix
`/api/api/v1` und haben `unexpected=[]`. Die Baseline verwendet Port 28181, der
grüne statische Build Port 28182 und ein eigenes Buildverzeichnis. Keine echte
Backendquelle oder Produktivdatenbank wird dabei angesprochen. Exakte IDs,
Payloads, Aufrufzahlen und fehlende automatische Nebenwirkungen stehen in den
API-Reportattachments. Desktop-/Mobilbilder wurden geprüft; der kleine beobachtete
Überlauf der nachfolgenden unveränderten Lesson-/Validationansicht ist kein neuer
globaler Layoutauftrag.

### Reproduktionsdateien und Prüfsummen

Die JSON-Rohreports sind Laufartefakte, keine zweite Aufgabenstatusquelle.

| Rohreport | SHA-256 |
|---|---|
| `proposal-isolation-baseline-46.json` | `6624f8ad416b1166d01d8ffe7ccd673e7cc8f93bf4c0b565df53415907b0ce90` |
| `proposal-isolation-fixed-51.json` | `465b3bfb951c7126d2e23c89f133d5e363ae51a332000be07a60cc1f075aadde` |
| Browser `red-report.json` | `f7110b2df6c1ac9c2cc17d98a2a6ba3423a7a826c889dd3e2086c20566d88a5f` |
| Browser `green-report.json` | `912748c2ece885d14dfc8ea770921e631d22f0639e66434ef02ef73254227a94` |

Identischer neuer Componenttest, SHA-256:
`1c41e615fde47a4b3ca665aab63311a252c0d8f493b780b79087c15c12565946`.
Identischer Browsertest, SHA-256:
`9e5815b60d9e04b768b9e493f117681262f7289d29e51b21acb01fe6fe3dcc44`.
Qualifizierter neuer Produktionsblob:
`8830ed1d2cc6db4b8e21b32ec2682da303896d1b`.

Die Reproduktion benötigt nur diese neuen Testdateien auf einer separaten Kopie
des genannten Baselinecommits; kein destruktiver Branchwechsel ist erforderlich.
Der grüne Lauf verwendet denselben Testinhalt auf dem Entwicklungsbranch.

### Fehlversuche und Prüfgrenzen

Die ersten beiden Component-Teststarts im eingeschränkten Prozessraum konnten
keine Worker starten und wurden mit Exit 130 beendet; sie lieferten keine
Testergebnisse. Der erlaubte erweiterte Ausführungskontext lief anschließend mit
unveränderten Testbefehlen. Der erste Browserstart endete vor Testinhalt mit
Chromium SIGTRAP. Zwei vorzeitig beendete ausführbare Browserläufe fanden danach
falsche exakte Label-Locators für umschlossene Selects beziehungsweise befüllte
Textareas; deren Textinhalt wurde Teil des gefundenen Labels. Der erste dieser
Läufe hatte einen Timeout, einen abgebrochenen und fünf nicht ausgeführte Fälle.
Die Korrektur auf die tatsächlichen ARIA-Rollen und zugänglichen Namen änderte
keine Assertion, Retryzahl oder Wartezeit. Diese Fehlversuche sind keine fachlichen
Rotnachweise und bleiben von den finalen Reports getrennt.

Zwei `require-await`-Befunde in neuen Testhelpern wurden vor dem grünen Gate
korrigiert. Der Node/npm-Wrapper wurde auf die tatsächlich gepinnten CLIs
korrigiert. Playwrights erster offizieller Downloadhost lieferte ungültige ZIPs;
der reguläre offizielle Fallback lud dieselben Browserbuilds erfolgreich. Das
lokal installierte Ruff-Binary benötigte sein ausführbares Dateiattribut.
Keine Gate-/Dependencyänderung und kein Testretry wurden dafür eingeführt.
Der Build meldet seine bestehende Größenwarnung für große Chunks; der Build besteht.

Docker und eine verifizierte isolierte PostgreSQL-Instanz stehen lokal nicht zur
Verfügung. `bash scripts/check-backend.sh` und `bash scripts/run-e2e.sh` werden
deshalb lokal nicht als ausgeführt ausgegeben. Ihre Skripte und aktuellen CI-
Einstiege wurden gelesen; keine private `.env` oder Nutzer-Volumes wurden benutzt.
Die nativen Gates laufen über die unveränderten vorhandenen PR-Workflows.

## B01–B14: Nachweiszuordnung

| ID | Konkreter Nachweis |
|---|---|
| B01 | Unveränderte Baseline, echte M2/B1- und Doppel-POST-Reproduktion; 14 bereits funktionierende Fälle ausdrücklich erhalten. |
| B02 | Modell-/Basisreset, aktuelle Generation, S1 Desktop/Mobil und Component einschließlich same-batch ABA. |
| B03 | Initial-/Hypothesen-/Versionsfehler und offene Reads sperren den direkten Handler; Lade-/Leer-/Fehleranzeige bleibt unterscheidbar. |
| B04 | APPROVED, konkrete `model_id`, Existenz und nichtleere Basis-ID; fremde/gemischte Liste und missing base sperren. |
| B05 | Kontrollierte vertauschte und bereits erfüllte Promises, M-/H-Rückkehr, StrictMode und echter Parent-/Router-Unmount. |
| B06 | Gleiche Auswahl/Rerender erhält Text; echter Modell-/Basiswechsel setzt den sichtbaren Vertragsregeln entsprechend zurück. |
| B07 | Vollständige exakte Create-Payloads in Component- und Browserassertions; alle Response-IDs plus DRAFT geprüft. |
| B08 | Zwei synchrone Submit-Events im selben React-/Browsertask, höchstens ein laufender Create. |
| B09 | Synthetischer H-Wechsel sowie tatsächlicher keyed Parent/Router; alter Erfolg/Fehler/Finally entsperrt keinen neueren Save. |
| B10 | Eingaben nach aktuellem Fehler erhalten; ausdrücklicher Retry; unklarer Abschluss ohne Auto-POST und bewusster Readback. |
| B11 | Fünf unveränderte Candidatefälle plus acht neue Fachfälle; allgemeine JSON-Objekterfassung bleibt erhalten. |
| B12 | DRAFT und keinerlei automatische Validation-/Approval-/Activation-Schreibaufrufe; native Regression prüft unveränderte Governancefakten. |
| B13 | Component/Parent und sieben echte Routerfälle getrennt vom neuen PostgreSQL-Servicebeleg ausgewiesen. |
| B14 | Lokaler unveränderter Frontendgate plus vollständige aktuelle PR-CI: Backend/Quality, Produktionsimage, Renderer, Frontend, Smoke und getrennte Finanz-/Lernowner. Exakte Ergebnisse/Identitäten stehen im PR-Handoff. |

## Bindung der vollständigen CI und Übergabe

Der zugehörige Entwicklungs-PR des oben genannten Branches ist die überprüfbare
Übergabe. Sein Abschlussbericht bindet **Head-SHA, vollständigen Tree, tatsächlichen
Checkout/PR-Testmerge, Workflow/Job und Versuch** an die tatsächlich abgerufenen
aktuellen Ergebnisse. Ein grüner Trigger-SHA wird nicht mit dem ausgecheckten
synthetischen PR-Testmerge oder einem späteren echten Main-Merge gleichgesetzt.
Historische CI-Zahlen aus #273 ersetzen keine aktuelle Prüfung.

Die vier geschützten Smoke-Skips sind keine bestandenen Ownerfälle. SELL-Bericht,
Vollabschlusskohorte sowie Journal- und FT011-Evidenceweg müssen in den vorhandenen
getrennten Ownerjobs tatsächlich laufen. Aktuelle PostgreSQL-FT019-/Governance-
Nachweise sind native Belege; Browsermocks bleiben UI-Nachweise. Workflow-Reruns,
Testretries, Skips und frühere Fehlversuche werden getrennt berichtet.

Implementierung und lokale Tests sind belegt. Technische Übergabereife setzt die
vollständigen aktuellen PR-Gates voraus und wird ausschließlich anhand dieses
Handoffs festgestellt. Eine Fachabnahme, Merge, Veröffentlichung oder beobachtete
PC-Installation wird dadurch nicht behauptet. Es wird kein Modell aktiviert.
Strang A bleibt unabhängig; bei späterer Integration ist der tatsächliche
kombinierte Main nichtdestruktiv aufzunehmen und neu zu qualifizieren.
