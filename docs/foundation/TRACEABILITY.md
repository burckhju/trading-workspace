# Traceability

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | TRACEABILITY.md |
| Dokumenttyp | Foundation |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-10 |

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
