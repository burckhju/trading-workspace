# FT-010 – Trade Management

## Status
Specified for Sprint 10 after S10-00 Architecture & Gap Review and explicit approval of the fachliche decision package. Production implementation remains gated by Definition of Ready and explicit implementation approval.

## Purpose
FT-010 enables the user to manage an actually open LONG trade after purchase while preserving the historical separation between planning, actual executions, management decisions and derived position state.

The system records user-confirmed facts and user-made management decisions. It does not decide whether, when or how much the user should sell, and it does not automatically change stops, targets, thesis or position size.

## User value
For an active trade the user can:

- see the current open quantity and entry basis,
- record an actual partial or full sale,
- see realized gross P&L after sales,
- document stop and target changes without rewriting the TradePlan,
- document thesis/management changes and notes,
- correct factual execution entries without erasing history,
- understand when a trade is economically closed,
- hand a fully closed trade to FT-011 Nachbeobachtung.

Calculated values are derived by the system and are not requested as user input.

## Core domain boundary

```text
Trade
!=
ExecutionRecord
!=
TradeManagementEvent
!=
Position
```

Semantics:

- `Trade` is the stable identity of the real trading case.
- `ExecutionRecord` is an immutable historical fact of an actual economic execution.
- `TradeManagementEvent` is an immutable historical record of a management decision or management-intent change.
- `Position` is the deterministic current projection from effective execution history.

A sale is an `ExecutionRecord`, not a management event. A stop change is a `TradeManagementEvent`, not an execution.

## FT-009 evolution contract

FT-010 evolves the released FT-009 execution model without creating a parallel sale model.

```text
ExecutionRecord
  side = BUY | SELL
```

All historical FT-009 purchase executions remain valid and are interpreted/migrated as `BUY`.

FT-010 must preserve:

- stable Trade identity,
- FT-009 origin/provenance,
- immutable execution history,
- exact historical TradePlanVersion/ProductSelection references,
- one Position per Trade in V1,
- provider/broker independence,
- explicit user confirmation of actual executions,
- no automatic trading decision.

## Execution V1

An effective execution records at least:

- stable identity,
- Trade identity,
- product identity,
- `side = BUY | SELL`,
- integral quantity greater than zero,
- actual average execution price per unit greater than zero,
- execution timestamp,
- recording timestamp,
- actor/audit context,
- correction/supersession relation when applicable.

```text
gross_amount = quantity * price_per_unit
```

The system records aggregated user-confirmed executions. Broker order objects, order states and individual broker fill legs remain outside V1.

## LONG-only and sale validation

Sprint 10 V1 remains LONG-only.

For a SELL execution:

```text
sell_quantity <= open_quantity_before
```

If:

```text
sell_quantity > open_quantity_before
```

the command fails closed. FT-010 must not create a negative Position, implicit short Position or new short Trade.

## Partial and full exit

Classification is derived and is not a separate user input.

```text
SELL quantity < open_quantity_before
-> PARTIAL EXIT
```

```text
SELL quantity == open_quantity_before
-> FULL EXIT
```

A partial exit leaves the Trade open. A full exit produces a closed Position/Trade state derived from effective execution history.

## Position projection

Position remains derived state.

For every effective execution history the current Position must be reproducible deterministically.

V1 uses the Average Cost Method.

For BUY:

```text
new_open_quantity = old_open_quantity + buy_quantity
new_remaining_cost_basis = old_remaining_cost_basis + buy_gross_amount
new_average_entry_price = new_remaining_cost_basis / new_open_quantity
```

For SELL, before applying the sale:

```text
applicable_cost_per_unit = current_average_entry_price
realized_gross_pnl_delta = sell_quantity * (sell_price_per_unit - applicable_cost_per_unit)
new_open_quantity = old_open_quantity - sell_quantity
new_remaining_cost_basis = old_remaining_cost_basis - (sell_quantity * applicable_cost_per_unit)
```

For a partial exit, the remaining average entry price stays equal to the pre-sale average cost, subject only to exact decimal arithmetic.

