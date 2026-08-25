# FT-006 Governed ModelVersion Provenance

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
