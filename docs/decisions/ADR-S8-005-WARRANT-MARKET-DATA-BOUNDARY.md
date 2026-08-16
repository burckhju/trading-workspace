# ADR-S8-005 – WarrantListing Market-Data Boundary

## Status
Accepted and consumer contract implemented in S8-07; provider-specific warrant mapping/adapter remains a follow-up gap.

## Decision
FT-008 market data is addressed for the concrete `WarrantListing` through TC-001/provider-neutral contracts. FT-008 must not reuse FT-001 provider mappings as if they were WarrantListing mappings and must not store provider identity in Warrant master data.

Market observations used by an evaluation require source, observation time, quality and reproducible snapshot/provenance semantics.

S8-07 defines a provider-neutral `WarrantListingQuoteProvider` contract with immutable bid/ask snapshots, source identity, observation time and quality. Provider-specific warrant mapping/discovery remains separate. When no valid snapshot is available, quote-dependent evaluation remains unavailable rather than fabricated or inferred.

## User impact
The application may initially mark quote-dependent criteria as unavailable instead of showing a misleading comparison. Once warrant market data is integrated, the user will see its source, timestamp and quality.
