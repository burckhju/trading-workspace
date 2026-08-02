# Trading Workspace Command v1.1

## Neue Funktionen

- Fortschrittsanzeige bei Health-Checks
- automatische Diagnose bei Start-Timeout
- farbige Statusausgabe
- neuer Befehl `doctor`
- Prüfung von Docker, Compose, Konfiguration, Lockdatei, Ports und Endpunkten

## Installation

```bash
cd ~/Boerse/trading-workspace
chmod +x scripts/workspace
```

## Wichtigste Befehle

```bash
./scripts/workspace start
./scripts/workspace open
./scripts/workspace status
./scripts/workspace health
./scripts/workspace doctor
./scripts/workspace logs
./scripts/workspace test
./scripts/workspace stop
```

## Doctor

```bash
./scripts/workspace doctor
```

Prüft:

- Docker
- Docker Compose
- Git und curl
- `docker/compose.yml`
- `docker/.env`
- `frontend/package-lock.json`
- Ports 5432, 8000 und 8080
- Compose-Konfiguration
- Containerstatus
- Health-Endpunkte

## Konfigurierbare Health-Wartezeit

```bash
TRADING_WORKSPACE_HEALTH_ATTEMPTS=90 TRADING_WORKSPACE_HEALTH_DELAY_SECONDS=2 ./scripts/workspace start
```
