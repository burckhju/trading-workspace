# Trading Workspace

Produktionsnahes Referenzrepository für den **Trading Workspace**.

## Status

- Sprint 0 – technische Basis: abgeschlossen
- Sprint 1 – fachliche Architektur: abgeschlossen und freigegeben
- Sprint 2 – FT-001 Basiswertverwaltung: released
- Sprint 3 – Market Data / EODHD / Provider-Abstraktion: released
- Sprint 4 – FT-006 Market Analysis: released
- Sprint 5 – FT-005 Candidate Qualification V1: released
- Sprint 6 – FT-007 TradePlan: released als `v0.6.0-trade-plan`
- Sprint 7A – FT-002 Trading Venues: released
- Sprint 7B – FT-003 Issuers: noch nicht begonnen

Die Repository-Implementierung und die akzeptierten ADRs/Feature Books bilden die verbindliche Architektur-Baseline. Sprint-7A erweitert die bestehende TradingVenue-Identität und führt keine parallele Venue-Stammdatenwelt ein.

## Implementierter Umfang FT-001

- Basiswerte mit primärer Notierung anlegen
- Basiswerte suchen und nach Lifecycle, Handelsplatz und Währung filtern
- Details, Notierungen, Verwendungen und Änderungshistorie anzeigen
- Stammdaten und Listings ändern
- Primärnotierung atomar wechseln
- Basiswerte verifizieren, deaktivieren und reaktivieren
- unreferenzierte Fehleinträge physisch löschen
- kontrollierte Handelsplätze und Währungen verwenden
- Optimistic Locking und append-only Audit-Historie

## Struktur

- `backend/` – FastAPI, SQLAlchemy Async, Alembic und FT-001-Backend
- `frontend/` – React-/TypeScript-Anwendung und FT-001-Oberflächen
- `docs/` – verbindliche Projekt-, Architektur-, Feature- und Betriebsdokumentation
- `tests/` – projektweite Integrations- und E2E-Tests
- `scripts/` – lokale Qualitäts- und Ausführungsskripte
- `docker/` – PostgreSQL-, Backend- und Frontend-Stack

## Lokale Qualitätsprüfung

```bash
./scripts/check-backend.sh
./scripts/check-frontend.sh
./scripts/run-e2e.sh
```

`check-backend.sh` verwendet eine vorhandene Python-Umgebung oder richtet bei fehlenden Entwicklungswerkzeugen eine lokale `backend/.venv` aus `requirements-dev.txt` ein.

## Anwendung mit Docker starten

```bash
cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yml up --build
```

- Frontend: `http://localhost:8080`
- Backend direkt: `http://localhost:8000`
- Backend über Nginx: `http://localhost:8080/api`
- Liveness: `GET /health`
- Readiness: `GET /health/ready`
- FT-001 REST API: `/api/v1`

## Backend lokal starten

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements-dev.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

## Frontend lokal starten

```bash
cd frontend
npm ci
npm run dev
```

Erforderlich sind die in `.nvmrc` und `package.json` festgelegten Node-/npm-Versionen.

## Verbindliche Dokumentation

- Feature Book: `docs/features/underlying/FEATURE.md`
- Architekturentscheidungen: `docs/decisions/`
- physisches Datenmodell: `docs/features/underlying/PHYSICAL_DATA_MODEL.md`
- REST API: `docs/features/underlying/REST_API.md`
- Betriebs- und Entwicklungsanleitung: `docs/technical/DEVELOPMENT_GUIDE.md`
- Sprint-2-Abschluss: `docs/planning/SPRINT_2_CLOSEOUT.md`
- vollständige Traceability: `docs/foundation/TRACEABILITY.md`
