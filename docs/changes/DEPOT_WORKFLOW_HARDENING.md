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

### Warrant position valuation

- Adds read-only indicative valuation for open LONG positions using the exact historical WarrantListing provenance from ProductEvaluation.
- Marks the LONG position at bid and exposes bid/ask, quote timestamp, market value, and unrealized gross P&L.
- Does not guess a listing for external trades without historical listing provenance.
- Does not estimate market value when a usable bid is missing.
- Keeps product valuation separate from Underlying-based stop/target monitoring.

## Non-scope

- Broker integration or order placement
- New trading decisions or recommendations
- New alert types or alert transition semantics
- Database migrations
- Fees, taxes, commissions, or net P&L
- Product substitution or automatic trade closing
