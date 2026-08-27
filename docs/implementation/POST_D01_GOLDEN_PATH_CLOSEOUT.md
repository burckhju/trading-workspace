# Post-D01 Golden Path Closeout and Capability Review

## Purpose

Close the post-D01 stabilization sequence after Extensions 02 through 08 by recording exactly which cross-feature seams are now qualified, which boundaries remain intentionally separate, and which capability gaps should be treated as future architecture work rather than hidden assumptions.

This closeout does not add a new product capability, runtime orchestration, model activation, provider integration, or schema migration.

## Qualified Golden Path

The repository now has deterministic qualification across the following released seams:

`MarketReference -> MarketDataInstrument -> ProviderInstrumentMapping -> DailyPrice -> FT-006 MarketAnalysis -> Readiness`

`FT-006 analysis output -> Market Context -> Relative Strength -> TOP_DOWN_CANDIDATE qualification`

`QUALIFIED / READY_FOR_PLANNING CandidateEvaluation -> explicit FT-007 handoff -> TradePlan -> immutable TradePlanVersion`

`APPROVED TradePlanVersion -> FT-008 ProductSelectionRun -> ELIGIBLE ProductEvaluation -> explicit ProductSelection`

`ProductSelection -> FT-009 workspace purchase -> Trade -> immutable BUY ExecutionRecord -> Position`

`open WORKSPACE_SELECTION Position -> user-confirmed full SELL -> immutable SELL ExecutionRecord -> deterministic reprojection -> open_quantity = 0 -> FT-011 eligible`

`closed Trade -> FT-011 PostTradeObservation -> completed observation horizon -> ExitReview -> FINALIZED/CURRENT ExitReviewVersion -> FT-012 handoff READY`

`finalized FT-011 provenance -> FT-012 LearningEvidence(type=FT011) -> FT011Evidence provenance -> Lesson V1/CURRENT -> SUPPORTS evidence link`

`FT-012 LearningEvidence -> FT-013 governed model V1 DRAFT -> explicit V1 approval -> evidence-backed Hypothesis -> Change Proposal -> retrospective Validation -> explicit approval -> immutable approved ModelVersion V2`

Together, these slices qualify the released downstream decision chain from the D01 MarketReference boundary through controlled model governance.

## What is proven

The qualification series proves the following architecture properties:

- semantic MarketReference data can supply the market leg without inventing a Listing;
- downstream candidate decisions consume released analysis outputs;
- Candidate, TradePlan, Product Selection, Trade/Position, Post-Trade, Learning, and Model Governance boundaries preserve immutable provenance identifiers;
- process states such as READY_FOR_PLANNING, APPROVED, FT-011 eligibility, handoff READY, and model approval remain explicit gates rather than automatic transitions;
- user decisions remain explicit where the released contracts require them;
- historical decisions are not silently retargeted by later evaluations, plan versions, selection runs, review versions, evidence, or model versions;
- the full-exit rule is represented by immutable execution history and deterministic position reprojection;
- FT-013 approval creates a new immutable approved version while preserving the previously approved version;
- runtime model activation remains separate from governance approval.

## Qualification shape

This is not one monolithic public HTTP end-to-end test.

The repository exposes the participating capabilities through different public API, application-service, domain, persistence, and deterministic integration boundaries. The closeout therefore treats the Golden Path as a composition of adjacent released seams rather than inventing an orchestration layer solely to make the path appear continuous.

This distinction is intentional and remains an architecture invariant for future work.

## Capability gaps intentionally left open

### 1. Automatic FT-011 -> FT-012 evidence materialization

Extension 07 proves that finalized FT-011 provenance can be represented and consumed as FT-012 LearningEvidence, but the released FT-012 application surface does not expose an automatic materialization command/service from ExitReviewVersion to LearningEvidence.

Future work may add this capability only as an explicit idempotent command or orchestrated handoff with preserved provenance and clear ownership. The current Golden Path must not be described as proving automatic materialization.

### 2. Runtime model assignment and activation

Extension 08 proves controlled governance through explicit approval of a new immutable ModelVersion. APPROVED does not mean ACTIVE.

The repository still needs a separately specified runtime-assignment/activation architecture if governed model versions are to control actual runtime consumers. That work must define active-version ownership, switching semantics, rollback, auditability, consumer compatibility, and protection against automatic trading behavior.

## Boundaries that are not capability defects

The following are intentionally outside the current closeout and are not treated as regressions:

- a single public API orchestrator spanning the entire Golden Path;
- live-provider E2E qualification in mandatory CI;
- broker order placement or broker synchronization;
- automatic TradePlan creation or approval;
- automatic Product Selection;
- automatic trade execution or position sizing;
- automatic lesson creation, hypothesis creation, proposal creation, validation, or approval;
- fees, commissions, taxes, and net-P&L expansion;
- general backtesting or shadow trading;
- cleanup of still-valid Listing-owned security contracts.

## Production issue discovered during Extension 08

The FT-013 handoff integration test exposed three SQLAlchemy parent/child persistence-ordering defects that were not visible in the previous isolated service coverage:

- HypothesisRecord had to be flushed before HypothesisEvidenceRecord links;
- ModelValidationRecord had to be flushed before ModelValidationEvidenceRecord links;
- a newly created ModelVersionRecord had to be flushed before its ModelApprovalRecord.

The fixes are intentionally minimal explicit `flush()` boundaries. They do not change the FT-013 domain contract or introduce new governance behavior; they make the existing foreign-key ordering deterministic under PostgreSQL.

## Current quality baseline

The final Extension 08 PR head qualified all repository gates on the same head:

- Frontend: PASS
- End-to-End: PASS
- Ruff: PASS
- Black: PASS
- mypy: PASS
- Alembic upgrade through `20260827_0028`: PASS
- Backend: 839 / 839 tests passed
- Coverage: 85.32%

The closeout PR is documentation-only apart from correcting Extension 08 documentation to reflect the already-merged persistence-ordering fixes.

## Recommended follow-up sequence

The Golden Path extension series is complete. Future work should no longer add another numbered Golden Path extension by default.

The next architecture decisions should be treated as independent product/architecture slices, in this order when they become valuable:

1. specify and implement idempotent FT-011 -> FT-012 LearningEvidence materialization;
2. specify runtime model assignment / controlled activation independently from FT-013 approval;
3. review governed ModelVersion provenance for real runtime consumers before connecting activation;
4. perform evidence-driven cleanup of legacy/compatibility contracts only where consumers prove removal is safe;
5. select the next user-facing product capability from the actual backlog rather than extending the stabilization chain for its own sake.

## Closeout decision

The post-D01 Golden Path stabilization objective is complete at the released seam level.

No additional Extension 09 is required to claim downstream integration confidence through FT-013 governance. Any further work must be justified as a distinct missing capability, runtime architecture change, cleanup slice, or user-facing feature.