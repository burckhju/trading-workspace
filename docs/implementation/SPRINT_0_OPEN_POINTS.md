# Sprint 0 – Bearbeitung offener Punkte

## Ziel

Dieses Dokument konsolidiert die nach SP-008 verbliebenen offenen Punkte und trennt
repositoryseitig lösbare Aufgaben von externen Betriebs- und Administrationsaufgaben.

## Erledigt

### Direkte Abhängigkeiten fixiert

Alle direkt deklarierten Backend- und Frontend-Abhängigkeiten sind auf exakte Versionen
festgelegt. Versionsbereiche mit `>=`, `<`, `^` oder `~` werden nicht mehr verwendet.

Backend:

- Laufzeitabhängigkeiten: `backend/requirements.txt`
- Entwicklungsabhängigkeiten: `backend/requirements-dev.txt`
- Paketmetadaten: `backend/pyproject.toml`

Frontend:

- direkte npm-Abhängigkeiten: `frontend/package.json`
- npm- und Node-Version: `packageManager`, `engines` und `frontend/.nvmrc`
- npm-Reproduzierbarkeitsregeln: `frontend/.npmrc`

### Python-Installation vom Build-Backend entkoppelt

Docker und GitHub Actions installieren das Backend über die exakt versionierten
Requirements-Dateien. Dadurch hängen technische Prüfungen und das Runtime-Image nicht
mehr davon ab, dass `hatchling` in der verwendeten Paketquelle verfügbar ist.

### Lokale Laufzeitversionen festgelegt

- Python: `backend/.python-version`
- Node.js: `frontend/.nvmrc`
- npm: `frontend/package.json`

### Release-Readiness-Prüfung ergänzt

`scripts/verify-release-readiness.sh` prüft die zwingenden lokalen Voraussetzungen,
insbesondere die Frontend-Lockdatei und die benötigten Laufzeitwerkzeuge.

## Extern blockiert

### Frontend-Lockdatei

Eine belastbare `frontend/package-lock.json` kann erst mit einer npm-Registry erzeugt
werden, die alle deklarierten Pakete und deren transitive Abhängigkeiten bereitstellt.
Die in der Ausführungsumgebung konfigurierte Registry beantwortet weiterhin mindestens
`@eslint/js` mit HTTP 404. Eine Lockdatei wird deshalb nicht manuell konstruiert.

Sobald eine vollständige Registry verfügbar ist, sind auszuführen:

```bash
cd frontend
npm install
npm ci
npm run typecheck
npm run lint
npm run format
npm run test:coverage
npm run build
```

Danach müssen Frontend-Workflow und Frontend-Dockerfile von `npm install` auf `npm ci`
umgestellt werden.

### Vollständiger GitHub-Actions-Lauf

Ein realer Workflow-Lauf benötigt ein GitHub-Repository mit aktivierten Actions sowie
Zugriff auf npm- und Python-Paketquellen. Dies kann nicht innerhalb des Repositorys
simuliert oder bestätigt werden.

### Branch Protection

Branch-Protection-Regeln sind Repository-Administration und keine versionierbare
Anwendungskonfiguration. Für `main` müssen mindestens folgende Checks verpflichtend
sein:

- Backend / quality
- Frontend / quality
- End-to-End / smoke

Zusätzlich sollen direkte Pushes auf `main` unterbunden und mindestens ein genehmigendes
Review verlangt werden. Die Aktivierung muss durch einen Repository-Administrator
erfolgen.

### Container-Image-Digests

Die vorhandenen Dockerfiles verwenden versionierte Image-Tags. Freigegebene Digests
können erst festgelegt werden, wenn die Ziel-Registry und der organisatorische
Freigabeprozess definiert sind. Ohne diese Vorgaben wird kein Digest angenommen.

## Status

Die repositoryseitig lösbaren Punkte sind erledigt. Verbleibend sind ausschließlich
Aufgaben, die eine funktionierende externe Registry, Docker-Runtime oder
GitHub-Administration benötigen.
