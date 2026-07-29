# SP-003 Datenbank

## Ziel

Bereitstellung der technischen PostgreSQL-Persistenzinfrastruktur ohne fachliche Tabellen, Repositorys oder Featurelogik.

## Umsetzung

- SQLAlchemy 2 mit asynchronem PostgreSQL-Treiber `asyncpg`
- anwendungsweit verwaltete Async-Engine und Session Factory
- verbindliche SQLAlchemy-Namenskonventionen für Constraints und Indizes
- request-scoped FastAPI-Dependency für Datenbanksessions
- Alembic-Migrationsumgebung mit asynchroner Engine
- datenbankgestützter Readiness-Endpunkt `GET /health/ready`
- konfigurierbarer Connection Pool und kontrolliertes Engine-Disposal im Lifespan

## Abgrenzung

SP-003 erzeugt bewusst keine Datenbanktabellen und keine leere Baseline-Revision. Migrationen werden erst zusammen mit einer fachlich spezifizierten physischen Datenbankänderung erzeugt. Dadurch entstehen weder Platzhaltermigrationen noch vorweggenommene Featureentscheidungen.

## Betrieb

Die Verbindung wird über `TRADING_WORKSPACE_DATABASE_URL` konfiguriert. Erwartet wird eine SQLAlchemy-URL mit dem Treiber `postgresql+asyncpg`. Zugangsdaten gehören ausschließlich in die Laufzeitumgebung und nicht in das Repository.

Migrationen werden aus `backend/` ausgeführt:

```bash
alembic upgrade head
```

Eine neue Revision wird erst für eine freigegebene physische Schemaänderung erzeugt:

```bash
alembic revision --autogenerate -m "beschreibung"
```
