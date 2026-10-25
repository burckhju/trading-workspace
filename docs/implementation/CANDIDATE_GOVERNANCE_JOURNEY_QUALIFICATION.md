# B — Candidate-Governance: Benutzerweg und Qualifikationsgrenzen

Stand: **2026-10-25, erster erfolgreicher nativer Gesamtweg und datierte Laufhistorie.**
Der jeweils abschließende Head-/Tree-/Run-/Job-Nachweis steht im
[Entwicklungs-PR #276](https://github.com/burckhju/trading-workspace/pull/276).
Der unten ausgewertete vierte Lauf belegt S0–S7 mit realer PostgreSQL-Persistenz,
getrennten Browsercommands und A→B→A. Die drei vorherigen Fehlversuche bleiben
Fehlversuche. **B07 ist für die GOOD-Referenz weiterhin offen**; die tatsächlich
erzeugten Analyseinputs haben LIMITED-Qualität. Die finale vollständige CI wird
im PR separat an dessen letzten Head gebunden. Ein neuer Dokumentationscommit
übernimmt keinen älteren grünen Lauf als Nachweis seines eigenen Trees.
Dieser Bericht ergänzt [PB-020 Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance),
[Aktivierung/Rückkehr](../planning/PRODUCT_BACKLOG.md#pb-020-activation) und die
[bestehende Candidate-Familie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family).
Er setzt keinen Arbeitsstatus auf Accepted/Observed und erklärt M9 nicht für abgeschlossen.

## Ausgangsstand und Identitäten

| Gegenstand | Geprüfte Grundlage / aktuelle Nachweisgrenze |
|---|---|
| Ausgangs-Main | `fbd77fb94947a1fdbfc0aeb90811353fae655a59` |
| Ausgangs-Tree | `027e1d0546f4c09d761ac10d1f59e87d613aff41` |
| Projektversion | `v1.5.14`; in diesem Schnitt keine Versionsänderung |
| Schema-Head | `20261017_0047`; keine neue Migration oder Schemaänderung |
| Erhaltener Vorgänger | #274, ausgeliefert über #275; [Proposal-Kontextqualifikation](MODEL_PROPOSAL_CONTEXT_QUALIFICATION.md) bleibt ein eigener abgeschlossener Nachweis |
| Parallelarbeit | A/#204 ist unabhängig; `features/market/pages/Underlying*` und dessen Navigationshelper bleiben unberührt |
| Erster erfolgreicher nativer Head / Tree | `1109f047f56e2a3804041c27d4f649f06fb9f9eb` / `7c5d25da0dcd65bf5d1cc5076665d1d2f1cfa230` |
| Tatsächlicher erfolgreicher Checkout | PR-Testmerge `1b31f4111c29b66f91cfe44b2694ae0a0f59f5f6` gegen den obigen Main; derselbe Tree |
| Erfolgreicher nativer Run / Job / Versuche | `40166152063` / `121087501390`; Workflowversuch 1, genau ein Ergebnis mit `retry=0`, 1 passed, 0 skipped/flaky/unexpected |
| Abschließender PR-Head und reguläre Gesamt-CI | Im oben verlinkten PR ausdrücklich an den letzten tatsächlichen Checkout/Tree gebunden. Der erfolgreiche Lauf unten ist ein unveränderlicher Entwicklungsbeleg, kein Main-Merge oder Ersatz für spätere Headprüfungen. |

Die aktuellen [FT-013](../features/FT-013_CONTROLLED_MODEL_GOVERNANCE.md),
[FT-019](../features/FT-019_GOVERNED_CANDIDATE_RULE_SEMANTICS.md),
[FT-020](../features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md) und
[ADR-FT019-001](../decisions/ADR-FT019-001-CANDIDATE-DEFINITION-SEMANTIC-VERSIONING.md)
sind die fachlichen Verträge. Historisches FT-013-V1-Nicht-Soll zur Aktivierung hebt
den späteren `RuntimeActivationService` nicht auf. Der vorhandene
[FT-019-PostgreSQL-Fall](../../tests/integration/backend/learning/test_ft019_candidate_governed_rule_semantics.py)
prüft Governance, Aktivierung, Evaluation und Rückkehr auf Serviceebene. Seine
direkt gesetzten Quellenfixtures sind kein Browsernachweis ab einer echten Lesson-Seite.
Die gezielte Prüfung der vorhandenen Tests und tatsächlichen Parent-/Routerpfade
hat für diesen Schnitt keinen bereits qualifizierten S2–S6-Gesamtfall identifiziert;
das ist kein repositoryweiter Abwesenheitsbeweis durch eine leere Textsuche.

## Gezielte Ausgangs-Übergangsmatrix

Diese Matrix hält den **Ausgangsstand vor dem ersten nativen Lauf** fest.
Die ausgeführte Nachher-Kette mit konkreten IDs und der aktualisierte B01–B16-Stand
stehen im Abschnitt „Vierter nativer Lauf“. **Vorhanden und geprüft** bezeichnet
hier ausschließlich die jeweils genannte lokale
Prüfung. **Vorhanden, Gesamtnachweis fehlt** trennt implementierte Ownerbefehle von
der ausstehenden nativen Reise. **Nachweislich fehlend** bezeichnet die belegte
Ausgangslücke vor der hier beschriebenen Ergänzung. **Nicht verifiziert** bezeichnet
einen noch nicht ausgeführten Nachweis. Die Kürzel L1/E1/H/P/A/B sind Rollen;
konkrete UUIDs entstehen erst im isolierten Lauf und müssen dessen Artefakte binden.
Sie werden hier nicht durch erfundene IDs ersetzt. API-Pfade sind relativ zu
`/api/v1`; der Browser verwendet den tatsächlich gebauten Proxypräfix.

| Übergang | Input / genaue Identitätsfelder | Schreibender Owner; Read / Command | Vorhandener Consumer / Test | Belegte Lücke und aktueller Stand |
|---|---|---|---|---|
| S0: Trade → Review → E1 → L1/L2 | `trade_id`, `post_trade_observation_id`, `exit_review_id`, `exit_review_version_id`, `learning_evidence_id`, `lesson_id`, `current_version_id` | Trade/Position-, PostTrade- und Learning-Owner; explizite Capture-/Review-/Materialisierungs-/Lessonbefehle. FT011-Materialisierung bindet `expected_exit_review_version_id` und Idempotency-Key. Observation-GET kann refreshen und ist hier schreibendes Setup. | Vorhandene Journal-/FT011-Browserfälle; neuer [Setup-Helfer](../../tests/e2e/support/candidate-governance-setup.ts) verwendet dieselben Owner-APIs. | **Vorhanden, Gesamtnachweis fehlt.** E1 wird nicht als nackte SQL-Zeile erzeugt. Nur markierte vergangene synthetische Preise sind Fixture. Der neue S0-Lauf ist noch nicht ausgeführt. |
| S2: ausgewählte L1 → H | `lesson_version_id=L1`, `source_lesson_version_id`, `hypothesis.id`; E1 bleibt über die exakten Lesson-Evidence-Links beim Learning-Owner | `LessonHypothesisHandoffService` → `ModelGovernanceService`; GET/POST `/model-governance/lesson-versions/{L1}/hypotheses` | Tatsächliche `LessonDetailPage`/`LessonReviewPanel` → `LessonHypothesisPanel`; `LessonDetailPage.governance.test.tsx`; vorhandener `test_ft013_governance_handoff.py` | **Nachweislich fehlend** war die Bindung an die betrachtete historische L1 statt stets aktuelle L2. Der Parent liefert jetzt nur den verifizierten Snapshot; 3 lokale Fälle prüfen historische Auswahl, Wechsel und unbekannte ID. Die generische Hypothesenroute prüft nun dieselbe Workspacegrenze wie die spezialisierte Route; PostgreSQL-Nachweis noch offen. |
| S2: H + genehmigte A → P | `model_id`, `base_model_version_id=A.id`, `hypothesis_id=H.id`, `proposal.id`, explizite V2-Definition | `ModelGovernanceService.create_proposal`; Modell-/Versions-/Proposal-Reads, POST `/model-governance/proposals` | Bestehendes `HypothesisProposalPanel`, #274-Kontextfälle; `test_ft020_proposal_context.py` | **Vorhanden und geprüft** auf gezielter Clientebene; #274-Erfassungslogik bleibt erhalten. Basis/Modell/Hypothese werden sichtbar benannt. Kein stilles Rebase oder No-op. Aktueller nativer Lauf fehlt. |
| S3: P + E1 + Cutoff → Validation | `proposal_id`, `validation.id`, `evidence_ids[]`, `evidence_cutoff_at`, `conclusion`, `metrics`, `notes` | `ModelGovernanceService.validate_proposal`; POST und GET `/model-governance/proposals/{P}/validations`; gespeicherte Links in `ModelValidationEvidenceRecord` | `ProposalValidationPanel`; `test_proposal_validation_read_service.py`; neuer `test_candidate_governance_boundaries.py` | **Nachweislich fehlend** war die Evidence-ID-Liste im vorhandenen Readback-DTO. Additive Projektion und genaue Anzeige sind lokal geprüft. Exakter Cutoff, Zeitzonenäquivalenz, spätere/fremde Evidence und keine Teilfakten sind als native Fälle ergänzt, noch nicht ausgeführt. |
| S4: validierter P → Approval + B | `proposal_id`, `approval.id`, `model_version_id=B.id`, `previous_version_id=A.id` | `ModelGovernanceService.approve_proposal`; POST `/model-governance/proposals/{P}/approve`, GET `/approval` | `ProposalApprovalPanel`; vorhandener FT-019-Test; neue native Cutoff-/Stale-Fälle | **Vorhanden, Gesamtnachweis fehlt.** Separate Freigabe bleibt erhalten; IDs und Vorgänger sind sichtbar. Es wird keine neue SUPPORTS-only-Regel eingeführt. Dass A nach Approval von B aktiv bleibt, muss der neue native Lauf bestätigen. |
| S5: B auswählen → aktivieren | `model_id`, ausdrückliche genehmigte Ziel-`version_id`, `activation.id`, `model_version_id` | Ausschließlich `RuntimeActivationService`; GET `/models/{id}/versions` und `/runtime-activation`, POST `/models/{id}/versions/{version_id}/activate` | Bestehendes `RuntimeActivationPanel`; `RuntimeActivationPanel.journey.test.tsx`; FT-019-Servicefall | **Vorhanden und geprüft** auf Componentebene. Aktive, neueste und gewählte genehmigte Version werden getrennt gezeigt; Fehler beim Current-Read ist kein Zustand „keine Aktivierung“. Native Speicherung noch offen. |
| S1/S5/S6: bestehende Analysefakten → Evaluation | `candidate_id`, drei `analysis_id`/`version`-Paare für MARKET/SECTOR/UNDERLYING; `evaluation.id`; tatsächlich gespeicherte `model_id`/`model_version` und `sources[]` | Analyse-Owner erzeugt echte Runs/Snapshots; `TopDownEvaluationOrchestrator` liest sie; `CandidateService` löst Runtime beim Command neu auf. POST `/candidates/{id}/evaluations/auto`, GET `/evaluations` | `CandidatePage`; `test_candidate_runtime_execution.py`, `test_runtime_readiness.py`, `test_evaluation_source_readback.py`; FT-019-Servicefall | **Nachweislich fehlend** war die API-Projektion der bereits gespeicherten konkreten Evaluationsquellen. Additiver Readback ist lokal geprüft. **Gesamtnachweis fehlt**; die ausdrücklich verlangte GOOD-Referenz ist durch die unten dokumentierte FT-006-Grenze nicht erfüllt. |
| S6: bewusste Rückkehr B → A | Erhaltenes `A.id` aus derselben Modellliste, neue `activation.id`; keine Löschung von B oder alten Evaluationen | Derselbe `RuntimeActivationService.activate` wie S5 | Tatsächlicher Governance-Parent bisher nur mit übergebenem Approvalziel; ergänzt um bewusste Auswahl einer kompatiblen APPROVED-Version; `RuntimeActivationPanel.journey.test.tsx` | **Nachweislich fehlend** war die nutzbare Auswahl der initialen A im Consumer. Componentregression prüft explizite Rückkehr; DRAFT/unbekannte Definition/fremde Modellliste bleiben ausgeschlossen. Native A→B→A-Reise noch offen. |
| S7: Reload / historische Links / Readfenster | `lesson_version_id`, `candidate`, `evaluation`; gespeicherte Validation-/Approval-/Activation-IDs | Bestehende lesende Ownerprojektionen; DB-Fingerprint und beobachtete Requests rahmen die vorgesehenen Readfenster | Lesson-Snapshotlink; `CandidatePage.history.test.tsx`; neuer geschützter Browserfall | **Vorhanden und geprüft** für genaue Clientauswahl; ungültige Evaluations-ID wird nicht auf „latest“ umgehängt. **Nicht verifiziert** sind native Fingerprintgleichheit, echte Desktop-/Mobilansichten und Cleanup dieses neuen Laufs. |

## Bestätigte Änderungen und erhaltene Verträge

### Quellen, Benutzerübergänge und Readback

Der Learning-Parent übergibt die tatsächlich betrachtete Lessonversion an den
bestehenden Hypothesenconsumer. Der zusätzliche genaue Quellenlink und die
Hypothesen-/Proposal-/Basis-IDs machen die Bindung prüfbar, auch wenn L2 bereits
existiert. Die Evidence selbst und ihre Interpretation bleiben beim Learning-Owner.
Der generische Hypothesenbefehl hatte nur die Existenz einer Lessonversion geprüft;
er verwendet nun dieselbe Lesson-/Workspace-Zuordnung wie der spezialisierte
Handoff. Die Regression
`test_generic_hypothesis_rejects_foreign_lesson_before_any_write` war vor dem Fix
rot und danach grün. Ihr minimaler SQLite-In-Memory-Aufbau prüft die reale
Owner-SELECT-Grenze, ersetzt jedoch keinen PostgreSQL-Transaktionsnachweis.

Validation gibt ihre schon gespeicherten Evidence-Verknüpfungen zusätzlich als
`evidence_ids` zurück. Candidate-Evaluationen geben ihre schon gespeicherten
`sources` mit Rolle, Quelltyp, Quell-ID/-version und Analysemodell-ID/-version
zurück. Beide Änderungen lesen den vorhandenen Bestand; sie berechnen nichts neu
und erzeugen kein zweites Quellen- oder Ergebnisregister. Die autorisierte
Candidate-Detailroute prüft den Workspace, bevor sie historische Quellen liest.
Die jeweiligen neuen Readbackregressionen scheiterten vor der Ergänzung an den
fehlenden Feldern und bestehen danach.

Der Aktivierungsconsumer bietet die bewusste Auswahl einer kompatiblen genehmigten
Version aus demselben Modell, einschließlich A. Er verwendet weiterhin den einen
Aktivierungsbefehl. `APPROVED` bleibt ein Versionsstatus, die aktive Runtime ein
separater Zustand. Ein späteres Approval verändert diesen Zustand nicht. Der
Proposalstatus wird im Parent erst nach bestätigten Validation-/Approvalantworten
fortgeschrieben; die ausgelieferte #274-Erfassungs- und Kontextschutzlogik bleibt
erhalten. Zusätzliche synchrone Operationssperren und Instanzbindung schützen die
Folgebefehle. Nach unklarem Abschluss erfolgt keine automatische Wiederholung;
bewusster Readback bleibt erforderlich. Clientlocks belegen keine globale
Exactly-once- oder Serialisierungsgarantie.

### Validation ist ein gespeicherter Befund

Die UI zeigt Cutoff als exakten ISO-Wert, gewählte Evidence-IDs, Conclusion,
Metrics, Notes und Validation-ID. Eine ausdrücklich synthetische Conclusion wird
vom Test gesetzt und begründet. Sie wird nicht aus PnL, Preview oder einem Testpass
abgeleitet. `LearningEvidence.created_at <= evidence_cutoff_at` prüft den
Erstellungszeitpunkt des Evidenceobjekts; Handelsdatum, beobachteter Preistag,
Ausführungszeit und heutige Quellenprüfung sind davon verschieden. Der Check
rekonstruiert weder damaligen Wissensstand noch historische Marktdaten.

Der vorhandene Approvalvertrag prüft Status, Validation und veraltete Basis.
Er enthält keine allgemeine Sperre für CONTRADICTS/INCONCLUSIVE. Der neue native
Grenzfall hält ausdrücklich einen CONTRADICTS-Befund fest, um keine zusätzliche
SUPPORTS-only-Geschäftsregel einzuführen. Sein finaler PostgreSQL-Suitenlauf wird
gesondert im PR gebunden. Der ausgeführte Browserfall verwendet INCONCLUSIVE.

### Harte Grenze: Preisqualität VALID wird im Analyseowner LIMITED

[`MarketAnalysisService.run`](../../backend/app/features/analysis/service/application.py)
übernimmt `DailyPrice.quality_status.value` in den Snapshot. Die unterstützte
Preisqualität heißt `VALID`; der vorhandene
[`calculator.calculate`](../../backend/app/features/analysis/domain/calculator.py)
stuft Zeilen mit `quality_status != "GOOD"` als LIMITED ein. Damit liefern auch
vollständige ownererzeugte Analysen der vorgesehenen synthetischen VALID-Preise
`LIMITED` / `COMPLETED_WITH_WARNINGS`. Der gezielte Code-/Berechnungsabgleich
bestätigt diese Abbildung; der vierte native Lauf weist sie zusätzlich an drei
echten ownererzeugten Analyseversionen mit jeweils 200 Preiszeilen nach.

Der Browserfall verlangt deshalb wahrheitsgemäß LIMITED und überprüft CAUTIOUS
sowie erfüllte übrige Pflichtkriterien. Ein erfolgreicher A→B→A-Lauf unter dieser
Qualität kann die technische Policywirkung belegen. Er erfüllt **nicht** die
ausdrücklich verlangte **GOOD-Referenz von B07**. Dieser offene Teil darf auch nach
einem grünen Browserreport nicht als vollständig bestanden erscheinen.

Dieser Schnitt verändert weder FT-006-Qualitätssemantik noch Preis-/Analysesnapshots,
um GOOD künstlich herzustellen. Nächster konkreter abhängiger Schnitt ist die
gesonderte Klärung und Qualifikation der Preis-zu-Analyse-Qualitätsabbildung beim
FT-006-Owner: entweder eine versionierte Qualitätskorrektur mit unveränderter
1.0.0-Reproduktion oder ein ausdrücklich belegter verlustfreier Adaptervertrag.
Eine Änderung des bestehenden Calculators kann den separaten
`quality_status_match` historischer Reproduzierbarkeitsprüfungen verändern;
eine bloße Normalisierung neuer Snapshots verändert die gehashte Quellqualität.
[FT-006-Provenienz](../features/FT-006_GOVERNED_MODEL_PROVENANCE.md) verlangt bei
Calculatoränderungen die gemeinsame Prüfung von Runtimeversion und
Implementierungsreferenz; [ADR-S4-005](../decisions/ADR-S4-005-MARKET-ANALYSIS-LIFECYCLE.md)
erhält historische Snapshots und deren Reproduktion. Eine solche Korrektur und
anschließende erneute GOOD-Referenzreise benötigen einen eigenen abgegrenzten
Auftrag. Die vorhandenen V1-/V2-Regeldefinitionen,
Aggregation und Fail-closed-Grenzen bleiben bestehen.

## Historischer Prüfstand vor dem ersten nativen Lauf

Diese Tabelle dokumentiert bewusst den damaligen Entwicklungsstand. Die späteren
nativen Läufe und der neue Candidate-Anlagefix folgen in datierter Reihenfolge.
Die Fallzahlen sind Beobachtungen, keine künftig festgeschriebenen Suitegrößen.

| Prüfung | Tatsächlich beobachtetes Ergebnis / Grenze |
|---|---|
| Backend Model/Candidate | Zunächst 59 gezielte Unit-/Handler-/Repository-/Runtimefälle in der getrennten Arbeitskopie erfolgreich. Anschließend in der zusammengeführten Arbeitskopie alle Model-/Candidate-Unitverzeichnisse: **80 erfolgreich**. Black/Ruff über 985 Dateien und mypy `app` mit 556 Quelldateien erfolgreich. Keine PostgreSQL-Ausführung in diesen lokalen Nachweisen. |
| Backend rote Reproduktion | Fremde Lessonversion über generische Hypothese, fehlende Validation-Evidence-IDs und fehlende Candidate-Quellenprojektion vor Ergänzung rot; dieselben gezielten Fälle danach grün. |
| UI | 115 gezielte Fälle erfolgreich, 0 übersprungen; darin 18 neue Fälle. Typecheck, Lint und Format erfolgreich. Die bisherigen Proposal-Kontextfälle bleiben erhalten. |
| Vollständiges lokales Frontendgate | Das unveränderte `bash scripts/check-frontend.sh` hat auf der zusammengeführten Arbeitskopie bestanden: **121 Dateien / 734 Tests**, Build und reguläre Prüfungen; Coverage 93,72 % Statements/Lines, 85,6 % Branches, 86 % Functions. Das ist noch keine aktuelle PR-/Main-CI. |
| Erhaltener #274-Browserweg | 7 unveränderte synthetische Browserfälle gegen einen eigenen lokalen statischen Build bestanden, jeweils `retry=0`, 0 Skips/Flaky/unexpected; Playwright 1.55.0 / Chromium 140.0.7339.16. Alle 7 API-Attachments melden keine unerwarteten Requests. Desktop-/Mobilbilder dieses bisherigen Proposalwegs wurden angesehen; sie ersetzen keine native Governance-Sichtprüfung. Der mobile Fullpagebeleg hat 4 px Überlauf bei 390 px Viewport und ist keine pixelperfekte Abnahme. |
| UI rote Reproduktion | 6 korrigiert reproduzierte Baselinefälle auf unverändertem v1.5.14-Produktionscode: historische L1, Auswahlwechsel, unbekannte Lessonversion, fehlende A-Auswahl, doppelte Aktivierung, fehlgedeuteter Runtime-Lesefehler. Weitere 3 Doppelcommands, 1 doppelte Evaluation und 2 verschwiegene Lesefehler wurden auf den jeweiligen Zwischenständen vor ihren Guards reproduziert. Für die übrigen 6 Ergänzungen wird kein Baseline-Rotnachweis behauptet. |
| Reine Runner-/Guardprüfung | 153 gezielte lokale Pythonfälle erfolgreich. Zusätzlich **21/21 Node-Guardfälle** im tatsächlich ausgeführten erweiterten Node-22-Prozess erfolgreich. Ein vorheriger eingeschränkter Wrapper zeigte nur den Dateirunner und wird nicht als 21-Fälle-Nachweis verwendet. Diese Prüfungen betreffen Ziel-/Request-/Report-/Manifestverträge; sie sind kein gestarteter PostgreSQL-/Browserstack. |
| Setup-Helfer | Strikte TypeScriptprüfung mit TS 5.8.3 und Playwright 1.55.0 erfolgreich; kein HTTP-Setup ausgeführt. |
| Abgebrochene/ungeeignete Versuche | Ein breiter Backendlauf mit vorhandenen TestClient-Startups wurde im eingeschränkten Prozessraum abgebrochen; kein Pass. Ein erster UI-Vitestversuch endete ohne Tests mit Exit 130. Der erste UI-Baselinereport hatte einen unzutreffenden ErrorNotice-Locator; maßgeblich ist die korrigierte Reproduktion, nicht dieser Erstreport. |
| Native PostgreSQL-Fälle | Vorhandene FT-013/019/020-Fälle erhalten; drei neue Fälle in `test_candidate_governance_boundaries.py` ergänzt. Noch nicht auf dem neuen finalen Stand ausgeführt. |
| Neuer Browserhauptfall | Noch nicht ausgeführt; 0 erfolgreiche native Hauptausführungen nachgewiesen. Keine Retry-/Skip-/Flaky-Ausführung als Erfolg gezählt. |
| Übrige reguläre Gates / bestehende Ownerwege | Vollständiges Backendgate einschließlich PostgreSQL, `run-e2e.sh` und vollständige aktuelle CI auf dem finalen Stand noch offen; das lokale Frontendgate ist oben getrennt nachgewiesen. Frühere v1.5.14-Reports werden nicht als neuer Lauf übernommen. |
| Desktop/Mobil / Cleanup | Keine neue native Sichtprüfung und kein ausgeführter Cleanupnachweis. Ein zukünftiger Screenshotupload allein ersetzt die Sichtprüfung nicht. |

Der separate lokale #274-Report `proposal-browser-report.json` hat SHA-256
`152122530405cab39d433a5c3684c024c2cd837a347463aa888c335ced45fc04`.
Die 15 verglichenen UI-Dateien stimmen mit der zusammengeführten Arbeitskopie
überein; Mock-HTTP bleibt vom ausstehenden PostgreSQL-Gesamtweg getrennt.

Die neuen nativen Grenzfälle prüfen unter dem bestehenden PostgreSQL-Testguard:

- `test_hypothesis_scope_rejection_and_exact_historical_lesson`: fremder Scope
  bleibt ohne neue Governancefakten; eine eigene historische L1 bleibt erlaubt.
- `test_validation_cutoff_scope_readback_and_non_supporting_approval`: exakter
  Cutoff einschließlich Zeitzonenäquivalenz, zu frühe Grenze, spätere/fremde
  Evidence, deduplizierte IDs, gespeicherte Conclusion und Freigabe ohne Aktivierung.
- `test_stale_proposal_and_activation_identity_rejections_leave_no_partial_facts`:
  veralteter Proposal, falsches Modell-/Versionspaar, fremder Scope und DRAFT-Ziel.

Der bestehende FT-019-Servicefall verwendet nun dieselben Quellreferenzen für seine
drei Evaluationen und prüft deren unveränderten gespeicherten Readback. Diese
Servicefixtures bleiben ausdrücklich vom neuen API-Setup mit real existierenden
Analysefakten getrennt.

## Reproduzierbare native Ausführung und Artefaktbindung

Der neue [geschützte Hauptfall](../../tests/e2e/candidate-governance-journey-postgres.spec.ts)
heißt `candidate governance: exact Lesson source, explicit A-B-A and immutable evaluations`.
Der [Runner](../../scripts/run-candidate-governance-e2e.sh) und der additive Job
`candidate-governance-owner` in [.github/workflows/e2e.yml](../../.github/workflows/e2e.yml)
sind der reguläre Einstieg für seine tatsächliche Ausführung. Der
[Reportprüfer](../../scripts/check-candidate-governance-e2e-report.py) bindet die
vorab entdeckte Test-ID und verlangt genau ein Passed-Ergebnis mit `retry=0`,
ohne Skip, Flaky oder erwarteten Fehler. Geschützte Skips im allgemeinen Smoke
sind kein Ersatz für diesen Job. Ein Workflow-Neustart und ein Testretry sind
unterschiedliche Versuche und müssen getrennt ausgewiesen werden.

S0 und die initiale A-Freigabe/-Aktivierung sind ausdrücklich markiertes API-Setup.
S2–S6 und die tatsächlichen Candidate-Evaluationen verwenden die Oberfläche.
Der synthetische Stack bindet eine eigene Run-ID, DB, Compose-/Netzidentität,
Ports, Mounts und Volumes. Der Guard läuft vor der Schreibfreigabe; Provider und
Versand bleiben deaktiviert. Browser und Setup-HTTP dürfen nur den verifizierten
lokalen Ursprung erreichen; Redirect- und Serviceworker-Ausweichwege werden
abgewiesen. Die Preisfixture prüft ihr Ziel nochmals, erzeugt nur vergangene
markierte Preise und verändert keine Governance-, Evidence- oder Analyseobjekte.

Reine Lesefenster vergleichen DB-Fingerprints und tatsächlich beobachtete Requests.
Observation-Refresh, Materialisierung, Validation, Approval, Aktivierung und
Evaluation liegen außerhalb dieser Fenster. „GET“ allein ist kein Read-only-Beleg.
Die native Ausführung muss Quellen-/Versionsketten, Payloads, gespeicherte
API-Readbacks, Mutationserwartungen, Desktop-/Mobilbilder, Report, Netz-/DB- und
Migrationsidentität sowie Cleanup an den tatsächlichen Checkout binden. Das
SHA-256-Manifest umfasst die vollständige Artefaktdateimenge einschließlich
versteckter/nestierter Dateien und Cleanup. Die tatsächlich geprüften Artefakte
der vier Läufe sind unten jeweils an ihren eigenen Checkout gebunden.

Unverändert zu erhalten und auf dem finalen Stand tatsächlich auszuführen sind
die beiden Finanzfälle `realized-gross-report-postgres.spec.ts` und
`closed-trades-report-postgres.spec.ts` sowie die beiden Lernfälle
`post-trade-journal-postgres.spec.ts` und
`post-trade-evidence-history-postgres.spec.ts`. Der neue Job ersetzt und benennt
keinen davon um. Produktionsimage, Renderer, reguläre Backend-/Frontend-/Smoke-Gates
und Veröffentlichungsschutz bleiben verbindlich; neue globale Schreibflags,
erhöhte Berechtigungen oder ein allgemeiner CI-Umbau gehören nicht zum Schnitt.

## B01–B16: Stand vor dem ersten nativen Lauf

| ID | Vorhandener Beleg / aktueller Stand | Noch erforderlich |
|---|---|---|
| B01 | **Belegt als gezielte Bestandsprüfung:** FT-013/019/020, ADR und #274 erkannt; vorhandene Owner/Consumer wiederverwendet. | Finalen gemeinsamen Diff/Head binden. |
| B02 | **Lokal geprüft:** L1-Parentbindung und historische Links; exakte E1/L1-Ownerkette im Setup vorgesehen. | Echte S0/S2-Persistenz mit UUIDs und L2-Verlauf im nativen Lauf. |
| B03 | **Lokal geprüft:** Modell/Hypothese/Basis sowie aktive/neueste/gewählte genehmigte Version werden getrennt dargestellt; #274-Kontextschutz erhalten. | Native Request-/Readbackkette am finalen Stand. |
| B04 | **Lokal geprüft, vorhandener Vertrag erhalten:** V1 unverändert; genau zwei V2-Policies, No-op und unbekannte Definitionen fail-closed. | Reguläre Regression auf finalem Tree. |
| B05 | **Teilbelegt:** Evidence-ID-/Cutoff-/Conclusion-Readback lokal; native Cutoff-/Scopefälle implementiert. | PostgreSQL-Ausführung, echte gespeicherte E1/Cutoff-Kette; kein Backtestnachweis vorgesehen. |
| B06 | **Teilbelegt:** getrennte Commands im vorhandenen Owner/Consumer; native Prüfung „Approval B, A weiter aktiv“ implementiert. | Tatsächliche Browser-/PostgreSQL-Ausführung. |
| B07 | **Nicht vollständig erfüllt:** GOOD-Referenz durch VALID→LIMITED-Abbildung im bestehenden FT-006-Owner blockiert. LIMITED-A→B→A-Hauptfall vorbereitet. | Nativer LIMITED-Lauf und davon getrennte spätere FT-006-Klärung/GOOD-Referenz; kein Umdeuten eines grünen LIMITED-Reports. |
| B08 | **Lokal geprüft:** bewusste A-Auswahl ruft denselben Aktivierungsowner auf; historische B-Version bleibt erhalten. | Native Rückkehr und unveränderte historische Evaluationen. |
| B09 | **Teilbelegt:** generische Hypothesen-Scopegrenze rot/grün reproduziert; vorhandene Pair-Prüfung erhalten; native Stale-/Scope-/Partial-Fact-Fälle ergänzt. | Aktueller PostgreSQL-Lauf dieser Grenzen. |
| B10 | **Teilbelegt:** Adapter/Readiness/Execution-Unitfälle; Ausführung löst Runtime erneut auf; Quellenreadback lokal. | Nativer Wechsel zwischen Readiness und Ausführung und Unverändertheit historischer Fakten. |
| B11 | **Lokal geprüft:** #274 plus gezielte Folgecommand-/Unmount-/Spätantwort-/Doppelaktionsfälle; keine automatische Wiederholung unklarer Commands. | Integration in finalen Tree und native Anwendungsstrecke; keine globale Exactly-once-Zusage. |
| B12 | **Nicht verifiziert:** neuer geschützter Gesamtfall implementiert, noch keine erfolgreiche Ausführung. | Genau eine erfolgreiche retryfreie, ungeskippte Browser→API→PostgreSQL-Hauptausführung. |
| B13 | **Teilbelegt:** Guards und geplante Readfenster lokal geprüft. | Beobachtete Requests, DB-Fingerprints und tatsächliche Netzentrennung im nativen Lauf. |
| B14 | **Nicht verifiziert als Lauf:** Ressourcen-/Report-/Manifestguards vorhanden; Desktop/Mobil und Cleanup noch nicht beobachtet. | Eigene Stackidentität, Bilder tatsächlich ansehen, vollständigen Cleanup prüfen. |
| B15 | **Teilbelegt:** vollständiges lokales Frontendgate und Backend-Statik bestanden; vorhandene vier Ownerfälle und reguläre Gates erhalten. Keine aktuelle gemeinsame Gesamt-CI behauptet. | Vollständige finale CI mit Head/Checkout/Tree, Runs/Jobs/Versuchen; vier Ownerfälle wirklich ausführen. |
| B16 | **Dokumentiert:** GOOD-Grenze, fehlende native/finale Ausführung und getrennte Fach-/Betriebsabnahme ausdrücklich genannt. | Ergebnisse und verbleibende Restarbeit nach finalen Läufen präzisieren, ohne Abnahmegrenzen aufzuheben. |

## Unveränderte Übergabegrenze

Der technische Handoff im PR bindet finalen PR-Head, tatsächlichen Checkout/Tree,
Run/Job, Workflowversuch, Testversuch und Artefaktmanifest. Der inzwischen bestandene
LIMITED-Hauptlauf macht **B01–B16 nicht pauschal vollständig abgenommen**: B07 bleibt
in der oben genannten GOOD-Referenz offen. Kein realer Nutzermodelleintrag wurde für
diese Qualifikation aktiviert. Main-Merge, Release, Tagging, Installation,
PC-Beobachtung, wirtschaftliche Wirksamkeit und menschliche Fachabnahme sind
separate, hier nicht nachgewiesene Schritte. Zusätzliche Performancestatistiken,
neue Regeln/Schwellen und andere Modellfamilien sind nicht Teil dieses Schnitts.

## Nativer Erstlauf — 2026-10-25, bestätigter Candidate-Anlagefehler

Der erste tatsächliche Lauf auf [PR #276](https://github.com/burckhju/trading-workspace/pull/276)
ist **fehlgeschlagen**, nicht übersprungen und nicht wiederholt worden:

| Identität | Beobachteter Wert |
|---|---|
| Branch-Head | `a41128d1d0b2fc64637bef02b816004ec75adc27` |
| Tatsächlicher PR-Testmerge | `bd329d0493b53440f10e60930854c49579d71b70` gegen Ausgangs-Main `fbd77fb9…` |
| Tatsächlicher Tree | `7edaf2c02ada4ead3976c3f7d0368e61a2066924` |
| E2E-Run / Job / Workflowversuch | [40164849586](https://github.com/burckhju/trading-workspace/actions/runs/40164849586) / `121083689500` / 1 |
| Hauptfall | 1 failed, 0 passed, 0 skipped, 0 flaky; ein Ergebnis mit `retry=0`; S2 nicht erreicht |
| Stack-/Run-ID | `tw-candidate-governance-e2e-16a141c6b924405c8a9c1726afb445cd` / `16a141c6-b924-405c-8a9c-1726afb445cd` |
| Artefakt | `12587584487`, ZIP-SHA-256 `57db4fa9343e9886554858d6c2141903fb35c0f073e036cd93f3e3994ae818f1` |
| Tatsächliche Artefaktprüfung | ZIP-Hash und vollständiges Manifest mit 22 Inhaltsdateien geprüft; 49 tatsächliche Setup-Requests aufgezeichnet, keine Guardverletzung |
| Cleanup | Eigentum verifiziert, `removed=true`, 0 Container/Netze/Volumes; `exit_status=1`, `cleanup_status=0` |

Die Ownerkette erzeugte bereits Trade/Observation/Review/E1/L1/L2 und alle drei
realen gespeicherten Analyseversionen. `POST /candidates` brach dann mit HTTP 500 ab:
PostgreSQL meldete `fk_candidate_events_candidate_id_candidates`, weil der
CREATED-Event beim gemeinsamen Flush vor seinem neuen Candidate eingefügt wurde.
Dies ist ein bestätigter Ownerfehler; der vorhandene FT-019-Servicefall hatte den
Candidate direkt als Fixture gesetzt und diesen Anlagepfad nicht ausgeführt.

Die begrenzte Korrektur flusht ausschließlich den neuen Candidate vor seinem
CREATED-Event innerhalb derselben bestehenden Transaktion. Es bleibt bei einem
gemeinsamen Commit; Schema, Constraints und Geschäftsregeln werden nicht geändert.
Die neue PostgreSQL-Regression prüft echte Owneranlage, genau einen gespeicherten
Candidate/CREATED-Event und den erneuten Read desselben Candidate. Der identische
native Hauptfall bleibt die Vorher-/Nachher-Regression. `evaluate()` besitzt seinen
Parent-Flush bereits; dort ist kein weiterer Reihenfolgenpatch begründet.

Der erste Checkout war shallow: sein `git show --format=%P` lieferte keine
Eltern-IDs. Die Eltern wurden unabhängig über den GitHub-Commitread verifiziert;
der Runner liest sie künftig direkt aus dem vorhandenen Commitobjekt. Der
Browserguard schließt zusätzlich WebSockets, ohne eine Gegenstelle zu verbinden.
Der Fehlversuch ist kein B12-Erfolg. Weitere tatsächliche Ausführungen und der
finale Head/Checkout/Tree werden getrennt im PR-Nachweis gebunden; kein Workflow-
oder Testretry wird aus einem späteren neuen Commit abgeleitet oder verschwiegen.

## Zweiter nativer Lauf — 2026-10-25, enger Testselektorfehler

[E2E-Run 40165257766](https://github.com/burckhju/trading-workspace/actions/runs/40165257766),
Job `121084880081`, Workflowversuch 1, prüfte Head
`4e3665504aa497ebbbf0220602791e0ae8937839` als tatsächlichen Testmerge
`b911b95bdac965ede1c5d05f8f80745d1be8ffac`, Tree
`2b3d561ae8d832528ccf3af407be2754d03076ef`.

Candidate-Anlage und CREATED-Event, initiale separate A-Freigabe/-Aktivierung,
echte A-Evaluation und Hypothese aus L1 waren erfolgreich. Die gespeicherte
A-Evaluation `da87f962-0eef-42b7-8dcf-b524539ce216` verwendet Modellversion 1,
ist `QUALIFIED` bei wahrheitsgemäßem `LIMITED`, und enthält alle fünf übrigen
REQUIRED-Kriterien als `FULFILLED`. Die drei echten Analysequellen und das reine
L1-Öffnungsfenster sind in den Requests und DB-Fingerprints enthalten.

Der Test lief anschließend beim exakten Labelselektor „Governed Model“ in seinen
unveränderten Timeout. Die tatsächlich gesichtete Browseransicht und erfolgreiche
GET-Readbacks zeigen das korrekt geladene Auswahlfeld. Der Labelselektor enthält
bei verschachtelten Select-/Textarea-Elementen Kindtext; die vorhandenen #274-Fälle
verwenden dafür bereits exakte Combobox-/Textbox-Rollen. Der Hauptfall übernimmt
diese eindeutigen Selektoren, einschließlich der anfänglich mit `{}` gefüllten
Metrics-Textarea. Kein Produktpatch und keine Timeout-/Assertionlockerung.
Die Basis A wird zusätzlich ausdrücklich ausgewählt; die vollständige Menge der
fünf übrigen REQUIRED-Kriterien wird vor dem Erfülltheitsvergleich geprüft.

Der Lauf bleibt **ein fehlgeschlagener Testversuch mit retry=0**, kein B12-Pass.
Artefakt `12587852368`, ZIP-SHA-256
`3f62e6e3710661c0f90e62e28bb29f5a2f677f640f6caf5ff68a4140664a52d0`:
Hash und vollständiges Manifest mit 25 Inhaltsdateien lokal geprüft. Eigener
Stack `tw-candidate-governance-e2e-92732182beff4cbaa52ed50648e0d541` vollständig
entfernt; Eigentum bestätigt, 0 Container/Netze/Volumes, `exit_status=1` und
`cleanup_status=0`. Smoke, Frontend und die vier alten Ownerfälle waren auf diesem
Stand grün; sie werden nicht auf den folgenden Commit übertragen. Die finale
Gesamt-CI und gegebenenfalls erfolgreiche retryfreie Hauptausführung werden mit
ihren tatsächlichen Rohartefakten im oben verlinkten PR getrennt nachgetragen.

## Dritter nativer Lauf — 2026-10-25, kanonischer Cutoff-Testwert

[Run 40165742033](https://github.com/burckhju/trading-workspace/actions/runs/40165742033),
Job `121086302804`, Versuch 1, bindet Head
`ae931e44c82950cef37bd7887d8cbf19f5bea6aa`, Checkout
`a4305128c9436b30ad705e1c0fdb31dac3d90c0e` und Tree
`db52241cbfbb969b4bd61b666a008f78b6665de9`. S2 einschließlich echter
DRAFT-Erzeugung gegen A ist durchlaufen. Vor dem ersten Validation-POST scheiterte
der Testwert `2026-10-25T06:32:00` an `locator.fill: Malformed value`.
Chromium normalisiert `datetime-local` mit Sekunden null auf `YYYY-MM-DDTHH:mm`;
der gepinnte Playwright-Fill prüft den gesetzten String auf exakte Gleichheit.
Der Testformatter lässt deshalb nur in diesem Fall `:00` weg. Zeitpunkt,
Zeitzone, Cutoff-Prüfung und echte Bedienung per `fill()` bleiben unverändert.
Weder Produktlogik noch Timeout, Retries oder Assertions werden gelockert.

Ein fehlgeschlagener Versuch, retry=0; noch kein Approval-/Aktivierungs-/Rückkehr-
Gesamtnachweis. Artefakt `12588786077`, ZIP-SHA-256
`034433811c216caf7d70b1abaf5601e22447d681643ef082ec578da1fc53fef1`, vollständig
geprüftes Manifest mit 26 Inhaltsdateien. Eigener Stack
`tw-candidate-governance-e2e-e6a7f7ca7d5244f6bd612b401f6a90f3` nach verifizierter
Eigentumsprüfung vollständig entfernt, 0 Container/Netze/Volumes,
`exit_status=1`, `cleanup_status=0`. Der folgende Commit benötigt wieder den
vollständigen eigenen Lauf und die regulären Gates.

## Vierter nativer Lauf — 2026-10-25, erfolgreicher Gesamtweg

[Run 40166152063](https://github.com/burckhju/trading-workspace/actions/runs/40166152063),
Governance-Job `121087501390`, Workflowversuch 1, prüfte Head
`1109f047f56e2a3804041c27d4f649f06fb9f9eb` als tatsächlichen PR-Testmerge
`1b31f4111c29b66f91cfe44b2694ae0a0f59f5f6`. Der verifizierte Tree ist
`7c5d25da0dcd65bf5d1cc5076665d1d2f1cfa230`; die rohen Commiteltern sind Main
`fbd77fb94947a1fdbfc0aeb90811353fae655a59` und der genannte Head.

Der entdeckte Hauptfall `e89dce19b56b71e4abc8-2c07670ff21949ff44a4` lief genau
einmal erfolgreich: **1 passed, 0 unexpected, 0 skipped, 0 flaky, retry=0**.
Die Reportdauer beträgt 26,676 Sekunden. Der identische strikte Reportprüfer wurde
im Runner und anschließend lokal gegen das heruntergeladene Rohartefakt ausgeführt.
Das ist der erste erfolgreiche neue Headlauf nach den drei dokumentierten Fehlern,
kein Workflow-Rerun und keine nach Retry grüne Testausführung.

### Konkrete Quellen und gespeicherte Entscheidungen

| Objekt | Tatsächlich gespeicherte Identität dieses Laufs |
|---|---|
| Lesson / gewählte L1 | `14866a24-6248-469e-847a-ea5b00da148e` / `a9b34f84-3b35-4bcb-bc85-eb597a59fb7a` |
| Spätere aktuelle L2 | `80482825-092e-4f89-b0c9-76a3be462d6c`; ersetzt die Hypothesenquelle L1 nicht |
| E1 | `3a7b1a4b-000a-4ba8-aab9-d4837a8896b2`, erstellt `2026-10-25T05:38:40.245972Z` |
| FT011-Quellversion | ExitReview `58e6efde-b9ca-41f1-b5b4-b9b319c6ee50`, Version `bc0ee8c5-f367-4222-aa37-c9a4dc2d57a7`; Trade/Observation-IDs bleiben im vollständigen Ownerkettenattachment erhalten |
| Hypothese / Proposal | `ccc9ea93-0a7a-4a66-b98f-7ff3b7ef380c` / `73f83420-ab8c-47bc-83ce-14c793225245` |
| Modell / genehmigte Basis A | `43a02c22-3031-4483-bcdf-a751dc775d41` / `f042d952-7926-4efc-9d60-3a3c175a8c73` (Version 1, V2-Schema, FAVORABLE + CAUTIOUS) |
| Validation | `75264fc0-f8d0-4792-bcb9-950697e34e03`; exakte E1, Cutoff `2026-10-25T05:38:49Z`, INCONCLUSIVE, Metrics `{}`, ausdrücklich synthetische Notes |
| Approval / B | `0e365bbc-9e41-44e1-bc39-4430c34ce97f` / `d67a1ba4-51ba-4957-997d-ba28d6790625` (Version 2, FAVORABLE only, Vorgänger A) |
| Aktivierung A / B / Rückkehr A | `5ba71473-0fec-4e95-819a-c3cddcf3ae87` / `526991d5-0731-4e9c-8e67-7f28d9e08548` / `1a2e0594-39ec-48cf-a78c-eb30bde667ab` |

S0 und die initiale A-Freigabe/-Aktivierung waren markiertes API-Setup. Die
Hypothese, der DRAFT, die abgewiesene und die gespeicherte Validation, Approval,
B-Aktivierung und Rückkehr wurden tatsächlich über die UI ausgelöst. Jede dieser
Aktionen erzeugte genau den geplanten Browsercommand. Der negative Cutoffversuch
antwortete 422 ohne irgendeine Fingerprintänderung; die anschließende bewusste
Lesefunktion bestätigte weiterhin null Validierungen. Der spätere gültige Command
speicherte einen Befund und genau einen Evidence-Link.

Approval erzeugte B und den Approvaldatensatz, aber **keine** Runtimeaktivierung.
Eine zusätzliche echte Evaluation unmittelbar nach Approval verwendete weiter A.
Der Candidate-Tab zeigte noch A-Readiness, als der andere Tab B aktivierte; erst
die tatsächliche nächste Ausführung löste B auf und persistierte dessen Version.

| Phase / Evaluation-ID | Tatsächlich verwendete Modellversion | TD-MARKET-001 | Gesamtergebnis |
|---|---|---|---|
| S1 `74eda143-3bff-4fbe-a854-b6f2be4941be` | A / 1 | FULFILLED | QUALIFIED |
| S4 nach Approval `ae0bc86d-1875-4397-af9d-707d1b4bb4b3` | A / 1 | FULFILLED | QUALIFIED |
| S5 `ed5fa1a4-aa98-4e83-866f-8c21c988017a` | B / 2 | NOT_FULFILLED | NOT_QUALIFIED |
| S6 `2dd8643b-7ed8-4b84-8493-0c632fff3239` | A / 1 | FULFILLED | QUALIFIED |

Alle vier Ergebnisse haben wahrheitsgemäß Qualität **LIMITED**. Die übrigen fünf
REQUIRED-Kriterien sind jeweils FULFILLED. Alle sonstigen Kriterien und die drei
Quellreferenzen bleiben identisch: MARKET `809596ae-9ef6-4c88-8095-de6bcd819af3`,
SECTOR `a2789d46-c0ac-4a94-a14a-3b0dd4e2a5f8`, UNDERLYING
`f85de620-3c99-477c-be6b-8c73cbe91417`, jeweils Analyseversion 1 und
`EOD_TREND_MOMENTUM/1.0.0`. S7 vergleicht alle gespeicherten Evaluationen mit ihren
ursprünglichen vollständigen Responses, beide ModelVersion-Definitionen und die
ursprünglichen Analyse-Runs. B und seine Ergebnisse bleiben nach der Rückkehr
unverändert über genaue historische Links erreichbar.

### Tatsächlich geprüfte Lesefenster, Isolation, Bilder und Cleanup

Vier reine Lesefenster beobachteten **7 / 3 / 4 / 22 GET-Requests**. In jedem
Fenster sind vollständiger DB-Fingerprint vor/nach identisch und keine schreibende
Browseraktion erlaubt. Der gesamte Requestbeleg enthält 133 API-Requests und
keine Guardverletzung. Observation-Refresh, Materialisierung, Hypothese, Proposal,
Validation, Approval, Aktivierung und alle vier Evaluationen liegen außerhalb
dieser Lesefenster.

Der Lauf verwendete ausschließlich Projekt
`tw-candidate-governance-e2e-d74e5df37268463c8383af63e5adcd31` und DB
`trading_workspace_test_cg_d74e5df37268463c8383af63e5adcd31`, PostgreSQL 17.11,
Schema `20261017_0047`, den synthetischen Defaultworkspace und den exakten
Runmarker. Backend nur im internen Netz, ohne veröffentlichten Port; DB und
Frontend nur auf `127.0.0.1:25432` beziehungsweise `127.0.0.1:8080`. Guardartefakte
binden Container-, Image-, Netz-, Volume- und Mountidentitäten vor Schreibfreigabe.
Die tatsächliche Browserherkunft ist `http://localhost:8080`, API-Präfix
`/api/api/v1`. Provider, Scheduler und Versand bleiben ausgeschaltet; keine
Redirect-/Serviceworker-/WebSocket-Ausweichwege werden zugelassen.

Die sechs nativen PNGs wurden tatsächlich geöffnet und gesichtet: S2 Policy/Basis
Desktop; S4 genehmigte B bei aktivem A Desktop; S5 aktives B Mobil; S7 Rückkehr-A-
Governance Mobil sowie historische B-Auswertung Desktop/Mobil. IDs, gespeicherter
Cutoff/Befund, aktive/neueste/gewählte genehmigte Version und historische
Analysequellen sind erkennbar. Die Mobilansichten sind 390 px breit; die mehrfach
verschachtelten bestehenden Karten führen zu schmalen Textspalten und zahlreichen
Umbrüchen. Controls und vollständige IDs sind erreichbar; eine allgemeine
Layoutmodernisierung oder pixelperfekte Mobilabnahme wird daraus nicht abgeleitet.

Die Sichtprüfung fand zugleich eine weitere konkrete Übergangslücke: Der
Hypothesen-Badge zeigte nach den Childcommands noch den alten OPEN-Stand;
S7 zeigte erst nach Reload CLOSED. Der bestehende Owner setzt bei Proposalanlage
PROPOSED und bei Approval CLOSED. Die enge Folgeänderung
stößt nach bestätigtem Proposal-/Approvalcommand den bereits autorisierten
`listForLessonVersion`-Read an. Währenddessen wird der Status als in Prüfung,
bei Lesefehler als nicht verifiziert angezeigt; die bestätigten Childpanels bleiben
gemountet. Weder Geschäftsstatus noch Commands werden clientseitig rekonstruiert
oder automatisch wiederholt. Überholte und fremde Antworten werden verworfen.
Sieben identische deterministische Componentregressionen waren auf dem unveränderten
Head `1109f047` rot und mit dieser Ergänzung grün, ohne Skips. Sie prüfen PROPOSED,
CLOSED, Lesefehler/bewussten Readretry, überholte Antwort, L1→L2→L1, fremde
Lessonversion und fehlende bestätigte Hypothese. Der Hauptfall fordert diese
Statusreadbacks nun zusätzlich unmittelbar nach DRAFT/Approval, einschließlich
der echten gespeicherten Werte. Sein Nachfolgerlauf und die vollständige CI werden
am neuen Head im PR gebunden; der vierte Pass wird nicht rückwirkend erweitert.

[Artefakt 12588676982](https://github.com/burckhju/trading-workspace/actions/runs/40166152063/artifacts/12588676982),
5.385.956 Bytes, ZIP-SHA-256
`6ad5e35576cd7569bf3a8fb69daf87e864cfe410e65537356630dda22f49b3bf`:
Downloadhash und gesamtes Manifest mit 26 Inhaltsdateien lokal geprüft, einschließlich
aller Bilder, Trace, Rohreport, Quellenketten, Netz-/DB-Identität und Cleanup.
Das ursprüngliche Artefakt wurde für die Sichtprüfung nicht verändert.
Cleanup bestätigt `ownership_verified=true`, `removed=true`, **0 Container,
0 Netze, 0 Volumes**, `exit_status=0`, `cleanup_status=0`.

### Aktualisierter B01–B16-Nachweisstand

| ID | Durch den ausgeführten Schnitt belegter Teil | Verbleibende Bindung / Grenze |
|---|---|---|
| B01 | Gezielte Ausgangsmatrix, bestehende FT-013/019/020-Owner und #274 erhalten; nur bestätigte Lücken ergänzt. | Abschließender Diff/Head im PR. |
| B02 | E1 aus echter FT011-Ownerkette; historische L1 trotz L2; eine Hypothese an L1 und keine an L2; S7 unverändert. | Exakte UUIDs und Responses oben/im Artefakt. |
| B03 | Modell/Hypothese/A im POST; genehmigte Basis, neueste B und aktive A sichtbar getrennt. | Aktueller Kontextschutz zusätzlich durch bestehende Component-/Browserfälle. |
| B04 | V1 und beide V2-Verträge unverändert; No-op und unbekannte Definitionen bleiben geschlossen. | Vollständige Regression des letzten Heads gesondert im PR. |
| B05 | Echter 422-Cutoffversuch ohne Änderung; gespeicherte E1, UTC-Cutoff, INCONCLUSIVE, Notes und Metrics exakt. | Breitere PostgreSQL-Cutoff-/Scopefälle im finalen Backendgate; kein Backtest. |
| B06 | Browserapproval B verändert Aktivierung nicht; weitere echte Evaluation verwendet A; B-Aktivierung folgt separat. | Keine neue Conclusion-Sperre. |
| B07 | LIMITED-A→B→A mit identischen Quellen, fünf erfüllten übrigen Pflichtkriterien und richtigen gespeicherten Versionen tatsächlich bestanden. | **GOOD-Referenz weiterhin nicht erfüllt**; gesonderte FT-006-Qualitätsklärung. |
| B08 | Explizite Auswahl und Aktivierung von A; neue Aktivierungs-ID; B und alle vier Evaluationen unverändert. | Keine Löschung/Retargetierung/automatische Auswahl. |
| B09 | Owner-Scopefix gezielt rot/grün; Cutoffcommand nativ ohne Teilfakten; weitere native Scope-/Stale-/Pair-Grenzfälle vorhanden. | Maßgeblich für die vollständige aktuelle PostgreSQL-Suite ist der finale Runbeleg im PR. |
| B10 | A-Readiness vor Aktivierungswechsel, Ausführung danach korrekt mit B; historische Ergebnisse unverändert. | Fehlende/INSUFFICIENT-/unbekannte Definitionsgrenzen zusätzlich in bestehenden Ownerregressionen. |
| B11 | #274 erhalten; lokale Doppel-/Spätantwort-/Unmountfälle; im nativen Weg jeweils genau ein geplanter Command und bewusster Fehlerreadback. Die anschließende Parent-Statuskorrektur ist oben mit sieben roten/grünen Fällen abgegrenzt. | Ihr eigener finaler nativer Runbeleg steht im PR; keine globale Exactly-once- oder allgemeine Serialisierungszusage. |
| B12 | Ein vollständiger echter S2–S6-Browser→API→PostgreSQL-Lauf einschließlich Rückkehr, retry=0/skip=0/flaky=0. | Nachfolgende Heads brauchen ihren eigenen Nachweis; Setup ist explizit getrennt. |
| B13 | Vier fingerprintgleiche Lesefenster und beobachtete Requests; verifizierte Isolation, keine unerwarteten Requests. | Schreibende Refresh-/Owneraktionen ausdrücklich außerhalb. |
| B14 | Eigener frischer Stack, strikter Report, vollständiges Hashmanifest, sechs Bilder gesichtet, Cleanup ohne Reste. | Mobile Textspalten eng; keine allgemeine Layoutabnahme. |
| B15 | Bestehende Smoke-/Finanz-/Lernjobs, Permissions und Concurrency strukturell identisch; nur eigener Governancejob ergänzt. | Maßgeblich ist die finale CI-Tabelle im PR einschließlich vier alter Ownerfälle, Image, Renderer und Veröffentlichungsschutz. |
| B16 | Fehlversuche, Qualitätsgrenze, noch getrennte CI-/Fach-/Betriebsabnahmen konkret ausgewiesen. | Kein Backtest, wirtschaftlicher Nutzen, PC-Nachweis oder M9-Gesamtabschluss. |

Nach dem Candidate-Anlagefix bestanden lokal **81 Model-/Candidate-Unitfälle**.
Nach der Parent-Statuskorrektur bestanden **83 gezielte Componentfälle**, darunter
die 46 unveränderten #274-Kontextfälle, fünf Candidate-Editorfälle und die sieben
neuen Statusfälle. Anschließend bestand auf der zusammengeführten Arbeitskopie
das vollständige unveränderte `bash scripts/check-frontend.sh`: **122 Dateien /
741 Tests**, Typecheck, Lint, Format und Build; Coverage 93,81 % Statements/Lines,
85,76 % Branches und 86,32 % Functions. Das ist ein aktueller lokaler Gesamtbeleg,
keine Vorwegnahme der folgenden PR-CI.
Die früheren Tabellen bleiben die historischen Vorbelege. Die endgültigen
Backend-/Frontend-/Smoke-/Ownerzahlen werden aus den tatsächlich abgeschlossenen
Reports des letzten Heads übernommen, nicht aus Collection, Zwischenfortschritt
oder automatisch abgebrochenen Vorgängerläufen.
