# Position risk and trend signals

Status: implemented; exact-head integration evidence in PR #244; 2026-10-04. No production activation or live acceptance.
Merged as `35a9cb7`; included in [version 1.5.0](../releases/V1.5.0-MARKET-CHARTS-AND-POSITION-RISK.md).
Version 1.5.1 adds a compact UI summary of the existing backend assessment:
trend, realized volatility, underlying/quote quality and warning activation.
Full metrics and provenance are expandable. Unavailable data masks current
signal values and retains the warning explanation. A parameter preview is
labelled as preview; its deliberately disabled backend configuration is never
misrepresented as a change to the saved activation. No rule, parameter,
evaluation, configuration command or delivery responsibility changes.
The no-release statements below describe the feature PR before this coordinated release.
User mandate: attached independent risk/trend specification dated 2026-10-04.
Baseline: `16e2feec398658c82fa8773fa29feaa1c8fbbba8` (main and v1.4.5, verified).
No AGENTS.md or additional agent instructions were found in the checkout.
Required main rules: PR, resolved review threads, up-to-date Backend / quality,
Frontend / quality and End-to-End / smoke; no bypass. Baseline workflows are green.

## Coordination and document reconciliation

Open work checked before implementation: #243 (market/sector/stock charts; initial specification
at 27ff3dd; implementation now visible at 4187d33), #205 (product history proposal), #187/#207 (different trading rules),
#225/#235 (scheduler), #220/#204/#197/#90. None is silently treated as delivered.
This work adds no chart platform, changes no scheduler lanes and duplicates no baseline
trading rules. main and open PRs must be checked again before structural integration/merge.

The approved ownership/identity ADRs S3-001/003/005, S4-001/002, S5-002,
S7-003/004/005/006 and FT019-001 apply. Historical non-scope statements do not
supersede the implementation: D01 permits reference-owned MDI, 0038 already retains
last successful warrant quotes, later FT019/020 code supports explicit runtime activation.
The early monitoring document's unconditional underlying axis is superseded by confirmed
PriceBinding. FT013 approval alone is not activation. Existing numerical V1 policies stay
immutable. No new FT number or claim of product-owner approval is introduced.

## Inventory (verified in source at baseline)

| Metric / signal | Owner and formula/version | History / quality | API and UI use | Actual alert effect |
| --- | --- | --- | --- | --- |
| SMA20/50/200, momentum20/60/120 | analysis `calculator.py`, EOD_TREND_MOMENTUM 1.0.0; arithmetic mean / simple return | immutable FT006 snapshots; default 200 rows; CLOSE or ADJUSTED_CLOSE | market-analysis runs; indirectly phase/scores | none |
| Realized volatility | same calculator; sample SD of 20 log returns × sqrt(252), 6 decimals | default baseline blocked with <200 rows despite 21 sufficient for RV20 | run metrics; no explicit position volatility explanation | none |
| ATR14 / RSI14 | analysis `position_analytics.py`, POSITION_ANALYTICS_V1; arithmetic TR mean / arithmetic gains-losses (not Wilder); flat RSI=50 | ATR uses raw OHLC/previous close; RSI selected closes; baseline completeness gate | used by phase/scores/indicative stop | none |
| Range / highest high20 | analysis; raw high-low, selected latest price | adjusted-close/raw-range mixture possible; preserve V1 and flag in new interpretation | stored metrics | none |
| HighestHighSinceEntry | position_monitoring `position_analytics.py` | first effective BUY; excludes entry and evaluation dates; latest terminal FT006 snapshot | analytics endpoint; phase/stop | none |
| Phase | POSITION_PHASE_V1 | >=3/10 post-entry sessions; SMA structure, RSI50/70, <=1ATR from peak; all inputs required | phase endpoint, trade management | ephemeral projection, no transition history |
| TrendScore / PeakScore | POSITION_SCORE_V1; 5×20 / 4×25 correlated components | all inputs incl. SMA200 required | scores endpoint / indicative stop | no alert; no calibrated probability |
| Dynamic stop | DYNAMIC_STOP_V1; peak minus 1..3 ATR by phase/scores | same run provenance, ATR>0; fail closed | dynamic-stop and alert-projection; position attention | display only; never changes confirmed stop |
| Stop / target | monitoring rule_prices/cycle/processor and FT010 price binding | exact instrument/currency; completed underlying low/high or qualified product indication | health + persisted alerts + delivery status | persistent edge state -> Alert -> Notification -> durable retry adapter |
| Bid/ask, spread, retention | market_data + ProductPositionValuation | last successful snapshot per listing/provider, original quote and receipt times, no series | product valuation / position details | existing confirmed price rules only |
| Relative strength | analysis top_down, RELATIVE_STRENGTH 1.0.0; aligned 60-session return difference, ±2pp | 61 common dates; historical reference identities | Candidate required criteria | no position warning |

