# Sprint 10 – FT-010 Rule Catalog

## Status
Specified after S10-00 Architecture & Gap Review and explicit approval of the fachliche decision package. Production implementation remains gated by Definition of Ready and explicit implementation approval.

## Scope
FT-010 manages an active LONG Trade by recording actual SELL executions, deriving partial/full exit and realized gross P&L, maintaining deterministic Position projection, and recording immutable management-decision history without rewriting planning history.

## RC-010-001 – User decision remains authoritative
FT-010 documents actual executions and user-made management decisions. It does not decide whether, when or how much to sell and does not automatically change stop, target or thesis.

## RC-010-002 – Execution and management event are different facts
An `ExecutionRecord` represents an actual economic execution. A `TradeManagementEvent` represents a management decision or management-intent change. They must not be collapsed into one generic event model merely for technical convenience.

## RC-010-003 – Execution side
The released ExecutionRecord evolves to support `BUY` and `SELL`. Historical FT-009 execution rows are migrated/interpreted as `BUY`. FT-010 must not introduce a parallel `SaleExecution` domain.

## RC-010-004 – Immutable execution history
Every confirmed BUY or SELL execution is immutable. Corrections preserve the original execution and establish which replacement is effective.

## RC-010-005 – Integral positive execution quantity
Execution quantity is integral and greater than zero. Direction is expressed by `side`, never by negative quantity.

## RC-010-006 – Positive execution price
Actual average execution price per unit must be greater than zero and use decimal arithmetic.

## RC-010-007 – LONG-only over-sell rule
For V1, `sell_quantity <= open_quantity_before`. A larger sale is rejected fail-closed and must not produce negative quantity, implicit SHORT state or a new short Trade.

## RC-010-008 – Partial exit
If `sell_quantity < open_quantity_before`, the sale is derived as a partial exit and the Trade remains OPEN.

## RC-010-009 – Full exit
If `sell_quantity == open_quantity_before`, the sale is derived as a full exit, resulting in zero open quantity and CLOSED lifecycle.

## RC-010-010 – Exit type is derived
PARTIAL/FULL exit classification is calculated from effective execution history and is not an independent user-entered fact.

## RC-010-011 – One Position per Trade remains
FT-010 preserves the V1 rule of one Position per Trade. A partial sale does not create a second Position and a full sale does not create a separate closed-position object.

## RC-010-012 – Position is a projection
The current Position is reproducible from effective execution history. Materialized persistence is permitted for read performance but is not the authoritative historical truth.

## RC-010-013 – Effective history query
The execution persistence boundary must support loading effective execution history for a Trade in the deterministic projection order required by the domain model.

## RC-010-014 – Average Cost Method
FT-010 V1 uses Average Cost Method. It must not mix FIFO, LIFO and average cost semantics.

## RC-010-015 – BUY projection
An effective BUY increases open quantity and remaining cost basis and recalculates weighted average entry price.

## RC-010-016 – SELL projection
An effective SELL reduces open quantity and remaining cost basis using the pre-sale average cost per unit.

## RC-010-017 – Realized gross P&L
For an effective SELL:

`realized_gross_pnl_delta = sell_quantity * (sell_price_per_unit - applicable_average_cost_per_unit)`.

## RC-010-018 – Gross, not net
FT-010 V1 P&L means realized gross P&L before fees, commissions and taxes. Ambiguous generic `profit`/`pnl` naming is prohibited at domain/API boundaries where it could imply net economics.

## RC-010-019 – Transaction costs remain non-scope
Fees, commissions, taxes and transaction costs are not stored as artificial zero-valued facts and do not affect FT-010 V1 cost basis or realized gross P&L.

## RC-010-020 – Closed Position representation
A full exit must be representable with `open_quantity = 0` and `remaining_cost_basis = 0`. Existing FT-009 positive-only persistence constraints must be evolved accordingly without losing historical entry information.

## RC-010-021 – Lifecycle derives from executions
A Trade is OPEN while effective open quantity is greater than zero and CLOSED when effective open quantity reaches zero after prior BUY history. A user-editable close flag must not override contradictory execution state.

## RC-010-022 – Correction rebuild
After an execution correction, Position and realized gross P&L are rebuilt from effective execution history. Correctness must not depend on reversing prior materialized mutations heuristically.

## RC-010-023 – Deterministic ordering
Projection ordering must be explicitly deterministic for executions. The implementation must define and test tie handling where execution timestamps are equal.

## RC-010-024 – Stop history
A user-confirmed stop change creates an immutable `STOP_CHANGED` TradeManagementEvent and never rewrites the original TradePlanVersion stop.

## RC-010-025 – Target history
A user-confirmed target change creates an immutable `TARGET_CHANGED` TradeManagementEvent and never rewrites original TradePlanVersion targets.

## RC-010-026 – Thesis history
A user-confirmed thesis change creates an immutable `THESIS_UPDATED` TradeManagementEvent and never rewrites original planning assumptions.

## RC-010-027 – Management note
A `MANAGEMENT_NOTE` is contextual user-authored management history and has no economic execution effect by itself.

## RC-010-028 – Management-event audit
Every management event has stable identity, Trade identity, event type, effective timestamp, recording timestamp and actor/audit context.

## RC-010-029 – No duplicate economic truth
A partial/full exit may be shown as an event in the UI timeline, but the actual sale remains authoritative as the SELL ExecutionRecord. FT-010 must not persist a second independent sale fact as a TradeManagementEvent solely for presentation.

## RC-010-030 – TradePlan and ProductSelection immutability
FT-010 consumes historical FT-007/FT-008 references but does not mutate TradePlanVersion, ProductSelection, ProductEvaluation or CandidateEvaluation.

## RC-010-031 – Product identity remains stable in V1
FT-010 V1 does not mutate `Trade.product_id` for a product switch and does not add a generic `PRODUCT_CHANGED` event that hides SELL/BUY economics.

## RC-010-032 – Product change non-scope
Product change requires a separate future fachliche decision because it can imply SELL old product, BUY new product and Trade-identity consequences.

## RC-010-033 – Broker boundary
ExecutionRecord remains an aggregated user-confirmed execution fact, not a broker Order or broker fill. Broker order lifecycle and synchronization remain non-scope.

## RC-010-034 – Historical capture survives provider failure
Missing live/provider/broker data must not block recording an actual sale that already occurred.

## RC-010-035 – Minimal sale input
The normal sale workflow requires only quantity sold and actual average sale price; execution time defaults to now and is changed only for backdating.

## RC-010-036 – Calculated fields are not user input
Partial/full classification, remaining quantity, remaining cost basis, average cost, realized gross P&L and lifecycle are system-derived.

## RC-010-037 – Atomic sale capture
A sale command must not leave execution history and materialized Position in inconsistent partially committed state.

## RC-010-038 – FT-011 handoff gate
FT-011 becomes eligible only after full economic exit derived from effective executions. A partial sale must not start virtual post-trade observation.

## RC-010-039 – Post-trade ownership remains downstream
FT-010 does not create PostTradeObservation, ExitReview, Journal or PerformanceRecord objects.

## RC-010-040 – No automatic trading decision
Warnings, consistency checks and calculations may support the user, but no FT-010 rule converts system analysis into an automatic sell, hold, stop or target decision.
