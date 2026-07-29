# SP-008 CI & Tests

## Ziel

SP-008 stellt reproduzierbare technische Quality Gates für Backend, Frontend und den
containerisierten Gesamtstack bereit. Die Tests prüfen ausschließlich das Sprint-0-Grundgerüst;
fachliche Tests für FT-001 bis FT-013 sind nicht enthalten.

## GitHub Actions

Drei getrennte Workflows werden bei Pull Requests und Pushes auf `main` pfadbasiert ausgeführt:

- `backend.yml`: Ruff, Black, mypy und pytest mit mindestens 85 Prozent Gesamt-Coverage.
- `frontend.yml`: TypeScript, ESLint, Prettier, Vitest mit Coverage-Schwellen und Vite-Build.
- `e2e.yml`: Docker-Compose-Stack und Playwright-Smoke-Tests in Chromium.

Alle Workflows besitzen minimale Leseberechtigungen, brechen veraltete Läufe über
Concurrency-Gruppen ab und laden relevante Testartefakte hoch.

## Teststruktur

- Backend Unit Tests: `tests/unit/backend/`
- Backend Integration Tests: `tests/integration/backend/`
- Frontend Component Tests: `frontend/src/**/*.test.tsx`
- End-to-End Tests: `tests/e2e/`

Der Playwright-Smoke-Test prüft die technische Startseite, den SPA-Router und den über Nginx
weitergeleiteten Backend-Liveness-Endpunkt. Er enthält keine fachlichen Abläufe.

## Lokale Ausführung

Backend:

```bash
python -m pip install --requirement backend/requirements-dev.txt
./scripts/check-backend.sh
```

Frontend:

```bash
cd frontend
npm install
npx playwright install chromium
cd ..
./scripts/check-frontend.sh
```

End-to-End mit Docker:

```bash
set -a
source docker/.env
set +a
./scripts/run-e2e.sh
```

## Reproduzierbarkeit

Die direkten Python- und npm-Abhängigkeiten sind auf exakte Versionen fixiert. Das Backend wird in
Docker und GitHub Actions über `backend/requirements.txt` beziehungsweise
`backend/requirements-dev.txt` installiert und hängt damit nicht mehr vom Build-Backend ab.

Eine belastbare `package-lock.json` konnte weiterhin nicht erzeugt werden, weil die konfigurierte
npm-Registry mindestens `@eslint/js` mit HTTP 404 beantwortet. Bis eine erzeugte Lockdatei vorliegt,
verwenden Frontend-Workflow und Docker-Build `npm install`. Danach sind beide auf `npm ci`
umzustellen. Der konsolidierte Status steht in `SPRINT_0_OPEN_POINTS.md`.

## Validierung in der Ausführungsumgebung

Die vorhandenen 23 Backend-Tests wurden erfolgreich mit 87,65 Prozent Coverage ausgeführt.
Workflow-YAML, JSON-Dateien, Shell-Syntax und Python-Syntax wurden lokal validiert. Ruff, Black und mypy konnten in der ursprünglichen Ausführungsumgebung nicht installiert werden.
Die Installationspfade wurden inzwischen von `hatchling` entkoppelt und verwenden exakt versionierte
Requirements-Dateien. Eine Docker-Runtime war nicht installiert. Diese Prüfungen werden deshalb erstmals
in einer GitHub-Actions-Umgebung mit erreichbaren öffentlichen Paketquellen vollständig ausgeführt.
