# Linux quick start

See `docs/technical/LINUX_DEPLOYMENT.md` for the supported ZIP download, Docker Compose configuration, migration, monitoring/Telegram setup, verification and smoke-test procedure.

## First installation

Run the startup helper once:

```bash
bash scripts/start-linux.sh
```

If `docker/.env` does not exist, the helper creates it from `docker/.env.example` and stops intentionally. Edit the file before starting the stack:

```bash
nano docker/.env
```

At minimum replace the example PostgreSQL password and keep it identical in `POSTGRES_PASSWORD` and `TRADING_WORKSPACE_DATABASE_URL`. Configure EODHD/Telegram only when needed.

Then start again:

```bash
bash scripts/start-linux.sh
```

The helper validates Compose, builds the images, starts PostgreSQL, applies all Alembic migrations and then starts backend and frontend.

## Normal subsequent start/update

Do **not** copy `docker/.env.example` over an existing `docker/.env`. The configured environment file is persistent local configuration.

Use:

```bash
bash scripts/start-linux.sh
```

Frontend: `http://localhost:8080`

Backend: `http://localhost:8000`

Readiness: `http://localhost:8000/health/ready`
