# Daily Position Loop Operational Validation

This runbook validates the already implemented open-position operating loop on the target Linux deployment. It is a stabilization/qualification procedure, not a new trading feature.

The validated chain is:

`deployment + market data -> position monitoring -> alert/attention -> Operational Workspace -> Trade Management -> captured sale`

The procedure preserves the existing ownership boundaries:

- executions and the position projection remain economic truth;
- TradePlan/TradeManagement remain the source of stop/target management levels;
- monitoring derives alerts/attention but does not execute trades;
- notifications only deliver already-created alert information;
- a sale is recorded only after an execution has actually happened outside the workspace.

## Prerequisites

Start the supported local deployment first:

```bash
bash scripts/start-linux.sh
```

The validator expects `docker/.env`, a running backend container, and a ready database. It never prints the environment file or its secrets.

## Read-only deployment and data-health validation

Run:

```bash
bash scripts/validate-daily-position-loop.sh
```

This verifies:

1. Docker Compose services are running;
2. backend liveness and readiness;
3. the database is on the repository Alembic head;
4. Börse Stuttgart delayed-source diagnostics;
5. the Operational Workspace open-position snapshot.

Require Stuttgart delayed data to be operationally ready:

```bash
bash scripts/validate-daily-position-loop.sh --require-stuttgart
```

A non-READY Stuttgart source fails the command instead of being treated as a valid product valuation source.

## Validate a real existing open trade

Use the trade UUID from the workspace:

```bash
bash scripts/validate-daily-position-loop.sh \
  --trade-id <uuid> \
  --require-stuttgart
```

The validator additionally prints provider-neutral Underlying monitoring health and held-product valuation, including source-attempt diagnostics exposed by the existing API.

## Reproducible controlled XSTU position

For deployment-near testing, reuse the existing safe XSTU seed tool through the validator:

```bash
bash scripts/validate-daily-position-loop.sh \
  --seed-price 2.42 \
  --seed-quantity 10 \
  --require-stuttgart
```

The seed uses the existing ProductSelection snapshot and `TradePositionService.record_initial_purchase(...)`. It does not insert a Position directly and does not simulate a broker connection. If the same selection already has an open position, the existing seed remains idempotent.

## Controlled monitoring cycle

Run exactly one monitoring cycle:

```bash
bash scripts/validate-daily-position-loop.sh \
  --trade-id <uuid> \
  --run-monitor
```

Telegram delivery is never silently enabled by this operational validator. If Telegram is configured and a live delivery is intentionally part of the qualification, authorize it explicitly:

```bash
bash scripts/validate-daily-position-loop.sh \
  --trade-id <uuid> \
  --run-monitor \
  --allow-telegram
```

Use only a controlled position before authorizing a live message. The existing durable notification semantics remain unchanged: transport failure must not roll back the trading alert.

## Manual user-flow completion

After the automated operational checks:

1. open the Operational Workspace at `http://localhost:8080`;
2. verify the controlled open position is visible;
3. confirm alert/data-health priority matches the API output;
4. open Trade Management for that position;
5. verify current stop/target, monitoring health, product valuation, alerts and immutable timeline;
6. if an execution has actually happened, record a partial sale through the existing sales workflow;
7. if the remaining quantity has actually been sold, record Full Close;
8. verify open quantity, realized P&L basis, timeline and CLOSED handoff.

Do not invent a sale purely to make the validation green. The workspace captures executions; it does not create them.

## Evidence to retain

For an operational qualification run, retain only non-secret evidence:

- Git commit deployed;
- Alembic head reported by the validator;
- Stuttgart source status and latest verified file timestamp;
- trade ID used for the controlled validation;
- Underlying monitoring status;
- held-product valuation status and selected source;
- whether one monitoring cycle was run;
- whether Telegram was explicitly authorized and its resulting persisted delivery state;
- resulting partial/full-close state and timeline observation when a real execution was captured.

Never paste `docker/.env`, bot tokens, API keys or database passwords into an issue, PR or support log.

## Failure classification

Classify a failed operational run before changing architecture:

- `ENVIRONMENT`: Docker, readiness, database or migration mismatch;
- `PROVIDER_DATA`: Stuttgart/EODHD unavailable, stale, missing or schema/source failure;
- `INTEGRATION`: valid source data exists but the existing API/monitoring composition fails;
- `UX`: API/domain state is correct but the user cannot complete the intended flow clearly;
- `BUG`: implemented behavior violates its current contract;
- `ARCHITECTURE_GAP`: only when the required behavior cannot be represented safely by an existing owner/capability.

A provider outage or stale quote is not an architecture gap and must remain fail-closed.
