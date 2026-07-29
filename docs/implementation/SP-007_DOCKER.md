# SP-007 Docker

## Ziel

Reproduzierbare Containerisierung des technischen Sprint-0-Grundgerüsts ohne Fachlogik und ohne Implementierung der Features FT-001 bis FT-013.

## Containerarchitektur

Der lokale Compose-Stack besteht aus drei Services:

- `database`: PostgreSQL mit persistentem Named Volume und `pg_isready`-Healthcheck
- `backend`: FastAPI-Anwendung als nicht privilegierter Benutzer mit technischem Liveness-Healthcheck
- `frontend`: mehrstufig gebautes React-Frontend, ausgeliefert durch Nginx

Nginx stellt die Single-Page-Anwendung auf Port `8080` bereit. Requests unter `/api/` werden ohne den Präfix `/api` an das Backend weitergeleitet. Damit ist für Browserzugriffe eine gemeinsame Origin möglich, ohne CORS-Konfiguration vorwegzunehmen.

## Dateien

- `backend/Dockerfile`
- `backend/.dockerignore`
- `frontend/Dockerfile`
- `.dockerignore`
- `docker/compose.yml`
- `docker/.env.example`
- `docker/nginx/default.conf`

## Lokaler Start

Aus dem Repository-Stamm:

```bash
cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yml up --build
```

Danach sind verfügbar:

- Frontend: `http://localhost:8080`
- Backend direkt: `http://localhost:8000`
- Backend über Nginx: `http://localhost:8080/api/health`
- PostgreSQL: `localhost:5432`

Vor dem Start muss das Beispielpasswort in `docker/.env` geändert werden. Die Datei `docker/.env` wird durch `.gitignore` ausgeschlossen.

## Lifecycle und Healthchecks

- PostgreSQL muss gesund sein, bevor das Backend gestartet wird.
- Das Backend muss seinen Liveness-Endpunkt erfolgreich beantworten, bevor das Frontend als abhängiger Service gestartet wird.
- Der Frontend-Container besitzt den separaten Nginx-Endpunkt `/healthz`.
- Alle Services verwenden `restart: unless-stopped`.

Der bestehende Datenbank-Readiness-Endpunkt `/health/ready` bleibt unverändert und ist nicht der Docker-Healthcheck des Backends. Dadurch wird zwischen Prozess-Liveness und externer Abhängigkeitsbereitschaft unterschieden.

## Abgrenzung

Nicht Bestandteil von SP-007 sind:

- Kubernetes oder andere Orchestrierungsplattformen
- TLS-Terminierung und öffentliche Domains
- Secret Stores
- produktive Registry- und Releaseprozesse
- automatische Alembic-Migrationen beim Containerstart
- CI-Ausführung und Image-Publishing
- Feature-spezifische Infrastruktur

## Validierung

Die Compose-Datei, Docker-Buildkontexte, Healthcheck-Kommandos, Environment-Verweise und Nginx-Routen wurden strukturell geprüft. Die bestehenden Backend-Regressionstests wurden erneut ausgeführt.

Docker oder eine kompatible Container-Runtime war in der Ausführungsumgebung nicht installiert. Deshalb konnten `docker compose config`, Image-Builds und ein tatsächlicher Stack-Start hier nicht ausgeführt werden.

## Offene Freigabepunkte

Die Projektdokumente schreiben die Technologien vor, enthalten aber keine freigegebenen Container-Image-Digests. Die verwendeten Major-/Minor-Tags müssen vor einem produktiven Release durch freigegebene Digests ersetzt werden.

Das Frontend besitzt weiterhin keine Lockdatei, weil die npm-Registry in SP-006 nicht verfügbar war. Der Container verwendet daher technisch notwendig `npm install`; nach Erzeugung einer freigegebenen Lockdatei ist dies auf `npm ci` umzustellen.
