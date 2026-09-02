# ADR-FT019-001 – Candidate Definition Semantic Versioning

## Status

Accepted for FT-019, 2026-09-02.

## Context

`TOP_DOWN_CANDIDATE/1.0` is the executable compatibility contract for the released Candidate 1.0 engine. Its `market_context_allowed` field is deliberately constrained to exactly `FAVORABLE` and `CAUTIOUS`, so a governed definition cannot claim semantics the engine does not execute.

FT-019 makes one governed Candidate rule materially effective: the required market-context gate may be configured to allow either only `FAVORABLE` or both `FAVORABLE` and `CAUTIOUS`.

Governed `ModelVersion` identity and Candidate definition schema identity answer different questions. Multiple immutable approved ModelVersions may use the same executable Candidate schema with different parameter values.

## Decision

1. `TOP_DOWN_CANDIDATE/1.0` remains semantically immutable. Its accepted definition and runtime behaviour stay identical to the released Candidate 1.0 contract.
2. The first parameterized Candidate semantics are introduced as `TOP_DOWN_CANDIDATE/2.0` because the meaning of `market_context_allowed` changes from a fixed compatibility discriminator to an executed business rule.
3. Schema versions change when structure, required inputs, rule meaning, or executable semantics change. A different parameter value within an unchanged schema contract creates a new governed ModelVersion, not a new schema version.
4. Runtime adaptation is fail-closed. Unknown keys, unknown schemas, missing required parameters, unsupported enum values, and unsupported parameter combinations are not executable.
5. `market_context_allowed` is required in 2.0 and has no implicit default. Executable configurations are exactly `{FAVORABLE}` and `{FAVORABLE, CAUTIOUS}`. `UNFAVORABLE` and `NOT_EVALUABLE` cannot be configured as allowed LONG contexts.
6. Approval and runtime executability remain separate concerns. Approval does not imply activation, and activation does not mutate `ModelVersion.status`.
7. Candidate Readiness and Candidate Evaluation use the same definition adapter. Runtime activation remains resolved through `RuntimeActivationService` at execution time.
8. Persisted Candidate provenance continues to reference the actually executed governed ModelVersion; schema version never replaces ModelVersion provenance.

## Consequences

A governed configuration can now deterministically change `TD-MARKET-001` and therefore Candidate qualification for otherwise identical inputs. Historical evaluations remain immutable and retain their original governed ModelVersion provenance. No generic expression language, rule DSL, plugin engine, automatic activation, or database migration is introduced.
