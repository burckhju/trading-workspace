# FT-003 – Issuers

## Status

Implementation complete on `feature/s7b-ft003-issuers`; release pending protected-branch CI and merge.

## User outcome

Trading Workspace centrally maintains stable provider-neutral issuer identities without adding recurring issuer maintenance to the normal trading workflow.

A trader must not enter internal issuer IDs, provider IDs, LEIs, versions or provenance data during normal trading. Later product import/selection should use the stable `issuer_id` automatically whenever reference data resolves the issuer unambiguously.

## Implemented scope

- global provider-neutral `Issuer` identity with internal UUID;
- issuing legal entity as V1 semantic level, separate from brand/group;
- mutable legal/display names that do not define identity;
- optional canonical country code and optional LEI;
- LEI uniqueness as hard duplicate protection when LEI is available;
- activation/deactivation lifecycle without hard delete;
- optimistic concurrency for administration;
- global audit using the existing audit infrastructure;
- consumer read contract exposing active issuer reference data;
- separate administration read/write contract including lifecycle/version metadata;
- dedicated exceptional admin UI with minimal fields;
- persistence, service, REST, frontend and architecture compatibility tests.

## Explicit identity boundaries

`issuer_id` is independent from:

- Underlying and any company behind an Underlying;
- TradingVenue identity;
- provider symbol/exchange identifiers;
- provider issuer identifiers;
- display/marketing/brand name;
- LEI.

LEI is optional standardized external evidence, not internal primary identity.

## Source of truth

Internal Issuer reference data is authoritative. Provider data may later contribute evidence or suggestions but must not silently create internal Issuers, overwrite master data or replace `issuer_id`.

The current EODHD Search DTO exposes symbol, exchange, name, type, currency and ISIN but no structured Issuer or LEI field. FT-003 therefore does not introduce issuer reconciliation or name-based matching from EODHD.

## Duplicate handling

- exact non-empty LEI collision: rejected;
- similar names: possible duplicate evidence only;
- automatic name-based merge: not implemented;
- merge/deduplication workflow: later administration scope if required.

## Lifecycle and historical references

Deactivation removes an Issuer from normal active reference-data reads but does not delete or change its `issuer_id`. Reactivation restores availability using the same identity. This allows future Warrants, product selections, positions and historical external observations to retain stable references.

## FT-004 consumer contract

A later Warrant may hold a required foreign-key-style reference to stable `issuer_id` while independently referencing Underlying/Listing, TradingVenue and provider product mappings.

Conceptually:

```text
Warrant
  -> issuer_id
  -> underlying/listing reference
  -> trading_venue_id
  -> provider product mapping
```

None of these identities is derived from another. FT-003 does not implement Warrant persistence, service, API or UI.

## TradePlan boundary

FT-007 remains product-neutral. FT-003 adds no Issuer, Warrant, Venue-execution, leverage, spread, ratio, expiry, quantity or product-price attributes to TradePlan or TradePlanVersion.

## Auswirkung für den Nutzer

### Normaler Trader

Keine neue Pflichtangabe und kein neuer Schritt im Trading-Workflow. Issuer wird Reference Data im Hintergrund.

### Späterer Product-/Warrant-Import

Ist der Emittent eindeutig auflösbar, verwendet das System automatisch die stabile `issuer_id`. Der Trader muss keine technische Zuordnung vornehmen.

### Unklare oder widersprüchliche Daten

Das System darf nicht raten. Solche Fälle werden später als administrativer Reconciliation-/Duplicate-Fall behandelt, statt dem Trader technische IDs oder Freitext-Zuordnungen abzuverlangen.

### Administrator

Manuelle Pflege ist auf Legal Name, Display Name sowie optional Country und LEI beschränkt. Interne UUID und technische Versionsdaten werden nicht manuell eingegeben.
