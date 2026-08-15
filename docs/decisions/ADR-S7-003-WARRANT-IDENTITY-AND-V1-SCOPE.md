# ADR-S7-003 – Warrant Identity and V1 Scope

## Status
Accepted for Sprint 7C after S7C-00 review.

## Decision
FT-004 V1 supports classic bank-issued call and put warrants only. Knock-outs, turbos, mini-futures, factor certificates and other structured products are outside V1.

A Warrant is a workspace-scoped aggregate with a stable internal UUID `warrant_id`. ISIN and WKN are external identifiers and must never be used as the internal identity. `ProductFamily` is fixed to `WARRANT`; call/put is modelled separately as `OptionDirection`.

A Warrant references the existing FT-003 `issuer_id` and FT-001 `underlying_id`. It does not duplicate issuer or underlying master data.

## Consequences
The product aggregate remains provider-neutral and can be referenced historically even if provider identifiers change. Workspace scope follows from the existing FT-001 Underlying boundary on which the V1 Warrant depends.

## User impact
Users manage one stable warrant record independent of provider symbols. They choose an existing issuer and underlying instead of re-entering their names. This slightly increases reference-data discipline but prevents duplicate or diverging master data.
