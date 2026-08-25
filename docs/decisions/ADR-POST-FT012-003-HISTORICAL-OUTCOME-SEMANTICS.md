# ADR POST-FT012-003 – Historical Outcome Semantics

## Status
Accepted

## Context
Historical external proposals may contain facts available at proposal time as well as later outcome data. Mixing those fields would introduce hindsight into Learning and future model validation.

## Decision
- Source facts observed at the historical decision time belong to the immutable `ExternalObservationVersion` source snapshot.
- Later measured outcomes are analytically derived observations and must retain their measurement horizon and provenance.
- Interpretation such as decision quality, rule adherence or a lesson is not stored as source evidence.
- `Evidence != Interpretation` remains binding.
- No historical outcome or lesson may directly mutate a model parameter or existing model version.
- Source-specific field classification is defined only after representative source files are inspected.

## Consequences
Future analytics can compare historical decisions with outcomes without leaking hindsight into the original decision snapshot or bypassing model-change governance.
