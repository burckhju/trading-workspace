# FT-006 Governed ModelVersion Provenance

The original legacy-baseline description below is retained as historical
documentation. The [25 October 2026 extension](#extension-2026-10-25-exact-runtime-provenance)
defines the contract for the versioned source-quality work in PR #278. It is a
development contract, not a release, business acceptance or production activation.

## Scope

This slice connects the released FT-006 `EOD_TREND_MOMENTUM / 1.0.0`
runtime consumer to FT-013 governed ModelVersion provenance without changing
trading logic, loading rules dynamically, assigning a newer version, or
activating a version.

The existing runtime identity (`model_id`, `model_version`), persisted input
parameters, snapshot and input hash remain the FT-006 reproducibility contract.
`governed_model_version_id` is additional immutable provenance.

## Released legacy baseline

A governed ModelVersion represents the released FT-006 baseline only when its
`definition` contains all of these exact values:

```json
{
  "runtime_contract": "FT-006:EOD_TREND_MOMENTUM:1.0.0",
  "runtime_model_id": "EOD_TREND_MOMENTUM",
  "runtime_model_version": "1.0.0",
  "implementation_ref": "backend/app/features/analysis/domain/calculator.py@8dcead013709d1ba2ad40e180fcc65ebe1c6589e",
  "rule_representation": "CODE_PLUS_PARAMETERS"
}
```

Additional descriptive fields are allowed. The required values are defined in
`app.features.analysis.domain.governed_provenance`.

The implementation reference points to the released calculator artifact on the
FT-013 baseline. If calculator behavior changes, the runtime model version and
this implementation reference must be reviewed together; silently retaining the
legacy contract would make provenance false.

## Baseline registration runbook

Baseline registration deliberately uses the existing FT-013 two-step governance
flow. It is an operator action, not a migration seed and not runtime activation.

1. Call `POST /api/v1/model-governance/models` with model key
   `EOD_TREND_MOMENTUM`, a descriptive name/purpose and the exact definition
   above. The response creates ModelVersion 1 in `DRAFT` state.
2. Review the returned model/version IDs and definition. Only after that review,
   call `POST /api/v1/model-governance/models/{model_id}/versions/{version_id}/approve`.
3. Confirm the version is `APPROVED`. No assignment or activation follows from
   this approval; FT-006 continues to execute the released code-based model.
4. Start a new FT-006 analysis and verify that its
   `market_analysis_runs.governed_model_version_id` equals the approved baseline
   version ID while the legacy `model_id`, `model_version`, input hash and
   calculation behavior remain unchanged.

The PostgreSQL integration test
`test_ft006_governed_provenance_postgres.py` exercises the same create → approve
→ persist-run sequence through `ModelGovernanceService` and verifies the stored
foreign key.

## Runtime resolution

Before a new `market_analysis_runs` row is inserted on PostgreSQL, persistence
looks for an FT-013 ModelVersion that satisfies all of the following:

- same workspace as the MarketAnalysis;
- governed model key equals the runtime `model_id`;
- status is `APPROVED`;
- definition matches the released runtime contract above;
- definition's runtime model version equals the version actually executed.

Exactly one match causes its ID to be persisted in
`market_analysis_runs.governed_model_version_id`.

Zero matches leave provenance `NULL`. Multiple matches also leave provenance
`NULL`. This is intentional: missing provenance is preferable to false or
ambiguous provenance.

## Approval and activation boundaries

This slice does not create or approve a governed model automatically. The
legacy baseline must be created through the existing FT-013 governance flow and
its initial version must be explicitly approved.

`APPROVED` is not interpreted as assignment or activation. Runtime continues to
execute the released FT-006 calculator. The governed lookup merely determines
whether an immutable approved ModelVersion is an exact provenance anchor for
that already-selected code artifact.

There is no activation endpoint, no current-version pointer, no dynamic rule
loading and no automatic switching after a later ModelVersion is approved.

## Historical records

The migration adds a nullable foreign key and does not rewrite existing
historical runs. Existing rows retain their original `model_id`, `model_version`,
parameters, snapshots and input hashes.

A future historical backfill is allowed only for rows whose legacy identity can
be proven to correspond to exactly one approved governed baseline matching this
contract. A backfill must never use "latest approved" or "currently active" as
a substitute for the version actually used by the historical calculation.

## User impact

Calculation behavior and results do not change. Once the approved baseline is
present, new analysis runs gain an auditable governed ModelVersion reference.
Surfacing that UUID/model metadata in the UI is a separate presentation change;
this slice establishes the persisted source of truth first.

## Extension 2026-10-25: exact runtime provenance

### Selected calculation and separate governance identity

New explicitly requested FT-006 runs use the fixed
`NEW_RUN_MODEL_ID = EOD_TREND_MOMENTUM` and `NEW_RUN_MODEL_VERSION = 1.0.1`
selection in `analysis/domain/model_versions.py`. Both listing and native
market-reference commands pass this exact identity to the common executor.
An explicit new `model_version: "1.0.0"` request remains available. Historical
retry and verify always use the identity already stored on their source run.
Unknown identities do not fall back to another calculator.

This selection is independent of approved FT-013 ModelVersions and of Candidate
runtime activation. The analysis runtime string `1.0.1`, an analysis run's
integer `version`, the governed ModelVersion's integer version/UUID and the
software package version are distinct identities. No activation pointer is
introduced for FT-006.

### Exact 1.0.1 implementation contract

`governed_runtime_definition(model_id=..., model_version=...)` returns the
unchanged legacy definition for `EOD_TREND_MOMENTUM/1.0.0`, the following
definition for `EOD_TREND_MOMENTUM/1.0.1`, and no contract for an unavailable
identity:

```json
{
  "runtime_contract": "FT-006:EOD_TREND_MOMENTUM:1.0.1",
  "runtime_model_id": "EOD_TREND_MOMENTUM",
  "runtime_model_version": "1.0.1",
  "implementation_ref": "backend/app/features/analysis/domain/calculator_v1_0_1.py@541fcadfd77bde314e774b19a50af2ed61900d0c",
  "rule_representation": "CODE_PLUS_PARAMETERS"
}
```

The reference identifies an existing artifact, not a future integration commit.
The complete checkout confirms these objects at
[commit 541fcadfd77bde314e774b19a50af2ed61900d0c](https://github.com/burckhju/trading-workspace/commit/541fcadfd77bde314e774b19a50af2ed61900d0c):

| Artifact under `backend/app/features/analysis/domain/` | Git blob | Dependency meaning |
|---|---|---|
| `calculator_v1_0_1.py` | `0b903ff20b3b92c7967ca0df05854a86ac83a5d5` | The separate source-quality policy invokes `calculator.calculate` for numerical computation and then derives quality/notes from unchanged source facts. |
| `calculator.py` | `7ece74da68639cd26c5bbc73fcdf8b65dac426b8` | The imported legacy arithmetic and historical 1.0.0 policy remain unchanged. |

Both blobs are identical at the inherited PR head
`cd395c9b8a1a864a2c91fd352343eaf3c4e94f7e`; the current service integration does
not change either calculator. Thus the new implementation reference makes the
dependency on the preserved legacy arithmetic inspectable. A later arithmetic
change would require its own reviewed runtime contract rather than silently
retaining this identity.

**Existing legacy-reference limitation, checked on 25 October 2026:** the old
contract literal ending in `@8dcead013709d1ba2ad40e180fcc65ebe1c6589e` remains
unchanged. That commit is absent from the complete current clone, and the
exact GitHub Contents API lookup for `calculator.py` at that ref returns
`404: No commit found for the ref`. This continuation therefore does not claim
to have resolved that historical target. The present legacy calculator bytes
and the dependency used by 1.0.1 are independently verified at the existing
541fc commit and the blobs above. The lookup failure does not authorize an
invented replacement ref, a rewrite of old governed definitions or a backfill
of historical runs.

### Matching and absent provenance

The PostgreSQL `before_insert` listener resolves only the contract for the
identity actually being persisted. A candidate baseline must have all of:

- the analysis's workspace;
- governed model key equal to the run's exact `model_id`;
- `APPROVED` status;
- the exact runtime contract, runtime model ID and runtime version;
- the exact `implementation_ref` and `rule_representation`.

Exactly one match writes the governed ModelVersion UUID. Zero matches, only a
legacy baseline for a new 1.0.1 run, only a DRAFT definition, a foreign workspace,
an incompatible model key/implementation contract, or multiple exact matches
leave the reference `NULL`. No oldest/latest/active tie-breaker is used.
An existing `NULL` reference remains `NULL` after a later approval or verify.

The original legacy registration runbook above refers specifically to a new
run explicitly requested with `model_version: "1.0.0"`. It cannot be used to
attach the old baseline to a new default 1.0.1 run. A 1.0.1 baseline requires
its own explicit governance action with the definition above. If the model
already exists, its successor must follow the existing proposal, validation
and approval flow. This document grants no approval or production execution
authority. Isolated synthetic tests use those same owner commands and never
activate an FT-006 runtime through registration.

### History, hash and read-only behavior

The exact runtime identity remains part of the canonical input hash. Identical
prices/parameters can produce different hashes for new 1.0.0 and 1.0.1 runs;
their numerical metrics and criteria stay equal. Old snapshot flags, warnings,
notes, quality outputs, times, criteria and hashes are not rewritten.
The original nullable column is sufficient; this extension adds no migration.

Retry remains limited to `FAILED` and `NOT_EVALUABLE`, preserves the stored
version and parameters, and copies only the persisted source snapshot. It is
not an upgrade. Verify dispatches by the stored identity and uses the original
analysis timestamp for the data-age check, comparing input hash, metrics,
criteria, quality and notes separately. It does not register, approve,
activate or backfill any model. In particular, a historical 1.0.0 run with
`VALID` source flags may truthfully reproduce `LIMITED` and verify successfully.

The synthetic PostgreSQL cases are maintained in
`tests/integration/backend/database/test_ft006_versioned_quality_postgres.py`.
They cover both owners, the two runtime identities, absent/unique/ambiguous
provenance, wrong scope/key/implementation, DRAFT status, unchanged historical
facts after a current price correction, and read-only fingerprints around
verification. Model registrations and approvals use `ModelGovernanceService`;
the small evidence anchor in the provenance-only successor fixture is not a
claim of the full B07 learning journey. Test definitions and successful
collection do not establish execution. Actual runs and remaining qualification
limits belong to the
[FT-006 qualification report](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md).
