# ADR-S10-008 — Execution currency evidence and period realized gross results

## Status

Accepted for implementation on 2026-10-17. After delivery of the source inventory,
the concrete currency/period proposal and an explanation of the user impact, the
user explicitly instructed: **“Ok, umsetzen”**. This accepts the proposed narrow
contract and authorizes its implementation. It is not acceptance of a finished
implementation, a release, a production migration or an observed installation.

The detailed contract and pre-defined acceptance cases are in
[period realized gross readiness](../implementation/PERIOD_REALIZED_GROSS_READINESS.md).
Work status remains in [PB-017](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl)
and [PB-019](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations).
This ADR does not allocate a new feature ID.

## Context

The FT-010 owner already projects effective BUY/SELL history using average cost.
Its additive `project_with_trace()` exposes exact individual SELL deltas through
the same calculation loop. Historical execution records contain price numbers,
but the existing capture contract does not establish their actual currency.
Selected evaluation listings, current product listings and quote-source choices
are different facts. They cannot retrospectively confirm an execution price.

A current cumulative position result does not identify period contributions.
Financial qualification must also remain independent of journal, review, lesson
and materialization completion.

## Decision

### One execution owner and explicit currency evidence

The existing trade-position owner stores an additive immutable currency
confirmation for a concrete execution ID. It contains the price currency, explicit
user confirmation, audit actor/time, optional note, request identity and optional
predecessor confirmation. Audit actor fields are not authentication evidence.
Changing this declaration appends a successor; economic execution fields and
their ordering timestamps are not changed. An economic correction creates a new
execution and requires its own explicit declaration.

All existing actual capture commands, including Learning `execute-as-trade`, can
receive the declaration and persist it atomically with their execution. Omission
remains compatible and means unknown currency. Existing executions receive no
backfill. A separate user command can confirm a historical execution. One effective
confirmation, workspace/identity boundaries, idempotency and concurrent successors
are enforced by the owner and qualified on PostgreSQL. No report GET writes facts.

### Narrow financial definition

Definition `realized-gross-sell-v1` includes effective SELLs of the workspace's
own non-cancelled trades, including partial sales of open trades and explicitly
captured own EXTERNAL trades. Pure external observations are not executions.
Each contribution uses the owner formula and operation order:
`quantity * (sale_price - average_cost_immediately_before_sale)`.
Complete effective histories are projected before period selection.

The current sale price and all BUY price components of its cost basis need the
same evidenced currency. Earlier SELL proceeds do not enter remaining purchase
costs, although their quantities and exact executions remain cost-basis sources.
No FX conversion is inferred. A report currency filters output; it confirms no
source currency. Known other sale currencies are excluded; unknown potentially
relevant currencies remain visible as gaps.

### Calendar boundaries and knowledge

The request explicitly gives inclusive `from_date`/`to_date`, an IANA report zone
and one report currency. Calendar boundaries are converted separately into the
half-open UTC interval from local first-day start to the next local day after the
last day. Aware execution instants use that interval. Date-only executions retain
their stored date and zone: their entire possible local-day interval must lie in
the report to count. Disjoint intervals are outside, partial overlaps ambiguous,
and uninterpretable source boundaries unknown. Invalid query boundaries are
rejected. Internal sorting anchors are never displayed as execution instants.

The report uses currently effective corrected facts. It does not reconstruct what
was known at period end. Later economic or currency corrections can change a new
request for the same period without rewriting earlier learning evidence.

### Exact values, coverage and reproducible provenance

The backend returns finite Decimal strings and qualified display strings; the
frontend does no money arithmetic. Display uses the currency reference's minor
unit and `ROUND_HALF_EVEN`, retaining its reference version. Raw SELL contributions
are summed before display rounding; a difference from rounded rows is explicit.

`EMPTY`, `COMPLETE`, `PARTIAL` and `NOT_COMPUTABLE` are distinct. A partial report
has a qualified subtotal and no calculable total; unknown is never zero. The
response includes every considered SELL, exclusions, relevant gaps, complete
execution provenance and exact confirmation IDs. Today's product name is marked
as present-day display, not historical economic identity.

### Bounded read consistency

A fresh, short `REPEATABLE READ READ ONLY` transaction is established before the
first business query. It materializes all required execution, cancellation,
supersession, currency-evidence and display-reference facts; calculation then
uses those inputs without further database reads. Global application isolation
and command behavior remain unchanged. No `FOR UPDATE`, market calls, learning
refreshes or interaction-length transaction is introduced.

One response contains the full considered result and provenance. Pagination and
drill-down use that response locally. A hash binds normalized filters, definition
and materialized inputs. A later request may replace the entire basis and must
show the change; stale frontend responses cannot overwrite the active request.
The hash is not a persistently restorable historical report session.

## Consequences and qualification

One additive migration introduces evidence at the existing owner, with no currency
backfill. Downgrading after declarations exist would destroy evidence and is not
a lossless rollback. Existing actual values and capture requests remain compatible.
The report is gross before fees, commissions and taxes, without full portfolio
performance, autonomous decisions or model activation.

Before technical delivery, qualify the independent September/correction goldens,
Decimal edge cases, date/zone boundaries, unknown and mixed sources, append-only
commands, all capture handoffs, real PostgreSQL correction races, unchanged read
state and an actual browser → owner API → PostgreSQL flow. Existing quality gates
remain unchanged. Missing tooling and unexecuted gates must be stated explicitly.

PR #249 remains a separate prioritised integrity fix before operational expansion;
it does not prevent implementation or isolated qualification of this slice. No
part of this decision completes original M8, accepts target operation or permits
publication, merge, tagging or deployment.

## 2026-10-20 amendment: reuse the entered purchase currency

The user explicitly instructed that the currency entered with the purchase also
applies to the sale and must not require repeated entry. Existing inputs should
be reused with the minimum necessary input. This supersedes the separate SELL
declaration and repeated same-side replacement declaration requirements above.
The precise contract, source inventory and acceptance cases are recorded in
[purchase currency reuse](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md).

One pure resolver at the execution owner gives priority to a direct current
confirmation, then a confirmed same-side execution predecessor, then the complete
preceding effective BUY prefix when all its resolved currencies are known and
equal. The last rule applies to sales and additional purchases. Later BUYs never
retroactively qualify an earlier unknown BUY. Explicit conflicting declarations
are preserved; mixed costs/proceeds are not converted. Reuse is reported with
the exact source execution and confirmation IDs, without manufacturing or
persisting a new `USER_CONFIRMED` declaration on the derived execution.

Definition `realized-gross-sell-v2` retains arithmetic, periods and snapshot
boundaries, and makes this changed qualification rule explicit. The actual
capture action confirms a typed currency code; a second checkbox is unnecessary.
A nonempty invalid code is rejected instead of silently omitted. Existing
immutable confirmations and their correction command remain authoritative.
No migration, default EUR backfill, current-listing inference or report GET
write is introduced. The user's separate authorization to merge after green
checks and make the release available for the PC continues to apply.
