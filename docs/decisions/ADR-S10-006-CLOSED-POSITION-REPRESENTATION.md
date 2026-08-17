# ADR-S10-006 – Closed Position Representation

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
The released FT-009 Position persistence requires positive open quantity and cost basis, so a fully exited trade cannot currently be represented. Removing the Position on close would erase the stable one-Position-per-Trade read identity and complicate downstream consumers.

## Decision
The same Position remains the materialized projection for the Trade after full exit.

A closed Position supports:

```text
open_quantity = 0
remaining_cost_basis = 0
```

The model must preserve or make reproducible historical entry information through execution history. A zero open quantity must not imply that historical average entry facts are lost.

`opened_at` remains the first effective BUY time. The closing time is derived/stored consistently from the effective full-exit SELL according to the final technical model.

## Consequences
Existing positive-only database/domain constraints must be migrated. The exact closed-position representation of `average_entry_price`/`closed_at` is a technical specification point, but it must preserve deterministic reconstruction and clear API semantics.

The one-Position-per-Trade invariant remains.

## User impact
After selling the final units the same trade/position view can show that the holding is closed instead of disappearing or being replaced by a second object.
