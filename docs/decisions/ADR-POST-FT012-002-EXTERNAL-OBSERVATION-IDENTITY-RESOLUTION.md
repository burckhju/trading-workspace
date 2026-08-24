# ADR POST-FT012-002 – External Observation Identity Resolution

## Status
Accepted

## Context
Historical source rows may identify an underlying or warrant by external names/identifiers that are incomplete or ambiguous. Silent guesses would contaminate later learning evidence.

## Decision
- Resolution consumes released Reference Data identities; the importer does not silently create new underlyings, warrants, issuers or venues.
- A unique deterministic match may be accepted automatically.
- Zero or multiple plausible matches produce an `UNRESOLVED` row and a review issue.
- The review queue presents the ambiguity and requires an explicit user resolution or discard.
- Product resolution may remain empty only when the source observation is semantically valid at underlying level; this must be allowed by the source mapping contract rather than guessed by the generic importer.
- User resolutions are persisted on the import row and remain auditable through disposition actor/time and raw source payload.

## Consequences
Variant A remains low-input for clean data while preventing guessed identities from becoming learning evidence.
