# Sprint 9 – Technical Closeout

## Scope

Sprint 9 implemented FT-009 Trade & Position / Purchase Execution Capture.

FT-009 records warrant purchases that actually occurred and derives the open position from the recorded purchase-execution history. The implementation does not recommend a purchase quantity and does not place orders.

## Delivered capabilities

The implementation provides:

- explicit separation of `Trade`, `ExecutionRecord` and `Position`;
- workspace-guided trades based on an existing historic FT-008 `ProductSelection`;
- externally initiated trades based on an existing FT-004 warrant;
- minimal execution capture using quantity and price per unit;
- initial purchases;
- additional purchases for an existing trade;
- immutable purchase execution records;
- deterministic position aggregation;
- weighted average entry price;
- preservation of historic TradePlan, ProductSelection and ProductEvaluation provenance;
- database constraints for core domain invariants;
- SQLAlchemy repositories and Unit of Work;
- consumer adapters for FT-008 ProductSelection and FT-004 Warrant;
- REST endpoints for initial and additional purchase capture.

## Explicit V1 boundaries

Sprint 9 does not implement:

- broker order placement;
- automatic position-size decisions;
- sell executions;
- partial exits;
- stop management;
- commissions, fees or taxes;
- broker-order lifecycle;
- trade-management events;
- FT-010 functionality.

These remain outside FT-009 V1.

## Persistence

Alembic revision:

`20260817_0014`

The migration introduces:

- `trades`;
- `execution_records`;
- `positions`.

The persistence model preserves the domain distinction between trade identity, immutable executions and the derived open-position snapshot.

A position is unique per trade in FT-009 V1.

## REST API

The following command endpoints are delivered:

- `POST /api/v1/trade-position/purchases/from-selection`
- `POST /api/v1/trade-position/purchases/external`
- `POST /api/v1/trade-position/trades/{trade_id}/purchases`

The API keeps user input intentionally small.

For an existing workspace selection, the user supplies the actual purchase quantity and purchase price. Historic product-selection and trade-plan provenance is resolved by the system.

For an external purchase, the user supplies the existing product identity, quantity and purchase price.

`executed_at` is optional at the API boundary.

## Validation evidence

Local FT-009 test suite:

`64 passed`

Backend quality validation covered:

- Ruff;
- Black;
- mypy;
- pytest.

Pull request CI completed successfully with:

- Backend quality;
- End-to-End smoke;
- Frontend quality.

All three required PR checks passed.

## Delivery evidence

Implementation pull request:

`#18`

Merge commit:

`1f98a4a2f4568dbe3e1352c0ae5e5e0c93034c2a`

Implementation commits included:

- `f8e276e` – FT-009 domain core;
- `b188d4c` – execution and position invariants;
- `4586b4f` – purchase application service;
- `34efef1` – persistence and Unit of Work;
- `042d0de` – ProductSelection and Warrant consumer integration;
- `c0cbcb9` – REST API;
- `9fd7992` – backend quality-gate conformance.

## Closeout decision

FT-009 implementation is technically complete for its defined V1 scope.

Sprint 9 may proceed to release-readiness closeout.
