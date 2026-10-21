# ADR-S10-009 — Closed-trade cohort and complete gross result

## Status and authorization

Accepted for implementation on **2026-10-20**. The execution brief initially
proposed this cohort. After the concrete readiness contract in PR #270 and a
plain-language explanation of the three rules' user impact, the user instructed
**“ok, umsetzen”**. This accepts the narrow cohort, coverage and sign rules below
and authorizes implementation, synthetic qualification and a reviewable PR.
It does not accept a finished implementation, authorize a merge or release of
this new slice, or establish an installed PC version.

The independently specified goldens and detailed precedence rules are in
[closed-trade readiness](../implementation/CLOSED_TRADES_READINESS.md).
Work status remains solely in
[PB-019 trade statistics](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics).
No new feature ID is allocated. The existing
[execution currency / period SELL decision](ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
and its currency-reuse amendment remain effective.

## Context

`realized-gross-sell-v2` answers which individual SELL contributions belong to a
period. It includes partial sales of trades that remain open. Grouping its
period-filtered usable rows cannot establish the complete result of a trade
whose final exit falls in that period: earlier SELL contributions are necessary.
The existing execution owner already supplies the full effective projection,
SELL trace, immutable corrections and evidenced currency resolution.

## Decision

### Population, actual full exit and current facts

The new definition is **`closed-trade-gross-v1`**, exposed at
`GET /api/v1/performance/closed-trades` with the existing explicit inclusive
`from_date`, `to_date`, `report_currency` and IANA `report_timezone` inputs.
The distinct frontend route is `/performance/closed-trades`.

Each actual own workspace trade is considered once by stable trade ID.
Explicitly captured own EXTERNAL trades are eligible; external observations
are not actual executions. Journal, review, lesson and post-trade observation
completion are not financial prerequisites and cannot multiply the population.
Cancelled trades are excluded before qualification.

The consumer supplies the complete effective execution history to
`PositionProjector.project_with_trace()`. A valid full exit requires a concrete
SELL trace reducing a previously positive quantity to zero. Its execution ID
and source precision establish the close. A stored closed flag, cancellation,
empty field, missing position or unprojectable history cannot establish it.
The existing prohibition on BUY after full closure remains unchanged.

Only that full-exit source selects the period. Existing `periods.py` rules
apply: separately computed local-day UTC boundaries, precise timestamps or
the entire possible date-only interval. Partial overlap is ambiguous;
uninterpretable precision is unknown. A date-only sorting anchor is not an
observed execution time and must not be displayed as one.

The report uses currently effective corrected facts in one snapshot. A permitted
price, quantity, date or currency correction can change the result, period or
closure eligibility. Original executions and confirmation histories remain
sources. The report does not reconstruct knowledge at historical period end.

### Complete trade result, currency evidence and exact sign

The same execution owner is the sole average-cost calculation. After full-history
projection, all effective lifetime SELL contributions belong to the trade result,
including contributions before the selected close period. The existing operation
order, finite Decimal precision and `cost_basis_before_close_reset` remain intact.
No balancing adjustment or second arithmetic implementation is introduced.

All required BUY price sources and **every effective SELL price source** must
resolve to one evidenced currency under the existing direct / same-side
predecessor / complete prior BUY-prefix rules. The last SELL's currency is
insufficient to qualify the whole trade or safely exclude it as another currency.
Earlier conflicting SELL proceeds remain relevant even when a later individual
SELL remains usable in the existing period report. No FX, default currency,
extra required confirmation or derived `USER_CONFIRMED` row is introduced.

Only a complete qualified trade result gets a positive, negative or neutral
classification. The exact unrounded owner value controls the sign; neutral means
exactly zero. `+0.004` is positive and `-0.004` negative even when the display
rounds both to `0.00`. Raw values and an explanation remain accessible.

Backend values are finite Decimal strings. Display follows the evidenced currency
reference's minor unit, reference version and `ROUND_HALF_EVEN`. Raw complete
trade results are summed before display rounding; any difference from rounded
row sums is explicit. The frontend performs no money or classification arithmetic.

### Disjoint coverage and honest aggregate states

Each examined trade takes the first applicable group:

| Priority | Group / count field | Aggregate effect |
|---|---|---|
| 1 | Cancelled / `cancelled` | Excluded. |
| 2 | History or closure unreliable / `history_unresolved` | Relevant gap. |
| 3 | Validly projected open / `open` | Excluded. |
| 4 | Valid closure reliably outside the period / `outside_period` | Excluded, even if its monetary sources are incomplete. |
| 5 | Valid closure, complete price sources uniformly in another currency / `other_currency` | Excluded, including uncertain period membership. |
| 6 | Valid closure, ambiguous or unknown period and no safe currency exclusion / `period_unresolved` | Relevant gap. |
| 7 | Closure in period, complete monetary result unqualified / `monetary_unresolved` | Relevant gap. |
| 8 | Closure in period, complete result qualified in report currency / `qualified` | One complete amount and one sign class. |

`examined` equals the sum of these eight counts.
`qualified = positive + negative + neutral`;
`in_period = monetary_unresolved + qualified`;
`unresolved = history_unresolved + period_unresolved + monetary_unresolved`.
Additional explanatory reasons do not increase any population count.

The conservative historical gap is deliberate: an unreliable own history can
make an otherwise known monthly report incomplete when no reliable exclusion is
possible. A guessed historical date or final currency cannot hide it.

| Qualified trades | Relevant gaps | State | Amount |
|---|---|---|---|
| None | None | `EMPTY` | Explicit total `0`, no subtotal. |
| Present | None | `COMPLETE` | Complete total, including exact zero; no subtotal. |
| Present | Present | `PARTIAL` | No total; subtotal of complete qualified trades only. |
| None | Present | `NOT_COMPUTABLE` | Neither total nor subtotal. |

A known remainder within an unqualified trade never contributes a partial trade
amount or a sign classification. Individual lifetime SELL source details retain
their own meaning and cannot be relabelled as sales in the close month.

### Read consistency, bounds and interface behavior

Reuse the existing bounded snapshot reader and its short fresh
`REPEATABLE READ READ ONLY` transaction. All required trades, executions,
supersession references, confirmations and display references are materialized
before calculation; the transaction ends before user interaction. The limits
remain 2,000 trades, 20,000 executions, 40,000 confirmations, 100,000 provenance
links and 10 seconds per database statement. Exceeding a limit fails the whole
request; it never returns truncated financial history.

A fingerprint binds this definition, explicit filters and materialized inputs.
GET does not repair or write executions, declarations, learning evidence or
other facts and does not call providers. Local pagination and source detail use
the same response. A changed basis is visible; obsolete responses cannot replace
the active filter/request. This fingerprint is not a restorable historical report.

Navigation distinguishes **“Verkäufe im Zeitraum”** from
**“Trades mit Vollabschluss im Zeitraum”**. Each row preserves a trade ID/link,
actual closure precision, monetary qualification, exact sign and complete source
trace. Product names are labelled as current display names. Empty, incomplete,
failed and loading states are distinguishable on desktop and mobile.

## Consequences and qualification

No schema migration or new required data entry is needed. Existing commands and
`realized-gross-sell-v2` remain compatible. This is gross performance before fees,
commissions and taxes. Win rate, average, median and profit factor are outside
this first slice; original M8 requirements remain visible.

Technical qualification must include the predeclared T1 multimonth/correction
goldens, mixed currency and history gaps, exact/rounded-zero distinctions,
date-only boundaries, disjoint counts, coherent PostgreSQL correction races,
unchanged read fingerprints and real browser → owner API → PostgreSQL journeys.
Existing gates remain required. A completed development PR and synthetic proof
remain separate from human acceptance, publication and target operation.

## 2026-10-21 integration amendment: existing report → exact single-trade sources

The user authorized the separate integration follow-up. The monetary definition,
owner projection, complete currency qualification and snapshot reader do not change.
The source view reads the existing closed report with explicit original filters,
checks definition/filter/trade/product identity, and renders the selected item and
its monetary sources from that single response. Optional plan/review/journal/lesson
reads remain separate and labelled; they do not confirm this financial snapshot.

Navigation carries only a validated flat allowlist and an optional whole-report
fingerprint. That fingerprint may change because of another trade or reference
metadata: it is not a per-trade change assertion, a signed URL or an old report
store. Return reads anew, preserving the supported row filter and local page;
an unavailable original page is announced. No generic `returnTo`, URL money,
additional financial arithmetic, persistence or new methodology is accepted.
See the [integration qualification map](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md).