For a full exit:

```text
open_quantity = 0
remaining_cost_basis = 0
```

The historical entry basis must remain analytically reproducible from execution history. Persistence representation of average entry on a closed Position must not destroy this history.

## Realized P&L

FT-010 V1 defines only:

```text
realized gross P&L before fees, commissions and taxes
```

No generic or ambiguous `profit`/`pnl` field may imply net economics.

Fees, commissions, taxes and transaction costs remain outside V1 and must not be represented as artificial zero-valued facts.

## Effective execution history and corrections

Confirmed executions are immutable.

A factual correction:

- preserves the original execution,
- creates a traceable replacement/correction relation,
- marks the superseded execution as ineffective for current projection,
- recalculates Position and realized gross P&L from effective execution history,
- never patches the original historical fact in place.

Correction is not deletion and is not silent overwrite.

## Trade lifecycle

Lifecycle is derived from effective execution history rather than an independent user-editable truth.

```text
first effective BUY -> OPEN
open_quantity > 0 -> OPEN
open_quantity == 0 after prior effective BUY history -> CLOSED
```

A UI confirmation records the actual SELL facts. It must not close a Trade independently of the economic execution history.

## TradeManagementEvent V1

FT-010 owns immutable Trade Management history separately from executions.

V1 event types:

- `STOP_CHANGED`
- `TARGET_CHANGED`
- `THESIS_UPDATED`
- `MANAGEMENT_NOTE`

Each event records at least:

- stable event identity,
- Trade identity,
- event type,
- effective timestamp,
- recording timestamp,
- actor/audit context,
- typed event data appropriate to the event type.

A management event never edits the original TradePlanVersion or ProductSelection.

### Stop changes
A stop change records the user's new actual management intent. The original planned stop remains part of the immutable TradePlanVersion.

### Target changes
A target change records the user's new actual management intent. Original plan targets remain unchanged.

### Thesis updates
A thesis update records a user-authored management-state change after trade opening. It must not rewrite the original planning thesis/assumptions.

### Management notes
A management note records contextual user commentary without changing economic execution facts.

## Timeline/read model

The UI may present executions and management events in one chronological trade timeline for usability, but their domain identities remain separate.

A partial exit or full exit may be displayed as a timeline event derived from a SELL ExecutionRecord. FT-010 must not persist a second independent economic truth for the same sale solely to populate the timeline.

## Product change boundary

Product change is explicit V1 non-scope.

A warrant/product change can imply at least:

```text
SELL old product
+
BUY new product
```

and can affect Trade identity semantics. FT-010 V1 therefore must not introduce a generic `PRODUCT_CHANGED` event that hides real executions or silently mutates `Trade.product_id`.

A future product-change feature requires a separate fachliche decision and ADR.

## FT-011 consumer contract

FT-011 may begin only when the real Trade is fully closed according to effective execution history.

Required handoff facts include:

- stable Trade identity,
- closed state derived from `open_quantity == 0`,
- complete effective execution history,
- actual exit quantities/prices/timestamps,
- realized gross P&L semantics,
- immutable TradeManagementEvent history,
- unchanged historical TradePlanVersion/ProductSelection provenance.

FT-011 must not reactivate real position risk or create real executions.

## UX principles

The active Trade view should make the following user actions explicit and low-input:

### Record sale
User enters normally:

- quantity sold,
- actual average sale price per unit,
- execution time only when different from `now`.

The system derives:

- partial vs. full exit,
- remaining open quantity,
- remaining cost basis,
- realized gross P&L,
- OPEN/CLOSED lifecycle.

### Change stop/target
User enters the new management value and optionally contextual information defined by the UI contract. The original plan remains visible and unchanged.

### Update thesis / add note
User explicitly records management context. These records never create executions.

### Correct execution
The UI must explain that the original record remains in history and that a correction recalculates derived current state.

## V1 non-scope

