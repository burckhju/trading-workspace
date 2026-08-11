# ADR-S5-009 – Top-down live readiness and EODHD reference hints

## Status
Accepted for Sprint 5 V1.

## Context
The semantic top-down model is provider-neutral, while a real end-to-end run requires analyzable listings, active provider mappings, sufficient EOD history and a completed FT-006 analysis for every market/sector reference. The application must make missing operational prerequisites visible without moving EODHD symbols into domain logic.

## Decision
1. Provider-specific symbol hints live below `app/providers/eodhd/` and are administration metadata only.
2. The existing provider-mapping validation remains mandatory before activation.
3. Public EODHD documentation verified for this implementation identifies:
   - DAX: `GDAXI.INDX`
   - S&P 500: `GSPC.INDX`
4. No unambiguous Nasdaq-100 EODHD index ticker was established by the project verification. `NASDAQ100` therefore has no default provider symbol and must be resolved through the EODHD Search API and validated administratively. An ETF proxy must not be substituted silently.
5. `/api/v1/top-down-reference-data/readiness` reports, per semantic reference:
   - active listing assignment,
   - EODHD provider mapping and activation state,
   - at least 61 persisted daily prices (needed for the V1 60-trading-day relative-strength return),
   - a completed FT-006 analysis.
6. `scripts/top_down_live_smoke.py` provides an operator-run smoke path. It refuses to trigger Candidate evaluation while any configured reference reports blockers.

## Consequences
- Live configuration failures are observable before Candidate qualification.
- Provider codes remain replaceable and cannot leak into Candidate rules.
- Nasdaq-100 remains explicitly incomplete until provider validation supplies an exact index instrument.
- Real network calls are not part of deterministic CI; CI tests the readiness and orchestration contracts with controlled data.
