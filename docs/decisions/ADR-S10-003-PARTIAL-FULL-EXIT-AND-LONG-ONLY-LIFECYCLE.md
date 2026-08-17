# ADR-S10-003 – Partial/Full Exit and LONG-only Lifecycle

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
Candidate/TradePlan V1 is LONG-only and FT-010 must not implicitly add SHORT semantics through sales. Partial/full exit and Trade closing require one unambiguous rule.

## Decision
For every SELL:

```text
sell_quantity <= open_quantity_before
```

A larger quantity is rejected fail-closed.

Classification is derived:

```text
sell_quantity < open_quantity_before  -> PARTIAL EXIT
sell_quantity == open_quantity_before -> FULL EXIT
```

Lifecycle is derived from effective execution history:

```text
open_quantity > 0 -> OPEN
open_quantity == 0 after prior BUY history -> CLOSED
```

A separate user-editable close flag does not override this state.

## Consequences
The Position model/persistence must support zero open quantity. Negative quantity is invalid. FT-011 handoff is gated by the derived CLOSED state.

## User impact
The user enters the actual sale quantity; the system automatically knows whether the trade remains open or is fully closed and prevents accidental implicit short positions.