## Data qualification matrix

| Metric/rule | Required data | Existing contract / time / quality | Implementation |
| --- | --- | --- | --- |
| Short trend and RV20 | 21+ completed adjusted closes, exact listing/MDI/currency/provider, source receipts | DailyPrice, persisted date not intraday close timestamp | independent versioned partial assessment; no weakening of FT006 V1 |
| ATR14/close | 15 raw OHLC/close observations on consistent scale | DailyPrice; adjustment-factor changes can indicate corporate action | reuse TR kernel; suppress raw ATR across scale changes |
| Quality | positive bid, ask>=bid, sizes, age, retention, source identity | WarrantQuoteSnapshot; sizes optional; unknown issuer date/timezone stays null | separate quality findings; mid denominator spread explicitly `(ask-bid)/mid*100` |
| Stock/warrant return comparison | >=2 distinct matching original instants for same stock/listing, warrant/listing/provider/currency and unchanged terms | stock EOD has trading date only; product retention is ONE snapshot; no matching-time series | qualified comparison contract; missing history and stock close-time evidence explicit; never use receipt as source time |
| Product direction/terms | Call/Put, ratio, strike, maturity, terms version | FT004 effective terms; ratio=underlying units/warrant; strike currency optional | Call/Put trend interpretation; expose facts/missing facts |
| Model-based price expectation | synchronized IV/Greeks with units, exercise style, dividends/rates, FX/quanto/conditions | absent from current quote and terms contracts | not evaluable, no volatility substitution or fixed-leverage expectation |
| Concentration/events | complete portfolio exposure, FX and event calendar | not established by this task | later slice; no synthetic event dates |

A last success or repeated retrieval is not product price history. Minimal future
Market Data extension: append distinct verified observations keyed by instrument,
listing, provider, original timestamp and payload fingerprint; preserve receipt and
quality, mark corrections append-only, no backfill. Unknown-time observations cannot
support synchronous return rules. Storage rights and verified stock session close
instants must be evidenced before source-specific automatic history is activated.
The risk feature must not create an independent quote collector.

## Prioritized scope and acceptance

| Priority | Evidence / benefit | Data and risk | Scope / acceptance |
| --- | --- | --- | --- |
| 1 | existing RV20 hidden behind 200-row baseline; give interpretable position risk | 21 adjusted closes; shorter estimate less stable | extract unchanged reusable kernels, independent versioned risk analytics, API + detail UI; old V1 results identical |
| 1 | phase is a snapshot, not a proven trend break | distinct completed dates, currency/identity continuity | SMA20 hysteresis and confirmation; first snapshot no break; Call/Put directions; gap/stale data never clear prior state; immutable evaluated snapshots |
| 1 | no valid historical product comparison | exact time, price kind and terms needed | qualification + descriptive paired-return evaluator; UI names missing inputs and never substitutes underlying/receipt dates |
| 2 | indicators mix adjustment axes and duplicate reads | raw ATR distinct from adjusted trend/RV | quality checks and one bounded persisted-data read per run; no provider access in risk GET/evaluation |
| 2 | new triggers must not silently affect old positions | explicit parameters + actor/version and confirmation | preview default; explicit per-position configuration/activation, preserve existing alert/outbox responsibilities |
| 3 | relative strength already owned by FT006; chart PR concurrently active | historical reference mapping and common currency | reuse later, no extra MACD/ADX or total score in first slice |
| 3 | maturity/moneyness/concentration/events may help | terms and FX/quanto/event contracts incomplete | expose available terms, document limitations; no speculative IV/Greeks model |

## First vertical slice contract

