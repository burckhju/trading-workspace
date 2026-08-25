# FT-013 Controlled Model Governance

## Status

**Variant B – Controlled Governance V1**

FT-013 provides a governed path from existing learning evidence to a new immutable model version without automatically activating that version in any trading or analysis runtime.

## User outcome

The user can:

1. register a model and its initial immutable definition,
2. explicitly approve the initial governed version,
3. formulate a hypothesis from existing `LearningEvidence` and/or a concrete `LessonVersion`,
4. create a concrete change proposal against one approved base model version,
5. run and persist a retrospective validation against an explicit evidence set and evidence cutoff,
6. explicitly approve a validated proposal, creating a new immutable approved `ModelVersion`.

## Non-scope

V1 intentionally does **not** provide:

- automatic model changes,
- automatic approval,
- runtime activation or switching of active model versions,
- order/execution decisions,
- a general backtesting engine,
- A/B or shadow trading,
- silent replacement of evidence after upstream corrections.

## Governance invariants

- `LearningEvidence` remains owned by FT-012; FT-013 stores references only.
- Historical evidence and model-version assignments are never rewritten.
- A proposal references exactly one approved base model version.
- Approval is explicit and audited.
- Proposal approval creates a new immutable model version.
- A proposal whose base is no longer the latest version is stale and cannot be approved.
- Retrospective validation rejects evidence created after its `evidence_cutoff_at`.
- Validation results are evidence, not an automatic approval decision.
- There is no activation endpoint in V1.

## REST surface

Base path: `/api/v1/model-governance`

- `POST /models`
- `GET /models`
- `GET /models/{model_id}/versions`
- `POST /models/{model_id}/versions/{version_id}/approve`
- `POST /hypotheses`
- `POST /proposals`
- `GET /proposals/{proposal_id}`
- `POST /proposals/{proposal_id}/validations`
- `POST /proposals/{proposal_id}/approve`

## Persistence

Alembic revision `20260825_0023` adds:

- `governed_models`
- `governed_model_versions`
- `model_hypotheses`
- `model_hypothesis_evidence`
- `model_change_proposals`
- `model_validations`
- `model_validation_evidence`
- `model_approvals`

The migration extends `20260824_0022`.
