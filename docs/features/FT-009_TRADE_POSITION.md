# FT-009 – Trade & Position / Purchase Execution Capture

## Status
Implemented in Sprint 9 and technically release-ready after PR #18; see `docs/implementation/SPRINT_9_TECHNICAL_CLOSEOUT.md` and `docs/implementation/SPRINT_9_FT009_RELEASE_READINESS.md`.

## Purpose
FT-009 records purchases that actually occurred and derives the open position from the effective purchase-execution history. The system documents user-confirmed facts; it does not decide whether, what, or how much the user should buy.

## User value
The normal workspace flow requires only the new facts the user actually knows after purchase:

- quantity purchased,
- actual average purchase price per warrant,
- execution time only when it differs from the default `now`.

Known TradePlan, ProductSelection, product, terms, listing, provenance and identity context is reused. Calculated values are never requested as user input.

## Entry contracts

### Workspace-guided purchase
A valid `ProductSelection` exists. FT-009 consumes the exact historic ProductSelection context and does not mutate it.

The user normally enters only:

- `quantity`,
- `price_per_unit`.

### External purchase
A TradePlan or ProductSelection is not required. The purchased product must resolve to an existing stable product identity from the reference/product domain.

The user enters:

- product identity/search input,
- `quantity`,
- `price_per_unit`,
- `executed_at` only when backdating is needed.

FT-009 must not create a shadow or free-text product identity.

### Additional purchase
An existing open Trade and Position are reused. A new immutable purchase execution is added to the same Trade and Position.

## Core domain boundary

```text
Trade
!=
ExecutionRecord
!=
Position
```

V1 cardinality:

```text
1 Trade -> 1 Position -> 1..n effective PURCHASE ExecutionRecords
```

A Trade is the stable identity of the real trading case. An ExecutionRecord is an immutable historical fact. A Position is the current derived holding state.

## Trade origin

V1 distinguishes:

- `WORKSPACE_SELECTION`
- `EXTERNAL`

A workspace-origin Trade references the exact `ProductSelection`. An external Trade does not fabricate a ProductSelection.

## Purchase execution V1

An `ExecutionRecord` with execution type `PURCHASE` records at least:

- stable identity,
- Trade identity,
- quantity,
- actual average purchase price per unit,
- execution timestamp,
- recording timestamp,
- calculated gross amount,
- audit/provenance information,
- correction/supersession relation when applicable.

`gross_amount = quantity * price_per_unit` is calculated by the system.

V1 records an aggregated user-confirmed purchase execution. Individual broker order/fill legs are not required.

## Position derivation

For effective purchase executions only:

```text
open_quantity = sum(quantity_i)
total_cost = sum(quantity_i * price_i)
average_entry_price = total_cost / open_quantity
```

Calculations use decimal arithmetic. Display rounding must never overwrite historical execution prices.

An additional purchase:

- creates a new ExecutionRecord,
- does not change an existing ExecutionRecord,
- does not create a new Trade,
- does not create a second Position for the same Trade.

## Execution time

`executed_at` and `recorded_at` are different facts.

- `executed_at`: when the purchase actually happened,
- `recorded_at`: when Trading Workspace recorded it.

The UI defaults `executed_at` to `now`; the user changes it only for a historical entry.

## Corrections

Confirmed ExecutionRecords are immutable. A correction creates a traceable replacement/correction relation. The original record remains auditable and is excluded from effective position derivation once superseded.

The exact persistence representation is an implementation detail, but in-place historical overwrite is prohibited.

## Duplicate handling

Similar quantity/price/time combinations can represent genuine separate purchases. Duplicate detection therefore warns but does not enforce a false business-key uniqueness constraint.

## Pre-execution boundary

A pre-execution check may support the user before an external purchase, but it is not required to record an execution that already occurred.

A missing provider/live quote must never prevent historical purchase capture.

## Consumer contracts

FT-009 consumes without rewriting:

- FT-004 product identity and reference context,
- FT-007 TradePlanVersion when available,
- FT-008 ProductSelection and its historical context when available,
- established audit/provenance and UoW/repository patterns.

Released FT-007 and FT-008 contracts remain unchanged unless a separately documented cross-feature gap is proven.

## V1 validation rules

- quantity must be greater than zero,
- warrant quantity is integral in V1,
- price per unit must be greater than zero,
- gross amount is system-calculated,
- a workspace-origin execution must not silently substitute another product for its ProductSelection,
- an external execution requires resolved product identity,
- implausible future execution times are rejected,
- past execution times are allowed.

## User workflow

### Workspace initial purchase

```text
ProductSelection
-> Record purchase
-> enter quantity + actual purchase price
-> confirm
-> Trade + ExecutionRecord + Position
```

### External initial purchase

```text
Resolve product
-> enter quantity + actual purchase price
-> confirm
-> Trade + ExecutionRecord + Position
```

### Additional purchase

```text
Open Position
-> Record additional purchase
-> enter quantity + actual purchase price
-> confirm
-> new ExecutionRecord
-> same Position recalculated
```

## V1 non-scope

- automatic quantity/position-size decisions,
- risk-budget input or recommendation,
- broker order placement,
- broker order lifecycle,
- individual broker fill synchronization,
- sales and partial sales,
- position closing,
- realized P&L,
- stop/target trade management after opening,
- portfolio-risk management,
- fees, commissions, taxes and transaction costs,
- automatic trading decisions.

## Acceptance criteria

1. A workspace purchase can be recorded with quantity and actual purchase price without re-entering known product/plan/selection data.
2. Initial purchase creates a Trade, immutable purchase ExecutionRecord and open Position atomically.
3. An external purchase can be recorded without fabricating TradePlan or ProductSelection history.
4. An additional purchase creates another immutable ExecutionRecord for the same Trade/Position.
5. Position quantity, total cost and average entry are deterministically derived from effective purchase executions.
6. Invalid quantity or price is rejected.
7. Backdated execution preserves separate `executed_at` and `recorded_at` values.
8. A possible duplicate produces a warning but can be explicitly confirmed as a genuine second purchase.
9. A correction does not overwrite the original execution history.
10. Missing live/provider data does not block recording a purchase that already occurred.
