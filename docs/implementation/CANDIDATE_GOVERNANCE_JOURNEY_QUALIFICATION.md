# B — Candidate-Governance: Benutzerweg und Qualifikationsgrenzen

Stand: **2026-10-25, Entwicklungsqualifikation; nativer Gesamtweg und finale CI noch offen.**
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
| Aktueller Entwicklungsnachweis | Gezielte Prüfungen auf getrennten Arbeitskopien sowie unten getrennt ausgewiesene lokale Prüfungen der zusammengeführten Arbeitskopie; noch kein unveränderlicher finaler PR-Tree/CI-Lauf nachgewiesen |
| Finaler PR-Head / tatsächlicher Checkout / Tree | **Offen.** Im Entwicklungs-PR an den final geprüften Stand zu binden; ein PR-Testmerge ist nicht der Branch-Head oder ein Main-Merge |
| CI-Run / Job / Workflowversuch / Testversuch | **Offen.** Für diesen neuen Schnitt noch kein nativer Browserlauf und keine finale Gesamt-CI ausgeführt |

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

## Übergangsmatrix

**Vorhanden und geprüft** bezeichnet ausschließlich die jeweils genannte lokale
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
SUPPORTS-only-Geschäftsregel einzuführen. Seine Ausführung ist noch offen.

### Harte Grenze: Preisqualität VALID wird im Analyseowner LIMITED

[`MarketAnalysisService.run`](../../backend/app/features/analysis/service/application.py)
übernimmt `DailyPrice.quality_status.value` in den Snapshot. Die unterstützte
Preisqualität heißt `VALID`; der vorhandene
[`calculator.calculate`](../../backend/app/features/analysis/domain/calculator.py)
stuft Zeilen mit `quality_status != "GOOD"` als LIMITED ein. Damit liefern auch
vollständige ownererzeugte Analysen der vorgesehenen synthetischen VALID-Preise
`LIMITED` / `COMPLETED_WITH_WARNINGS`. Der gezielte Code-/Berechnungsabgleich
bestätigt diese Abbildung; ein neuer nativer Ownerlauf wird dadurch nicht behauptet.

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

## Ausgeführte lokale Prüfungen und offene native Nachweise

Diese Ergebnisse gehören zu gezielten Entwicklungsprüfungen, nicht zur noch
fehlenden Gesamtprüfung des final integrierten Trees. Die Fallzahlen sind aktuelle
Beobachtungen, keine künftig festgeschriebenen Suitegrößen.

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

## Vorgesehene native Ausführung und Artefaktbindung

Der neue [geschützte Hauptfall](../../tests/e2e/candidate-governance-journey-postgres.spec.ts)
heißt `candidate governance: exact Lesson source, explicit A-B-A and immutable evaluations`.
Der [Runner](../../scripts/run-candidate-governance-e2e.sh) und der additive Job
`candidate-governance-owner` in [.github/workflows/e2e.yml](../../.github/workflows/e2e.yml)
sind für seine tatsächliche Ausführung vorgesehen. Der
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
versteckter/nestierter Dateien und Cleanup. Noch gibt es hierfür keine neu
ausgeführten nativen Artefakte.

Unverändert zu erhalten und auf dem finalen Stand tatsächlich auszuführen sind
die beiden Finanzfälle `realized-gross-report-postgres.spec.ts` und
`closed-trades-report-postgres.spec.ts` sowie die beiden Lernfälle
`post-trade-journal-postgres.spec.ts` und
`post-trade-evidence-history-postgres.spec.ts`. Der neue Job ersetzt und benennt
keinen davon um. Produktionsimage, Renderer, reguläre Backend-/Frontend-/Smoke-Gates
und Veröffentlichungsschutz bleiben verbindlich; neue globale Schreibflags,
erhöhte Berechtigungen oder ein allgemeiner CI-Umbau gehören nicht zum Schnitt.

## B01–B16: aktueller Nachweisstand

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

## Übergabegrenze

Der nächste technische Handoff muss finalen PR-Head, tatsächlichen Checkout/Tree,
Run/Job, Workflowversuch, Testversuch und Artefaktmanifest nachtragen. Bis dahin
ist dieser Stand implementiert und gezielt lokal geprüft, **nicht vollständig
technisch abgenommen**. B07 bleibt auch bei bestandenem LIMITED-Hauptlauf in der
oben genannten GOOD-Referenz offen. Kein realer Nutzermodelleintrag wurde für
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
