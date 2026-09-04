# Linux Deployment

This runbook describes the supported local Linux deployment path for the Trading Workspace using Docker Compose.

## Prerequisites

- 64-bit Linux host
- Docker Engine
- Docker Compose v2 (`docker compose`)
- `curl` and `unzip` when using the ZIP distribution path

No Python or Node installation is required for the Docker deployment.

## Download the current main branch as ZIP

```bash
mkdir -p ~/trading-workspace-install
cd ~/trading-workspace-install
curl -L https://github.com/burckhju/trading-workspace/archive/refs/heads/main.zip -o trading-workspace-main.zip
unzip trading-workspace-main.zip
cd trading-workspace-main
```

For a reproducible deployment, archive or record the Git commit used for the installation.

## Configure

Create the Docker environment file once:

```bash
cp docker/.env.example docker/.env
chmod 600 docker/.env
```

At minimum replace `POSTGRES_PASSWORD=change-me` and keep the password synchronized in `TRADING_WORKSPACE_DATABASE_URL`.

The monitoring capability is disabled by default. To enable completed-daily position monitoring, configure an EODHD key and set:

```dotenv
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=true
TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY=<secret>
TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=true
```

Outbound Telegram delivery remains optional and disabled by default. To enable it, additionally set:

```dotenv
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=true
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__BOT_TOKEN=<secret>
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__CHAT_ID=<destination>
```

Do not commit `docker/.env`. Do not paste secrets into logs or support output.

## Start

The repository helper validates Docker/Compose, creates `docker/.env` from the template when missing, validates the Compose model and starts the stack:

```bash
bash scripts/start-linux.sh
```

Equivalent explicit command:

```bash
docker compose --env-file docker/.env -f docker/compose.yml up --build -d
```

## Verify

```bash
docker compose --env-file docker/.env -f docker/compose.yml ps
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/health/ready
```

Expected endpoints:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Backend through frontend nginx: `http://localhost:8080/api`

Inspect backend logs without exposing the environment file:

```bash
docker compose --env-file docker/.env -f docker/compose.yml logs -f backend
```

## Controlled monitoring smoke run

The normal background monitor is started by the backend only when monitoring is enabled. For a one-shot operational check without allowing a real Telegram send:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec backend \
  python -m app.features.position_monitoring.cli
```

If Telegram is configured, the command refuses live Telegram delivery unless it is explicitly authorized:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec backend \
  python -m app.features.position_monitoring.cli --allow-telegram
```

Use a controlled test position before allowing a live delivery.

## Stop and update

Stop containers while retaining PostgreSQL data:

```bash
docker compose --env-file docker/.env -f docker/compose.yml down
```

Do not add `-v` unless the PostgreSQL volume is intentionally disposable.

For a later ZIP-based update, back up `docker/.env` and the PostgreSQL data first, extract the new archive to a new directory, copy the environment file deliberately, then rebuild the stack. Database migrations run as part of the backend container startup convention; verify readiness before using the workspace.
