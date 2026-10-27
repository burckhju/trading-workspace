# Traceability – aktueller Nachweiseinstieg

> Nachweisfortschreibung 26.10.2026, UI3: [Lesson-Ansicht, Quellen und vorbefüllte Prüfung](../implementation/UI_LESSON_CONSOLIDATION.md) verbindet den vorhandenen FT-012-Review-Kontext mit genau einer ausgewählten Inhaltsversion, kompakten exakten Quellen, vollständig vorbefülltem Folgeversionseditor und dem bestehenden Navigationsschutz für Review- und Hypotheseneingaben. Basis ist Main `f8f61a11` / VERSION 1.5.21 einschließlich der integrierten #284/#285; der ältere Tag `v1.5.21` auf `059860ea` ist davon getrennt. Implementierungscommit `986f20a2` / Tree `014efb38`, vollständiger Frontend-Check mit 1.009 Tests, gezielte lokale Nachweise und der lokal nicht ausführbare geschützte PostgreSQL-Ownerlauf sind im Bericht getrennt gebunden; die regulären CI-Nachweise gehören zum tatsächlichen neuen PR-Head. Arbeitsstatus ausschließlich [PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons); kein neuer Release-, Fachabnahme- oder PC-Betriebsnachweis. Historische Qualifikationen und der markierte Baselinebestand unten bleiben unverändert.

> Nachweisfortschreibung 25.10.2026, #278: [FT-006 Runtime-/Quellenqualität](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md) verbindet feste neue Analyseversion 1.0.1, historische 1.0.0-Reproduktion, Snapshot/Hash/Provenienz und den bestehenden Candidate-Consumer mit echten Markt-/Sektorreferenzidentitäten. Die neue GOOD-B07-Browserausführung ist auf Head `18e3e141`, Tree `4c0abfea`, Testmerge `71f16737` in [Run `40182968277` / Job `121137734172`, Versuch 1](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/job/121137734172) tatsächlich bestanden; [vollständiger datierter B07-Nachweis](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md). Der historische LIMITED-Nachweis bleibt erhalten. Die Gesamt-CI des Folgecommits einschließlich der eng reproduzierten Frontend-Testkorrektur wird im bestehenden PR #278 mit eigenen Identitäten gebunden. Arbeitsstatus ausschließlich [PB-013 Analyse](../planning/PRODUCT_BACKLOG.md#pb-013-analysis) und [PB-020 Candidate](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family). Kein Abschluss weiterer M0–M11-Ziele.

