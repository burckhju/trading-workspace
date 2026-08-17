# Sprint 10 – FT-010 Implementation Traceability

## Scope

This document closes the implementation traceability for FT-010 Trade Management against the approved feature specification, Sprint 10 rule catalog, ADR-S10-001 through ADR-S10-007, and Definition of Ready.

## Traceability chain

`Requirement / rule -> architecture decision -> implementation -> verification`

| Capability / rule group | Decision / specification | Implementation evidence | Verification evidence |
|---|---|---|---|
| BUY/SELL execution side and historical BUY migration | ADR-S10-001; RC-010-003 | `domain/enums.py`, `domain/models.py`, persistence models, Alembic `20260817_0015` | domain, persistence, repository and migration tests |
| Effective immutable execution history | ADR-S10-002/007; RC-010-004/013 | `supersedes_execution_id`, effective repository query, Alembic `20260817_0016` | repository tests and correction tests |
| Deterministic Position projection | ADR-S10-002; RC-010-012/015/016/023 | `domain/projector.py` | projector tests including deterministic ordering |
| LONG-only partial/full exit | ADR-S10-003; RC-010-007 through RC-010-010 | `TradePositionService.record_sale()` and `PositionProjector` | application, REST, integration and browser tests |
| Average Cost and realized gross P&L | ADR-S10-004; RC-010-014/017/018 | `PositionProjector`, Position fields, REST DTOs | projector/application/REST tests |
| Closed Position representation | ADR-S10-006; RC-010-020/021 | Position zero-quantity state, `closed_at`, Alembic `20260817_0017` | domain, migration, projector, REST and UI tests |
| Immutable management history | ADR-S10-005/007; RC-010-024 through RC-010-029 | `TradeManagementEvent`, persistence/repository/UoW, Alembic `20260817_0018` | management-event, application and migration tests |
| Current management state | ADR-S10-005 | `domain/management.py`, effective management-event query | management state tests |
| Execution correction rebuild | ADR-S10-007; RC-010-022 | `correct_execution()` plus deterministic reprojection | `test_corrections_timeline.py`, integration test |
| Management-event correction | ADR-S10-007 | `correct_management_event()` with immutable supersession | correction and REST tests |
| No duplicate sale truth | ADR-S10-005; RC-010-002/029 | `domain/timeline.py` composes distinct facts without persisting a sale management event | timeline unit/REST/integration tests |
| TradePlan/ProductSelection immutability | RC-010-030 | FT-010 consumes Trade provenance but exposes no mutation path to planning/selection | service/API boundaries and management tests |
| Provider/broker independence | RC-010-033/034/035 | sale command accepts actual quantity/price/time only and has no provider/broker dependency | integration test and Playwright request assertions |
| FT-011 handoff gate | RC-010-038/039 | `ft011_eligibility()` and REST handoff endpoint | unit and REST tests; partial false/full true |
| Frontend active-trade workflow | FT-010 UI acceptance | `frontend/src/features/trade/`, router integration | 5 focused tests, full frontend suite, browser E2E |

## Migration traceability

Sprint 10 extends the released FT-009 Alembic head `20260817_0014` with one linear chain:

1. `20260817_0015` – execution side and historical BUY semantics.
2. `20260817_0016` – execution supersession relation.
3. `20260817_0017` – closed-position and realized-gross-P&L projection state.
4. `20260817_0018` – immutable trade-management events.

Validated head: `20260817_0018`.

## Required invariant evidence

The Sprint 10 Definition of Ready required explicit proof of the following invariants. All are covered by the committed FT-010 test set:

- released FT-009 BUY behavior remains supported;
- historical execution migration uses BUY semantics;
- BUY/BUY weighted-average projection;
- partial SELL leaves positive open quantity;
- full SELL produces zero quantity and CLOSED state;
- over-sell fails closed;
- negative Position state is rejected;
- realized gross P&L follows Average Cost;
- deterministic rebuild equals current materialized state;
- correction retains the original fact while excluding it from effective current projection;
- management changes do not rewrite planning history;
- timeline composition does not create duplicate sale truth;
- FT-011 eligibility is false after partial exit and true after full exit;
- provider/broker capability is not required to capture an actual historical sale.

## Verification snapshot

Verified on the Sprint 10 feature branch before closeout documentation:

- FT-010 backend unit suite: `126 passed`;
- FT-010 backend integration scenario: `1 passed`;
- backend Ruff for FT-010 implementation/tests: PASS;
- frontend full Vitest suite: `86 passed`;
- frontend ESLint: PASS;
- frontend TypeScript: PASS;
- frontend Prettier: PASS;
- frontend production build: PASS;
- FT-010 Playwright browser scenario through Docker Compose/reverse proxy: `1 passed`;
- Alembic head: `20260817_0018`;
- branch diff check: PASS.

These are local pre-PR results. Protected CI and merge evidence are intentionally not claimed here.