`POSITION_RISK_V1` is independent of the old V1 projections. Default proposal:
SMA20, ±0.5% hysteresis, two distinct completed observed sessions to confirm a change,
RV20 annualization 252, illustrative high-volatility threshold 40% with reset at 35%.
These are reviewable proposals, not empirically validated safe limits. Parameters and
activation belong to immutable position monitoring configuration versions; off by default.
No initial adverse snapshot is a demonstrated break. Repeated same-session observations
never add confirmation. Revisions of the same date are separately fingerprinted and do
not generate a fresh crossing. Unknown quality freezes the last confirmed state and
breaks pending confirmation. Fresh dates after a gap must establish new confirmation.

Analysis owns numerical kernels; Monitoring owns signal semantics, immutable results,
configuration and alert edges. Public owner readers supply identity, terms and prices.
GET is read-only, explicit evaluation persists a preview; scheduled runs reuse the same
service. New informational/warning triggers require explicit activation. Data-quality
findings never generate a sale/price alert. Existing alert state, notification uniqueness
and outbox/restart delivery are reused. No stop, quantity, order or confirmed plan mutation.

Testing: arithmetic fixtures + V1 parity; trend deterioration/recovery/flat oscillation,
Call/Put, first snapshot, same-date repeats, stale/gap/invalid/constant/short series,
adjustment jumps, unknown quote time, one-sided quote and zero volume, FX/asynchrony,
identity mismatch; persisted preview/config/version/restart/concurrency; API/UI and
mandatory repository gates. Synthetic examples show mechanics, not loss reduction.

## Methodology sources (checked 2026-10-04)

- https://www.optionseducation.org/advancedconcepts/volatility-the-greeks
- https://www.optionseducation.org/advancedconcepts/understanding-options-greeks

OIC distinguishes realized and implied volatility and describes Greeks as local model
sensitivities, not exact price predictions. Its material covers OCC exchange-traded
options, not contractual German issuer warrants. This implementation therefore derives
no warrant theoretical fair value or execution return from stock movement. Concrete
product exercise/quanto/adjustment conditions are not in the current typed contract;
no unverified product condition is inferred from a name or from OIC examples.

## Handoff

Current stage: implementation, controlled domain/SQL/API tests and diff review complete. Final exact-head CI and merge evidence: PR #244.
No deployment, data-provider activation, real notification, release-number reservation,
production threshold activation, historical validation or loss-reduction claim.

## Implemented interfaces and upgrade contract

The position risk API is under `/api/v1/position-monitoring/trades/{trade_id}/risk`:

| Method/path suffix | Effect |
| --- | --- |
| GET `/risk` | live preview from persisted owner inputs, no provider request or write |
| POST `/risk/preview` | supplied `parameters`, unactivated parameter preview, no write |
| POST `/risk/evaluations` | persist an immutable snapshot; active configuration may create an Alert, never direct delivery |
| GET `/risk/history` | latest 20 immutable evaluations with input rows, fingerprint, previous snapshot and parameters |
| PUT `/risk/configuration` | `parameters`, `enabled`, `expected_revision`, exact `confirmation=CONFIRM_POSITION_RISK_CONFIGURATION`; explicit actor/correlation headers as for existing local commands; stale revision returns 409 |

The new owner readers are `OpenPositionReader`, `RiskProductReader`, `RiskListingReader`
and `RiskMarketDataReader`. They expose typed read contracts without cross-feature
persistence imports in the Monitoring consumer. Analysis owns `RiskMetrics` and
`SynchronizedPricePair`/`ProductComparison`; the latter is a future Market Data reader's
input contract. The current persisted reader deliberately supplies no fictitious pairs.
The UI renders backend comparison results as a normalized table, leaving chart ownership
with #243. GET is available in expanded position details, configuration in Trade Management.

An enabled existing monitoring scheduler also evaluates risk from a bounded 61-row
persisted daily history per position, serially, without additional provider traffic.
It records preview state while disabled. A position-row lock serializes evaluations
and configuration changes. Identical daily values reuse a snapshot even when re-received; the last-success quote
is display context and does not make a new daily signal observation. GET shows current
quote context; stored evaluations preserve the context at their original evaluation.
This risk history is explicitly not an independent product quote collector. Verified
synchronous pairs, if supplied by a future owner reader, are fingerprinted and stored
in full; original saved-quote evidence is preserved on each actual signal snapshot. Parameter/terms/source
changes start a new baseline; old open risk alerts are invalidated (not resolved as an
improvement). No risk alerts or notification records are created while disabled.
Active alerts are replayed into the existing idempotent notification creator, recovering
an interruption between alert commit and outbox creation. Delivery remains with the
existing durable notification service and its configured Telegram adapter.

