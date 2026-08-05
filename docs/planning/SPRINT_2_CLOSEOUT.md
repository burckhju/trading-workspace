# Sprint 2 – Abschluss FT-001 Basiswertverwaltung

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Sprint | Sprint 2 |
| Feature | FT-001 Basiswertverwaltung |
| Status | Implemented – Final Documentation Complete |
| Datum | 2026-08-04 |

## Zielerreichung

FT-001 wurde vertikal über Datenmodell, Persistenz, Repository, Domain, Service Layer, REST API, DTOs, Validierungen, Backend-Tests, React API Client, Frontend Views sowie Integrations- und E2E-Testartefakte umgesetzt.

Es wurden keine weiteren Fachfeatures implementiert. Die Sprint-1-Architektur wurde erweitert, aber nicht ersetzt. Technische Konkretisierungen wurden in ADR-S2-001 bis ADR-S2-003 dokumentiert.

## Implementierungsnachweis

| Bereich | Nachweis |
|---|---|
| Datenmodell | `docs/features/underlying/PHYSICAL_DATA_MODEL.md` |
| SQLAlchemy | `docs/features/underlying/SQLALCHEMY_MODEL.md` |
| Migration | `docs/features/underlying/ALEMBIC_MIGRATION.md` |
| Repository | `docs/features/underlying/REPOSITORY.md` |
| Domain | `docs/features/underlying/DOMAIN_LOGIC.md` |
| Service Layer | `docs/features/underlying/SERVICE_LAYER.md` |
| REST API | `docs/features/underlying/REST_API.md` |
| DTOs | `docs/features/underlying/DTOS.md` |
| Validierungen | `docs/features/underlying/VALIDATIONS.md` |
| Backend-Tests | `docs/features/underlying/BACKEND_TESTS.md` |
| React API Client | `docs/features/underlying/REACT_API_CLIENT.md` |
| Frontend Views | `docs/features/underlying/FRONTEND_VIEWS.md` |
| Frontend-Tests | `docs/features/underlying/FRONTEND_TESTS.md` |
| Integration/E2E | `docs/features/underlying/INTEGRATION_E2E_TESTS.md` |

## Qualitätsnachweis

Nachgewiesen wurden:

- 89 erfolgreiche Backend-Tests,
- erfolgreicher TypeScript-Typecheck,
- ESLint ohne Warnungen oder Fehler,
- 18 erfolgreiche Vitest-Tests,
- erfolgreicher Frontend-Produktionsbuild,
- erfolgreicher Docker-Compose-Build und gesunde PostgreSQL-, Backend- und Frontend-Container,
- vier erfolgreiche Playwright-Szenarien im ersten Compose-Lauf.

Der zunächst fehlgeschlagene Foundation-E2E-Test war auf eine veraltete Sprint-0-Überschrift gekoppelt. Der Test wurde auf die aktuelle FT-001-Startseite umgestellt. Eine vollständige erneute Compose-/Playwright-Ausführung nach dieser letzten Korrektur ist im Zielsystem noch als finaler Betriebsnachweis auszuführen.

## Architekturreview

- Underlying und Listing bleiben getrennte Aggregatebestandteile.
- Workspace-Isolation ist durchgehend umgesetzt.
- Referenzdaten werden nicht im Frontend dupliziert.
- Repositorys steuern keine Transaktionen.
- Domain und Service Layer bleiben von FastAPI und React unabhängig.
- Fachänderung und Audit-Event werden atomar persistiert.
- Optimistic Locking verhindert stilles Überschreiben konkurrierender Änderungen.
- Audit-Events bleiben append-only und vom Lebenszyklus gelöschter Aggregate unabhängig.
- UI-Filter werden serverseitig auf dem vollständigen Datenbestand ausgeführt.
- Keine parallelen Implementierungen oder doppelte Datenhaltung wurden eingeführt.

## Abschlussstatus

**Sprint 2 ist implementierungs- und dokumentationsseitig abgeschlossen.**

Vor einer produktiven Freigabe ist der korrigierte Gesamtstand einmal vollständig über folgende Befehle in der vorgesehenen Ziel- oder CI-Umgebung auszuführen:

```bash
./scripts/check-backend.sh
./scripts/check-frontend.sh
./scripts/run-e2e.sh
```
