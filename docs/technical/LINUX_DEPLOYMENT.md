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
4. verifies that the requested Compose file order preserves every existing project
   container’s recorded chain, including stopped containers,
5. builds backend/frontend and, when opted in, the issuer renderer,
6. starts the opted-in renderer with a bounded sandbox health check,
7. starts PostgreSQL and waits for database readiness,
8. runs `python -m alembic upgrade head` with `--no-deps` in the backend image,
9. starts backend and frontend.

This ordering prevents the application from being treated as ready before required database migrations have been applied.

Equivalent manual operation for a **base-only** installation is shown below.
Retain the complete reviewed overlay chain for any enabled quote providers; a
manual operation does not perform the helper’s existing-container provenance check:

```bash
docker compose --env-file docker/.env -f docker/compose.yml config --quiet
docker compose --env-file docker/.env -f docker/compose.yml build backend frontend
docker compose --env-file docker/.env -f docker/compose.yml up -d database
docker compose --env-file docker/.env -f docker/compose.yml run --rm --no-deps backend python -m alembic upgrade head
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
git pull --ff-only
bash scripts/start-linux.sh
```

For a ZIP-based update, extract the new archive to a new directory and copy the existing `docker/.env` deliberately into that installation. Then run:

```bash
bash scripts/start-linux.sh
```

The helper applies pending Alembic migrations before starting backend and frontend. Verify `/health/ready` before using the workspace.

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
[the Frankfurt setup instructions](../frankfurt-quotes.md) to configure the source deliberately.
Manual Compose operations still need `-f docker/compose.frankfurt.yml` in addition
to the ordinary Compose file. The helper prints matching status/log commands.

## Automatischer Kursabruf

Aktive Basiswerte und Optionsscheine können automatisch geprüft und in getrennten
Intervallen aktualisiert werden. Einrichtung, Provider-Grenzen und Diagnose:
[Automatischer Kursabruf](../automatic-market-data.md).

## Issuer monitoring and existing overlay chains (1.4.1)

For an installation intentionally using the canonical issuer integration:

```bash
bash scripts/start-linux.sh --issuer-monitoring --check
bash scripts/start-linux.sh --issuer-monitoring
```

`--check` validates Compose and reads existing container labels without creating
configuration, refreshing provider files, building images, migrating, or starting
containers. The second command deploys and resumes the configured background work;
it does not send a separate test message or accept provider terms. Retain existing
monitoring/Telegram settings. The renderer uses the existing private consent volume.

`docker/frankfurt.env` is still included automatically when present. For any other
required existing exchange/custom overlay, repeat `--overlay FILE` in its original
order on both commands. Relative paths are resolved from the repository, even when
the helper is invoked elsewhere. The canonical issuer overlay is appended last;
use `--issuer-monitoring`, not `--overlay`, for that file. The helper supplies the
absolute repository sandbox-profile path unless an explicit shell value is set.

The helper refuses to omit or reorder a file recorded on an existing project
container. This includes stopped containers. An unavailable Docker inspection or
missing provenance stops deployment. No existing overlay is inferred, activated,
deleted or silently replaced. A routine issuer update therefore needs the issuer
flag again. Printed status/log commands contain the complete shell-quoted chain.

Container labels prove paths/order, not unchanged file contents or environment
values. Review private configuration locally; never post full `compose config`
output. Old package overlays must not be combined with the canonical issuer overlay.
An intentional migration away from old packages or a relocated ZIP checkout needs
a reviewed manual deployment with the complete intended chain, preserved project
name/volumes and existing environment. There is no force/bypass option in the helper.

Renderer failure stops before database migration and backend recreation. Migration
failure also stops before backend recreation. Built images and a restarted renderer
may already exist; no automatic rollback or data deletion is attempted. Verify
readiness, loaded runtime settings, complete refresh/monitoring cycles and source
coverage after deployment using the [issuer operations guide](ISSUER_MONITORING_OPERATIONS.md).
A healthy sandbox does not prove provider access or consent reuse.

## Reviewed legacy issuer migration (1.4.3)

The normal startup helper intentionally refuses removing/reordering old package
files or relocating a checkout. For the reviewed four-service legacy issuer
installation, use `scripts/migrate-legacy-issuer.sh` from a **separate, clean release
checkout pinned to a qualified commit**. This is an explicit migration, not a
provenance bypass. Other topologies stop for review. Requires Bash, Git, Docker
Compose v2, coreutils and tar; Python runs offline in the existing backend image.
No host Python/Node installation is needed. Plan build disk space and backup space.

After `v1.4.3` is published and its commit/CI verified, the following concrete
example creates a detached sibling worktree without changing the existing checkout:

```bash
cd ~/Boerse/trading-workspace
git fetch origin tag v1.4.3
git worktree add --detach ../trading-workspace-v1.4.3 v1.4.3
bash ../trading-workspace-v1.4.3/scripts/migrate-legacy-issuer.sh prepare \
  "$PWD" "$HOME/Boerse/trading-workspace-deploy-v1.4.3"
```

The preparation never restarts a running service. It retains `.env` byte-for-byte
in a new directory (0700, files 0600), reads actual container settings, validates
the proposed model and builds separate commit-tagged images. Existing database
and consent volumes are external references and cannot silently become new empty
volumes. The Stuttgart bind remains at its original absolute source. The overlay
is last so actual false values stay false despite the canonical opt-in defaults.
Unexpected overrides, mounts, ports, restrictions or extra services cause refusal.

