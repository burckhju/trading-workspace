# ADR-S5-010 – Deterministic top-down E2E fixture before live credentials

## Status
Accepted for Sprint 5 V1.

## Context
The production top-down path is ready for semantic references, provider mappings, persisted daily prices, completed FT-006 analyses and automatic Candidate evaluation. A true EODHD smoke run additionally requires operator credentials and validated provider instruments, which are intentionally unavailable in deterministic CI.

## Decision
1. Add a deterministic integration fixture that produces provider-shaped EOD daily prices for a broad market, sector reference and underlying.
2. Feed those rows through the existing `DailyPriceImportService` contract and the existing FT-006 `EOD_TREND_MOMENTUM 1.0.0` calculator.
3. Use the approved `MARKET_CONTEXT 1.0.0`, `RELATIVE_STRENGTH 1.0.0` and `TOP_DOWN_CANDIDATE 1.0.0` domain models without alternate test-only calculations.
4. The fixture must prove one complete positive LONG path: favorable market, sector outperforming market, underlying outperforming sector, and `QUALIFIED` Candidate result.
5. The fixture remains test/operator tooling only. It is not a production provider and must never be selectable by runtime dependency injection.
6. `scripts/top_down_fixture_smoke.py` is the credential-free operator entry point. `scripts/top_down_live_smoke.py` remains the authoritative live-environment smoke path.

## Consequences
- CI can prove that the approved top-down models compose correctly even without EODHD credentials.
- The live smoke test is reduced to configuration/provider verification rather than discovering basic model-integration defects.
- No mock-provider behavior leaks into production domain or provider configuration.
