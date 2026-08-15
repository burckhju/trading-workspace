# ADR-S7-002 – Issuer Identity, Source of Truth and Lifecycle

Status: Accepted – Sprint 7B / S7B-00

## Context

FT-003 introduces Issuer as stable reference data for later Warrant/Product Selection capabilities.
The current repository contains no Company, Organization, LegalEntity, Issuer, Institution or
Counterparty aggregate that can be reused. `Underlying` is workspace-scoped, while
`TradingVenue` is global reference data. Provider instrument mappings already keep provider
symbols and exchange codes outside internal reference-data identity.

Issuer must therefore not be inferred from an Underlying or from the company behind an
Underlying. A product issuer is an independent legal-entity role: an instrument referencing a
Siemens underlying can be issued by another legal entity such as a bank.

## Decision

1. `Issuer.id` is a stable internal UUID and the provider-neutral primary identity.
2. Issuer V1 models the concrete issuing legal entity, not a brand and not a corporate group.
   `legal_name` identifies the maintained legal-entity name; `display_name` is presentation data
   and may differ without changing identity.
3. Issuer is global reference data. No workspace-owned duplicate issuer master data is created.
   Workspace-specific preferences or mappings require a concrete later use case.
4. `Issuer.id` is distinct from LEI, provider issuer IDs, provider names, brands, symbols,
   Underlying identity and TradingVenue identity.
5. LEI is optional standardized external evidence. It may support duplicate detection and later
   reconciliation but is not the internal primary key and is never synthesized.
6. V1 master data is intentionally minimal: stable UUID, legal name, display name, optional ISO
   country code, optional LEI, active/inactive lifecycle, optimistic-concurrency version and
   timestamps.
7. Legal-name or display-name changes do not change `Issuer.id`.
8. Deactivation preserves the issuer and all historical references. Hard delete is not part of
   normal lifecycle semantics.
9. Mergers/reorganizations are not modeled as automatic identity replacement in V1. If a legal
   successor relationship becomes necessary, it requires a separate explicit design so historical
   references are not silently rewritten.
10. Internal issuer master data is authoritative. Provider data may supply suggestions/evidence,
    but provider discovery does not automatically create issuers or overwrite issuer master data.
11. Duplicate detection is not automatic merge. LEI can provide strong evidence; normalized names
    can only indicate candidates. Ambiguous candidates are never guessed or merged automatically.
12. Provider-specific issuer reconciliation is not implemented in FT-003 unless the repository has
    a concrete provider source with sufficiently structured issuer data and stable identifiers.
    The current EODHD integration exposes instrument/provider mapping information, not a proven
    issuer-master-data contract suitable for automatic reconciliation.
13. TradePlan and TradePlanVersion remain product-neutral and receive no issuer fields.
14. FT-004 may later reference `issuer_id` directly from Warrant/Product persistence. That ID must
    remain independent of `trading_venue_id`, Underlying/Listing identity and provider product IDs.

## Source-of-truth policy

- New internal issuers are created through controlled reference-data administration/system
  workflows, not as a side effect of provider discovery.
- Administrative creation may accept externally sourced evidence, but the resulting internal UUID
  is generated and owned by Trading Workspace.
- Provider names never become immutable identity keys.
- LEI, when present, is canonicalized and uniqueness-protected because two active master records
  must not silently represent the same LEI.
- Name similarity alone is insufficient for automatic merge or automatic identity assignment.
- Conflicting source data is surfaced for administrative resolution rather than silently
  overwriting authoritative master data.

## Duplicate semantics

For V1, duplicate handling is conservative:

- exact same non-null LEI: duplicate/conflict prevention;
- normalized legal/display-name similarity: candidate evidence only;
- provider identifier equality: future provider-boundary evidence only;
- no automatic merge;
- no destructive rewrite of historical references.

A full merge workflow is deferred until a concrete administration use case exists.

## Lifecycle

Issuer lifecycle is `active` / `inactive`.

- Active issuers may be used for new product references.
- Inactive issuers remain readable and historically referencable.
- Reactivation uses the same `issuer_id`.
- Deactivation never mutates Warrant, Product, Trade, Position or historical-observation references.

## FT-004 consumer contract

A future Warrant may reference independently:

- `issuer_id` → stable FT-003 Issuer identity;
- `trading_venue_id` → stable FT-002 TradingVenue identity;
- Underlying/Listing reference;
- provider product/mapping identifiers in the provider boundary.

No one of these identifiers may be derived from another.

FT-003 does not introduce Warrant tables, services, APIs, UI, pricing or product-selection logic.

## User impact

Normal traders do not maintain issuer IDs, LEIs, provider issuer IDs, provenance or mapping data.
Issuer is background reference data. Later product import/selection should use an unambiguous
issuer automatically; user involvement is reserved for genuine unresolved administrative cases.
FT-003 therefore adds no routine input to the normal trading workflow.

## Consequences

- FT-004 receives a stable provider-neutral issuer reference without coupling Product to Underlying
  company identity.
- Historical observations and later trade/position data can reuse the same `issuer_id`.
- Name changes and deactivation do not destroy historical referential stability.
- Provider integration can evolve independently without owning internal issuer identity.
- Corporate-group hierarchy, parent/subsidiary structures and automatic deduplication remain out of
  scope until a concrete requirement justifies them.
