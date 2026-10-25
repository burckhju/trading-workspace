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

## 2026-10-25 — Candidate governance journey qualification

The bounded [Candidate governance qualification](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md)
reuses this rule and both existing V2 policies. Candidate evaluation readback now
projects the exact already persisted analysis sources, including role, source
ID/version and analysis model ID/version. The existing consumer offers historical
evaluation links; an invalid requested evaluation is not silently replaced with
the latest result. Re-activation of an earlier compatible APPROVED version uses
the existing activation owner. No definition, criterion or aggregation semantics
change, and no migration is introduced.

The protected Browser→API→PostgreSQL journey first passed in
[run 40166152063](https://github.com/burckhju/trading-workspace/actions/runs/40166152063),
job `121087501390`, on head `1109f047`: one actual pass, retry=0, no skip/flaky.
Exact owner-created sources, A→B→A, four immutable evaluations, four read-only
fingerprint windows, six inspected desktop/mobile images and complete cleanup are
recorded in the qualification report. Three preceding failed head runs remain
documented. The final PR separately binds the last checkout/tree and complete CI,
including the PostgreSQL boundary cases; this earlier pass is not transferred to
a later head.

There is a concrete limit to the requested GOOD-quality reference: the existing
FT-006 owner copies DailyPrice `VALID` into analysis snapshots, while its calculator
treats values other than `GOOD` as `LIMITED`. The new journey asserts this actual
LIMITED state. Even a passing LIMITED A→B→A run does not satisfy the GOOD-reference
part of B07. FT-006 quality semantics remain unchanged; the dependent correction
and requalification require a separate bounded task. This qualification makes no
backtest, financial-superiority, M9-acceptance, release or observed-PC claim.
