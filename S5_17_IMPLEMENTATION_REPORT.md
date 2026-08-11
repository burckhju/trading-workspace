# S5.17 – Architecture Review & Gap Closure

## Umgesetzt

- Product Backlog auf tatsächlichen FT-005-/FT-006-Stand synchronisiert.
- PB-012/PB-013-Abhängigkeit korrigiert; kein zirkulärer Backlog mehr.
- Feature-Katalog für FT-005/FT-006-Leserichtung und Top-down-Abhängigkeit synchronisiert.
- Domain Map um CandidateEvaluation sowie Benchmark-/Sektor-Referenzbeziehungen ergänzt.
- FT-005 Candidate Qualification V1 als Feature-Dokument ergänzt.
- Sprint-5-Traceability ergänzt.
- Sprint-5-ADRs in die etablierte `docs/decisions`-Ablage überführt und zentral indiziert.
- Architecture Review mit expliziten verbleibenden Gates dokumentiert.
- direkte Candidate-Service-Persistence-Queries in `SqlAlchemyCandidateRepository` verschoben.
- offensichtliche Router-Formatierungsdrift bereinigt.

## Tests

- `PYTHONPATH=backend python -m pytest -q` → **230 passed**.
- Candidate-/Top-down-Fokuslauf → **24 passed**.
- Python Compile-/Importcheck → grün.
- Alembic-Revisionskette manuell geprüft: `0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007`.

## Nicht als bestanden behauptet

- Ruff / Black / mypy / Coverage: Toolchain in diesem Paket nicht vollständig verfügbar.
- Frontend TypeScript/Lint/Vitest/Coverage/Build: `node_modules` fehlen.
- PostgreSQL Upgrade/Downgrade: keine reale PostgreSQL-Umgebung verfügbar.
- Live EODHD E2E: Credentials/validierte reale Konfiguration fehlen.
- Playwright/E2E in vollständiger Umgebung.
- Git-Cleanliness/PR/Branch-Protection: ZIP enthält kein `.git`.

## Offener fachlicher Scope

FT-005 heißt weiterhin „Watchlisten und Kandidaten“. Sprint 5 enthält Candidate Qualification und den Lifecycle-Zustand `WATCHING`, aber kein eigenständiges generisches Watchlist-Aggregat. Vor der Erklärung „FT-005 vollständig abgeschlossen“ ist eine explizite Entscheidung erforderlich, ob `WATCHING` V1 genügt oder ein separater Watchlist-Teil noch folgt.

## Status

Candidate Qualification V1: **Technical Review bestanden / architektonisch konsistent**.

Sprint 5 gesamt: **noch nicht final abgeschlossen**, bis die dokumentierten Release-/Quality-Gates und die Watchlist-Scopeentscheidung geklärt sind.
