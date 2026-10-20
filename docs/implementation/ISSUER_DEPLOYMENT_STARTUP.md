# Issuer deployment startup stabilization

Date: 2026-10-01. Baseline: `022f495392634e71fb3935ea79b34816b20540ba` (v1.4.0).
Category: deployment integration bug; no domain or architecture change.

## Problem and reproduction

The canonical `scripts/start-linux.sh` only includes base Compose and an existing
Frankfurt overlay. It cannot carry the canonical issuer overlay or additional
operator-owned exchange overlays. Recreating an issuer-enabled backend through
that entry point therefore omits its issuer settings and network. The renderer
image is not explicitly rebuilt. The migration command also allows Compose to
start dependencies before the intended application-start phase.

Reproduce without production data using the existing disposable-checkout/fake-Docker
tests: represent an existing backend's `com.docker.compose.project.config_files`
label containing the issuer overlay, then invoke the default helper. The baseline
continues to build/migrate/start with only the base file instead of stopping.

## Scope and acceptance criteria

1. `--issuer-monitoring` explicitly adds the canonical issuer overlay. Repeated
   `--overlay FILE` arguments carry existing exchange/custom overlays in order.
   New installations remain opt-in; no provider is activated by file presence.
2. Before builds, migrations or cache synchronization, inspect all existing project
   containers (including stopped containers). Refuse missing/reordered prior Compose
   files or unreadable provenance. Do not guess how obsolete package overlays map to
   the new overlay, or silently migrate a relocated installation.
3. `--check` performs only configuration/provenance validation: no configuration
   creation, cache refresh, image build, container start, migration or delivery.
4. Build the renderer with backend/frontend when opted in; require its bounded
   sandbox health check before migrations or backend recreation. Alembic runs with
   `--no-deps`; failures stop the sequence. Volumes and environment files are retained.
5. Print correctly shell-quoted status/log commands for the same complete chain.
6. Regression tests execute the actual shell entry point with synthetic Docker
   responses; existing Frankfurt, first-install and failure behavior remains covered.

## Architecture, risk and boundaries

This belongs to the existing deployment helper, with the existing Compose services,
private consent volume and sandbox profile. No new runtime service, schema, source
policy, trading rule, notification command or external dependency is introduced.
It supports the operational stabilization goals in Roadmap M10/M11 and the existing
monitoring capability in the Product Backlog; it does not change their approval states.

Container labels establish previous Compose paths/order, not previous file contents
or environment values. Operators still review effective settings and preserve their
private configuration. An intentionally removed overlay or a relocated checkout
requires deliberate manual deployment using the runbook; there is no bypass flag.
A failed startup can leave new images or a restarted renderer, and later failures
can follow successful migrations. There is no automatic rollback or volume deletion.

## Validation and live boundary

Final automated results and exact head are recorded in the pull request. Mandatory
PostgreSQL, coverage, frontend, E2E, image-permission, renderer-sandbox and version
guards remain unchanged. No live provider call or production mutation is a test.
JMBbot could not be resolved from this workspace on 2026-10-01; deployed images,
loaded settings, consent reuse, provider coverage and delivery remain unverified.
