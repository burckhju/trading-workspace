# Sprint 9 – FT-009 Release Readiness

## Feature

FT-009 – Trade & Position / Purchase Execution Capture

## Readiness assessment

**READY**

FT-009 has been implemented, merged to `main`, and validated by the repository quality and CI gates.

## Functional readiness

Confirmed:

- initial purchase from historic ProductSelection;
- external purchase for an existing warrant;
- additional purchase for an existing trade;
- immutable ExecutionRecord history;
- derived open Position;
- weighted average entry price;
- minimal user input;
- historic workspace-selection provenance;
- workspace isolation at resolver and repository boundaries;
- REST command API.

## Architecture readiness

Confirmed:

- `Trade != ExecutionRecord != Position`;
- FT-009 is isolated in its own feature module;
- released FT-004, FT-007 and FT-008 contracts are consumed rather than rewritten;
- persistence mirrors the domain boundaries;
- Unit of Work owns the FT-009 transaction boundary;
- ProductSelection resolution is read-only;
- no shadow product identity is introduced.

## Database readiness

Migration head introduced by FT-009:

`20260817_0014`

Core DB constraints cover:

- valid trade-origin provenance;
- positive execution quantity;
- positive execution price;
- execution recording time not before execution time;
- positive position aggregates;
- valid position execution chronology;
- one position per trade.

## API readiness

Delivered endpoints:

- `POST /api/v1/trade-position/purchases/from-selection`
- `POST /api/v1/trade-position/purchases/external`
- `POST /api/v1/trade-position/trades/{trade_id}/purchases`

Invalid quantity and price values are rejected at the API boundary.

Unknown upstream references are translated into explicit not-found responses.

## Verification

Local FT-009 suite:

`64 passed`

Pull request #18:

- Backend / quality: passed
- End-to-End / smoke: passed
- Frontend / quality: passed

Merge commit:

`1f98a4a2f4568dbe3e1352c0ae5e5e0c93034c2a`

## Remaining scope

The following capabilities are intentionally deferred:

- sales and partial exits;
- stop and trade management;
- product changes during an open trade;
- broker integration and order lifecycle;
- fees, commissions and taxes;
- post-trade review.

These belong to subsequent feature scope, especially FT-010 and later features.

## Decision

FT-009 satisfies the Sprint 9 implementation and technical release-readiness criteria for the specified V1 scope.
