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

### Held-product valuation

- Resolves the exact historical WarrantListing instead of guessing a venue or replacement product.
- Uses the held product Bid for indicative LONG market value and unrealized gross P&L.
- Keeps product valuation separate from Underlying-based Stop/Target monitoring.
- Exposes quote observation time and age as explicit data-health facts.
- Treats quotes older than the product-valuation freshness limit as `STALE`.
- Keeps stale Bid/Ask values visible for diagnosis but does not calculate a current market value or unrealized P&L from them.
- Does not create trading alerts or automatic buy/sell decisions from product valuation state.

### Trade timeline

- Exposes the existing combined execution/management timeline in the operational position workflow.
- Shows BUY/SELL executions and management decisions with occurred/effective and recorded timestamps.
- Keeps corrected and superseded facts visible instead of hiding immutable history.
- Refreshes the timeline after successful sale and management captures without introducing a second history model.

### Operational workspace prioritization

- Reuses the existing ephemeral Operational Workspace read model instead of adding a new attention domain.
- Keeps persisted open position alerts as the highest-priority operational position signal.
- Replaces the generic open-position action with a read-only data-health action when the existing monitoring health service reports `MISSING`, `STALE`, or `ERROR`.
- Leaves healthy open positions as the existing normal trade-management action.
- Does not create alert records, notification records, or persisted attention state from data-health problems.
- Treats ordering as an operational presentation rule, not as a trading recommendation.

## Deferred

- Product-data health is currently shown in the trade workflow but is not yet projected into a separate Operational Workspace action.
- Multi-target monitoring and pre-threshold distance warnings remain deferred until existing trading/management rules define their semantics.
- Intraday Underlying monitoring remains separate from the current completed-daily Stop/Target contract.

## Non-scope

- Broker integration or order placement
- New trading decisions or recommendations
- New alert types or alert transition semantics
- Database migrations
- Fees, taxes, commissions, or net P&L
- Product substitution or automatic trade closing
