# Linux quick start

See `docs/technical/LINUX_DEPLOYMENT.md` for the supported ZIP download, Docker Compose configuration, migration, monitoring/Telegram setup, verification and smoke-test procedure.

For deployment-near qualification of the already implemented open-position operating loop, use `docs/technical/DAILY_POSITION_LOOP_VALIDATION.md` and `bash scripts/validate-daily-position-loop.sh`.

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

## Existing Frankfurt quote configuration

The startup helper includes `docker/compose.frankfurt.yml` whenever
`docker/frankfurt.env` exists. It preserves that file, `docker/.env`, and all
provider activation/usage settings. No login, paid data service or subscription
is created. To require Frankfurt configuration before starting, use:

```bash
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
curl -fsS http://localhost:8000/api/v1/position-monitoring/quote-sources/frankfurt/health
```

If the file is absent, `--frankfurt` stops before Docker operations. Follow
[the Frankfurt setup instructions](docs/frankfurt-quotes.md) to configure the source deliberately.
Manual Compose operations still need `-f docker/compose.frankfurt.yml` in addition
to the ordinary Compose file. The helper prints matching status/log commands.

## Automatischer Kursabruf

Aktive Basiswerte und Optionsscheine können automatisch geprüft und in getrennten
Intervallen aktualisiert werden. Einrichtung, Provider-Grenzen und Diagnose:
[Automatischer Kursabruf](docs/automatic-market-data.md).
