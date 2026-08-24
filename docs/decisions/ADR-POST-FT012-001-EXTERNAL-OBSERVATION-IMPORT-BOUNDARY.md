# ADR POST-FT012-001 – External Observation Import Boundary

## Status
Accepted

## Context
FT-012 already owns immutable/versioned `ExternalObservation` records and import provenance structures. Historical Hebeltrader proposals are observations of third-party decisions, not workspace executions.

## Decision
- File import writes only to the External Observation/Learning boundary.
- `ExternalObservation != Trade` remains an invariant.
- Import rows begin as reviewable staging records and become observations only through an explicit accepted disposition.
- Unambiguous valid rows may be prepared automatically, but unresolved rows require user review before acceptance.
- A `Trade` may only be created through the separately exposed explicit `execute-as-trade` command; import itself never invokes that command.
- Corrections to an already accepted observation create a new immutable `ExternalObservationVersion`; historical versions are never mutated.

## Consequences
The importer can scale to large historical datasets while retaining provenance and protecting the semantic distinction between observed third-party behavior and the user's own executed trades.
