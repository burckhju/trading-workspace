# S6-05 Implementation Report – FT-007 TradePlan Application Service

## Status

Completed – 2026-08-11.

## Scope

Implemented the FT-007 application-service layer over the S6-04 Unit-of-Work boundary. This unit covers manual and CandidateEvaluation-originated creation, provenance validation, lifecycle commands, amendment orchestration and explicit version-specific approval. REST API and frontend remain out of scope.

## Delivered

- `TradePlanService` as the application command boundary for FT-007.
- Manual TradePlan creation with active workspace/Underlying validation.
- Candidate-originated TradePlan creation with exact CandidateEvaluation handoff and no `latest` re-resolution.
- Candidate/workspace/evaluation consistency validation and LONG-only handoff enforcement.
- Initial version creation as `DRAFT`, including append-only creation/version events.
- Explicit `DRAFT -> READY_FOR_REVIEW`, `READY_FOR_REVIEW -> DRAFT` and abandon commands using the domain lifecycle rules.
- Explicit version-specific approval with actor, timestamp, correlation ID, approval row and audit event.
- Approval serialization using row locking of the durable TradePlan identity before the approval decision.
- Amendment from an `APPROVED` base only, requiring a non-empty change reason and creating a new `DRAFT` version with `previous_version_id`.
- Automatic lifecycle visibility of the prior approved version as `SUPERSEDED` only when a newer version is explicitly approved; the historical approval proof remains unchanged.
- Repository status-projection support while content fields of historical TradePlanVersion snapshots remain untouched.
- Application-service tests covering manual/candidate creation, explicit lifecycle changes, approval/supersede behavior and amendment rules.

## Architecture Notes

- `READY_FOR_PLANNING` from FT-005 is deliberately not used as an approval trigger or persistence prerequisite. FT-007 validates stable origin provenance only; approval remains an explicit user command.
- Candidate-originated creation references exactly the supplied immutable CandidateEvaluation and never resolves a later evaluation.
- Status is treated as lifecycle projection/audit context. Thesis, Entry, Invalidation, Targets and RiskAssumptions are not edited in place after creation; business-content changes use a new TradePlanVersion.
- Approval is bound to one concrete version and is never derived from Candidate qualification, market analysis or an automatic calculation.
- No Warrant/product attributes, position sizing, order quantity, broker behavior or execution logic were introduced.

## Quality Gates

- `PYTHONPATH=backend python -m pytest -q tests/unit/backend` – 253 passed.
- `PYTHONPATH=backend python -m compileall -q backend/app/features/trade_plan` – passed.
- Ruff 0.15.1 is pinned by the repository but is unavailable in the current runtime. Installation was attempted and could not proceed because the runtime has no network access. No Ruff success result is claimed.

## Next Unit

S6-06 – CandidateEvaluation Handoff / provenance integration hardening: persistence-backed origin validation tests, read-side provenance exposure and service-level retrieval/query behavior required before the REST contract is introduced.