- automatic buy/sell/hold decisions,
- automatic exit recommendation or execution,
- automatic stop/target decisions,
- SHORT trades or negative positions,
- product change/product substitution,
- portfolio allocation or portfolio-risk engine,
- depot/broker synchronization,
- broker order placement,
- broker order lifecycle,
- individual broker fills,
- fees,
- commissions,
- taxes,
- transaction costs,
- net P&L,
- FT-011 virtual observation/Exit Review,
- FT-012 Journal/Performance evaluation.

## Acceptance criteria

1. Historical FT-009 purchase executions remain valid after the execution-side evolution and behave as BUY executions.
2. An actual sale creates an immutable SELL ExecutionRecord for the existing Trade.
3. SELL quantity greater than the current open quantity is rejected and never creates negative or SHORT state.
4. A sale smaller than current open quantity is derived as a partial exit and leaves the Trade OPEN.
5. A sale equal to current open quantity is derived as a full exit and results in `open_quantity = 0` and CLOSED lifecycle.
6. Position state is reproducible from effective BUY/SELL execution history rather than dependent on opaque incremental mutation.
7. Average Cost Method is used consistently for remaining cost basis and realized gross P&L.
8. Realized P&L is explicitly gross before fees, commissions and taxes.
9. A factual execution correction preserves the original execution and rebuilds derived state from effective history.
10. Stop changes are immutable TradeManagementEvents and do not rewrite TradePlanVersion.
11. Target changes are immutable TradeManagementEvents and do not rewrite TradePlanVersion.
12. Thesis updates and management notes remain separate from actual executions.
13. A unified UI timeline may combine presentation of executions and management events without duplicating economic truth.
14. Product change is not implemented as a generic mutation/event in V1.
15. A Trade becomes eligible for FT-011 only after a full economic exit derived from effective executions.
16. Missing provider/broker capability does not block recording a historical actual sale.
17. No FT-010 workflow makes an automatic trading decision.


## Explicit price basis correction (2026-09-14)

Automatic stop/target checks require a confirmed instrument and currency binding in the immutable management history. The former unconditional underlying-price interpretation is superseded. Legacy unbound rules remain blocked; legacy open alerts without provenance are quarantined. Product rules reuse the existing product valuation source and retain indicative-data warnings. See [Monitoring price basis](../monitoring-price-basis.md) for the binding contract, migration and local validation.

## Additive arithmetic provenance for realized SELLs (2026-10-17)

`PositionProjector.project_with_trace()` exposes the already accepted ADR-S10-004
arithmetic without changing `project()` or its Position result. Both calls use
one calculation loop and the existing `(executed_at, recorded_at, id)` ordering.
The trace contains the complete ordered immutable effective ExecutionRecord
snapshots once, plus a SELL index, applicable average cost, direct gross delta,
and quantity/cost basis before and after each SELL. The prefix before that index
contains all previous BUYs **and SELLs** needed to explain the remaining basis.
The SELL snapshot itself supplies the exact ID, quantity, price and time precision.

The trace does not select effective records or qualify trade cancellation,
reporting periods or execution currency. Callers must use the existing owner
contracts for those inputs. Date-only anchors remain internal ordering values;
the original calendar date and timezone stay in the source snapshot.

Decimal operations and precision are unchanged. At a full exit,
`cost_basis_before_close_reset` exposes any remainder before the existing reset
to zero; this is not an additional realized-PnL adjustment. SQL Numeric values
and unquantized domain results must not silently be equated.

There is no verified execution-currency capture contract in the current BUY/SELL
paths. Historical selection, current listings, quote-source decisions and
stop/target price bindings do not establish the currency of actual execution
prices. This arithmetic trace therefore makes no monetary reporting claim for
existing user records. The [source/period readiness contract](../implementation/PERIOD_REALIZED_GROSS_READINESS.md)
contains the separately decidable minimum capture extension and V1 report proposal;
[qualification](../implementation/PERIOD_REALIZED_GROSS_QUALIFICATION.md) distinguishes
synthetic arithmetic and actual owner/database checks from the still absent report
API/UI and human acceptance. Status remains exclusively in
[PB-017](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) and
[PB-019](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics).

## 2026-10-17 follow-up: explicit execution currency and period consumer

