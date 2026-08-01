# Development Guide

> Verbindliche Entwicklungs- und Arbeitsanleitung für den Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-015 |
| Dokument | DEVELOPMENT_GUIDE.md |
| Dokumenttyp | Guide |
| Version | 1.1 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | noch offen |
| Freigabedatum | noch offen |

---

# Zweck

Dieses Dokument beschreibt den verbindlichen Entwicklungsprozess des **Trading Workspace**.

Es beantwortet die Frage:

> Wie wird die Software eingerichtet, entwickelt, geprüft, dokumentiert und übergeben?

Der Guide gilt für alle Entwickler, Reviews, Automatisierungen und zukünftigen ChatGPT-Sitzungen.

---

# Grundsätze

Die Entwicklung erfolgt

- featureorientiert,
- nachvollziehbar,
- reproduzierbar,
- testgetrieben beziehungsweise testbegleitet,
- in kleinen überprüfbaren Schritten,
- ohne autonome Handelsentscheidungen durch die Software.

Die fachliche Entscheidung verbleibt immer beim Benutzer.

---

# Verbindliche Quellen

Vor einer Änderung sind mindestens zu berücksichtigen:

```text
README.md
docs/foundation/
docs/features/
docs/reference/
docs/architecture/
docs/technical/
docs/implementation/
```

Für die technische Ausführung sind insbesondere maßgeblich:

```text
backend/pyproject.toml
backend/requirements.txt
backend/requirements-dev.txt
frontend/package.json
frontend/.npmrc
docker/compose.yml
scripts/
.github/workflows/
```

Bei einem Widerspruch zwischen Dokumentation und ausführbarer Konfiguration muss der Widerspruch vor Freigabe geklärt werden.

---

# Entwicklungsablauf

Jede Änderung folgt grundsätzlich diesem Ablauf:

```text
1. Feature und Anforderungen lesen
2. betroffene Referenz- und Architekturdokumente lesen
3. Ist-Zustand des Codes prüfen
4. Änderung und Auswirkungen planen
5. Implementierung durchführen
6. Tests und Qualitätsprüfungen ausführen
7. Dokumentation aktualisieren
8. Diff prüfen
9. Review und Übergabe durchführen
```

Nicht direkt mit der Implementierung beginnen, wenn Anforderungen, Datenmodell oder Verantwortlichkeit unklar sind.

---

# Arbeitsbereich

Eine Arbeitseinheit bearbeitet grundsätzlich

- ein Feature,
- einen Fehler,
- eine technische Verbesserung oder
- eine klar abgegrenzte Dokumentationsänderung.

Unabhängige Änderungen werden nicht in denselben Commit aufgenommen.

Änderungen an gemeinsamen Contracts, Datenformaten oder Architekturregeln müssen ausdrücklich als projektweite Auswirkung behandelt werden.

---

# Voraussetzungen

## Unterstützte Werkzeuge

| Werkzeug | Version beziehungsweise Quelle |
|---|---|
| Python | `backend/.python-version`, aktuell 3.12 |
| Node.js | `frontend/.nvmrc`, aktuell 22.16.0 |
| npm | `frontend/package.json`, aktuell 10.9.2 |
| Docker | aktuelle unterstützte Docker-Engine mit Compose V2 |
| Git | aktuelle unterstützte Version |

Zusätzlich empfohlen:

- Bash-kompatible Shell,
- `curl`,
- ein Editor mit Python-, TypeScript-, ESLint- und Markdown-Unterstützung.

## Voraussetzungen prüfen

Im Repository-Stamm:

```bash
bash scripts/verify-release-readiness.sh
```

Das Skript prüft mindestens:

- Python,
- Node.js,
- npm,
- Docker,
- Backend-Abhängigkeitsdateien,
- Python-Versionsdatei,
- Node-Versionsdatei,
- Frontend-Lockdatei.

Ein fehlendes `frontend/package-lock.json` ist ein offener Sprint-0-Punkt und verhindert reproduzierbare Frontend-Installationen mit `npm ci`.

---

# Repository beziehen

```bash
git clone <repository-url>
cd trading-workspace
```

Aktuellen Stand prüfen:

```bash
git status
git branch --show-current
git log --oneline -5
```

Das Arbeitsverzeichnis soll vor Beginn einer neuen Änderung sauber sein.

---

