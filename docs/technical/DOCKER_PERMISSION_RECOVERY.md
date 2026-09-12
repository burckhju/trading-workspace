# Docker source permissions after a restrictive Git checkout

## Symptom and cause

An image can build successfully but fail during `python -m alembic upgrade head`
with `PermissionError: [Errno 13]` on `/app/app/core/config/settings.py`.
This failure is during Python import, before the migration in that invocation
can connect to PostgreSQL or execute schema changes.

A Git checkout performed under `umask 077` can create owner-only files (0600)
and directories (0700). Docker `COPY` from a local build context preserves
permissions and, without `--chown`, assigns root ownership. The runtime correctly
uses the unprivileged `app` user, which cannot read those root-only files.
The successful build used root and therefore did not demonstrate runtime access.

A healthy, older backend is not proof that the new image has started. The Linux
startup helper stops on a failed migration before replacing the backend/frontend.
An old backend may return `ready` but 404 on a newly introduced route.

References:
- https://docs.docker.com/reference/dockerfile/#copy
- https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html

## Permanent image fix and regression coverage

The backend Dockerfile normalizes **image-owned code only** before `USER app`:
`/app`, application and migration directories are 0755; application/migration
files, `alembic.ini` and `requirements.txt` are 0644. Source ownership stays root,
so `app` may read/import it but may not rewrite it. No host checkout permissions,
`.env` files, mounted secrets or database volumes are changed.

`Backend / restrictive-umask image` builds the production Dockerfile from a
disposable CI checkout deliberately set to 0600/0700. It checks non-root imports,
source readability/non-writability, the disabled Frankfurt health route, and a
real Alembic upgrade against disposable PostgreSQL. The ordinary quality and
end-to-end jobs remain required validation, not substitutes for this regression.

## Local recovery through Git

Keep the configuration/database backups made before the update. Run from the
existing Linux checkout. This block stops on local changes, a non-main branch,
divergent history, a failed build or a failed migration. It does not discard code
or reset history. Restarting the backend/frontend briefly interrupts the app.

```bash
(
  set -euo pipefail
  # Normal code checkout; do not apply the backup's private mask to Git/build.
  umask 022
  cd "$(git rev-parse --show-toplevel)"

  if [[ "$(git branch --show-current)" != main ]]; then
    echo "Stop: switch to the intended main checkout after reviewing local work."
    exit 1
  fi
  if [[ -n "$(git status --porcelain)" ]]; then
    git status --short
    echo "Stop: review local changes before updating."
    exit 1
  fi

  git fetch origin main
  git merge --ff-only origin/main
  bash scripts/start-linux.sh
  git log -1 --oneline

  docker compose --env-file docker/.env -f docker/compose.yml ps
  curl --fail --silent --show-error \
    --retry 15 --retry-delay 2 --retry-connrefused --max-time 5 \
    http://localhost:8000/health/ready
  echo
  curl --fail --silent --show-error \
    http://localhost:8000/api/v1/position-monitoring/quote-sources/frankfurt/health
  echo
)
```

Use the configured backend port instead of 8000 when non-default. A prior
`umask 077` does not need to be undone on every existing source file: the corrected
image normalizes their modes during build. No `chmod -R 777`, root runtime,
`git reset --hard`, configuration overwrite or `docker compose down -v` is needed.
Do not change the database password to fix a Python source permission error.

If the exact permission failure persists, stop and inspect the effective local
Dockerfile/build context and any source bind mounts rather than changing database
state. The user PC is not validated by a passing CI job; confirm the local rebuild
and both endpoints after the update.

Frankfurt stays disabled without its separately approved source configuration.
Expected default health reason: `FRANKFURT_DISABLED`, not an active quote feed.
Use the Frankfurt activation runbook only when an upstream feed is verified.

## Keep backup permissions scoped

`umask 077` is appropriate for backups and credentials, not for the whole
checkout-and-build sequence. Keep it in its own subshell, for example:

```bash
backup="$(mktemp -d "$HOME/trading-workspace-backup-XXXXXXXX")"
(
  umask 077
  cp docker/.env "$backup/docker.env"
  # Keep database dump output inside this private directory as well.
)
# The caller's mask is unchanged here. Use the normal checkout/build path above.
```

Existing `.env` and database backup permissions must remain private. Never paste
credentials or raw environment files into diagnostic reports.
