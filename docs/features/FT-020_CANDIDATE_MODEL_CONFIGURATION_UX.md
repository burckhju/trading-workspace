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

## Context-bound proposal entry

The existing proposal form binds a hypothesis visit, a model/version load and an
explicit submission separately. Returning to the same hypothesis or model ID does
not authorize an earlier response to update the new visit. The handler requires a
successful current load and an existing APPROVED base belonging to the selected
model; mixed model identities or ambiguous version IDs fail closed.

Changing model or base resets the bound definition, policy and rationale. An
equivalent selection or normal rerender preserves deliberate input. While a save
is pending, these fields are locked synchronously; navigating away remains
possible, and the old server request may still finish. Its response cannot update
another form instance or unlock a later save. A successful response must match the
submitted hypothesis/model/base identities and report DRAFT before it is shown.

Current errors preserve the draft. There is no automatic POST retry or serverwide
exactly-once claim. Reopening the existing Lesson page provides conscious readback
after an uncertain network completion. See the bounded
[Strang B qualification](../implementation/MODEL_PROPOSAL_CONTEXT_QUALIFICATION.md)
for reproduced regressions, preserved protections and separate native evidence.

## Non-scope

No new Candidate trading rule, schema 3.0, generic rule builder, JSON editor for Candidate configuration, DSL, activation engine, automatic activation, automatic model selection, validation algorithm, backtest, navigation redesign or unrelated cleanup is introduced.

## Traceability

- Issue: #72
- Predecessor: FT-019 / #70 / PR #71
- Candidate runtime authority: `backend/app/features/candidate/domain/runtime_definition.py`
- Governance authority: `backend/app/features/model/service/application.py`
- Runtime activation authority: `backend/app/features/model/service/runtime_activation_service.py`
- Configuration UX: `frontend/src/features/model/components/HypothesisProposalPanel.tsx`

## 2026-10-25 — Existing governance journey continuation

The [Candidate governance qualification](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md)
extends the existing Lesson/Governance/Candidate consumers. The actual viewed
Lesson snapshot supplies the hypothesis source, including historical L1 after L2
exists. Proposal model, hypothesis and approved base are explicit. Validation
readback exposes its stored Evidence IDs, exact cutoff, conclusion, metrics and
notes; Approval exposes its ID and the predecessor version. These additions retain
the released #274 proposal-entry context protection.

The existing RuntimeActivationPanel separates the current runtime, latest version
and deliberately selected compatible APPROVED target. This permits explicit return
to retained A through the same activation command. It does not automatically select
or activate the latest version. Follow-up command controls bind responses to their
current instance and prevent synchronous duplicate submissions. Uncertain command
completion requires deliberate readback; client locks are no serverwide exactly-once
guarantee. Failed reads remain visible instead of implying absent saved facts.

The 115 targeted local UI cases, including 18 new cases, are a bounded development
result. The unchanged complete local frontend gate subsequently passed 734 tests
in 121 files and its build on the combined working copy. The first complete native
S2–S6 journey passed on head `1109f047` in run `40166152063`, job `121087501390`:
one pass, no retry/skip/flaky, exact historical readback and complete cleanup.
All six actual desktop/mobile images were inspected. They exposed a remaining
parent hypothesis-status readback gap after child commands; the narrow follow-up
reads the existing owner state instead of inferring a business status. The mobile
governance cards remain narrow but expose complete IDs and controls. The final PR
binds the complete CI of its last head separately. The report records the FT-006
VALID→LIMITED quality boundary; B07's GOOD reference is not satisfied by a LIMITED
run. No SUPPORTS-only approval rule, validation algorithm, backtest or economic
policy recommendation is introduced, and no acceptance status is raised.
