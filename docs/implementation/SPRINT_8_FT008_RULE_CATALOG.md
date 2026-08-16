# Sprint 8 / FT-008 – V1 Rule Catalog

## Status
Architecture/rule closure before production implementation.

## 1. Entry contract

A ProductSelectionRun requires:

- one existing TradePlan;
- one exact TradePlanVersion belonging to that plan;
- status `APPROVED`;
- the TradePlan underlying as the authoritative underlying context.

Draft, ready-for-review or otherwise non-approved versions are rejected. FT-008 never changes the TradePlanVersion.

## 2. Product universe V1

Universe construction is deterministic and separate from eligibility.

A V1 universe candidate must:

1. be an FT-004 `Warrant` in the same workspace;
2. reference the same `underlying_id` as the TradePlan;
3. use `ProductFamily.WARRANT` (the only FT-004 V1 family);
4. resolve an exact effective `WarrantTermsVersion` at the run evaluation time;
5. expose at least one concrete `WarrantListing` context to evaluate.

FT-008 records which exact terms version and listing were considered. It does not create missing Warrants, Issuers, Underlyings, Venues, Terms or Listings.

### Direction

TradePlan V1 is LONG-only. FT-004 supports CALL and PUT, but the repository contains no approved FT-008 rule that equates LONG automatically with CALL for every strategy. Therefore direction compatibility is an explicit eligibility/model rule and is **not** hidden in universe construction.

## 3. Eligibility V1

Eligibility produces an explicit result per considered product context. Initial rule categories are:

- product/reference lifecycle usability;
- terms validity at `evaluated_at`;
- direction compatibility with the approved TradePlan/model;
- maturity validity at `evaluated_at`;
- listing/tradability context availability;
- required market-data availability and quality for quote-dependent rules.

A failed rule produces an exclusion reason. A rule that cannot be evaluated because required data is absent produces a missing/insufficient-data result; it must not silently pass.

### No invented thresholds

The current repository does not define approved numeric FT-008 thresholds for:

- minimum/maximum remaining maturity;
- strike or moneyness corridor;
- spread;
- price;
- volume/liquidity;
- leverage/omega;
- delta or other Greeks;
- implied volatility;
- issuer preference/concentration.

These values therefore remain **UNSPECIFIED** until an explicit model version is approved. Production code must not invent defaults.

## 4. Evaluation V1

Each ProductEvaluation must preserve at least:

- ProductSelectionRun identity;
- `warrant_id`;
- `warrant_terms_version_id`;
- `warrant_listing_id`;
- evaluation timestamp;
- eligibility/evaluation model ID and version;
- input values and their provenance;
- parameters/rules applied;
- criterion outcomes;
- missing-data reasons;
- calculated metrics, with formula/rule identity;
- provider metrics clearly labelled as provider-supplied;
- overall eligibility/evaluation status and reasons.

No internal Black-Scholes, IV solver or Greeks engine is part of V1.

## 5. Missing-data and quality semantics

FT-008 distinguishes at minimum:

- `AVAILABLE` – required value is present with acceptable provenance;
- `MISSING` – required value is absent;
- `INSUFFICIENT` – data exists but is not sufficient for the rule/evaluation;
- `NOT_APPLICABLE` – the criterion does not apply to this evaluation.

The final names may reuse an existing shared enum only if semantics match exactly. Missing or insufficient data must remain visible in API/UI and in historical evaluation records.

## 6. User selection

ProductSelection is an explicit user action against an existing ProductEvaluation in the same run.

The system must not create ProductSelection from:

- highest score;
- first sort position;
- only remaining eligible product;
- provider recommendation;
- previous run selection.

A user may also finish/review a run without selecting a product. Selection rationale may be captured, but V1 must not require the user to reproduce technical provenance manually.

## 7. Run and amendment semantics

Multiple runs may exist for one approved TradePlanVersion. Each run is historically independent.

A TradePlan amendment/new version does not migrate prior evaluations or selections. A new approved version receives a new run when product selection is required.

## 8. Current implementation blocker

Quote-dependent eligibility/evaluation cannot be production-complete until TC-001 exposes a provider-neutral WarrantListing market-data contract with source/time/quality/snapshot semantics. Existing FT-001 provider mappings must not be repurposed silently.

Reference-data-only domain/persistence work may proceed independently where it does not pretend that quote-dependent evaluation is available.

## 9. Definition of Ready for production domain code

Ready now:

- aggregate and identity boundaries;
- approved TradePlanVersion handoff;
- historical terms/listing references;
- universe vs eligibility separation;
- explicit user-selection boundary;
- missing-data principle;
- prohibition on invented numeric thresholds.

Still requires explicit model approval before implementation of numeric scoring/filtering:

- maturity thresholds;
- strike/moneyness rules;
- spread/liquidity rules;
- price/leverage/Greek/IV rules;
- score/ranking formula and weights.

## 10. User impact

The first FT-008 implementation can provide a transparent, historically reproducible selection workflow without pretending that unapproved thresholds or unavailable warrant quotes exist. Users will see considered products, exclusions and missing data separately, and will make the final product choice themselves.
