# Legacy issuer deployment migration

Date: 2026-10-02. Baseline: v1.4.2 (`20077d1879a70b12849ff7cf01a10c601c6ab9f4`).
Category: deployment integration; no trading rule, schema or runtime architecture change.

## Problem and evidence

A legacy installation can have eight package overlays, a checkout predating the
release, and unlabelled images with additional application files. Git checkout,
image identity and effective configuration are separate facts. Replacing the
chain with base + canonical issuer overlay loses runtime overrides (in particular
Telegram activation, provider timeouts/cache and monitoring parallelism), and a
separate checkout changes the relative Stuttgart bind path. The normal startup
helper correctly refuses omission of existing Compose paths; removing that guard
would conceal the incompatibility.

The operator's reviewed topology has four standard project services, the standard
named database/consent volumes, one read-only Stuttgart bind, and twelve backend
settings differing from base. Private reports and their values are not source
artifacts. The synthetic reproduction represents that topology and deliberately
uses false activation flags to detect inadvertent activation by the canonical
opt-in overlay.

## Scope and acceptance criteria

1. `scripts/migrate-legacy-issuer.sh prepare` runs from a separate clean, pinned
   release checkout. It copies the existing `.env` byte-for-byte to a new private
   directory outside Git, reads Docker inspection, and refuses unreviewed drift.
2. An offline stdlib validator checks the four-service topology, existing resource
   restrictions and mounts. Only the twelve reviewed keys may differ from base;
   their actual values become a private final preservation overlay. The complete
   target application/database environment, published ports and data mounts must
   match the running containers. No values are printed in diagnostics.
3. Existing PostgreSQL and consent volumes become explicit external references;
   the Stuttgart source is absolute and missing host paths cannot be created.
   Images get separate commit-based tags and OCI revision labels. Preparation
   builds but never stops/recreates a production service or calls a provider.
4. `apply` rechecks the clean release, sealed inputs, effective Compose output,
   immutable prepared image IDs and running container identity before stopping.
   All four services must still be present/running. Additional project containers
   and repeated apply attempts are refused.
5. After stopping backend/renderer, obtain a custom-format database backup and
   consent tar archive. Check their directory listings before any replacement or
   migration. These are archive-integrity checks, not a successful restore drill.
6. Start the renderer with the production sandbox and bounded health check, run
   Alembic with `--no-deps`, then start backend/frontend with bounded readiness.
   Verify deployed image IDs, settings/data bindings and unchanged DB container.
   Never restart/recreate the database, stamp, delete volumes or roll back silently.
7. Every failure blocks the next phase. The private directory retains logs,
   backups and phase markers for deliberate recovery. No consent is accepted and
   no notification test is sent. Normal existing monitoring/delivery can resume
   after deployment according to the preserved settings.

## Ownership and limits

The helper is a bounded operational migration for this reviewed topology, not a
replacement for the generic startup helper or a new deployment service. The
normal provenance guard remains unchanged. Extra exchange overlays, additional
mounts, different resource limits, scaling and new environment overrides require
separate review; they are rejected. New application defaults not represented in
Compose or a running environment still require release review. The helper cannot
infer historical frontend build arguments or prove the contents of old images.

The original checkout, `.env`, package files and image tags remain available.
Private state must be retained as the deployment's configuration; it is not a
throwaway diagnostic directory. No secret files belong in Git/support uploads.
Use its full Compose chain for status and later reviewed maintenance. Do not run
the base startup command against the migrated stack.

This addresses operational stabilization in Roadmap M10/M11 and the existing
monitoring backlog without changing feature approvals, source-selection contracts
or model/trading policies. No new ADR is required: existing services, contracts,
volumes, sandbox and migration mechanism are retained.

## Verification

- Pure validator regressions cover settings, dollar escaping/decoding, topology, mounts,
  resources, ports, secret-safe errors and immutable preparation identity.
  Docker Compose serializes resolved JSON with doubled dollar signs; the validator
  decodes that single layer before comparing it to raw Docker inspection. The real
  container fixture includes a bind path with spaces and a literal dollar sign.
- Shell regressions execute the real entry point in disposable Git checkouts with
  fake Docker, covering build-only preparation, private permissions, ordering,
  input drift and backup/renderer/migration/application failures.
- The renderer workflow additionally runs the actual preparation and deployment
  against disposable PostgreSQL, backend, frontend and sandboxed renderer
  containers. A synthetic DB row and volume marker survive; backups are readable,
  false flags remain false, images match and readiness/migrations succeed. No real
  provider data, production credentials or personal consent are used.
- Existing full backend/PostgreSQL/coverage, frontend, E2E, production image,
  sandbox and version checks remain release gates. Final SHA/results are in the PR.

GitHub checks do not prove deployment or provider reachability on the operator
host. JPMorgan product access/consent reuse and complete monitoring cycles remain
separate live acceptance steps.
