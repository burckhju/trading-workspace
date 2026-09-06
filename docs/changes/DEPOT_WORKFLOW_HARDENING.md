# Depot Workflow Hardening

## Scope

This change hardens the existing FT-010 position workflow without changing trade execution semantics.

### Sale capture

- Keeps the existing immutable SELL ExecutionRecord path.
- Adds a low-input full-close action that submits the current open quantity through the same sale endpoint.
- Exposes the already-supported optional execution timestamp.
- Makes clear that sale capture documents an already executed transaction and does not place a broker order.

### Monitoring data health

- Adds a read-only position monitoring health view with `OK`, `MISSING`, `STALE`, and `ERROR`.
- Reuses the existing provider-neutral completed-daily Underlying price contract and the configured stale threshold.
- Does not create alerts for missing, stale, or failed market data.
- Does not mutate monitoring rule state.

### Trade timeline

- Exposes the existing combined execution/management timeline in the operational position workflow.
- Shows BUY/SELL executions and management decisions with occurred/effective and recorded timestamps.
- Keeps corrected and superseded facts visible instead of hiding immutable history.
- Refreshes the timeline after successful sale and management captures without introducing a second history model.

## Deferred

Current product valuation, market value, and unrealized gross P&L remain a separate follow-up. The provider-neutral `WARRANT_LISTING_QUOTE` boundary exists, but the currently configured EODHD adapter does not implement that capability yet. This slice therefore does not pretend that a reliable current product quote is available.

## Non-scope

- Broker integration or order placement
- New trading decisions or recommendations
- New alert types or alert transition semantics
- Database migrations
- Fees, taxes, commissions, or net P&L
- Product substitution or automatic trade closing
