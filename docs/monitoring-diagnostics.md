# Verify position monitoring after a venue change

Three separate observations matter: a verified primary listing, available prices
for that listing, and a completed automatic rule evaluation. A healthy database
or `market-data/refresh/status.running` alone does not prove stop/target monitoring.

## Trade Management

Open **Trade verwalten → Positions-Alerts**. The underlying data panel shows the
selected primary listing's name, ISIN, MIC and currency, plus the provider's
completed daily close/low/high. Stop evaluation uses the underlying daily low;
target evaluation uses the underlying daily high. Warrant bid/ask/reference prices
and market value remain in **Produktbewertung**. Each persisted stop/target alert
is labelled with its underlying price field. The current data panel describes the
current selection; it does not relabel historical alerts with a new venue.

The original provider update time and retrieval time are separate. A new retrieval
is not a new trading day. Stale, identity-conflicting or invalid data retain their
error status; valid stale daily prices may be displayed with the warning. No price
is invented, converted or copied between instruments. The existing health endpoint
still uses its configured provider, cache, budget and age policy.

## Check the automatic runner

```bash
curl -fsS http://localhost:8000/health/ready
curl -fsS http://localhost:8000/api/v1/position-monitoring/runtime/status | jq
```

`runtime/status` is read-only and never starts a cycle, imports data, changes a
rule, creates an alert or sends a notification. It adds no provider requests.
It reports the runner created by the existing application lifespan:

- `enabled`: configured scheduling switch. Defaults to false; data refresh and
  automatic stop/target checks are independently configured.
- `running`: the runner is executing or waiting for its next interval.
- `cycle_running`: a runtime cycle is currently in progress.
- `last_cycle_started_at`, `last_cycle_completed_at`, `next_run_at`: actual loop
  observations; null means there is no corresponding evidence yet.
- `last_error`: a safe fixed code for the most recent failed attempt, cleared when
  a later cycle completes. `last_error_at` retains the last failure timestamp.
- `last_result`: counters of the last completed cycle. A completed cycle can have
  missing data or rule errors; it does not mean all positions were checked.

Counters distinguish `subject_errors` (such as missing primary mapping/rules),
`missing_market_data`, `stale_market_data`, `market_data_errors`, `position_errors`,
`positions_checked`, and `rules_evaluated`. Alert and delivery counts are separate.
On failure, earlier counters and their completion timestamp are retained and labelled
as the previous completed cycle, never as evidence that the failed cycle succeeded.

These observations are **process-local**, include all workspaces handled by that
runner and reset on backend restart. They are neither durable monitoring history
nor a cluster-wide status or proof of evaluation of one specific trade. A one-shot
CLI cycle in a separate process does not update this endpoint. The UI is a snapshot
when Trade Management loads; reload to observe progress.

## Verify a particular position

Set `TRADE_ID` to the real trade UUID. For the existing UNH example:

```bash
TRADE_ID='dd8338bd-a092-42c0-94c0-c068a9094f77'
curl -fsS "http://localhost:8000/api/v1/position-monitoring/trades/${TRADE_ID}/health" | jq
curl -fsS "http://localhost:8000/api/v1/position-monitoring/trades/${TRADE_ID}/product-valuation" | jq
```

For a switched basis require `basis.venue_mic == "XFRA"`, its verified
`basis.listing_id`, the intended currency, matching `daily_price.listing_id`, and
the completed `daily_price.trading_date`. `status == "OK"` means the current data
and subject resolution meet monitoring requirements. Check the runtime counters
separately and inspect persisted alerts at `/api/v1/alerts/trades/<trade UUID>`.
Absence of alerts alone is not proof that a cycle ran.

The old Xetra listing may still have blocked secondary refresh jobs. Do not use
their aggregate count to judge the current primary mapping. Existing FT-006
analysis snapshots remain tied to their original listing; generate a new analysis
for the new primary when dynamic-stop/phase/score projections need it.

If scheduling is disabled, review the existing
`TRADING_WORKSPACE_POSITION_MONITORING__ENABLED` configuration and notification
settings before activating it. This diagnostic change does not enable scheduling
or Telegram, change intervals, purchase access or authorize order execution.

Deploy with `git pull --ff-only` and `bash scripts/start-linux.sh --frankfurt` for
the existing Frankfurt installation. The script builds the images and applies the
normal Alembic upgrade; this change adds no schema migration. Retain the existing
environment and access settings.