The private directory contains secrets, inspection data and eventually backups.
Do not publish it. Review its local `operation.log` on failure; share only the
phase/error summary after redaction. Do not edit prepared inputs: they and their
resolved model are checked again at apply. If preparation fails, services remain
running; use a **new** private directory after resolving the cause. Never delete an
old private directory that already contains an applied configuration or backups.

The successful preparation prints the exact apply command. In a maintenance
window (API/frontend requests can fail while backend is stopped), for this example:

```bash
bash ~/Boerse/trading-workspace-v1.4.3/scripts/migrate-legacy-issuer.sh apply \
  "$HOME/Boerse/trading-workspace-deploy-v1.4.3"
```

The sequence revalidates images/configuration/containers; stops backend and
renderer; creates and checks listings of a custom PostgreSQL dump and a consent
archive; starts/health-checks the sandboxed renderer; runs Alembic; starts the
application; checks actual images, mounts/settings and the unchanged DB container.
The database is not recreated. Ensure no independent writer/setup process is
running during this maintenance window. A readable archive listing is not proof
of a tested restore. Keep backups privately according to the operator's policy.

A failure leaves its last reached phase visible and prevents a repeated apply.
There is **no automatic rollback**. Before `migration-started` exists, if no
container replacement occurred (check `operation.log`/Docker IDs), the original
stopped backend/renderer can be started by their saved IDs. After replacement or
migration has begun, inspect the phase, schema and image compatibility before
choosing recovery; do not stamp, blindly downgrade or restore over a live database.
Preserve the original checkout, images, private state and backup files for review.
Do not remove phase markers just to retry.

For subsequent diagnosis use the same immutable chain:

```bash
bash ~/Boerse/trading-workspace-v1.4.3/scripts/migrate-legacy-issuer.sh compose \
  "$HOME/Boerse/trading-workspace-deploy-v1.4.3" ps
bash ~/Boerse/trading-workspace-v1.4.3/scripts/migrate-legacy-issuer.sh compose \
  "$HOME/Boerse/trading-workspace-deploy-v1.4.3" exec -T backend \
  python -m app.tools.audit_monitoring_performance
```

The wrapper permits `ps`, `logs` and `exec`; it does not provide a generic update or
rollback command. Keep the release worktree and private directory at their prepared
paths. Future updates need deliberate review of the complete base + canonical +
preservation chain. The normal base-only start remains intentionally blocked.

A successful apply proves image identity, loaded environment/bindings, readiness,
renderer sandbox health and completion of the migration command. It does not prove
fresh provider quotes, product-level consent reuse, a complete post-restart
monitoring cycle or Telegram delivery. Use the issuer operations runbook for those
separate live checks; test messages and changed consent remain separately approved.


### Diagnose an existing prepared deployment with 1.4.4 tooling

Version 1.4.3 used a byte comparison for rendered Compose JSON. Different whitespace
or object-field order could therefore reject an unchanged effective model with
`Effective Compose configuration changed`. Version 1.4.4 compares parsed content
while retaining exact input seals, scalar types, array order and all existing
release/configuration guards. Do not edit/reseal `candidate.json`, remove phase
markers or repeat `apply` to repair this diagnostic failure.

Once tag `v1.4.4` and its final-commit checks are published, obtain its tool in a
separate clean checkout. Keep the original v1.4.3 checkout and private state in
place. This example uses the prepared paths from the v1.4.3 example above:

```bash
git -C "$HOME/Boerse/trading-workspace" fetch origin tag v1.4.4
git -C "$HOME/Boerse/trading-workspace" worktree add --detach \
  "$HOME/Boerse/trading-workspace-tools-v1.4.4" v1.4.4
bash "$HOME/Boerse/trading-workspace-tools-v1.4.4/scripts/migrate-legacy-issuer.sh" \
  compose "$HOME/Boerse/trading-workspace-deploy-v1.4.3" ps </dev/null
```

Only `compose` supports an older prepared release. It checks the tool checkout,
sealed inputs, original release commit/cleanliness and effective model, then uses
that original release for Compose files and the seccomp path. It does not substitute
new images or change the loaded application version. The pinned helper image from
preparation is still required; retain the original images as already required by
the migration procedure. `prepare`/`apply` remain bound to their own release root.
Actual content changes or unavailable inputs/images stop the command for review.

For the pending read-only diagnostics, stdin is closed inside the wrapper so
`docker compose exec -T` cannot consume the remaining shell command block:

```bash
bash <<'SH'
tw_diag() {
  bash "$HOME/Boerse/trading-workspace-tools-v1.4.4/scripts/migrate-legacy-issuer.sh" compose \
    "$HOME/Boerse/trading-workspace-deploy-v1.4.3" "$@" </dev/null
}
tw_diag exec -T backend python -m app.tools.audit_monitoring_performance --wait-seconds 60
tw_diag exec -T backend python -m app.tools.monitoring_resume preflight
tw_diag exec -T issuer-renderer python -c 'import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen("http://127.0.0.1:8091/health", timeout=10)), indent=2))'
SH
```

These queries do not send a test notification or accept consent. Renderer health
can identify stored state; product access in a fresh context is still needed to
prove its reuse. Report tool version and actually deployed image revision separately.