Migration `20261004_0044` is additive after `20261004_0043`: no data conversion, activation
or defaults written to existing positions. The two new tables preserve configuration
versions and evaluation inputs. Downgrade refuses when either contains history. Preserve
that history and follow the established backup/upgrade procedure before deployment;
do not force a downgrade or stamp. No VERSION change or tag is reserved in this feature PR.

Explicit remaining input limits: no verified exchange calendar (missing weekdays,
including possible holidays, fail closed); no provider-independent stock close instant;
no product price history; no observed latest refresh outcome in the last-success cache;
no exercise/quanto or synchronized IV/Greek contract. Market Data needs the minimal
append-only history extension above before a real synchronous product comparison can run.
The kernel and its API view can evaluate suitable controlled owner inputs today; production
EOD and one saved issuer quote cannot supply them. Sudden quote changes cannot be tested
from a single saved success. No historical calibration or holdout performance is claimed.


### Concurrent schema coordination

PR #243 merged as `f580bfe9295d32336c1456f91cdf1476cacfd580` during final CI.
This main revision is integrated here. Our distinct `20261004_0044` migration now
follows its `20261004_0043`; Alembic has exactly one head. PositionDetails preserves
both the chart link and risk panel. The merged Market Data `TimeSeriesReader`
provides EOD chart data, not verified original stock/warrant time pairs; the explicit
risk qualification and missing product-history boundaries therefore still apply.
The original pinned baseline remains recorded above. All mandatory gates are rerun
on the combined code before merge; no unmerged dependency is assumed.

## Validation and operator handoff

Checkpoint `bbb96f66db8f9e0e8226ae6e7c127d95fb91971a`: GitHub Backend quality
passed 2,341 tests with 85.40% coverage; Frontend quality and production build,
43 End-to-End tests, restrictive-umask image, issuer sandbox and real disposable
legacy-update qualification passed. Subsequent changes add defensive cache-payload
qualification, repeat-warning/downgrade tests, and the distinct 0044 migration name.
Final exact-head checks and merge evidence are recorded in PR #244; the thresholds
and required gates are unchanged. Local configured Backend unit run passed 2,202
checks; the full local script could not qualify PostgreSQL in this execution environment.
Frontend component assertions passed locally but the local worker did not exit;
the completed GitHub frontend gate is the reliable full-run evidence.

No host was accessed. There is no new release/tag and no proven JMBbot deployment.
Risk warnings remain disabled until explicitly confirmed per position. Existing
scheduler/Telegram settings are preserved; no real message or consent was sent.
The current migrated deployment's private directory and release root are unknown.
Consequently no host update is prescribed against an assumed base-only Compose chain.
Use the reviewed installation path in [Linux deployment](../technical/LINUX_DEPLOYMENT.md)
and [legacy migration](LEGACY_ISSUER_DEPLOYMENT_MIGRATION.md), preserving actual
configuration, database/consent volumes and the Stuttgart bind before an approved update.

For an **already migrated** deployment, these existing, read-only commands run from
its qualified tool/release checkout. Enter the real existing private state directory;
this does not prepare/apply a deployment or change an activation:

```bash
read -r -p 'Existing private deployment state directory: ' TW_DEPLOY_STATE
bash scripts/migrate-legacy-issuer.sh compose "$TW_DEPLOY_STATE" ps </dev/null
bash scripts/migrate-legacy-issuer.sh compose "$TW_DEPLOY_STATE" exec -T backend \
  python -m alembic current </dev/null
bash scripts/migrate-legacy-issuer.sh compose "$TW_DEPLOY_STATE" exec -T backend \
  python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=10).status)' </dev/null
```

After a separately approved upgrade, verify one Alembic head/current revision, runtime
health and the risk detail UI of an existing controlled position. The initial configuration
must be disabled; missing product history/time evidence must remain explicit. Review the
parameter preview before any activation. Do not create fictitious trades on the real depot.
Retain the snapshot/configuration history; downgrade now deliberately refuses to erase it.