The later user instruction **“Ok, umsetzen”** approves the concrete additive
currency and narrow V1 report proposal; see
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md).
It supersedes the preceding readiness limitation as an implementation decision,
without turning historical unknown prices into confirmed currency facts.

`ExecutionCurrencyConfirmationService` is part of this execution owner. The
append-only `execution_currency_confirmations` relation binds one explicit
`USER_CONFIRMED` currency declaration to an exact execution, with actor/time,
note, request identity and optional superseded confirmation. All existing capture
commands and Learning `execute-as-trade` accept an optional declaration in their
own atomic transaction. Omission remains unknown; there is no default or backfill.
An economic correction needs a separate declaration for the replacement execution.

The existing booking/date history offers explicit confirmation and replacement
of a previous declaration. A confirmation changes no quantity, price, execution
date, recording timestamp or ordering key. Its GET history is pure and returns
current/history from one materialized query result. Commands retain the bounded
per-trade lock. Database constraints enforce workspace/execution identity, root
and successor uniqueness, request identity and immutability.

`performance.service.reader.RealizedGrossSnapshotReader` is a new read consumer of these
facts and `PositionProjector.project_with_trace()`. It takes a short dedicated
PostgreSQL `REPEATABLE READ READ ONLY` snapshot, materializes all sources, closes
the transaction and builds period SELL rows and summary from the same inputs.
It does not own executions or copy the average-cost calculation. Journal, review,
quotes and learned evidence are not inputs. Exact contract, limits, qualification
and migration consequences are in the
[report delivery record](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md).

Migration `20261017_0047` is additive above `20261014_0046`. It does not alter old
economic records or infer currencies. Its downgrade explicitly refuses to remove
the relation once confirmations exist. This development change is not a release
or target migration, and the existing cumulative position display is not thereby
relabelled as a historically qualified monetary period report.

## 2026-10-20 amendment: purchase currency reuse

The user expressly removed repeated currency entry for the same-currency sale.
The [ADR amendment](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
and [reuse contract](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md)
supersede the separate SELL/replacement declaration rule above. One pure owner
resolver first uses a direct current declaration, then a confirmed same-side
execution predecessor, then the complete preceding effective BUY prefix if all
its currencies are known and equal. The last rule applies to sales and additional
purchases. Unknown earlier BUYs are not repaired from later entries.

`currency_confirmation` remains the actual direct declaration. Additive
`currency_resolution` supplies the reused currency and concrete execution and
confirmation IDs on capture/replay, timeline, currency-history and report reads.
No derived declaration is written, including on GET. An explicit conflicting
currency is preserved and prevents a same-currency monetary contribution when
the required cost basis differs. The shared PositionProjector arithmetic remains
unchanged. The report definition becomes `realized-gross-sell-v2`.

Saving a typed actual BUY currency is its explicit confirmation; a second
checkbox is removed. Existing same-currency SELL, additional-purchase and date
correction forms need no repeated code. Actual exceptions remain deliberate
actions. This change needs no migration and fabricates no missing historical
currency. Tests and release evidence are linked from the reuse qualification;
the Product Backlog remains the sole work-status source.


## 2026-10-21: additive read-only single-trade sources

The existing trade-management page has an independent `view=sources` mode and a
new-tab entry that does not unmount an in-progress capture form. Five pure GETs
under `/api/v1/trade-position/trades/{trade_id}/sources` compose existing owner
facts, exact original planning, review/journal versions and historical evidence
relations. An explicit invalid version never falls back to latest.

A lock-free `TradeReader` is injected only into this read composition; command
repositories retain their existing locks. Each section materializes a separate
bounded read-only transaction and displays its own read window. No global
snapshot, new write owner, migration, provider access or monetary recomputation
is introduced. The closed-trade-report integration remains open; a raw position
amount is not presented as a qualified total.

[Source contract, fresh local tests and explicit native/browser gaps](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md)
document this local development slice. This amendment does not establish release,
installation, complete A1–A16 acceptance or a general trade-quality methodology.
