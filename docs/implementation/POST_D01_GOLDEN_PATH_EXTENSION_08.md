# Post-D01 Golden Path Extension 08

## Purpose

Close the downstream Golden Path with the released FT-013 controlled-governance seam: existing FT-012 LearningEvidence can support an explicit hypothesis, proposal, retrospective validation, and audited approval that creates a new immutable approved ModelVersion.

## Qualified path

`FT-012 LearningEvidence -> governed model V1 DRAFT -> explicit V1 approval -> OPEN hypothesis -> DRAFT proposal against approved V1 -> retrospective validation -> explicit proposal approval -> immutable approved ModelVersion V2`

## Invariants

- FT-013 references FT-012 LearningEvidence; it does not rewrite or own the evidence.
- The initial governed model version starts DRAFT and requires explicit approval.
- A hypothesis requires existing learning evidence and remains an explicit governance artifact.
- A proposal references exactly one approved base model version.
- Retrospective validation uses an explicit evidence set and cutoff.
- Proposal approval is explicit and audited.
- Approval creates a new immutable approved ModelVersion whose `previous_version_id` points to the approved base version.
- The historical V1 model version remains approved and unchanged.
- No runtime activation or switching occurs in this slice.

## Non-scope

- automatic model changes
- automatic hypothesis/proposal creation
- automatic approval
- runtime model activation or active-version switching
- order/execution decisions
- general backtesting or shadow trading
- schema changes

## Implementation

Added `tests/integration/backend/learning/test_ft013_governance_handoff.py` using the released FT-012 PostgreSQL integration fixture and the released `ModelGovernanceService`.

During PostgreSQL qualification, the new handoff test exposed three existing SQLAlchemy parent/child persistence-ordering defects in `ModelGovernanceService`. The slice therefore also added minimal explicit `flush()` boundaries so that:

- `HypothesisRecord` is persisted before `HypothesisEvidenceRecord` links;
- `ModelValidationRecord` is persisted before `ModelValidationEvidenceRecord` links;
- a newly created `ModelVersionRecord` is persisted before its `ModelApprovalRecord`.

These fixes do not change the FT-013 governance contract or introduce new model behavior. They make the existing foreign-key ordering deterministic under PostgreSQL. No migration or schema change is included.
