# ADR-S8-003 – Product Universe and Eligibility

## Status
Accepted for Sprint 8 after S8-00 review.

## Decision
Product-universe construction and eligibility evaluation are separate model steps.

The V1 universe starts from FT-004 warrants for the TradePlan underlying and records the exact terms/listing context considered. Eligibility rules are explicit, versioned and auditable; a product must not silently disappear because an eligibility criterion failed.

No numeric maturity, spread, leverage, moneyness, Greek, issuer or price threshold is introduced without an approved model rule in the Model Book.

## User impact
The user can distinguish “not considered” from “considered but excluded” and can see the reason for each exclusion. Thresholds will not change invisibly in implementation code.
