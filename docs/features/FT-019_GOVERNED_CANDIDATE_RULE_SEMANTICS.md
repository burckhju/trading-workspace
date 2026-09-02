# FT-019 – Governed Candidate Rule Semantics

## Status

Implementation – 2026-09-02.

## Purpose

FT-019 closes the governed Candidate capability chain by making one approved and explicitly activated Candidate definition parameter materially affect real Candidate evaluation.

The runtime chain remains:

```text
Governed ModelVersion Definition
  → Approval
  → explicit Runtime Activation
  → Candidate Runtime Readiness
  → CandidateService.evaluate()
  → typed Candidate definition adapter
  → Candidate criterion semantics
  → Candidate Evaluation Result
  → persisted governed ModelVersion provenance
```

Approval and activation remain separate. `ACTIVE` is not a `ModelVersion.status`; `RuntimeActivationService` remains the runtime source of truth.

## Candidate Rule Catalog

FT-019 governs exactly one existing required rule:

### TD-MARKET-001 – Primary market context

Severity: `REQUIRED`.

Input source: `MarketContextAssessment` already present in `CandidateEvaluationInput`.

Data-quality semantics remain unchanged:

- `market_context == NOT_EVALUABLE` → criterion `NOT_EVALUABLE`;
- `market_quality == INSUFFICIENT` → criterion `NOT_EVALUABLE`;
- otherwise the actual market context is tested for membership in the configured allowlist.

Aggregation remains unchanged:

- any required `NOT_FULFILLED` → Candidate `NOT_QUALIFIED`;
- otherwise any required `NOT_EVALUABLE` → Candidate `NOT_EVALUABLE`;
- otherwise Candidate `QUALIFIED`.

Warnings, criterion order, short-circuit behaviour and all other Candidate rules are unchanged.

## Definition Schemas

### TOP_DOWN_CANDIDATE/1.0

1.0 remains immutable and executable with its released semantics:

```json
{
  "schema": "TOP_DOWN_CANDIDATE/1.0",
  "direction": "LONG",
  "market_context_allowed": ["FAVORABLE", "CAUTIOUS"]
}
```

The adapter continues to reject any changed 1.0 allowlist, unknown key, unsupported direction or unsupported schema. The 1.0 engine continues to use the original explanation and qualification behaviour.

### TOP_DOWN_CANDIDATE/2.0

2.0 makes `market_context_allowed` an executed governed business rule:

```json
{
  "schema": "TOP_DOWN_CANDIDATE/2.0",
  "direction": "LONG",
  "market_context_allowed": ["FAVORABLE"]
}
```

or:

```json
{
  "schema": "TOP_DOWN_CANDIDATE/2.0",
  "direction": "LONG",
  "market_context_allowed": ["FAVORABLE", "CAUTIOUS"]
}
```

Contract:

- `direction`: required, exactly `LONG`;
- `market_context_allowed`: required, non-empty list;
- no implicit default;
- executable configurations are exactly `{FAVORABLE}` and `{FAVORABLE, CAUTIOUS}`;
- `UNFAVORABLE` and `NOT_EVALUABLE` are not executable allowlist values;
- unknown definition fields fail closed;
- unknown schema versions fail closed.

Schema version and governed ModelVersion are independent. Parameter changes inside this 2.0 contract create a new immutable governed ModelVersion; they do not create another Candidate schema version.

## Observable user semantics

Given otherwise identical Candidate inputs with market context `CAUTIOUS`:

- active ModelVersion A using 2.0 with `FAVORABLE, CAUTIOUS` → `TD-MARKET-001 = FULFILLED`;
- active ModelVersion B using 2.0 with only `FAVORABLE` → `TD-MARKET-001 = NOT_FULFILLED`;
- if all other required criteria are fulfilled, A produces `QUALIFIED` while B produces `NOT_QUALIFIED`.

The criterion stores and exposes the actual context, the configured allowed context(s), and an explanation describing whether the actual context is allowed by the active Candidate rule. No definition JSON blob is used as the user explanation.

## Runtime readiness and TOCTOU

`CANDIDATE_RUNTIME_MODEL` continues to use the same fail-closed adapter as real Candidate execution:

- valid 1.0 → `COMPLETE`;
- valid 2.0 → `COMPLETE`;
- invalid or unknown definition → `BLOCKED`.

Frontend code does not infer executability from schema JSON. `CandidateService.evaluate()` resolves the active model again at execution time; therefore an activation change after a readiness read is authoritative for the subsequent evaluation.

## Provenance and history

Each Candidate evaluation persists the actual governed model key and ModelVersion number used at execution. A later activation switch does not retarget earlier evaluations. Criterion snapshots retain their actual value, expected value and explanation.

Re-activating an earlier immutable approved ModelVersion is supported by the existing activation architecture and restores that version's rule behaviour without mutating historical evaluations.

## Persistence and frontend impact

No database migration is required. Existing ModelVersion definition storage, CandidateEvaluation provenance and CandidateCriterion persistence are sufficient.

No new frontend schema logic is introduced. FT-018 remains driven by backend readiness and `can_evaluate`; existing criterion rendering receives the more specific rule explanation through the existing API contract.

## Security boundary

2.0 accepts only typed enum configuration. It does not accept expressions, Python, SQL, URLs, commands or dynamic executable code.

## Traceability

| Requirement | Implementation / evidence |
| --- | --- |
| 1.0 remains immutable | `qualification.evaluate_candidate()` and 1.0 adapter path |
| explicit 2.0 schema | `candidate.domain.runtime_definition` |
| parameter is materially effective | `evaluate_candidate_with_market_context_rule()` |
| unknown/missing fields fail closed | runtime adapter unit tests |
| missing input remains NOT_EVALUABLE | Candidate runtime-definition unit test |
| readiness/evaluate parity | runtime-readiness unit tests use the same adapter |
| activation A→B changes result | Candidate runtime execution unit test |
| Governance→Approval→Activation→Evaluation | FT-019 PostgreSQL integration test |
| historical provenance remains immutable | FT-019 PostgreSQL integration test |
| rollback/re-activation restores semantics | FT-019 PostgreSQL integration test |
| no migration | existing schema reused |
| semantic versioning decision | `ADR-FT019-001-CANDIDATE-DEFINITION-SEMANTIC-VERSIONING.md` |

## Non-scope

FT-019 does not add a generic rule DSL, relative-strength threshold parameter, volatility/range-position trading rule, new runtime resolver, new activation engine, automatic activation, automatic model selection, governance UI redesign, rule editor, backtesting, broker integration or database migration.
