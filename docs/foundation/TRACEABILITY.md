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
