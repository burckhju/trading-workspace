# FT-020 – Governed Candidate Model Configuration UX

## Purpose

FT-020 makes the governed `TOP_DOWN_CANDIDATE/2.0` market-context policy understandable and changeable without editing definition JSON. It extends the existing Hypothesis → ModelChangeProposal → Validation → Approval → Runtime Activation workflow; it does not create a second governance path.

## Supported policy

The specialized Candidate configuration UX exposes only:

- `FAVORABLE + CAUTIOUS`
- `FAVORABLE only`

The proposed definition is always explicit `TOP_DOWN_CANDIDATE/2.0`, `LONG`, with a required `market_context_allowed` value. No implicit default exists.

## V1 → V2 derivation

A valid immutable `TOP_DOWN_CANDIDATE/1.0` base is presented as the legacy `FAVORABLE + CAUTIOUS` policy. When the user explicitly proposes a policy change, FT-020 derives a new `TOP_DOWN_CANDIDATE/2.0` proposed definition. The V1 ModelVersion is never mutated or reinterpreted and no runtime migration occurs automatically.

## V2 → V2 derivation

A valid V2 base can propose the other supported policy while remaining schema 2.0. A policy-value change does not create a new schema version.

## Safety and governance

- The Proposal Base ModelVersion remains explicit and is not assumed to be the active runtime version.
- Current and Proposed policy are shown separately.
- A no-op policy selection cannot be submitted through the specialized Candidate UX.
- Unknown keys, missing parameters, unsupported schema versions and unsupported policy values make the specialized editor read-only. Unknown content is never silently normalized or dropped.
- The impact preview describes only the deterministic effect on the required market-context criterion; it is not retrospective validation, a backtest, a performance prediction or a recommendation.
- Approval still creates a new immutable `APPROVED` ModelVersion and does not activate it.
- Runtime activation remains an explicit, separate action through the existing Runtime Activation contract.
- Runtime executability and Candidate readiness remain backend-authoritative through the existing Candidate runtime adapter.
- Existing stale-base protection remains authoritative; FT-020 never silently rebases a proposal.

## Impact preview

`FAVORABLE + CAUTIOUS` → `FAVORABLE only`:

> Candidates in a CAUTIOUS market context will no longer satisfy the required market-context criterion.

`FAVORABLE only` → `FAVORABLE + CAUTIOUS`:

> Candidates in a CAUTIOUS market context will become eligible to satisfy the required market-context criterion.

## Non-scope

No new Candidate trading rule, schema 3.0, generic rule builder, JSON editor for Candidate configuration, DSL, activation engine, automatic activation, automatic model selection, validation algorithm, backtest, navigation redesign or unrelated cleanup is introduced.

## Traceability

- Issue: #72
- Predecessor: FT-019 / #70 / PR #71
- Candidate runtime authority: `backend/app/features/candidate/domain/runtime_definition.py`
- Governance authority: `backend/app/features/model/service/application.py`
- Runtime activation authority: `backend/app/features/model/service/runtime_activation_service.py`
- Configuration UX: `frontend/src/features/model/components/HypothesisProposalPanel.tsx`
