# Trade capture, cancellation and execution dates

## Scope

There may be **at most one non-cancelled open trade per workspace and warrant identity**
(`product_id`, not the underlying ticker, venue symbol or listing). While it is open,
a new initial purchase from a selection, external capture or the existing learning
handoff fails with `409 OPEN_TRADE_EXISTS`. The purchase form links to the existing
trade; further real purchases are explicitly recorded in **Nachkauf erfassen** there.
No request is automatically converted into a subsequent purchase. After a full sale
or cancellation, a deliberately new capture may open a new trade.

The initial guard takes `FOR NO KEY UPDATE` on the workspace's warrant row.
This lock serializes creators but is compatible with foreign-key `KEY SHARE` locks
already acquired by concurrent raw trade inserts; `FOR UPDATE` would deadlock on
those lock upgrades. A database trigger also protects
new/reopened positions and serializes concurrent writes under the application's
PostgreSQL default READ COMMITTED isolation. Trade mutations lock their parent trade,
so sale, correction, additional purchase and cancellation cannot overwrite one another.
Migration `20260912_0036` does not repair existing duplicates automatically and does not
contain user IDs or change any existing economic record. Legacy open duplicates remain
visible until an operator explicitly cancels the incorrect entry. A partial unique
index could not safely be installed over those existing duplicates; the trigger guards
new/reopened positions without destroying the old facts.

## Retry protection

The four purchase/sale endpoints accept an optional `request_id` UUID. The first-party
forms reuse the ID for an unchanged submission after a lost response (session storage
per tab, in-memory fallback) and disable simultaneous submissions. The server stores a
workspace-scoped key and semantic payload fingerprint with the execution, takes a
transaction-scoped advisory lock, and returns the same execution/trade identity on a
retry. The returned position reflects its current projection, not an old cached balance.
Different data under a reused key fail with `409 CAPTURE_KEY_CONFLICT`. Cancelled
captures cannot be resurrected through replay. Successful UI captures clear the pending
key; an explicitly submitted real subsequent purchase can then use a new key.

Older API clients without a key remain compatible, but do not acquire retry protection
for additional purchases or sales. They must send `request_id` plus an explicit execution
date/time to obtain it. The one-open-trade rule applies regardless. Separate tabs with
new keys are distinct commands: additional purchases must not be deduplicated solely
by equal amount/price, since two genuine executions can be identical. No broker order
is sent by these recording endpoints.

## Execution date is not recording date

Purchase, additional purchase and sale forms have a required editable calendar date,
initially today in the browser's timezone, and an optional known time. Future executions
are rejected. The server always generates the real `recorded_at`; it is never changed
to match an economic date.

- Known time: send an aware `executed_at` timestamp.
- Unknown time: send `executed_on` plus an IANA `execution_timezone`. The calendar date
  and timezone are retained. An internal UTC midnight anchor supports the existing
  projection contract; it is **not evidence of a midnight execution**. Timeline and
  trade views show the date and disclose the unknown time. Position opening/closing
  date precision is retained as `opened_on` / `closed_on`.
- Do not supply both representations or a timezone without a date. Naive timestamps
  are rejected. Keyed captures require explicit time data for stable retries.
- Existing records are not relabelled or backdated automatically. The existing
  execution-correction endpoint accepts either representation and adds an immutable
  superseding record; the old recording and execution date remain in the timeline.

Date-only events use their internal day anchors and recording order for deterministic
same-day ordering. Mixed precise/date-only histories can be ambiguous; projection
rejects sequences that would sell before a purchase, oversell, or reopen a closed
trade. Do not invent a time to resolve an ambiguous execution sequence. Minor units,
FX, broker settlement date and automatic historical date inference are outside scope.

## Explicit cancellation, not a fabricated sale

`GET /api/v1/trade-position/trades/{id}/cancellation` returns a read-only preview with
trade/product identities, original amounts and executions, possible retained duplicate
IDs, blockers and a state fingerprint. Reading this endpoint changes no economic facts.

`POST /api/v1/trade-position/trades/{id}/cancel` requires:

```json
{
  "expected_product_id": "<verified product UUID>",
  "expected_state_token": "<exact preview token>",
  "reason": "versehentlich doppelt erfasst",
  "duplicate_of_trade_id": "<optional retained same-product open trade UUID>",
  "confirmed": true
}
```

The browser shows **Stornierung prüfen**, then requires a reason and explicit
confirmation of that exact trade. A stale preview fails closed. No other trade is
modified; the optional duplicate link is verified and locked along with the target.
Only a purchase-only open entry without dependent sales, post-trade reviews or learning
records can be cancelled. In-progress notification delivery must finish before retry.
The API does not offer an unsafe force switch or deletion.

The transaction writes cancellation metadata and one audit event, resolves open alerts
and disables pending notifications. Original BUYs, position quantities/costs, notes and
provenance are retained. Cancelled trades are excluded from depot active/closed actions,
position totals, valuation and monitoring subjects. Historical position reads still
contain the original numerical facts and explicitly return `is_cancelled=true`; they
are not actual holdings. A cancellation is not a full exit and cannot start FT-011.
New economic/monitoring facts and notification delivery for a cancelled trade are
blocked; the existing timeline adds an explicit cancellation entry, not a SELL.
An exact repeated cancellation returns the existing state without another audit entry.
Failure while auditing rolls back all cancellation and derived-state changes.

This follows the application's existing trusted-local-user boundary. Actor headers
provide audit attribution, **not authentication or role-based access control**. Do not
expose the unprotected administrative API to an untrusted network. No credentials,
subscription, notification send, live user mutation or broker action is part of the
migration or regression tests.

## Deployment and verification

Back up the local database, fast-forward the checkout, and run `bash scripts/start-linux.sh`.
This existing helper builds images, applies migrations and preserves an existing
Frankfurt overlay. Verify `python -m alembic current` in the new backend container shows
`20260912_0036` (or a later revision). Do not use `alembic stamp` or remove volumes.
A downgrade refuses to remove cancellation support while cancelled trades exist;
otherwise old software would reinterpret their historical positions as holdings.
Downgrading removes new date precision and request metadata: restore a verified backup
rather than treating downgrade as lossless.

Only after deployment, inspect the intended erroneous trade and its retained counterpart
in the new preview, then explicitly cancel the erroneous ID. Verify cancellation flags,
BUY-only historical executions, absence from active positions, and unchanged retained
trade. No per-user data is modified by installing this feature.

## Validation

Backend regression cases cover real disposable PostgreSQL migrations including legacy
duplicates, same-key concurrent retries, conflicting keys, simultaneous distinct first
purchases, raw database trigger enforcement, cancellation fingerprint/product checks,
sale blockers, audit rollback, suppressed notifications, monitoring exclusion and
immutable date corrections. Frontend tests cover preview/confirmation/dismissal, failed
response retries and calendar date inputs. A real browser-to-database workflow runs only
with `TRADE_E2E_WRITES_ALLOWED=1` on the disposable CI stack. Do not enable that test on a
user database. All existing Backend, image, Frontend and End-to-End gates remain required.
