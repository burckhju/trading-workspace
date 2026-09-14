# Explicit underlying venue switch

Use this command after deciding which venue should supply a stock's monitoring
prices. Automatic discovery continues to preserve the existing primary listing;
it never chooses another venue. This operation is separate from warrant quotes.

The command requires an explicit workspace, ISIN selection, source MIC, target
MIC and unchanged quotation currency. There are no instrument seeds, migrations,
new subscriptions or provider activation flags. It uses the configured EODHD
account, synchronizes account usage and retains its configured budget, limiter
and retry policy. The existing reference tables must contain an active target
venue and currency. An instrument identity alone does not prove price coverage.

## Verification and writes

`python -m app.tools.switch_underlying_venue` is read-only by default. It checks
the current primary listing and corroborates the target stock by exact ISIN,
currency and MIC through the existing EODHD catalog/search service. `DRY_RUN`
reports `data_verified: false`: it has not imported or verified EOD history.

With `--apply`, for each explicitly supplied ISIN:

1. Create an additional non-primary listing through the audited FT-001 service,
   or reuse the exact active target listing. Never rewrite the old listing's
   ticker, venue, currency or historical prices.
2. Create/validate the provider mapping through existing discovery and mapping
   administration, including provider-neutral market-data identity. Preserve
   disabled/conflicting mappings and block the switch instead of replacing them.
3. Import up to 400 calendar days ending yesterday through the existing EOD import
   service. Require valid, nonempty data and a persisted latest completed row
   with matching identity/currency/provenance. The row must meet the existing
   `position_monitoring.max_completed_price_age_days` limit (default four days).
   Today's candle, a future row, stale history or a failed/empty import cannot
   authorize the switch.
4. Recheck source/target/mapping versions and instrument identity. Change primary
   flags using the audited FT-001 service only after verification. The old listing
   remains active and retains its data. Stop and target numbers are unchanged;
   they are subsequently evaluated against the selected venue's daily low/high.

Failures are isolated per ISIN and return `BLOCKED` plus a reason, with a nonzero
process exit status. Other selected instruments still run. A failed probe may
leave a staged non-primary listing/mapping and imported history, but it does not
switch the primary. Retry with the same arguments; successfully switched rows
are reverified and return `ALREADY_PRIMARY` without duplicate listings/mappings
or additional primary-change audit events. This is not an atomic all-or-nothing
batch: inspect each result. No alert cycle, order or notification is triggered by
the command itself.

## Docker operation

Pull/build the merged code using `bash scripts/start-linux.sh --frankfurt` first.
This performs the usual Alembic upgrade; this change introduces no new migration.
Use the same Compose overrides as the existing installation. For an installation
with the Frankfurt override, the following is a one-stock example. Replace the
ISIN selection with the explicitly reviewed stocks; repeat `--isin` for each.

Pause the backend during the operation so background imports and monitoring do
not race the maintenance process or maintain separate EODHD usage counters. Keep
the database running. The frontend can temporarily report the backend unavailable.

```bash
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml stop backend

docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml run --rm --no-deps backend \
  python -m app.tools.switch_underlying_venue \
  --workspace-id 00000000-0000-4000-8000-000000000001 \
  --from-mic XETR --to-mic XFRA --currency EUR \
  --isin US0378331005 --apply

# Run this even if the preceding command reports blocked instruments.
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.frankfurt.yml up -d backend

curl -fsS http://localhost:8000/health/ready
```

Omit `--apply` for the initial read-only identity report. The command does not
accept a file of old provider evidence: target proof is obtained again using the
configured account. Instrument/provider errors expose safe codes, not request URLs
or tokens. A permission or subscription error needs review of the existing access;
the command never purchases additional coverage.

## End-to-end verification and limits

For each changed ISIN require `APPLIED` or `ALREADY_PRIMARY`, `data_verified: true`,
the intended target MIC/currency, verified provider identity, a completed
`trading_date`, `close`, `low`, `high` and the original `retrieved_at`. The output
includes both listing IDs, mapping ID and the configured age limit.

After restarting the backend, the catalog scan picks up the new primary listing.
Check `/api/v1/market-data/refresh/status`: the relevant `EODHD_MAPPING` and
`UNDERLYING_EOD` jobs should finish successfully. In the underlying master-data
detail, the new venue must be primary and the previous listing still present.
Trade monitoring health should resolve the new mapping. A successful import is
not proof of a completed alert cycle; use the existing monitoring diagnostics to
check that separately.

Existing FT-006 analysis runs retain their original listing and snapshot. They
are not relabelled or copied onto the new venue. Run a new market analysis for the
new primary listing when positions need dynamic-stop/phase/score projections;
otherwise those projections can correctly report missing analysis. Warrant
valuation, executions, position quantities, trade plans and historical alerts
are not rewritten. EOD data do not provide live or executable order prices.

Cross-currency switching is deliberately rejected. A USD/CHF candidate requires
a separate rule-currency decision and is outside this operation.

Regression coverage includes a PostgreSQL path through the real listing/mapping/
import services, preservation of previous history, idempotent retry, empty/stale/
invalid quotes, concurrent primary changes, disabled mappings, identity conflicts,
read-only plans and isolated/redacted batch errors. Live account coverage must be
verified by running the command in the installation with its configured key.
