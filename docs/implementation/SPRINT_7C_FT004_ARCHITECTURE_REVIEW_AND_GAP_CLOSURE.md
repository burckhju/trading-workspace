# Sprint 7C / FT-004 – Architecture Review and Gap Closure

## Baseline
Verified repository baseline: `main == origin/main == 4ad4e0440502336af4be8cd5c85fd7c3c2d5e7b1`; release tag `v0.8.0-issuers` peels to the same commit. Known legacy untracked files were not staged or modified.

## Product scope V1
Classic bank-issued CALL/PUT warrants only. Knock-outs, turbos, mini-futures, factor certificates and other structured products are excluded.

## Aggregate boundaries
- Warrant: stable workspace-scoped product identity.
- Issuer: existing FT-003 global identity, referenced by `issuer_id`.
- Underlying: existing FT-001 workspace identity, referenced by `underlying_id`.
- WarrantListing: separate tradability context with FT-002 venue.
- WarrantTermsVersion: immutable/effective-dated contractual terms.
- ProviderInstrument and MarketDataSeries: separate technical/market-data concepts.

## EODHD capability gap
Repository inspection proves EODHD search/EOD price and listing-mapping capabilities, but not a complete warrant product-reference feed with reliable issuer, underlying, strike, maturity, ratio and call/put semantics. Warrant-specific provider ingestion is therefore not Definition-of-Ready and is not implemented in S7C V1.

## Definition of Ready closure
The following decisions are accepted for implementation:
1. Product scope: classic CALL/PUT warrants.
2. Stable UUID identity; workspace scoped.
3. `issuer_id` and `underlying_id` consume released contracts.
4. Product/listing split.
5. Effective-dated terms history.
6. Ratio definition: underlying units per warrant.
7. Quotation currency belongs to WarrantListing.
8. Administrative active/inactive is separate from maturity.
9. Provider mapping remains a follow-up gap; no silent FT-001 contract change.

## User-impact summary
The administration workflow distinguishes product, contractual terms and venue listings. Master-data references are selected instead of duplicated. Terms corrections create history. Provider automation is intentionally absent until its semantics are proven.