> Nachweisergänzung 2026-10-14: [integrierter Handoff-Teilschnitt, PostgreSQL-/Browserbelege und offene Journalstrecke](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md). Die Fortschreibung trennt Prüfcommits, echte DB-Transaktionen und abgefangenes Browser-HTTP. Arbeitsstatus ausschließlich im [zentralen Backlog](../planning/PRODUCT_BACKLOG.md#pb-019-materialization); keine Fach-/Betriebsabnahme.
> Maßgeblich bleiben [PB-019 Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization), [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) und [PB-018 Currentness](../planning/PRODUCT_BACKLOG.md#pb-018-currentness); der historische Bestand unten bleibt unverändert.

> Nachweisfortschreibung 2026-10-15: [Journal-V1 mit echter PostgreSQL-/Browser-Korrekturstrecke](../implementation/FT012_JOURNAL_WRITE_QUALIFICATION.md) verbindet gespeicherten Entwurf, Finalisierung, Folgeversion und explizite Journal-Evidence/Lesson. Prüfcommit `666e8ab…`, Befehle, Artefakte und verbleibender Lesson-Review-Scope im Bericht. Arbeitsstatus ausschließlich [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal); kein Release-/Fachabnahmenachweis.

> Ergänzung 2026-10-15: [explizite Lesson-Prüfung und Folgeversion](../implementation/FT012_LESSON_REVIEW_DOR.md), [ADR zum Quellen-/Widerspruchs- und Transaktionsvertrag](../decisions/ADR-POST-FT012-006-EXPLICIT-LESSON-REVIEW.md). Maßgeblicher Arbeitsstatus ausschließlich [PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons). Neuer Prüfstand separat; historische Journalqualifikation ist kein Ersatz.

> Fortschreibung 2026-10-16: [Lesson-Review mit echter versionierter Evidenzkorrektur](../implementation/FT012_LESSON_REVIEW_QUALIFICATION.md), geprüfter Code `4081563…`, getrennte Currentness-/Relations-/Transaktionsgrenzen und alle drei Gesamtgates. #259/#260 normal integriert; finale #261-Prüfungen/Mergebeleg in dessen PR. Status ausschließlich [PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons), keine Fachabnahme/Release-/Zielbetriebsbehauptung.

## Revision und Verantwortlichkeit

Konsolidiert am 2026-10-13 anhand von `main` / `a78288ad38610656480d0363abe657b567c7ba94` / Softwaretag `v1.5.5`. Diese Ergänzung ist ein Dokumentations-/Nachweisstand zur fachlichen Prüfung, keine neue menschliche Abnahme oder Betriebsfreigabe.

**Nur das [Product Backlog](../planning/PRODUCT_BACKLOG.md#abnahmematrix) führt aktuellen Arbeitsstatus.** Dieses Dokument führt zu Nachweisen und erhält deren Historie. Die unten unverändert erhaltenen Approved-, Accepted-, RC- oder Released-Aussagen gelten für ihre damaligen Umfänge, Daten und Commits, nicht als konkurrierende heutige Statusliste.

## Verbindliche Kette

```text
Ursprüngliches Soll / spätere belegte Präzisierung
→ Umfangsentscheidung bzw. ausdrücklich offene Entscheidung
→ tatsächliche Implementierung und Consumer
→ Testquelle und Ausführung auf identifiziertem Commit
→ fachliche Abnahme
→ Software-Auslieferung und gesonderter Betriebsnachweis
```

Jeder Schritt kann einen eigenen fehlenden Nachweis haben. Ein vorhandener Router, Testquelltext, grüner Workflow oder Softwaretag ersetzt keinen nachfolgenden Schritt. Model-Approval und Runtime-Aktivierung bleiben getrennt. „Nicht geprüft“ ist ein zulässiger Nachweisstand, kein Nullwert oder Funktionsbeweis.

## Einstieg in den aktuellen Nachweisgraphen

| Soll / Entscheidungskontext | Implementierungs-/Consumerquelle | Test-/Abnahme-/Betriebsfelder |
|---|---|---|
| [Alle M0–M11-Inhaltsziele](../planning/PRODUCT_BACKLOG.md#originalzuordnung) und [unveränderte Baseline](archive/ROADMAP_2026-07-22.md) | Bestehende FT-/Owner-Zuordnung im [Katalog](../planning/MODULE_AND_FEATURE_CATALOG.md#ownership) | [Einzige Abnahmematrix](../planning/PRODUCT_BACKLOG.md#abnahmematrix) |
| S1/S2-Referenzdatenverträge; spätere ETF-Präzisierung | [API-Komposition](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py); [UI-Komposition](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [Chart-/ETF-Nachtrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/MARKET_CHARTS.md) | [FT-001](../planning/PRODUCT_BACKLOG.md#pb-006-underlying), [FT-004](../planning/PRODUCT_BACKLOG.md#pb-011-warrants) |
| S5-/S6-/S8-Übergaben; genaue Versionen statt latest | [Golden-Path-Nähte](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md); [konkrete APPROVED-Planversion](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py); [Evaluation versus Selection](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/domain/models.py) | [Candidate](../planning/PRODUCT_BACKLOG.md#pb-012-candidate), [Plan](../planning/PRODUCT_BACKLOG.md#pb-014-assumptions), [Vergleich/Scoregrenze](../planning/PRODUCT_BACKLOG.md#pb-015-comparison) |
| FT-010 SELL/Supersession/Average Cost; Produktwechsel-V1-Abgrenzung | [FT-010-Vertrag und Sep-14-Nachtrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); [Releasevorbereitung / PR #22 / 18fe1df90e4f63529867fc32b5b6441d90738ff4](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.2.0-TRADE-MANAGEMENT.md) | [Execution-/Management-Historie](../planning/PRODUCT_BACKLOG.md#pb-017-history), [Produktwechsel](../planning/PRODUCT_BACKLOG.md#pb-017-product-change) |
| FT-011 nach realem Vollverkauf; COMPLETED/FINALIZED/CURRENT | [Observation-Service](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/observation_service.py); [Handoff-Service](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/handoff_service.py) | [Gelesene Handoff-Tests](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py); [Review-Nachweise](../planning/PRODUCT_BACKLOG.md#pb-018-review) |
| FT-012 besitzt materialisierte Evidence, nicht FT-011 | [Extension 09](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_EXTENSION_09.md); [tatsächlicher UI-Aufruf und Evidence-Readback](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) | [Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization), [Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons) |
| Ursprüngliche Journal-/Performance-Zusage bleibt eigenständig | [Prozessmodell](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/domain/TRADING_PROCESS_MODEL.md); Review/Evidence/Lesson ist kein Ersatzbeleg | [Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal), [Performance](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics) |
| FT-013-Freigabe versus spätere getrennte Runtime-Aktivierung | [V1-Governancevertrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-013_CONTROLLED_MODEL_GOVERNANCE.md); [FT-020-Präzisierung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md); [RuntimeActivationService](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/model/service/runtime_activation_service.py) | [Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance), [Aktivierung/Rückkehr](../planning/PRODUCT_BACKLOG.md#pb-020-activation), [konkrete Kandidatenfamilie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family) |
| Qualität/Zeitsemantik statt erfundener Live-Daten | [IV-/Kursbelege 1.5.4](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.4-IV-DATA-AND-RISK.md); [Abrufdiagnose 1.5.5](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.5-ISSUER-COVERAGE.md) | [Datenbelege](../planning/PRODUCT_BACKLOG.md#market-data-evidence), [JMBbot](../planning/PRODUCT_BACKLOG.md#operations-installation) |

## Historische Präzisierung statt rückwirkender Umschreibung

Der [Konfliktabgleich](../planning/PRODUCT_BACKLOG.md#konfliktaufloesung) ordnet ältere Aussagen den späteren Quellen zu. Insbesondere wird der Golden-Path-Closeout nicht gelöscht: Seine damaligen offenen Materialisierungs-/Aktivierungslücken werden über spätere Quellen erläutert. Auch frühere V1-Nicht-Scope-Aussagen, S6-Reviewstände, STOCK-only-Angaben und historische RC-Notizen werden nicht nachträglich umformuliert.

## Prüf- und Zugriffsschranken

Aktuelle Basis-CI, gelesene Einzelschritte, nicht ausgeführte lokale Befehle und fehlende Quellen-/Betriebszugriffe stehen ausschließlich im [Nachweisregister](../planning/PRODUCT_BACKLOG.md#nachweisregister). Konkrete neue Fachabnahmen, vollständige Live-E2E und eine aktuelle JMBbot-Installation werden nicht behauptet. Die fünf Ausgangsdokumente wurden vor Bearbeitung mit ihren Git-Blob-Hashes abgeglichen; die folgende historische Traceability bleibt bytegenau erhalten (Quellblob `d0cb63972ad37e8644a2f55537e9a3c1702061e1`).

<a id="historische-nachweise"></a>
## Unverändert erhaltener historischer Bestand

<details>
<summary>Historische Traceability am Basiscommit öffnen – keine zweite aktuelle Statusquelle</summary>

<!-- BEGIN UNCHANGED TRACEABILITY BASELINE a78288ad -->
# Traceability

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | TRACEABILITY.md |
| Dokumenttyp | Foundation |
| Version | 1.2 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-11 |

## Zweck

Dieses Dokument verbindet Anforderungen, Architekturentscheidungen, Implementierung, Tests und Abnahme. FT-001 bildet die ursprüngliche Baseline; Sprint 5 ergänzt die Traceability für FT-005/FT-006 Top-down Candidate Qualification.

## Verbindliche Kette

```text
Anforderung → Entscheidung → Implementierung → Test → Abnahme
```

## FT-001 Gesamttraceability

| Ebene | Verbindliche Quellen |
|---|---|
| Anforderungen | `docs/features/underlying/REQUIREMENTS.md`, U-R-001 bis U-R-021 |
| Facharchitektur | `docs/features/underlying/FEATURE.md`, `DATA.md`, `API.md`, `UI.md` |
| Entscheidungen | ADR-S1-001 bis ADR-S1-013, ADR-S2-001 bis ADR-S2-003 |
| Persistenz | `PHYSICAL_DATA_MODEL.md`, `SQLALCHEMY_MODEL.md`, `ALEMBIC_MIGRATION.md` |
| Backend | `REPOSITORY.md`, `DOMAIN_LOGIC.md`, `SERVICE_LAYER.md`, `REST_API.md`, `DTOS.md`, `VALIDATIONS.md` |
| Frontend | `REACT_API_CLIENT.md`, `FRONTEND_VIEWS.md` |
| Testnachweise | `BACKEND_TESTS.md`, `FRONTEND_TESTS.md`, `INTEGRATION_E2E_TESTS.md` |
| Abschluss | `docs/planning/SPRINT_2_CLOSEOUT.md`, `STEP15_REVIEW.md` |

## Implementierungsschritte

| Schritt | Implementierung | Test-/Reviewnachweis |
|---:|---|---|
| 1 Datenmodell | `docs/features/underlying/PHYSICAL_DATA_MODEL.md` | Modell- und Architekturreview im Dokument |
| 2 SQLAlchemy | `backend/app/features/market/persistence/models.py` und Paketmodule | `tests/unit/backend/features/market/test_persistence_models.py` |
| 3 Alembic | `backend/migrations/versions/20260803_0001_ft001_initial_schema.py` | Migrationstests und Offline-DDL-Nachweis |
| 4 Repository | `backend/app/features/market/persistence/repositories.py` | Repositorytests, `REPOSITORY.md` |
| 5 Domain | `backend/app/features/market/domain/` | Domain-Unit-Tests, `DOMAIN_LOGIC.md` |
| 6 Service Layer | `backend/app/features/market/services/` | Service-Tests, `SERVICE_LAYER.md` |
| 7 REST API | `backend/app/features/market/api/` | Router-/OpenAPI-Tests, `REST_API.md` |
| 8 DTOs | `backend/app/features/market/api/dtos.py` | DTO-Vertragstests, `DTOS.md` |
| 9 Validierungen | DTO- und Domainvalidierungen | Validierungstests, `VALIDATIONS.md` |
| 10 Backend-Tests | `tests/unit/backend/features/market/` | 89 erfolgreiche Tests, 92 % FT-001-Paketabdeckung |
| 11 React API Client | `frontend/src/features/market/services/`, `types/` | Client-Tests, `REACT_API_CLIENT.md` |
| 12 Frontend Views | `frontend/src/features/market/pages/` | Komponentenstruktur, `FRONTEND_VIEWS.md` |
| 13 Frontend-Tests | kolokalisierte `*.test.tsx`/`*.test.ts` | 18 erfolgreiche Vitest-Tests, Typecheck und ESLint erfolgreich |
| 14 Integration/E2E | `tests/e2e/`, Docker Compose | gesunde Container, erfolgreicher Build, E2E-Nachweis in `INTEGRATION_E2E_TESTS.md` |
| 15 Dokumentation | README, Feature-Dokumente, Abschlussdokument | `STEP15_REVIEW.md` |

## Kritische Regeltraceability

| Regel | Entscheidung | Implementierung | Nachweis |
|---|---|---|---|
| Unsichtbarer Single Workspace | ADR-S1-004, ADR-S2-001 | `WorkspaceModel`, serverseitige Workspace-Auflösung | Persistenz-, Repository- und Service-Tests |
| Underlying/Listing-Trennung | ADR-S1-002 | Domain- und Persistenzmodelle | Modell- und Domain-Tests |
| ISIN/WKN optional und eindeutig | ADR-S1-006, S1-008 bis S1-010 | partielle Indizes, Normalisierung, Domainvalidierung | Persistenz-, Domain- und Service-Tests |
| Genau eine aktive Primärnotierung | ADR-S1-002 | partieller Unique-Index plus Domaininvariante | Modell-, Domain- und Service-Tests |
| Optimistic Locking | ADR-S1-011 | `version_id_col`, Commands mit erwarteter Version | Domain-, Service-, API- und UI-Tests |
| Audit append-only | ADR-S1-012, ADR-S2-003 | `AuditEventModel`, Append-Repository, atomare UoW | Repository-, Service- und Detail-UI-Tests |
| Kontrollierte Referenzdaten | ADR-S1-007, ADR-S2-002 | Referenztabellen und Read-only API | Migrations-, API-, Client- und View-Tests |
| Löschschutz | ADR-S1-005 | UsageRepository und Serviceprüfung | Service-, API- und UI-Tests |

## Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-08-01 | Sprint-0-Baseline angelegt |
| 0.2 | 2026-08-03 | FT-001- und Sprint-1-Traceability ergänzt |
| 0.3–0.4 | 2026-08-03 | Sprint-2-Datenmodell und SQLAlchemy-Mapping ergänzt |
| 1.0 | 2026-08-04 | Vollständige FT-001-Implementierungs- und Testtraceability abgeschlossen |


## FT-005 / Sprint-5 Candidate Qualification Traceability

| Ebene | Verbindliche Quellen |
|---|---|
| Fachlicher Scope | `docs/features/FT-005_CANDIDATE_QUALIFICATION.md`, `docs/domain/DOMAIN_MAP.md`, `docs/domain/TRADING_PROCESS_MODEL.md` |
| Analysegrundlage | `docs/features/FT-006_MARKET_ANALYSIS.md`, ADR-S4-001/002/005 |
| Top-down-Entscheidungen | ADR-S5-001, ADR-S5-002, ADR-S5-003 |
| Source Resolution / Referenzen | ADR-S5-007, ADR-S5-008 |
| Live-/E2E-Workflow | ADR-S5-009 bis ADR-S5-012 |
| Domain | `backend/app/features/analysis/domain/top_down.py`, `backend/app/features/candidate/domain/` |
| Application | `backend/app/features/candidate/service/` |
| Persistence | `backend/app/features/candidate/persistence/models.py`, Migrationen `0006`/`0007` |
| API | `backend/app/features/candidate/api/`, Top-down-Reference-Administration |
| Frontend | `frontend/src/features/candidate/` |
| Tests | `tests/unit/backend/features/candidate/`, `tests/unit/backend/features/market/test_top_down_*`, `tests/integration/backend/test_top_down_fixture_e2e.py` |
| Review | `docs/implementation/SPRINT_5_ARCHITECTURE_REVIEW_AND_GAP_CLOSURE.md` |

### Kritische Sprint-5-Regeltraceability

| Regel | Entscheidung | Implementierung | Nachweis |
|---|---|---|---|
| Market → Sector → Underlying → Candidate | ADR-S5-001 | Analysis Top-down + Candidate Orchestration | Domain-, Orchestration- und E2E-Fixture-Tests |
| Relative Strength 60 Tage / ±2 pp | ADR-S5-002 | `analysis/domain/top_down.py` | Grenz- und E2E-Tests |
| Kein Candidate Score | ADR-S5-003 | `candidate/domain/qualification.py` | Candidate-Domain-Tests |
| LONG-only Candidate Model 1.0 | ADR-S5-003 | `evaluate_candidate` | Domain-Tests |
| `INSUFFICIENT` Required-Quelle nicht qualifizierbar | ADR-S5-003 | Candidate Qualification | Quality-Grenztests |
| Immutable Evaluation + konkrete Analyseversionen | ADR-S5-003, ADR-S5-007 | Candidate Persistence/Orchestration | Migration-, Service- und Orchestrator-Tests |
| Providerneutrale semantische Referenzen | ADR-S5-007/008 | Market Reference Assignments | Referenzdomain-/Admin-API-Tests |
| Keine stillen Live-Writes | ADR-S5-011/012 | Live Workflow + Action Metadata | Workflow-/API-Tests |

## FT-007 / Sprint-6 TradePlan Specification Traceability

### UI-Fortschreibung 2026-10-25: gebundener Kontext und Approved-Amendment

[PB-014 Planinhalte und Herkunft](../planning/PRODUCT_BACKLOG.md#pb-014-entry)
und [PB-015 bewusste Produktauswahl](../planning/PRODUCT_BACKLOG.md#pb-015-comparison)
→ [begrenzter UI-Auftrag und Qualifikation](../implementation/TRADE_PLAN_SELECTION_CONTEXT.md)
→ einmalige manuelle Basiswertauswahl oder konkrete gespeicherte CandidateEvaluation
→ eine zentrale Planansicht mit genauer Versionsauswahl
→ gemeinsames vollständiges Inhaltsformular für Anlage und Approved-Amendment
→ vorhandener Amendment-Endpunkt mit fester Basis und explizitem Änderungsgrund
→ neue DRAFT-Version bei weiterhin ausdrücklicher Auswahl der bisherigen Freigabe
→ FT-008-Plan-/Versionsbindung und gespeicherter Run ohne neue Schreibaktion.

Der TRIGGER-Referenzfall enthält Referenzpreis, Gültigkeit, sämtliche Begründungen,
drei Targets und alle Risikoangaben; nur These und Änderungsgrund ändern sich im
einzigen Amendment-Request. PRICE und PRICE_RANGE, historische Runs/Trades,
Kontext-/Mutationsschutz, Reparaturrückkehr und Tastatur/390 px werden im aktuellen
UI-Testumfang getrennt nach React-Mocks, Browserfixtures und nativer Umgebung
qualifiziert. Ergebnisse gelten ausschließlich für ihren tatsächlichen Prüfstand.

Die bestehende DRAFT-Rückkehr bleibt eine Statusaktion. Ein allgemeiner
Inhaltsrevisionsvertrag für bereits gespeicherte Entwürfe bleibt offen. Kein
Überschreiben historischer Inhalte, kein Produkteditor-/API-Umbau und keine
unintegrierte Regelübernahme aus #187. Die historische S6-Qualifikation unten
bleibt erhalten und ersetzt den neuen Nachweis nicht.

| Ebene | Verbindliche Quellen |
|---|---|
| Transition Baseline | `docs/planning/SPRINT_6_TRANSITION_BASELINE.md` |
| Feature Specification | `docs/features/FT-007_TRADEPLAN.md` |
| Domain Boundary | `docs/domain/DOMAIN_MAP.md`, `docs/domain/TRADING_PROCESS_MODEL.md` |
| Identity / Versioning | ADR-S6-001 |
| Origin / CandidateEvaluation | ADR-S6-002 |
| Lifecycle / Approval | ADR-S6-003 |
| Amendment | ADR-S6-004 |
| Risk Boundary | ADR-S6-005 |
| Product Neutrality | ADR-S6-006 |
| Provenance | ADR-S6-007 |
| LONG-only | ADR-S6-008 |
| DoR Review | `docs/implementation/SPRINT_6_FT007_SPECIFICATION_AND_DOR_REVIEW.md` |

### Kritische Sprint-6-Regeltraceability – Implementierungsnachweis

| Regel | Entscheidung | Implementierungsnachweis |
|---|---|---|
| langlebige TradePlan-ID + immutable Versionen | ADR-S6-001 | Domain-, Persistence-, Amendment-Tests |
| konkrete CandidateEvaluation statt latest | ADR-S6-002 | Domain-/Service-/Repositorytests |
| explizites versionsgenaues Approval | ADR-S6-003 | Lifecycle-, Service-, API- und Audit-Tests |
| Approved nicht in-place ändern | ADR-S6-004 | Domain-/Concurrency-/Persistence-Tests |
| keine Position Size / Order Quantity | ADR-S6-005 | Domain-/DTO-/API-Vertragstests |
| keine Warrant-/Produktattribute | ADR-S6-006 | Model-/DTO-/Schema-Tests |
| keine FT-005/006-Neuberechnung | ADR-S6-007 | Service-/Integrationstests |
| V1 vollständig LONG-only | ADR-S6-008 | Domain-/DTO-Validierungstests |


### S6-13 Quality-Gate-Nachweis

- Backend: vollständiger Unit-Regressionslauf zuletzt 274/274 in S6-09; nachfolgende FT-007-Units änderten keinen Backend-Produktionscode.
- Frontend: Typecheck, ESLint und Prettier grün; 59/59 Unit-/Component-Tests grün.
- Frontend Coverage: Statements 91.42 %, Branches 77.60 %, Functions 83.47 %, Lines 91.42 %; alle konfigurierten Thresholds erfüllt.
- Production Build: `tsc -b && vite build` grün.
- E2E: 8/8 Playwright-Szenarien grün, einschließlich Manual → Review → Approval, CandidateEvaluation-Provenance und Amendment-Lineage.

| Architecture Review | `docs/implementation/SPRINT_6_ARCHITECTURE_REVIEW.md` – Accepted |


## FT-002 / Sprint-7A Trading Venue Traceability

| Regel | Entscheidung / Spezifikation | Implementierungsnachweis |
|---|---|---|
| stabile provider-neutrale Venue-Identität | ADR-S7-001, FT-002 Feature | bestehendes `TradingVenueModel`, Listing-FK |
| MIC ≠ interne ID ≠ Provider Exchange Code | ADR-S7-001 | Venue-Persistence, ProviderInstrumentMapping, Reconciliation-Tests |
| globale Venue-Identität | ADR-S7-001 | globale Venue-Tabelle; workspace-scoped Provider-Mappings |
| keine stille Provider-Stammdatenmutation | ADR-S7-001 | `VenueReconciliationService`, Mapping-Administration |
| Low-input Venue-Nutzung | FT-002 Feature | `UnderlyingFormPage` Tests und FT-002 E2E Contract |
| Deaktivierung erhält historische Referenzen | FT-002 Feature | Status-Service, Listing-FK `RESTRICT` |
| FT-004 konsumiert stabile Venue-ID | Sprint-7A Architecture Review | Consumer Contract, keine Warrant-Implementierung |
| TradePlan bleibt produktneutral | ADR-S6-006, ADR-S7-001 | keine Venue-Felder in FT-007 |


### Sprint-7A Release Evidence

| Nachweis | Ergebnis |
|---|---|
| Pull Request | #8 |
| Merge Commit | `7f39bc0` |
| Backend CI | PASS |
| Frontend CI | PASS |
| End-to-End CI | PASS |
| Release Status | FT-002 Released |


## FT-003 / Sprint-7B Issuer Traceability

| Regel | Entscheidung / Spezifikation | Implementierungsnachweis |
|---|---|---|
| stabile provider-neutrale Issuer-Identität | ADR-S7-002, FT-003 Feature | `IssuerModel`, Repository-/Service-/API-Tests |
| `issuer_id` ≠ Name ≠ LEI ≠ Provider-ID | ADR-S7-002 | UUID-Persistenz, mutable Stammdaten, LEI-Kontrakte |
| Issuer ≠ Underlying/Underlying-Unternehmen | ADR-S7-002 | keine Underlying→Issuer-Beziehung in FT-003 |
| globale Issuer-Identität | ADR-S7-002 | globale `issuers`-Tabelle ohne `workspace_id` |
| Duplicate Detection ≠ Automatic Merge | ADR-S7-002 | LEI-Konfliktschutz; kein fuzzy-name Merge |
| keine stille Provider-Stammdatenmutation | ADR-S7-002, S7B Gap Review | keine Provider-Issuer-Erzeugung/Reconciliation in FT-003 |
| Lifecycle erhält historische Referenzen | FT-003 Feature | deactivate/reactivate mit stabiler UUID |
| Low-input Issuer-Nutzung | FT-003 Feature | Consumer-Read + separate Admin-UI/API |
| FT-004 konsumiert stabile Issuer-ID | FT-003 Feature, S7B Closeout | expliziter Consumer Contract, keine Warrant-Implementierung |
| TradePlan bleibt produktneutral | ADR-S6-006, ADR-S7-002 | keine Issuer-Felder in FT-007 |


### Sprint-7B Release-Candidate Evidence

| Nachweis | Ergebnis |
|---|---|
| Working Branch | `feature/s7b-ft003-issuers` |
| Baseline | `a3a60cb` / `v0.7.0-trading-venues` |
| Provider Issuer Source | kein belastbarer strukturierter Contract im aktuellen Repository |
| FT-004 Consumer Contract | dokumentiert; keine Warrant-Implementierung |
| Release Status | Implemented – Release Candidate; CI/Merge noch ausstehend |


## FT-004 / Sprint-7C Warrant Traceability

| Regel | Entscheidung / Spezifikation | Implementierungsnachweis |
|---|---|---|
| klassische Call-/Put-Optionsscheine als V1-Scope | ADR-S7-003 | `ProductFamily.WARRANT`, `OptionDirection`, Domain-/API-Tests |
| stabile interne Warrant-Identität | ADR-S7-003 | `WarrantModel.id` als UUID; externe Identifier bleiben Attribute |
| Warrant ≠ Issuer ≠ Underlying ≠ Listing ≠ ProviderInstrument | ADR-S7-003/004/006 | getrennte FKs/Aggregate; keine Provider-ID als Warrant-ID |
| FT-003 Issuer-Contract wird konsumiert | ADR-S7-003 | `issuer_id` FK auf released `issuers`; aktive Referenzprüfung |
| FT-001 Underlying-Contract wird konsumiert | ADR-S7-003 | `underlying_id` FK auf bestehende `underlyings`; keine neue Underlying-Welt |
| Warrant ≠ handelbare Notierung | ADR-S7-004 | separates `WarrantListingModel` |
| TradingVenue gehört zur Notierung | ADR-S7-004 | `WarrantListing.trading_venue_id`; kein Venue-Feld am Warrant |
| Product Terms sind historisch reproduzierbar | ADR-S7-005 | immutable/effective-dated `WarrantTermsVersionModel` |
| Ratio-Semantik ist eindeutig | ADR-S7-005, S7C Architecture Review | Underlying-Einheiten pro Warrant; positive Decimal-Validierung |
| Maturity ≠ administrativer Lifecycle | ADR-S7-003/005 | `maturity_date` in Terms; `ACTIVE/INACTIVE` separat |
| Reference Data ≠ Market Data | ADR-S7-006 | keine Bid/Ask/Spread/Greeks/IV-Felder im Warrant-Aggregat |
| Provider Discovery ≠ stabile Product Identity | ADR-S7-006 | kein spekulatives EODHD-Warrant-Mapping; Capability-Gap dokumentiert |
| konkurrierende Änderungen überschreiben nicht still | FT-004 Service/API | expected-version Contract, `WARRANT_CONCURRENT_MODIFICATION` |
| Duplicate-Identifiers/Listing werden fachlich behandelt | FT-004 Service/API | stabile 409-Fehlercodes + DB-Constraints/Race-Tests |
| FT-008 bleibt außerhalb FT-004 | ADR-S7-003/006 | keine Ranking-, Scoring-, Selection- oder TradePlan-Änderung |
| ein geöffneter Produktkontext für Anzeige und Aktionen | ADR-S7-004, UI-Konsolidierung 25.10.2026 | `WarrantAdminPage`, gemeinsames Produktdetail; `WarrantAdminPageWithDelete.test.tsx` prüft Löschen von Produkt B mit dessen Version, obwohl A zuerst im Katalog steht |
| Terms-Editor übernimmt exakt den aktuellen Stand und hält seine Ausgangsversion | ADR-S7-005, `warrant-strike-currency.md` | `WarrantAdminConsolidation.test.tsx` für PUT, Decimal-Strings, Strike 0, unbekannte Währung, vollständigen `addTerms`-Request und sichtbaren Versionskonflikt; keine historische Mutation |
| Entwürfe und verspätete Antworten bleiben im ursprünglichen Produktkontext | ADR-S7-004, Frontend-Zustandsregeln | Produktseiten-Regressionen sowie `WarrantIdentifierCorrection.test.tsx` und `WarrantValuationEvidence.test.tsx`: unveränderliche Edit-Basis, synchroner Save-Lock, Dirty-/Abbruchpfad, keine veralteten Callbacks auch zwischen Ziel-Commit und passiver Bereinigung |
| ungespeicherte Änderungen bleiben bei abgebrochener Navigation erhalten | Frontend-Formular-/Routingregeln | `useProductNavigationGuard.test.tsx` mit echtem MemoryRouter: Route-Wechsel, Zurück-Navigation mit genauem Ziel, Abbrechen/Verwerfen, laufende Speicherung und `beforeunload`; der native Dialog bindet die Tastaturbedienung an die Entscheidung |
| atomare Anlage und exakter Reparaturrücksprung bleiben erhalten | ADR-S7-004, ADR-S8-002 | `WarrantCreateWithListing.test.tsx`, `WarrantSelectionRepair.test.tsx`, bestehende ProductSelection-Reparatur-/Deep-Link-Tests und `warrant-listing-without-symbol.spec.ts` für tatsächliche Persistenz, historische Runs und Desktop-/Mobilbedienung |
| Produktwechsel, Terms-Änderung und Löschziel sind im Browser bedienbar | ADR-S7-004, Frontend-Barrierefreiheit | `tests/e2e/warrant-admin-consolidation.spec.ts`: Chromium mit synthetischen API-Antworten, 1440/390 Pixel, Tastaturaktionen, Request-Prüfung und Screenshots; dies ersetzt keine native Backend-/Persistenzprüfung |

Die neuen Zeilen bezeichnen die vorgesehenen bzw. ergänzten Regressionen, keine
zusätzliche Fach- oder Releaseabnahme. Der tatsächliche Prüfstand dieses Schnitts
wird ausschließlich im [PB-011-Eintrag](../planning/PRODUCT_BACKLOG.md#pb-011-warrants)
fortgeschrieben; die folgenden Sprint-7C-Ergebnisse bleiben historische Nachweise.

### Sprint-7C Local Release-Candidate Evidence

| Nachweis | Ergebnis |
|---|---|
| Working Branch | `feature/s7c-ft004-warrants` |
| Baseline | `4ad4e044` / `v0.8.0-issuers` |
| Backend full unit/integration suite | 333/333 PASS |
| Backend coverage | 85.04% PASS |
| Backend Ruff | PASS |
| Frontend unit suite | 77/77 PASS |
| Frontend coverage | 90.87% statements/lines, 83.65% functions, 77.62% branches PASS |
| Frontend TypeScript / ESLint / Prettier | PASS |
| Frontend production build | PASS |
| Provider Warrant Source | kein vollständiger belastbarer Contract im aktuellen Repository |
| Release Status | Implemented – Local Release Candidate; protected CI/merge/release pending |

## FT-008 / Sprint-8 Product Selection Architecture Traceability

| Requirement / decision | Architecture evidence | Implementation consequence |
|---|---|---|
| ProductEvaluation ≠ ProductSelection | ADR-S8-001 | no automatic user choice from evaluation/ranking |
| Approved TradePlanVersion handoff | ADR-S8-004 | runs reject non-approved plan versions |
| Historical product context | ADR-S8-002 | evaluation references Warrant + exact TermsVersion + Listing |
| Universe ≠ Eligibility | ADR-S8-003 | exclusions remain explicit and auditable |
| Warrant market data via TC-001 | ADR-S8-005 | no reuse of FT-001 provider mapping as WarrantListing mapping |
| Explainable/versioned evaluation | ADR-S8-006 | model ID/version, inputs, rules, outcomes and provenance persisted |
| No invented V1 thresholds | S8 FT-008 Rule Catalog | numeric filters/scoring wait for explicit model approval |
| Browser-level fail-closed market-data behavior | S8-12 E2E | unverified/missing WarrantListing quote remains NOT_EVALUABLE and selection disabled |
| Evaluation remains separate from user decision | S8-10/S8-12 | eligible fixture still requires explicit confirmation before persisted ProductSelection |
| Live-provider claim boundary | ADR-S8-007/S8-12 | fixture-backed E2E does not imply verified live warrant Bid/Ask capability |

| Provider capability + V1 selection policy | ADR-S8-007 | unverified provider capability fails closed; normal selection requires ELIGIBLE evaluation |

## Sprint 9 / FT-009 specification traceability

| Requirement / decision | Specification evidence |
|---|---|
| Actual purchase capture, no quantity recommendation | `docs/features/FT-009_TRADE_POSITION.md`, ADR-S9-003 |
| Trade / ExecutionRecord / Position separation | ADR-S9-001 |
| Workspace and external origins | ADR-S9-002 |
| Initial and additional purchases | ADR-S9-004 |
| Immutable history and corrections | ADR-S9-005 |
| Optional pre-execution support | ADR-S9-006 |
| V1 rules and non-scope | `docs/implementation/SPRINT_9_FT009_RULE_CATALOG.md` |
| Definition of Ready | `docs/reviews/SPRINT_9_DEFINITION_OF_READY.md` |

### Sprint 9 / FT-009 implementation evidence

| Capability / decision | Implementation evidence |
|---|---|
| Trade / ExecutionRecord / Position separation | `backend/app/features/trade_position/domain/models.py` |
| Workspace-guided purchase origin | `backend/app/features/trade_position/service/application.py`, `service/resolvers.py` |
| External purchase origin | `backend/app/features/trade_position/service/application.py`, FT-004 Warrant consumer resolver |
| Initial purchase capture | `TradePositionService.record_initial_purchase()` |
| Additional purchase / Nachkauf | `TradePositionService.record_additional_purchase()` |
| Immutable execution history | `ExecutionRecord`, append-only execution repository path |
| Derived open position | `Position.from_execution()`, `Position.apply_purchase()` |
| Persistence boundary | Alembic `20260817_0014`, `trades`, `execution_records`, `positions` |
| Transaction boundary | `SqlAlchemyTradePositionUnitOfWork` |
| REST command API | `/api/v1/trade-position/...` |
| Local FT-009 verification | 64 tests passed |
| CI verification | PR #18: Backend quality, End-to-End smoke and Frontend quality passed |
| Delivery | Merge commit `1f98a4a2f4568dbe3e1352c0ae5e5e0c93034c2a` |
| Technical closeout | `docs/implementation/SPRINT_9_TECHNICAL_CLOSEOUT.md` |
| Release readiness | `docs/implementation/SPRINT_9_FT009_RELEASE_READINESS.md` |

### FT-009 release

| Release evidence | Reference |
|---|---|
| Release version | `v1.1.0-trade-position` |
| Release document | `docs/releases/V1.1.0-TRADE-POSITION.md` |
| Implementation merge | `1f98a4a2f4568dbe3e1352c0ae5e5e0c93034c2a` |
| Sprint 9 closeout merge | `3d78e60f3cf89354c195b400c9ecf70f8c126f5f` |

## FT-010 / Sprint 10 Trade Management Traceability

| Requirement / decision | Implementation evidence | Verification |
|---|---|---|
| BUY/SELL execution evolution | `trade_position/domain/enums.py`, models, migration `20260817_0015` | domain/migration tests |
| Effective immutable execution history | execution supersession + effective repository query, migration `20260817_0016` | repository/correction tests |
| Deterministic Position / Average Cost / gross P&L | `domain/projector.py`, migration `20260817_0017` | projector/application tests |
| Partial/full LONG exit | `TradePositionService.record_sale()` | unit, REST, integration, browser E2E |
| Immutable management decisions | `TradeManagementEvent`, migration `20260817_0018` | management/migration tests |
| Corrections preserve audit history | execution and management correction commands | correction/integration tests |
| No duplicate sale truth | `domain/timeline.py` | timeline/REST/integration tests |
| FT-011 only after full exit | `ft011_eligibility()` | unit/REST/integration tests |
| Provider-independent historical sale capture | sale application boundary has no provider/broker dependency | integration + Playwright request contract |
| Frontend active-trade workflow | `frontend/src/features/trade/` | Vitest + Playwright |

Detailed mapping: `docs/implementation/SPRINT_10_FT010_IMPLEMENTATION_TRACEABILITY.md`.

Architecture review: `docs/implementation/SPRINT_10_ARCHITECTURE_REVIEW.md`.

Technical closeout: `docs/implementation/SPRINT_10_TECHNICAL_CLOSEOUT.md`.

Release readiness: `docs/implementation/SPRINT_10_FT010_RELEASE_READINESS.md`.

## Issuer deployment stabilization (1.4.1)

| Requirement | Implementation | Verification |
|---|---|---|
| Preserve the complete existing Compose chain before mutation | `scripts/start-linux.sh` provenance preflight / `--overlay` | `tests/unit/backend/test_start_linux_script.py` |
| Explicit issuer opt-in, renderer health before migration/app recreation | `--issuer-monitoring`, bounded health wait, Alembic `--no-deps` | startup regression tests; existing renderer sandbox CI |
| Read-only preparation and unchanged private configuration | `--check` | startup regression tests |

Scope, acceptance criteria and operational limits: [implementation report](../implementation/ISSUER_DEPLOYMENT_STARTUP.md).

## Dynamic issuer monitoring diagnostics (1.4.2)

| Requirement | Implementation | Verification |
|---|---|---|
| Current issuer jobs, including discovered products, remain visible | `app/tools/audit_monitoring_performance.py` runtime-catalogue scope | `tests/unit/backend/tools/test_audit_monitoring_performance.py` |
| Scheduler completion and positive-bid evidence stay distinct | Per-job evidence, unverified-product list, unchanged quote-time boundaries | Synthetic pending, failed, retained and nonpositive quote regressions |
| Indicative refresh errors remain visible without changing rule status | `rule_issues` includes `refresh_error` | Indicative-error regression; existing concurrency tests |

Scope and acceptance criteria: [implementation report](../implementation/DYNAMIC_ISSUER_MONITORING_AUDIT.md).

## Reviewed legacy issuer migration (1.4.3)

| Requirement | Implementation | Verification |
|---|---|---|
| Preserve effective settings/data during explicit package replacement | `migrate-legacy-issuer.sh`, offline `legacy_issuer_deployment` validator | Validator and shell regression suites |
| Backups and sandbox health precede schema/application replacement | Separate prepare/apply phases; immutable input/image checks | Failure regressions; disposable Docker/PostgreSQL migration in renderer workflow |
| Keep operational evidence distinct from provider/live acceptance | Private state and explicit post-deployment checks | [Implementation/acceptance criteria](../implementation/LEGACY_ISSUER_DEPLOYMENT_MIGRATION.md) |


## Compose integrity correction (1.4.4)

| Requirement | Implementation | Verification |
|---|---|---|
| Identical JSON configuration must tolerate presentation differences | Offline `verify_configuration`; byte-level seals retained | Strict scalar/array/duplicate-key tests; real shell failure reproduction |
| Diagnose an existing prepared release without replacing it | `compose` uses its sealed release root and validates both checkouts | Cross-checkout drift tests; real Docker CI checks unchanged container IDs |
| Keep tool and deployed versions distinct | [Runbook](../technical/LINUX_DEPLOYMENT.md#diagnose-an-existing-prepared-deployment-with-144-tooling) | [Acceptance criteria](../implementation/LEGACY_ISSUER_DEPLOYMENT_MIGRATION.md#compose-integrity-correction-144) |

## JPMorgan price-binding correction (1.4.5)

| Requirement | Implementation | Verification |
|---|---|---|
| Exact route identity without requiring an undisplayed JPMorgan clock | Shared `issuer_pages.parse_product_page`; both price bindings remain mandatory | Missing-clock reproduction and negative binding regressions |
| Consent and route discovery share the same provider evidence | Existing setup, renderer and backend call the same parser | Actual-parser setup/renderer tests; SQL discovery/selection/adapter tests |
| Unknown timestamps and non-executable indications remain explicit | Unchanged quote adapter and indicative policies | Missing-time stream result and retention assertions; full regression suite |
| Safely update the already canonical stack | Existing prepare/apply helper with fresh private state | Second real Docker deployment, DB/consent retention and sandbox checks |

Scope and acceptance criteria: [implementation report](../implementation/JPMORGAN_PRICE_BINDING.md).

<!-- END UNCHANGED TRACEABILITY BASELINE a78288ad -->

</details>

## TC-001 Quellenmodus-/Pacing-Qualifikation — 2026-10-21

[Datenaktualisierung](../planning/PRODUCT_BACKLOG.md#market-data-refresh) und
[Datenqualität](../planning/PRODUCT_BACKLOG.md#market-data-quality) →
[Qualifikationsbericht mit A01–A14](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md).
Basis `5e9ede2dc29f52eaff601d30614df6bc9c25c426` / v1.5.11;
historischer Code-/Testcommit `3d47732665c8b66984923d88a65cf99e74d96791`, Tree
`1b8dd1badb32e9a9d017ffd44656065f1021ac4b`; Dokumentationshead des C-Stands
`bade0e33a67e21b9d2a7e504a798e95ba619dcd0`. Die folgende Tabelle beschreibt
diesen Vorherstand; die anschließend getroffene Entscheidung steht im Nachtrag.

| Gegenstand | Implementierungs-/Vertragsbezug | Neuer begrenzter Nachweis |
|---|---|---|
| Quellenmodus und Zusatzpause | Unveränderte `refresh.py`, Frankfurt-Client/Adapter, `quote_runtime.py`; [Schedulervertrag](../automatic-market-data.md#current-lanes-and-source-mode-pacing-qualification-2026-10-21) | `test_refresh_source_modes.py`: drei Modi mit echtem Resolver/Retention/Adapter/Client und getrennten Warte-/Zugriffszählern; Public zwei HTTP, Snapshots ein Zugriff im Referenzfall |
| Cache, Fehler, Originalzeiten | [Frankfurtvertrag](../frankfurt-quotes.md#source-mode-pacing-qualification-2026-10-21), gemeinsamer prozesslokaler Lock/Cache/Backoff | `test_source_mode_contract.py`: TTL, Retry-After 120 s, koordinierte Leser, alte Datei trotz mtime, fünf Dateifehler und Freigabeschranken |
| Konkurrenz und Lifecycle | Bestehendes Budget nach `_pace()`, Discovery-Deferral, Quote-Fehler, Stop/Join | Zwei echte Budgetkonkurrenzen und Pacing-Cancellation; vorhandene Lane-/Same-Cycle-/Leadergrenztests bleiben erhalten |

322 gezielte Tests auf dem benannten Code-/Testcommit bestanden; keine Skips oder
automatischen Retries. Vollständige statische Backendprüfungen bestanden.
Lokale vollständige PostgreSQL-/Container-/Frontend-/Browsergates nicht
ausgeführt; aktuelle finale PR-CI separat nachweisen. Die Sandbox-
Executorstörung und der korrigierte Ruff-Importbefund sind im Bericht erhalten.
**Historisches Ergebnis C:** Damals keine Produktionsänderung; die zusätzliche
Snapshot-Schedulerpause war noch nicht entschieden. Kein Merge, Release,
Providerzugriff, Nutzerbestands- oder PC-Nachweis folgt aus diesen Tests.

### Nachtrag: Variante 2 entschieden

Die Nutzeranweisung „wie vorgeschlagen gezielt ändern“ entscheidet die zuvor
offene Frage: `_warrant` lässt die zusätzliche `_pace()`-Pause für normalisierte
`HTTPS_JSON`-/`LOCAL_FILE`-Quoteaufrufe entfallen. Publicquote und Publicdiscovery
behalten ihr Pacing; Clientlock/-budget, TTL, Backoff, Rechte, Originalzeiten und
Jobintervalle bleiben erhalten. Implementierungsbezug ist die vorhandene
Providerroute in `refresh.py`, ohne neue MIC- oder Quellenwahlregel.

Neuer Prüfcommit: `187c16b63e0d4dc16b2204f80aec4533c34173e6`; gezielter Prüfumfang/-ausgang:
`344 bestanden, 0 Fehler/Skips/Deselektionen`. Der [Entscheidungsnachtrag mit Abnahmenachweis und
Nachweisgrenzen](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md#nachtrag-variante-2-entschieden)
führt neue Ergebnisse getrennt von den 322 historischen Tests. Die frühere
C-Entscheidung ist damit abgelöst; die vollständigen Gates müssen dem neuen
finalen PR-Head zugeordnet werden. Ihr Einstieg bleibt gegenüber `5e9ede2` und
`bade0e33` unverändert. Der Arbeitsstatus bleibt bis zur Integration
**Technical Review** im Backlog; keine neue CI-, Release- oder Betriebsabnahme.

Mit „Wenn alles grün mergen und für den PC bereitstellen“ hat der Nutzer den
anschließenden Integrations- und Release-Schritt ausdrücklich freigegeben.
Die [Release-Notiz v1.5.12](../releases/V1.5.12-SNAPSHOT-QUOTE-PACING.md) verbindet
diesen begrenzten TC-001-Schnitt mit dem vorhandenen PC-Updateweg. Der finale
PR-Stand und danach der tatsächliche Main-Push müssen unverändert alle Gates
bestehen. Commit-, Run- und veröffentlichter Tagbezug werden in
[PR #271](https://github.com/burckhju/trading-workspace/pull/271) festgehalten;
die technische Installation auf dem PC bleibt ein gesonderter Nachweis.

## FT-012 Journal write continuation — 2026-10-14

[PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) →
[DoR](../implementation/FT012_JOURNAL_WRITE_DOR.md) →
[ADR-POST-FT012-005](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md) →
`learning/application/journal_service.py`, `learning/persistence/journal_repository.py`,
`learning/api/journal_router.py`, `TradeJournalPanel.tsx`, `JournalEvidenceOrigin.tsx`.
Tests: `test_journal_commands.py`, `test_journal_api.py`, `test_journal_source_inspection.py`,
`test_journal_write_postgres.py`, `TradeJournalPanel.test.tsx`, `journalClient.test.ts`,
`post-trade-journal-postgres.spec.ts`. These are trace links, not independent status
or proof that a test has run. FT-011 remains the source-currentness owner; Performance
and Governance only read exact version/source/inspection-time boundaries. M0–M11 unchanged.

### UI6 — Journalansicht und exakte Quellenaufrufe, 2026-10-26

[PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) und der bestehende
ADR-POST-FT012-005-Vertrag → exakter
`/post-trade?trade_id=…&journal_version_id=…`-Aufruf aus `JournalEvidenceOrigin`
→ `TradeJournalPanel` mit einem ausgewählten Textbereich, vorbefüllter Bearbeitung
und fest gebundener Bestätigung → bestehende History-/Versionsreads und
Journalcommands mit getrenntem Receipt und aktuellem Readback.
`PostTradeLearningPage` koordiniert genau einen `PendingNavigationGuard`;
optionale Statusadapter in `LessonDraftFromEvidence` und `PostTradeReviewPage`
erhalten Eingaben und ihre Quelle bei Refresh und schützen laufende Writes.
Der eigenständige FT-011-Evidenceweg und der normale Lesson-POST behalten ihre
eigenen Verträge. Die von UI3 geprüften Journalquellenlinks bleiben kompakt.

Basis ist Main `eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4` / `v1.5.23` einschließlich
UI1–UI5. Der [eigene UI6-Nachweis](../implementation/UI_JOURNAL_CONSOLIDATION.md)
ordnet Abnahmefälle, tatsächlich ausgeführte Prüfungen, Commit/Tree,
PR-#90-Dateikollision und verbleibende Grenzen getrennt zu. Die Übergabe endet
mit einem separaten Draft-PR; daraus folgen keine Statushochsetzung, fachliche
Abnahme, Veröffentlichung oder nachgewiesene PC-Installation. Historische
Journalqualifikationen und vorhandene UI1–UI5-Nachweise bleiben unverändert.

## FT-011/FT-012 consistency and historical inventory — 2026-10-16

[PB-019 Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization) →
[DoR](../implementation/FT011_MATERIALIZATION_CONSISTENCY_DOR.md) →
[ADR-007](../decisions/ADR-POST-FT012-007-MATERIALIZATION-CONSISTENCY.md) →
`post_trade/persistence/materialization_guard.py`,
`post_trade/application/materialization_handoff.py`,
`learning/application/ft011_evidence_history_service.py`,
`learning/api/materialization_router.py`, `Ft011EvidenceHistory.tsx`.
Historical links select the concrete `lesson_version_id` in the existing Lesson
detail. Tests: `test_ft011_consistency_postgres.py`,
`test_materialization_handoff.py`, `test_ft011_evidence_history.py`,
`post-trade-evidence-history-postgres.spec.ts` and matching React regressions.
These are trace links, not a second status register or a claim of completed runs.
No migration, provider, automated interpretation or new financial owner.

Qualification of the defined FT-011/FT-012 consistency/inventory slice:
[exact code/test commit, PostgreSQL races, browser and full-gate evidence](../implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md).
This trace extends the existing PB-019 link; no second status or human acceptance.

## Realized gross SELL arithmetic and period readiness — 2026-10-17

[PB-017 Brutto-PnL](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) and
[PB-019 Periodenauswertung](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
→ [source matrix, DoR and decisions still required](../implementation/PERIOD_REALIZED_GROSS_READINESS.md)
→ accepted ADR-S10-002/004 and the existing FT-010 owner
→ `trade_position/domain/projector.py::PositionProjector.project_with_trace`
→ `test_projector_trace.py`, `test_realized_gross_trace_postgres.py`
→ [exact qualification and code references](../implementation/PERIOD_REALIZED_GROSS_QUALIFICATION.md).

This additive trace preserves one arithmetic loop and the existing Position
contract. The complete effective execution prefix explains each SELL's cost
basis, including earlier sales. Synthetic EUR assumptions do not establish user
execution currencies. Monetary report API/UI, the proposed report snapshot,
currency capture/confirmation and domain acceptance remain separate requirements.
No new FT-ID, migration, release, automatic evidence or target-installation claim.

## Explicit currency and period report continuation — 2026-10-17

The preceding trace-only entry remains the historical first-stage evidence. The
later explicit user instruction “Ok, umsetzen” accepts the concrete follow-up
contract in [ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md).

[PB-017 currency/position owner](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl)
and [PB-019 period report](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
→ approved [source/period contract](../implementation/PERIOD_REALIZED_GROSS_READINESS.md)
→ `trade_position/service/currency_confirmations.py`, migration `20261017_0047`
and all existing actual capture commands, including Learning `execute-as-trade`
→ existing `PositionProjector.project_with_trace()`
→ `performance/service/reader.py`, `performance/domain/report.py`,
`GET /api/v1/performance/realized-gross`
→ `frontend/src/features/performance/pages/RealizedGrossPage.tsx` and the existing
trade/selection capture and booking-history UI
→ `test_execution_currency_confirmations_postgres.py`,
`test_realized_gross_report_postgres.py`, period/API/domain/frontend unit contracts
and `tests/e2e/realized-gross-report-postgres.spec.ts`
→ [exact code and qualification record](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md).

One response's summary, counts, rows and provenance share a bounded read snapshot;
explicit corrections may change subsequent responses. Currency declarations are
append-only owner data, not a second execution ledger or report-generated fact.
The definition is gross realized SELL output, not full M8/portfolio performance.
Current status stays only in the linked backlog; no release or PC claim follows.

## Realized gross report publication boundary — 2026-10-18

The later explicit instruction to merge after successful checks and make the
result available for the PC authorizes the bounded release continuation.
The exact recovered implementation tree is
`fc12f0f7fa8d8e8157be3a9dc3818169301c48ec`, published as recovery commit
`d8dc36f5f891a6dd29cb0a0a8dba41d485201f76`; the historical qualification commits
above keep their original test meaning.

[PB-019 period output](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
→ separate current-main integration of the priority integrity fix #249
→ `scripts/run-realized-gross-e2e.sh`
→ additional `End-to-End / realized gross owner` job in the existing workflow
→ unchanged guarded PostgreSQL/browser report scenario, with exactly one passing
case and no skip, retry or flaky result
→ [1.5.9 release and managed PC update contract](../releases/V1.5.9-REALIZED-GROSS-REPORT.md).

The existing publication workflow also requires successful actual main-push
Backend, Frontend and End-to-End workflows for the precise tagged commit.
Published software, migration 0047 and real target installation remain separate
evidence; this trace neither invents historical execution currencies nor closes M8.

## A: Navigation — 2026-10-25

[PB-007 Basiswertverwaltung](../planning/PRODUCT_BACKLOG.md#pb-007-underlying-ui)
→ bestehender [PR #204](https://github.com/burckhju/trading-workspace/pull/204)
→ [FT-001 Listen-/Formularvertrag](../features/underlying/FEATURE.md)
→ `UnderlyingListPage`, `UnderlyingDetailPage`, `UnderlyingFormPage` und
`underlyingListNavigation`
→ [aktuelle Navigationsqualifikation A01–A14](../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md).

Der bestehende Branch integriert Main `fbd77fb94947a1fdbfc0aeb90811353fae655a59`
/ v1.5.14 ohne Konflikte und bewahrt #249/#267, #269/#271/#273 sowie #274/#275.
Die aktuelle Ergänzung ändert keine zusätzliche Produktivlogik: kontrollierte
Detail-/DELETE-Antworten nach A→B→A, falsche Detail-ID, reine Rückzieländerung
während offenem PATCH auf Desktop/Mobil und strengere vollständige FT-001-
API-/Mutationsverträge werden neu qualifiziert. Der vorhandene deterministische
`flushSync`-Nachweis bleibt erhalten.

122 fokussierte Tests, das vollständige Frontend-Gate mit 780 Tests und 24
synthetische Browserfälle sind den im Bericht genannten Quelltrees zugeordnet.
Die vollständige reguläre PR-CI einschließlich der vier vorhandenen Ownerfälle
wird mit finalem Head, tatsächlichem Checkout/Tree, Run/Job und Versuch im PR
dokumentiert; alte grüne Läufe ersetzen sie nicht. Mock-HTTP, PostgreSQL-Nachweis,
Main-Merge, Veröffentlichung und beobachteter PC-Betrieb bleiben getrennt.
Dieser Abschnitt betrifft nur A; bestehende und spätere B-Nachweise bleiben
unverändert erhalten.

## FT-001 Formularintegrität nach PR #249 — 2026-10-20

[PB-007 Basiswertverwaltung](../planning/PRODUCT_BACKLOG.md#pb-007-underlying-ui)
→ [FT-001 U-R-002/013/015/018](../features/underlying/REQUIREMENTS.md)
→ [Formularvertrag](../features/underlying/FEATURE.md#sicheres-formular-bei-navigation-und-ladefehlern)
→ `frontend/src/features/market/pages/UnderlyingFormPage.tsx`
→ `UnderlyingFormIsolation.test.tsx` und
`tests/e2e/underlying-form-isolation.spec.ts`.

Der ursprüngliche Schutz aus [PR #249](https://github.com/burckhju/trading-workspace/pull/249)
ist seit 18.10.2026 gemergt. Die Ergänzung auf Basis von
`254fe35b76027b72cd989715e17bd0ae55af55eb` bindet gleichwertige Querykodierungen
an denselben stabilen Parametersnapshot und deaktiviert verlassene Formulare
bereits in der Layout-Phase. Die Regressionen prüfen Eingabenerhalt bei gleicher
Formularidentität und alte Speicherantworten zwischen Ziel-Commit und passivem
Cleanup; der Ladeeffekt behält sein eigenes Abbruchkennzeichen. UUID, geladene
Version, kontrollierte Referenzen sowie STOCK-/ETF-Verträge bleiben erhalten.

Die exakten Prüfheads, ausgeführten Ergebnisse, Browserartefakte und CI-Läufe
stehen im zugehörigen Folge-PR. Diese Zuordnung übernimmt keine historischen
Testerfolge als Nachweis für den neuen Stand. Der Aufgabenstatus bleibt allein in
PB-007; [PR #204](https://github.com/burckhju/trading-workspace/pull/204) und dessen
Listen-Navigation bleiben separat. Daraus folgen weder Mergefreigabe noch neue
fachliche Abnahme, Release- oder Betriebsnachweise.

## Purchase currency reuse — 2026-10-20

[PB-017 execution owner](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) and
[PB-019 period output](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
→ user's explicit instruction to reuse the entered purchase currency for sales
→ [ADR-S10-008 amendment](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
→ shared pure execution-owner currency resolution with exact source IDs
→ additive capture/timeline/history/report read fields, unchanged direct confirmations
→ existing capture forms without repeated SELL entry or an extra currency checkbox
→ backend resolver and API tests, real PostgreSQL owner/report correction cases,
and the existing isolated browser scenario extended to actual BUY/SELL entry
→ [precise source inventory, contract and qualification](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md).

Definition `realized-gross-sell-v2` changes currency qualification only; owner
arithmetic and bounded report snapshot remain unchanged. There is no migration,
automatic historical currency backfill or new feature ID. The historical V1.5.9
test references above do not serve as tests for this amendment.


## 2026-10-26 — UI4: Tradeübersicht und Buchungsansicht

[PB-016 Positionsübersicht](../planning/PRODUCT_BACKLOG.md#pb-016-positions) und
[PB-017 Event-Historie](../planning/PRODUCT_BACKLOG.md#pb-017-history)
→ bestehende ADR-S10-002-/007-/008-Verträge und S11-005-Currentness
→ eine zusammenhängende `TradeManagementPage`-Übersicht mit Backendwerten
→ `ExecutionDatesPanel` als gemeinsamer Timeline-Read für aktuelle Buchungen,
Historie und einen exakt gebundenen Datum-/Währungseditor
→ rein darstellende `TradeTimelinePanel`, aus `TradeAlertsPanel` herausgelöst
→ unveränderte Korrektur- und Currency-Confirmation-Endpunkte mit getrennten
Retry-/Replayverträgen
→ vorhandener `PendingNavigationGuard`, geteilt über den tradebezogenen Kontext,
und Refresh ohne Verlust paralleler Managemententwürfe
→ [UI4-Akzeptanzmatrix, konkrete Prüfeinstiege und Nachweisgrenzen](../implementation/UI_TRADE_BOOKINGS_CONSOLIDATION.md).

Ausgangsbasis ist `f8f61a11f65e9b36735704a2fabc3e4e953d4a77`, Version 1.5.21.
Der eigenständige Branch `refactor/trade-bookings-consolidation` enthält weder
UI3-Learning-/Hypothesenänderungen noch eine Versionserhöhung. Die UI3-Implementierung `986f20a2` und der vor Übergabe erneut gelesene
[UI3-Draft-PR #286](https://github.com/burckhju/trading-workspace/pull/286)
mit Head `89bad2a4ecfb5915c78dacde150edea533f6b0f0` bleiben getrennt. Dessen
Lesson-Backlog-/Traceability-Fortschreibung und gemeinsame Journal-Browserfälle
werden von UI4 nicht verändert. Ursprüngliche Fakten, vollständige Supersession-IDs, getrennte
Ausführungs-/Erfassungszeiten und belegte beziehungsweise unbekannte
Währungsherkunft bleiben nachvollziehbar.

Die Seiten-/Editorregressionen, bestehenden Backend-Ownerfälle und ausgewählten
Browserfälle werden am finalen Implementierungsstand im Draft-PR gebunden.
Geroutete UI-Mocks belegen keine finanzielle Persistenz; dafür stehen die echten
BUY-/SELL-Korrektur- und Währungsherkunftsfälle auf einem isolierten synthetischen
PostgreSQL-Stack. Lokales PostgreSQL 16.15 und reguläres PostgreSQL-17-PR-Gate
bleiben getrennte Nachweise. Keine neuen Backendformeln, Migrationen,
Mengen-/Preiskorrektur-Oberflächen, Review-Neufinalisierung, Release- oder
Betriebsabnahme werden aus dieser UI-Konsolidierung abgeleitet. Die historischen
FT-009-/FT-010- und Währungsqualifikationen oben bleiben unverändert erhalten.

**Anschließende Integrationsfreigabe vom 26.10.2026:** Nach dem UI3-Merge auf
`eb443bdf7569b5a187b4be97dba1e1fcb7a0ed0f` ist die gemeinsame Qualifikation von
UI3 und UI4 sowie bei grünen Prüfungen die Integration und PC-Bereitstellung als
**1.5.22** beauftragt. Der [Integrationsnachtrag](../implementation/UI_TRADE_BOOKINGS_CONSOLIDATION.md#nachtrag-26102026-freigegebene-integration-und-pc-bereitstellung)
trennt den ursprünglichen UI4-Prüfstand von den neuen PR-/Main- und Tag-Nachweisen.
Die Freigabe ändert keinen fachlichen Backlogstatus und belegt keine bereits
erfolgte Installation auf dem Ziel-PC.

## Read-only trade-source composition — 2026-10-21

[PB-018 historical currentness](../planning/PRODUCT_BACKLOG.md#pb-018-currentness) and
[PB-019 separation of decision quality and result](../planning/PRODUCT_BACKLOG.md#pb-019-decision-quality)
→ [bounded source/read contract](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md)
→ `trade_position/service/source_view.py` and `api/source_router.py`
→ existing TradeManagementPage source mode / `TradeSourcesView.tsx`
→ `test_source_view.py` (33 executed cases), `TradeSourcesView.test.tsx` (22 executed cases)
→ five native cases in `test_trade_source_view_postgres.py`: first full run 3 passed /
2 fixture failures, corrected without changing owner rules; final run tracked in PR #272
→ actual protected browser path in `support/trade_source_journey.ts`, first passed on
8cc68f6 / checkout dbe9819, plus six guarded EOD-seed contract tests.

Fresh local regressions cover 680 unit cases in affected backend areas and the
unchanged full frontend gate (598 tests). This is not the full backend gate or
a Browser→API→PostgreSQL qualification. The final delivery receipt binds the new
reconstruction to a concrete local commit/tree; no identity with the previously
claimed unretained implementation is asserted. Closed-report #270 integration,
final full CI, human acceptance and publication remain distinct. Publication as
[Draft-PR #272](https://github.com/burckhju/trading-workspace/pull/272) and the first
real source browser run are now evidenced in the qualification addendum. Earlier
local-only limits above are historical; no closed-report integration is inferred.

## 2026-10-21 — separate closed-report/source-view integration

The follow-up combines pinned #270 (`de413843`) and #272 (`95086541`) on
`integration/closed-trade-result-sources`, not main. It adds the approved list →
qualified result/exact sources → original filter/page return. No new FT/PB or
monetary/quality owner is introduced. `ClosedTradeResult` and validated context
reuse `closed-trade-gross-v1` and the existing exact source readers. Financial
and optional read windows remain separate. The whole-report fingerprint is not
claimed to identify a particular trade change or restore a historical report.

[Integration inventory, contract and A1–A16 test map](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md)
links the new UI tests, augmented guarded native browser journeys and unchanged
PostgreSQL concurrency contracts. Actual full-gate runs, final checkout/tree and
visual review are bound in the integration PR; earlier dependency CI is not reused
as a new integration success. Human acceptance and M7/M8 completion remain separate.

### 2026-10-21 — concurrent main advance retained in source integration

Main advanced separately through #271 to `5c76ff49` (existing v1.5.12 metadata)
while the integration's `f1898487` full gates were running. The final audit detected
the different base and did not promote those passing results to current-main
readiness. The integration branch incorporates that exact main as a separate
parent, preserving both documentation histories and the already merged pacing
change. No main write, new release or dependency upgrade is performed here.
Fresh whole-tree CI and both native journeys are required on the combined head;
PR #273 binds the new results separately from the genuine earlier successes.

## 2026-10-23 — joint source journey and journal/FT-011 qualification

The concrete Startprompt 11 extends development PR #273 with the existing #269
journal/evidence qualification, preserving both original heads as merge parents.
Main `5c76ff49` and #270/#272/#271 ancestry are retained. Only the two conflict
blocks in `e2e.yml` require semantic integration: the union of trigger paths and
all three unchanged job definitions. No monetary, learning, migration or dependency
implementation is replaced. The twelve other #269 files are inherited unchanged.

[Existing A1–A16 plus joint I01–I16 evidence map](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md)
→ unchanged SELL and closed-trade owner cases in separate fresh stacks
→ separate journal/FT-011 job with its two existing pinned cases
→ actual final checkout/tree, raw report identities, artifact hashes, screenshots
and full-gate results recorded in [PR #273](https://github.com/burckhju/trading-workspace/pull/273).
Historical per-branch successes are not a joint execution and are not added together.
The Product Backlog remains authoritative; human acceptance, main merge, publication
and observed PC operation are not inferred from this development qualification.

## 2026-10-24 — Strang B: Proposal-Kontextintegrität

[PB-020 Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance) und
[bestehende Candidate-Familie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family)
→ [FT-020-Kontextvertrag](../features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md#context-bound-proposal-entry)
→ `HypothesisProposalPanel.tsx`: gebundene Hypotheseninstanz, aktuelle Modell-/
Versionsgeneration, vollständiger Handler-Guard und synchron gesperrter Submit-Snapshot
→ 46 kontrollierte Component-/Parent-/Candidatefälle plus fünf unveränderte FT-020-Fälle
→ sieben synthetische Browserfälle über den vorhandenen Lesson-Router, einschließlich
Desktop/Mobil und altem Save bei echtem Unmount
→ zusätzliche native Fehlzuordnungs-/DRAFT-Regression auf der bestehenden
`ModelGovernanceService`-/PostgreSQL-Grenze
→ [Reproduktion, erhaltene Schutzmechanismen und B01–B14-Nachweismatrix](../implementation/MODEL_PROPOSAL_CONTEXT_QUALIFICATION.md).

Mock-HTTP, native Transaktion und vollständige CI bleiben getrennte Nachweise.
Head, tatsächlicher PR-Testmerge/Tree, aktuelle Jobs und Versuche werden im
Entwicklungs-PR des Branches `fix/model-proposal-context-isolation` festgehalten.
Strang A/#204, Backend-Produktionslogik, Runtime-Semantik, Versionen und Workflows
bleiben unverändert. Der Product Backlog bleibt die einzige Aufgabenstatusquelle;
dieser Nachtrag erklärt weder Fachabnahme noch Merge, Release oder PC-Installation.

## 2026-10-25 — B: Candidate-Governance

[PB-020 Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance),
[Aktivierung/Rückkehr](../planning/PRODUCT_BACKLOG.md#pb-020-activation) und
[Candidate-Familie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family)
→ bestehende FT-013/019/020-Owner und unveränderter #274-Erfassungsschutz
→ verifizierter Lesson-Snapshot als Hypothesenquelle, additive gespeicherte
Validation-Evidence- und Candidate-Analysequellenprojektion
→ bewusste Auswahl einer erhaltenen APPROVED-Version im bestehenden
Runtime-Aktivierungsconsumer und genaue historische Evaluationslinks
→ [Übergangsmatrix, B01–B16 und Qualifikationsgrenzen](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md).

Basis ist `fbd77fb94947a1fdbfc0aeb90811353fae655a59`, Tree
`027e1d0546f4c09d761ac10d1f59e87d613aff41`, v1.5.14, Schema `20261017_0047`.
59 Backend- und 115 UI-Fälle sind die gezielten Ergebnisse der getrennten
Arbeitskopien. Anschließend bestanden auf der zusammengeführten Arbeitskopie
80 Model-/Candidate-Unitfälle (81 nach dem nativen Candidate-Anlagefix), die vollständige Backend-Statik, das unveränderte
Frontendgate mit 121 Dateien / 734 Tests und Build sowie 153 reine Python- und
21 Node-Guardfälle. Diese Ergebnisse werden nicht zu einer Suite addiert.
Der neue geschützte Browser→API→PostgreSQL-Gesamtfall bestand erstmals in Run
`40166152063`, Job `121087501390`, Head `1109f047`, tatsächlicher Checkout
`1b31f411`, Tree `7c5d25da`: genau ein Pass ohne Retry/Skip/Flaky. Konkrete
L1/E1-/Entscheidungs-/Versionsketten, vier historische Evaluationen, vier unveränderte
Lesefenster, sechs tatsächlich gesichtete Bilder und vollständiger Cleanup sind
im Bericht gebunden. Drei vorherige Fehlversuche bleiben sichtbar. Die Sichtprüfung
begründet den engen Parent-Hypothesenstatus-Readback nach Proposal/Approval.
Der Entwicklungs-PR bindet abschließend die native Grenzfallsuite und sämtliche
Gates am letzten Head, tatsächlichen Checkout/Tree und Run/Versuch; ein früherer
grüner Head oder v1.5.14-Report ersetzt diesen Gesamtnachweis nicht.

Die reale FT-006-Abbildung von Preisqualität VALID zu Analysequalität LIMITED
verhindert die verlangte GOOD-Referenz von B07. Sie bleibt als konkrete Restarbeit
ausgewiesen, auch wenn ein späterer LIMITED-A→B→A-Lauf besteht; dieser Schnitt
ändert keine FT-006-Semantik. A/#204 und die vier vorhandenen Finanz-/Lernownerfälle
bleiben unabhängig erhalten. Keine Statushochsetzung, neue Fachregel, Backtest-/
Überlegenheitsbehauptung, M9-Gesamtabnahme, Veröffentlichung oder PC-Beobachtung
wird aus dieser Entwicklungsqualifikation abgeleitet.

## 2026-10-25 — #278: ausgeführter GOOD-B07-Nachtrag

Die zuvor ausdrücklich offene GOOD-Referenz ist nun eigenständig nachgewiesen:
[FT-006-Ownerintegration und Qualifikation](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md)
→ zwei echte MARKET_REFERENCE-Owner und ein Listingowner mit expliziter
Analyse-Runtime 1.0.1, Originalflags/-warnungen, Snapshot/Hash und unveränderter
Legacy-Reproduktion
→ bestehender Candidate-Resolver und unveränderte Policies
→ [nativer GOOD-A/A/B/A-Beleg](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md)
auf `18e3e141` / Tree `4c0abfea` / PR-Testmerge `71f16737`, Run `40182968277`,
Job `121137734172`, Versuch 1, Artefakt `12594962453`. Genau ein erwarteter
Governancefall ohne Retry/Skip/Flaky, drei konkrete GOOD-Quellen, unveränderte
Historie, 14 Verify- und vier GET-Fingerprintfenster, sechs gesichtete Bilder
und vollständiger Cleanup sind belegt. Die vier Finanz-/Lernownerfälle sind
auf demselben Stand ebenfalls bestanden.

Der historische LIMITED-Bericht oben bleibt unverändert. Der erste kombinierte
Frontendlauf hatte einen kontrolliert reproduzierten Select-Laderace in einem
bestehenden Test; die Korrektur wartet auf die tatsächliche Option und erhält
alle ursprünglichen Assertions. Der aktuelle PR bindet den Folgecommit und
seine vollständigen regulären Gates separat. B07-Abschluss ist keine
Fachabnahme, Main-Integration, Veröffentlichung, PC-Beobachtung oder
Gesamtabnahme der offenen M0–M11-Modellziele. Arbeitsstatus bleibt ausschließlich
in den betroffenen PB-013-/PB-020-Einträgen.

## 2026-10-25 — Berichtswährung fest EUR

[PB-019 Perioden- und Tradeauswertungen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
→ ausdrücklicher Nutzerwunsch nach fester Euro-Berichtswährung
→ [ADR-S10-008-Nachtrag](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
→ zwei bestehende Berichtsformulare mit schreibgeschütztem EUR und explizitem
API-Filter, sichtbare Abweisung eines Nicht-EUR-Abschlusslistenlinks ohne Ersatzread
→ erhaltene Ownerrechnung, Währungsbestätigungen und Quellen-/Antwortbindung
→ [enger Schnitt und neue Qualifikation](../implementation/REPORT_EUR_UI_QUALIFICATION.md).

Die bisherigen fünf nativen Ownerfälle und ihre Runner bleiben erhalten. Reale
Quellenlücken sind keine Nullbeträge und werden durch die feste Berichtsauswahl
nicht bestätigt. Keine neue Kennzahl, Migration oder vollständige M8-Abnahme.

## 2026-10-25 — begrenzte Basisstatistiken für vollständige Abschlussberichte

[PB-019 Tradeübergreifende Statistiken](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics)
→ neuer ausdrücklicher Nutzerauftrag vom 25.10.2026, getrennt von ADR-S10-009
→ [Vertrag `closed-trade-statistics-v1` und vorab festgelegte Sollwerte](../implementation/CLOSED_TRADE_STATISTICS_V1.md)
→ reine Backendaggregation bereits qualifizierter vollständiger Ownerergebnisse
und der vorhandenen Berichtsgesamtsumme
→ additiver Statistikbereich desselben GET mit eigener Definition und exakter
`report.basis.id`, ohne Änderung des Finanz-/Quellenfingerprints
→ bestehende Abschlussübersicht mit Backendwerten, Gründen und Population des
gesamten Berichts, unabhängig von lokaler Tabellenansicht und Seite
→ gezielte Domain-/API-/UI-Referenzen und ergänzte Assertions im unveränderten
nativen Abschlussberichtfall, unter den bestehenden regulären PR-Gates.

Der neue Schnitt umfasst ausschließlich Trefferquote, Durchschnitt, Median und
Profit-Faktor brutto bei `COMPLETE` mit N > 0. Nullgründe bei unvollständiger
oder leerer Auswahl und fehlendem Verlustnenner bleiben ausdrücklich sichtbar.
Die ursprünglichen Quellen-, Korrektur-, Read-only- und Navigationsverträge
gelten weiter. Tatsächliche Head-/Tree-/Run- und Bildnachweise werden im
Statistik-Draft-PR gebunden; die älteren Erfolge anderer PRs ersetzen sie nicht.
Keine neue Feature-ID, allgemeine Backlogbereinigung, Fachgesamtabnahme,
Merge-, Release- oder PC-Freigabe.
