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

## Canonical startup command

The supported Linux startup entry point is:

```bash
bash scripts/start-linux.sh
```

Use this command for the first installation and for normal subsequent starts after configuration. Do not replace it with ad-hoc `docker compose up` commands unless you intentionally operate the individual deployment steps yourself.

## First installation and configuration

On the first invocation, if `docker/.env` does not exist, the helper creates it from `docker/.env.example`, sets restrictive file permissions and **stops intentionally before starting containers**:

```bash
bash scripts/start-linux.sh
```

Then edit the generated configuration:

```bash
nano docker/.env
```

At minimum replace `POSTGRES_PASSWORD=change-me` and keep the same password in `TRADING_WORKSPACE_DATABASE_URL`.

Example structure:

```dotenv
POSTGRES_PASSWORD=<local-secret>
TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://trading_workspace:<same-local-secret>@database:5432/trading_workspace
```

If the password contains URL-reserved characters, percent-encode the password portion in `TRADING_WORKSPACE_DATABASE_URL`.

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

After editing the environment file, start again:

```bash
bash scripts/start-linux.sh
```

## What the startup helper does

The helper performs these steps in order:

1. validates Docker and Docker Compose v2,
2. refuses the unchanged example PostgreSQL password,
3. validates the Compose model,
4. builds backend and frontend images,
5. starts PostgreSQL and waits for database readiness,
6. runs `python -m alembic upgrade head` in the backend image,
7. starts backend and frontend.

This ordering prevents the application from being treated as ready before required database migrations have been applied.

Equivalent manual operation, if needed for diagnostics, is:

```bash
docker compose --env-file docker/.env -f docker/compose.yml config
docker compose --env-file docker/.env -f docker/compose.yml build backend frontend
docker compose --env-file docker/.env -f docker/compose.yml up -d database
docker compose --env-file docker/.env -f docker/compose.yml run --rm backend python -m alembic upgrade head
docker compose --env-file docker/.env -f docker/compose.yml up -d backend frontend
```

For normal operation prefer `bash scripts/start-linux.sh`.

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
- Liveness: `http://localhost:8000/health`
- Readiness: `http://localhost:8000/health/ready`

Inspect backend logs without exposing the environment file:

```bash
docker compose --env-file docker/.env -f docker/compose.yml logs -f backend
```

## Important: preserve docker/.env

`docker/.env` is local deployment configuration. Once it has been configured, do **not** run:

```bash
cp docker/.env.example docker/.env
```

again. That command overwrites database, EODHD, monitoring and Telegram configuration with template values.

When a newer repository version adds environment variables, compare `docker/.env.example` with the existing `docker/.env` and add only the required new keys deliberately.

## Existing PostgreSQL volumes and password changes

`POSTGRES_PASSWORD` initializes the PostgreSQL role password only when the PostgreSQL data directory is first created. Changing `POSTGRES_PASSWORD` later does not change the password stored in an existing PostgreSQL volume.

If `/health/ready` reports database unavailability and the backend log contains `InvalidPasswordError`, do not delete the volume. First verify whether an existing volume still has an older role password. Synchronize the PostgreSQL role deliberately if required.

Never use `docker compose down -v` as a password-repair step; `-v` deletes the persisted PostgreSQL volume.

## Controlled monitoring smoke run

The normal background monitor is started by the backend only when monitoring is enabled. For a one-shot operational check with Telegram disabled:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python -m app.features.position_monitoring.cli
```

If Telegram is configured, the command refuses live Telegram delivery unless it is explicitly authorized:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python -m app.features.position_monitoring.cli --allow-telegram
```

Use a controlled test position before allowing a live delivery.

## Stop

Stop containers while retaining PostgreSQL data:

```bash
docker compose --env-file docker/.env -f docker/compose.yml down
```

Do not add `-v` unless the PostgreSQL volume is intentionally disposable.

## Update an existing installation

Before updating, back up `docker/.env` and the PostgreSQL data. Never overwrite the configured `docker/.env` with the template from the new version.

For a Git checkout:

```bash
git pull origin main
bash scripts/start-linux.sh
```

For a ZIP-based update, extract the new archive to a new directory and copy the existing `docker/.env` deliberately into that installation. Then run:

```bash
bash scripts/start-linux.sh
```

The helper applies pending Alembic migrations before starting backend and frontend. Verify `/health/ready` before using the workspace.