# Backend einrichten

## Virtuelle Umgebung

Im Repository-Stamm:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## Abhängigkeiten installieren

```bash
python -m pip install --upgrade pip
python -m pip install --requirement requirements-dev.txt
```

`requirements-dev.txt` bindet die produktiven Abhängigkeiten aus `requirements.txt` bereits ein.

## Backend lokal starten

Voraussetzung ist eine erreichbare PostgreSQL-Datenbank und eine konfigurierte Umgebung.

Beispiel:

```bash
cp .env.example .env
```

Die Datei `.env` darf nicht versioniert werden.

Start:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Backend-Endpunkte prüfen

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/ready
```

Die API-Dokumentation ist nur verfügbar, wenn sie in der Umgebung aktiviert ist.

---

# Frontend einrichten

## Node.js-Version aktivieren

Mit `nvm`:

```bash
cd frontend
nvm use
```

Falls die Version noch nicht installiert ist:

```bash
nvm install
nvm use
```

Prüfen:

```bash
node --version
npm --version
```

Erwartet werden die in `.nvmrc` und `package.json` definierten Versionen.

## Lockdatei

`frontend/package-lock.json` muss im Repository versioniert sein.

Die Lockdatei wird ausschließlich durch npm erzeugt und nicht manuell bearbeitet.

Erstmalige Erzeugung, solange sie noch fehlt:

```bash
npm install
```

Nach Aufnahme der Lockdatei gilt für lokale Entwicklung und CI verbindlich:

```bash
npm ci
```

`npm install` darf danach nur verwendet werden, wenn Abhängigkeiten bewusst geändert und `package.json` sowie `package-lock.json` gemeinsam aktualisiert werden.

## Frontend lokal starten

```bash
npm run dev
```

Standardmäßig wird die Vite-Entwicklungsumgebung verwendet.

Die API-Basisadresse wird über die dokumentierte Frontend-Umgebung konfiguriert.

## Frontend-Build prüfen

```bash
npm run build
```

---

# Umgebungsvariablen

## Grundregel

Versioniert werden ausschließlich sichere Beispieldateien:

```text
backend/.env.example
frontend/.env.example
docker/.env.example
```

Lokale Dateien wie `.env` dürfen nicht eingecheckt werden.

## Docker-Umgebung anlegen

Im Repository-Stamm:

```bash
cp docker/.env.example docker/.env
```

Vor Verwendung müssen insbesondere Passwörter und lokale Ports geprüft werden.

Beispielwerte wie `change-me` dürfen nicht in einer produktiven Umgebung verwendet werden.

## Geheimnisse

Nicht zulässig im Repository sind:

- Passwörter,
- API-Schlüssel,
- Tokens,
- Broker-Zugangsdaten,
- private Zertifikate,
- produktive Verbindungsdaten.

---

# Datenbank und Migrationen

## Datenbank über Docker starten

```bash
docker compose --env-file docker/.env -f docker/compose.yml up -d database
```

Status prüfen:

```bash
docker compose --env-file docker/.env -f docker/compose.yml ps
```

## Migrationen anwenden

Im aktivierten Backend-Virtualenv:

```bash
cd backend
alembic upgrade head
```

Aktuellen Stand prüfen:

```bash
alembic current
alembic heads
```

## Neue Migration erzeugen

Nur nach bewusster Änderung des Datenmodells:

```bash
alembic revision --autogenerate -m "<kurze-beschreibung>"
```

Die erzeugte Migration muss vor Ausführung manuell geprüft werden.

## Migrationsregeln

Migrationen müssen

- versioniert,
- nachvollziehbar,
- reproduzierbar,
- auf Datenverlust geprüft

sein.

Manuelle Schemaänderungen ohne Migration sind nicht zulässig.

---

# Gesamten Docker-Stack starten

Im Repository-Stamm:

```bash
cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yml config
docker compose --env-file docker/.env -f docker/compose.yml up --build -d
```

Status:

```bash
docker compose --env-file docker/.env -f docker/compose.yml ps
```

Prüfungen:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/health/ready
curl --fail http://localhost:8080/
curl --fail http://localhost:8080/api/health
```

Beenden:

```bash
docker compose --env-file docker/.env -f docker/compose.yml down
```

Mit Löschung lokaler Volumes:

```bash
docker compose --env-file docker/.env -f docker/compose.yml down --volumes
```

Der Befehl mit `--volumes` löscht lokale Daten und darf nur bewusst ausgeführt werden.

---

# Container-Images

Für Sprint 0 werden versionierte Image-Tags verwendet.

Beispiele:

```text
python:3.12-slim
node:22-alpine
nginx:1.27-alpine
postgres:17-alpine
```

Image-Digests werden erst aufgenommen, wenn

- Ziel-Registry,
- Zielplattform,
- image-spezifischer Digest,
- Aktualisierungsprozess und
- Freigabeverantwortung

festgelegt und geprüft sind.

Ein Digest darf nicht ungeprüft oder für unterschiedliche Images identisch übernommen werden.

---

# Qualitätsprüfungen

## Backend

Im Repository-Stamm:

```bash
bash scripts/check-backend.sh
```

Das Skript führt derzeit aus:

- Ruff,
- Black-Prüfung,
- mypy im strikten Modus,
- Pytest,
- Coverage mit mindestens 85 Prozent.

Einzelfehler werden nicht durch Überspringen eines Prüfschritts umgangen.

## Frontend

Im Repository-Stamm:

```bash
bash scripts/check-frontend.sh
```

Das Skript führt derzeit aus:

- TypeScript-Typprüfung,
- ESLint ohne Warnungen,
- Prettier-Prüfung,
- Vitest mit Coverage-Grenzen,
- Produktionsbuild.

Aktuelle Mindestwerte:

| Messwert | Mindestwert |
|---|---:|
| Lines | 80 % |
| Functions | 80 % |
| Statements | 80 % |
| Branches | 70 % |

## End-to-End

```bash
bash scripts/run-e2e.sh
```

Das Skript

- baut den Docker-Stack,
- wartet auf die Services,
- führt Playwright aus,
- beendet den Stack anschließend automatisch.

E2E setzt Docker sowie installierte Frontend-Abhängigkeiten voraus.

---

# Einzelne Frontend-Befehle

Im Verzeichnis `frontend/`:

```bash
npm run typecheck
npm run lint
npm run format
npm run test
npm run test:coverage
npm run build
npm run e2e
```

Automatische Formatierung:

```bash
npm run format:write
```

Formatierung darf keine inhaltlichen Änderungen verdecken. Der Diff ist danach erneut zu prüfen.

---

# Tests

Neue oder geänderte Fachlogik benötigt automatisierte Tests.

Ein Bugfix soll einen Test enthalten, der den Fehler vor der Korrektur reproduziert.

Testarten:

```text
tests/unit/
tests/integration/
tests/contract/
tests/workflow/
tests/performance/
tests/e2e/
tests/fixtures/
```

Tests müssen

- deterministisch,
- unabhängig voneinander,
- ohne produktive Zugangsdaten,
- mit kontrollierten Testdaten

ausführbar sein.

---

# Entwicklungsbranch

Vor Beginn:

```bash
git switch main
git pull --ff-only
git switch -c <typ>/<kurze-beschreibung>
```

Beispiele:

```text
feature/trade-plan-validation
fix/provider-timeout
docs/sprint-0-development-guide
chore/frontend-lockfile
```

Direkte Änderungen auf `main` sind nicht vorgesehen.

---

# Commits

Commits sollen klein, sachlich zusammengehörig und nachvollziehbar sein.

Empfohlenes Format:

```text
<typ>: <kurze-beschreibung>
```

Typen:

```text
feat
fix
docs
test
refactor
chore
ci
build
```

Beispiele:

```text
docs: revise development guide
fix: validate stale market data
test: cover trade plan risk limits
```

Vor einem Commit:

```bash
git status --short
git diff --check
git diff
```

Danach gezielt stagen:

```bash
git add <dateien>
git diff --cached --check
git diff --cached
```

Keine generierten, lokalen oder geheimen Dateien versehentlich committen.

---

# Pull Request

Ein Pull Request muss mindestens beschreiben:

- Zweck der Änderung,
- betroffene Features und Dateien,
- fachliche Auswirkungen,
- technische Auswirkungen,
- ausgeführte Tests,
- offene Punkte und Risiken,
- gegebenenfalls Migrationen,
- gegebenenfalls Screenshots oder API-Beispiele.

Vor dem Merge müssen die erforderlichen CI-Prüfungen erfolgreich sein.

