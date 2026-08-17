# Sprint 9 – FT-009 Rule Catalog

## Status
Specified after S9-00 through S9-07 review. Production implementation remains gated by explicit user approval.

## Scope
FT-009 captures actual warrant purchases and derives the initial/open position. It supports initial purchases, additional purchases, workspace-guided origin and external origin.

## RC-009-001 – Actual fact, not recommendation
FT-009 records a quantity and purchase price the user confirms actually occurred. It does not recommend or decide quantity.

## RC-009-002 – Minimal input
Known context is reused, current calculations are derived, and the user is asked only for facts that cannot be reliably obtained from existing context. Workspace purchase input is normally quantity plus actual average price.

## RC-009-003 – Stable Trade identity
A Trade is a stable identity for the real trading case. It is not the same object as the Position or any execution fact.

## RC-009-004 – Immutable execution history
Every confirmed purchase creates an immutable ExecutionRecord. Additional purchases never edit earlier purchases.

## RC-009-005 – One Position per Trade in V1
A V1 Trade owns exactly one Position. Multiple purchase executions may contribute to that Position.

## RC-009-006 – Additional purchase
An additional purchase for an open Trade creates a new PURCHASE ExecutionRecord and recalculates the same Position.

## RC-009-007 – Quantity
Quantity must be integral and greater than zero for warrant purchases in V1.

## RC-009-008 – Price
Actual average purchase price per unit must be greater than zero and represented with decimal arithmetic.

## RC-009-009 – Gross amount
Gross amount is calculated as `quantity * price_per_unit` and is never an independent user input.

## RC-009-010 – Position aggregation
For effective PURCHASE ExecutionRecords:

- `open_quantity = sum(quantity)`
- `total_cost = sum(quantity * price_per_unit)`
- `average_entry_price = total_cost / open_quantity`

Historical unit prices remain unchanged.

## RC-009-011 – Workspace origin
A workspace-origin Trade references the exact historical ProductSelection. ProductSelection and ProductEvaluation remain immutable FT-008 facts.

## RC-009-012 – External origin
An external Trade may exist without TradePlanVersion or ProductSelection. Product identity must still resolve through the existing product/reference boundary.

## RC-009-013 – No shadow product
FT-009 must not create free-text or execution-local product identities that bypass FT-004 reference ownership.

## RC-009-014 – Different purchased product
If the user bought a product different from the existing ProductSelection, the system must not silently treat it as the selected product. It must use an explicit deviation/external-origin path.

## RC-009-015 – Execution and recording time
`executed_at` and `recorded_at` are stored separately. Backdated execution is valid; implausible future execution is invalid.

## RC-009-016 – Duplicate warning
Potential duplicate detection is advisory. Similar facts are not a hard uniqueness key because genuine repeated purchases are valid.

## RC-009-017 – Correction
A confirmed ExecutionRecord is never patched in place for a factual correction. Corrections preserve the original record and establish which execution is effective.

## RC-009-018 – Position reconstruction
The current Position must be reproducible from effective execution history. A superseded execution does not contribute to the current derived position.

## RC-009-019 – Pre-execution is optional support
A PreExecutionCheck may exist before purchase but is not a prerequisite for recording an actual historical purchase.

## RC-009-020 – Provider failure
Missing live provider capability must not block capture of an execution that already occurred.

## RC-009-021 – Transaction costs
Fees, commissions, taxes and other transaction costs are explicit V1 non-scope and do not contribute to FT-009 V1 cost basis.

## RC-009-022 – Order boundary
FT-009 V1 does not model broker orders, order states or individual broker fills. An ExecutionRecord is not an Order.

## RC-009-023 – Sale boundary
Sales, partial sales, closing, realized P&L and post-open trade management are outside Sprint 9 V1.

## RC-009-024 – Atomic initial capture
Initial purchase persistence must not leave a partially created Trade/Execution/Position set when the use case fails.

## RC-009-025 – Explicit confirmation
System-calculated context does not itself create an execution. The user explicitly confirms the actual purchase facts.
