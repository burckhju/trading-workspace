# S6-09 Implementation Report — FT-007 REST API

## Scope

Expose the approved FT-007 TradePlan command/read model through the existing FastAPI boundary. No frontend changes.

## Implemented

- Added `/api/v1/trade-plans` router and registered it in the application bootstrap.
- Added Pydantic request/response DTOs for product-neutral TradePlan content:
  - thesis;
  - Entry (`PRICE`, `PRICE_RANGE`, `TRIGGER`);
  - Stop/Invalidation;
  - ordered targets;
  - user-authored risk assumptions.
- Added create command for both approved origins:
  - manual origin requires `underlying_id`;
  - Candidate origin requires exact `candidate_id` + immutable `candidate_evaluation_id` and deliberately rejects an API-supplied `underlying_id` override.
- Added read endpoints for TradePlan latest state, version history and exact version detail.
- Added amendment endpoint against an exact approved base-version ID.
- Added explicit lifecycle command endpoints:
  - submit for review;
  - return to draft;
  - abandon;
  - approve.
- Added request-scoped service/query dependencies using the existing database-session dependency pattern.
- Added stable translation of FT-007 `ValueError` failures into the central `ApplicationError` REST envelope (`404`, `409`, `422`).
- Propagates `X-Actor-ID` and `X-Correlation-ID` into all mutating application-service commands.
- API responses expose version-specific CandidateEvaluation provenance, lifecycle events and approval proof through the S6-06 read side.

## Invariants preserved

- Candidate-originated TradePlans resolve their underlying from the exact persisted CandidateEvaluation handoff; callers cannot override it through REST.
- No endpoint resolves a "latest" CandidateEvaluation.
- Approval is an explicit command against one concrete immutable TradePlanVersion.
- Amendments are created against an exact approved base version.
- FT-007 remains LONG-only and product-neutral.
- No Warrant, Issuer, Product Selection, Position Sizing, Order Quantity or Execution fields/endpoints were introduced.

## REST surface

- `POST /api/v1/trade-plans`
- `GET /api/v1/trade-plans/{trade_plan_id}`
- `GET /api/v1/trade-plans/{trade_plan_id}/versions`
- `GET /api/v1/trade-plans/{trade_plan_id}/versions/{version_id}`
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{base_version_id}/amendments`
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version_id}/submit-review`
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version_id}/return-draft`
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version_id}/abandon`
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version_id}/approve`

## Tests

- New FT-007 REST API tests: 8 passed.
- Full FT-007 unit suite: 43 passed.
- Full backend unit regression suite: 274 passed.
- `compileall`: passed.
- Ruff 0.15.1 remains pinned in `backend/pyproject.toml` but was not executable in the supplied runtime, so no Ruff pass is claimed for this unit.

## Next unit

S6-10 — Frontend API / Types: add typed FT-007 client contracts and API calls, without yet implementing the full TradePlan UI workflow.