---

# Dokumentationspflicht

Eine Änderung muss die betroffenen Dokumente aktualisieren, wenn sie

- Anforderungen,
- Architektur,
- Datenmodell,
- API,
- Modell- oder Regelversion,
- Bedienablauf,
- Betriebsanleitung,
- Test- oder Freigabeverfahren

verändert.

Dokumentationsänderungen werden im selben Pull Request wie die Implementierung vorgenommen.

---

# Nachvollziehbarkeit fachlicher Berechnungen

Für jede Empfehlung, Bewertung oder fachlich relevante Berechnung müssen nachvollziehbar sein:

- Datenquelle,
- Datenstand,
- Modell oder Regelwerk,
- Version,
- Eingaben,
- Konfiguration,
- Ergebnis,
- Warnungen und Einschränkungen.

Eine Änderung an fachlicher Modelllogik benötigt eine neue Modell- oder Regelversion.

Historische Trades bleiben mit der ursprünglich verwendeten Version verknüpft.

---

# Fehlerbehebung

## `No module named ruff`, `black`, `mypy` oder `pytest`

Backend-Virtualenv aktivieren und Entwicklungsabhängigkeiten installieren:

```bash
cd backend
source .venv/bin/activate
python -m pip install --requirement requirements-dev.txt
```

## `npm ci` meldet fehlende Lockdatei

Prüfen:

```bash
ls frontend/package-lock.json
```

Fehlt die Datei, im Frontend einmalig ausführen:

```bash
npm install
```

Danach `package-lock.json` prüfen und versionieren.

## Falsche Node-Version

```bash
cd frontend
nvm install
nvm use
```

## Docker-Variablen fehlen

```bash
cp docker/.env.example docker/.env
```

Danach `docker/.env` prüfen.

## Port bereits belegt

Belegte Ports ermitteln oder in `docker/.env` anpassen:

```text
POSTGRES_PORT
BACKEND_PORT
FRONTEND_PORT
```

## Docker-Service wird nicht gesund

```bash
docker compose --env-file docker/.env -f docker/compose.yml ps
docker compose --env-file docker/.env -f docker/compose.yml logs database
docker compose --env-file docker/.env -f docker/compose.yml logs backend
docker compose --env-file docker/.env -f docker/compose.yml logs frontend
```

## Arbeitsverzeichnis enthält unbekannte Änderungen

```bash
git status --short
git diff
```

Änderungen nicht blind verwerfen. Bei Bedarf zuerst sichern:

```bash
git diff > ../working-tree-backup.patch
```

---

# Übergabecheckliste

Vor Übergabe oder Review:

```markdown
- [ ] Änderung ist fachlich abgegrenzt.
- [ ] Betroffene Anforderungen und Dokumente sind aktualisiert.
- [ ] Keine autonome Handelsentscheidung wurde eingeführt.
- [ ] Datenquelle, Modellversion, Eingaben und Ergebnis bleiben nachvollziehbar.
- [ ] Backend-Prüfungen sind erfolgreich.
- [ ] Frontend-Prüfungen sind erfolgreich.
- [ ] Erforderliche E2E-Tests sind erfolgreich.
- [ ] Migrationen wurden geprüft.
- [ ] Keine Geheimnisse oder lokalen Dateien sind enthalten.
- [ ] `git diff --check` ist erfolgreich.
- [ ] Der gestagete Diff wurde vollständig geprüft.
- [ ] Offene Punkte und externe Blocker sind dokumentiert.
```

---

# Freigabe

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn

- alle beschriebenen Befehle mit dem aktuellen Repository übereinstimmen,
- `frontend/package-lock.json` vorhanden ist,
- Backend-, Frontend- und Docker-Setup auf einem frischen System geprüft wurden,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

Bis dahin bleibt der Status `🔵 Review`.

---

# Siehe auch

- `docs/architecture/Source_Architecture.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/implementation/SPRINT_0_OPEN_POINTS.md`
- `scripts/check-backend.sh`
- `scripts/check-frontend.sh`
- `scripts/run-e2e.sh`
- `scripts/verify-release-readiness.sh`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Abgleich mit Repository, Werkzeugversionen und Prüfscripten; Ergänzung von Setup, Docker, Git, Tests, Fehlerbehebung und Freigabekriterien |
