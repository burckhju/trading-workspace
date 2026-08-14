# ADR-S7-001 – Trading Venue Identity, Source of Truth and Reconciliation

Status: Accepted – Sprint 7A

## Context

FT-002 completes the existing TradingVenue reference-data capability. TradingVenue already exists as a global entity and Listing already references it. Provider instrument mappings keep provider-specific exchange codes separately.

Sprint 7A must not create a parallel venue identity, must not let provider codes own internal identity, and must minimize manual venue input in normal trading workflows.

## Decision

1. `TradingVenue.id` is the stable internal, provider-neutral identity.
2. `TradingVenue.id`, MIC, provider exchange code and provider-specific identifiers are distinct concepts.
3. TradingVenue is global reference data. Workspace-specific configuration is not introduced without a concrete use case.
4. MIC is a standardized attribute, canonicalized to uppercase and unique. It is not the internal identity.
5. Provider exchange codes remain in provider/mapping boundaries. Provider discovery may supply evidence but does not create or overwrite internal venues automatically.
6. Reconciliation uses existing active provider mappings as evidence. A unique match may confirm/preselect a venue; ambiguity is not guessed; a clear conflict blocks mapping activation; unresolved evidence creates no new trader input.
7. Venue lifecycle uses activation/deactivation. Deactivation does not delete or rewrite existing Listing references.
8. Venue administration is an admin/system capability. Normal traders do not maintain MIC, country, timezone, technical version or provenance.
9. Low-input consumer rule: when exactly one valid venue is available, the system uses it automatically; user selection is requested only when multiple valid venues make the choice materially relevant.
10. Currency remains a Listing/Product concern in Sprint 7A. No default currency is added to TradingVenue because a venue can support instruments in different currencies and the existing Listing already owns `currency_code`.
11. TradePlan remains product-neutral and gains no Venue fields.

## Reconciliation ownership

Internal reference data is authoritative for venue identity. Provider data is evidence for mapping and validation.

- `MATCHED`: exactly one existing venue supports the provider evidence and agrees with the Listing.
- `CONFLICT`: provider evidence uniquely points to a different venue; mapping activation is blocked.
- `AMBIGUOUS`: more than one venue is plausible; no automatic choice is made.
- `UNRESOLVED`: no sufficient evidence exists; no venue is auto-created.

## Consequences

- Historical Listing, CandidateEvaluation and TradePlanVersion semantics are not rewritten by later venue changes.
- FT-004 can reference the same stable `TradingVenue.id` for a Warrant without duplicating venue master data.
- Product Selection can present a venue choice only when multiple executable venues are genuinely available.
- Reference-data administration stays exceptional rather than becoming a recurring trader workflow.
