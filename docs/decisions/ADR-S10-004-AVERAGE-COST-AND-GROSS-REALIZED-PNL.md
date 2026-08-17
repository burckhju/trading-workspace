# ADR-S10-004 – Average Cost and Gross Realized P&L

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
FT-009 already derives weighted average entry price for multiple purchases. FT-010 needs a single reproducible cost-basis method for partial sales and realized P&L. Fees, commissions and taxes are not modeled in the released baseline.

## Decision
FT-010 V1 uses Average Cost Method.

Before a SELL, the current average entry price is the applicable cost per sold unit.

```text
realized_gross_pnl_delta
= sell_quantity * (sell_price_per_unit - average_cost_per_unit)
```

Remaining cost basis is reduced by:

```text
sell_quantity * average_cost_per_unit
```

FT-010 exposes only realized **gross** P&L before fees, commissions and taxes.

Transaction costs remain non-scope and are not represented as artificial zero facts.

## Consequences
FIFO and LIFO are not implemented or mixed into V1. Decimal arithmetic and deterministic tests are mandatory. API/UI naming must make gross semantics explicit.

## User impact
After a partial or full sale the user sees a consistent realized result that matches the already familiar weighted-average entry method, with a clear warning that fees and taxes are not included.
