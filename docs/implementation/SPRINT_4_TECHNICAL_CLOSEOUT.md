# Sprint 4 – Technical Closeout

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Sprint | 4 |
| Feature | FT-006 Marktanalyse |
| Status | Release Candidate mit externen Quality-Gate-Blockern |
| Datum | 2026-08-06 |
| Release Candidate | v0.4.0-market-analysis-rc.1 |

## Ziel

Dieser Closeout verifiziert den technischen Stand nach fachlicher und architektonischer Abnahme von FT-006. Es werden keine neuen Fachfunktionen eingeführt.

## Reproduzierbar ausgeführte Prüfungen

### Backend Regression

Aus dem Repository-Root:

```bash
PYTHONPATH=backend pytest -q
```

Ergebnis:

- 197 Tests bestanden.
- Keine fehlgeschlagenen oder übersprungenen Backend-Tests im gesammelten Suite-Lauf.

### Backend Coverage

```bash
PYTHONPATH=backend pytest --cov=backend/app --cov-report=term --cov-fail-under=85
```

Ergebnis:

- 197 Tests bestanden.
- Gesamt-Coverage: 87,20 %.
- Quality Gate >= 85 % bestanden.

### Python Compile Check

Die Anwendung und Migrationen wurden bereits in der vorherigen Arbeitseinheit erfolgreich kompiliert; die aktuelle Regression lädt alle betroffenen Python-Module ohne Importfehler.

### Alembic Revisionskette

```text
20260803_0001
 -> 20260805_0002
 -> 20260805_0003
 -> 20260806_0004
 -> 20260806_0005
```

`alembic heads` liefert genau einen Head: `20260806_0005`.

## Nicht ausführbare Quality Gates

### Python Devtools

Eine frische isolierte Installation wurde versucht. Die konfigurierte Paketquelle liefert weder das Build-Backend `hatchling>=1.27` noch die gepinnten Runtime-Pakete wie `alembic==1.18.4`.

Daher konnten in dieser Laufzeit nicht frisch ausgeführt werden:

- Ruff
- Black
- mypy

Dies ist ein Infrastruktur-/Registry-Blocker und keine festgestellte Verletzung im Quellcode. Die CI-Konfiguration enthält die vorgesehenen Befehle weiterhin unverändert.

### Frontend

`npm ci` wurde mit Node 22.16.0 und npm 10.9.2 ausgeführt und scheitert reproduzierbar an der konfigurierten Paketquelle:

```text
404 Not Found: yocto-queue@0.1.0
```

Damit sind in dieser Umgebung nicht ausführbar:

- TypeScript-Typecheck
- ESLint
- Prettier
- Vitest inkl. Coverage
- Produktions-Build
- Playwright-E2E

Die vorhandene `package-lock.json` referenziert die offizielle `yocto-queue-0.1.0.tgz`; der Fehler entsteht beim Abruf über die interne Registry.

### PostgreSQL / Docker

Die aktuelle Laufzeit stellt weder `docker` noch `postgres`/`psql` bereit. Der Release-Readiness-Check meldet deshalb korrekt:

```text
FEHLT IM PATH: docker
Release-Bereitschaft ist nicht erfüllt.
```

Ein realer PostgreSQL Upgrade-/Downgrade-Lauf der Revision `20260806_0005` konnte deshalb nicht durchgeführt werden.

## CI-Verträge

Die vorhandenen GitHub-Actions-Workflows definieren weiterhin die final erforderlichen Gates:

Backend:

- Python 3.12
- Ruff
- Black
- mypy
- pytest mit >= 85 % Coverage

Frontend:

- Node gemäß `.nvmrc`
- `npm ci`
- TypeScript
- ESLint
- Prettier
- Vitest Coverage
- Build

E2E:

- Docker Compose mit PostgreSQL
- Chromium/Playwright Smoke Tests

## Release-Entscheidung

FT-006 ist fachlich und architektonisch abgenommen und die lokal ausführbare Backend-Qualität ist grün. Ein finaler Release darf dennoch erst erfolgen, wenn die extern blockierten Frontend-, Python-Devtool-, PostgreSQL- und E2E-Gates in einer vollständigen CI-/Entwicklungsumgebung erfolgreich gelaufen sind.

Daher wird der Stand als **v0.4.0-market-analysis-rc.1** klassifiziert, nicht als finales `v0.4.0-market-analysis`.

## Offene Punkte

1. Vollständige Python-Abhängigkeiten aus einer freigegebenen Registry installieren und Ruff, Black und mypy ausführen.
2. `npm ci` aus einer Registry mit vollständigem Lockfile-Artefaktbestand ausführen und alle Frontend-Gates starten.
3. Docker-/PostgreSQL-Stack starten und Alembic Upgrade bis `20260806_0005` sowie Downgrade/erneutes Upgrade testen.
4. Playwright Smoke Tests gegen den vollständigen Stack ausführen.
5. Nach grünen Gates Release Candidate zu `v0.4.0-market-analysis` freigeben.
