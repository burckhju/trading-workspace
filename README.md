# Trading Workspace

Technisches Repository des Trading Workspace.

## Status

Sprint 0 – technisches Grundgerüst.

Dieses Repository enthält die verbindliche Repositorystruktur, den Backend-Bootstrap,
die Datenbankinfrastruktur, den technischen Core, die fachlich neutrale Shared-Schicht
den Frontend-Bootstrap, die Docker-Umgebung sowie CI- und Testautomatisierung.
Fachlogik und Implementierungen der Features FT-001 bis FT-013 sind nicht Bestandteil
dieses Stands.

## Struktur

- `backend/` – Python-/FastAPI-Backend
- `frontend/` – React-/TypeScript-Frontend
- `docs/` – verbindliche Projekt-, Architektur- und Entwicklungsdokumentation
- `tests/` – übergreifende Testbereiche
- `scripts/` – projektweite Automatisierungsskripte
- `docker/` – Container- und Deployment-Artefakte
- `.github/` – GitHub-spezifische Konfiguration

Die verbindlichen Architektur- und Entwicklungsregeln befinden sich unter `docs/`.

## Verbindliche Backend-Konventionen

- Feature-Domain-Schicht: `domain/`
- Backend-Einstiegspunkt: `backend/app/main.py`

## Backend starten

Aus `backend/`:

```bash
python -m pip install --requirement requirements.txt
python -m uvicorn app.main:app
```

Der technische Liveness-Endpunkt ist unter `GET /health` verfügbar. Der
Datenbank-Readiness-Endpunkt ist unter `GET /health/ready` verfügbar.

## Datenbank

Die technische Persistenzschicht verwendet PostgreSQL, SQLAlchemy Async und Alembic.
SP-003 enthält noch keine fachlichen Tabellen oder Feature-Repositorys. Details stehen
unter `docs/implementation/SP-003_DATABASE.md`.

## Technischer Core

Der Backend-Core umfasst zentrale Konfiguration, strukturiertes Logging,
Fehlerbehandlung, Request-Kontext, Application Dependency Injection und kontrolliertes
Lifecycle-Management. Authentifizierung und Autorisierung sind mangels verbindlicher
Detailvorgaben noch nicht implementiert.

## Shared

Die Shared-Schicht enthält ausschließlich fachlich neutrale Typen, Value Objects,
Zeitfunktionen, Verträge und Validatoren. Details stehen unter
`docs/implementation/SP-005_SHARED.md`.

## Frontend starten

Aus `frontend/`:

```bash
npm install
npm run dev
```

Der technische Frontend-Bootstrap verwendet React, TypeScript, Vite, React Router und
Tailwind CSS. Er enthält ausschließlich eine neutrale Sprint-0-Startseite und eine
404-Seite. Fachliche Routen und Feature-Oberflächen sind nicht enthalten. Details stehen
unter `docs/implementation/SP-006_FRONTEND_BOOTSTRAP.md`.

## Docker starten

Aus dem Repository-Stamm:

```bash
cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yml up --build
```

Der Stack stellt PostgreSQL, das FastAPI-Backend und das über Nginx ausgelieferte
Frontend bereit. Das Frontend ist standardmäßig unter `http://localhost:8080`
erreichbar. Technische Backend-Endpunkte können direkt über Port `8000` oder über den
Nginx-Präfix `/api` aufgerufen werden. Details stehen unter
`docs/implementation/SP-007_DOCKER.md`.

## Qualitätssicherung

GitHub Actions führt getrennte Backend-, Frontend- und End-to-End-Quality-Gates aus.
Die entsprechenden lokalen Prüfläufe stehen unter `scripts/` bereit. Details und bekannte
Einschränkungen stehen unter `docs/implementation/SP-008_CI_AND_TESTS.md`. Der konsolidierte
Status der verbliebenen externen Punkte steht unter
`docs/implementation/SPRINT_0_OPEN_POINTS.md`.

## Implementierungsstand

- SP-001 Repositorystruktur: abgeschlossen
- SP-002 Backend Bootstrap: abgeschlossen
- SP-003 Datenbank: abgeschlossen
- SP-004 Core: abgeschlossen
- SP-005 Shared: abgeschlossen
- SP-006 Frontend Bootstrap: abgeschlossen
- SP-007 Docker: abgeschlossen
- SP-008 CI & Tests: abgeschlossen
