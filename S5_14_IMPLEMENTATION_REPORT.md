# S5.14 – Deterministic first complete top-down E2E path

## Implemented
- Added `tests/integration/backend/test_top_down_fixture_e2e.py`.
- The fixture creates provider-shaped EOD daily prices for a broad-market reference, a sector reference and an underlying.
- The fixture invokes the existing `DailyPriceImportService` contract for all three subjects.
- Imported data is passed through the existing FT-006 `EOD_TREND_MOMENTUM 1.0.0` calculation.
- The approved `MARKET_CONTEXT 1.0.0` is calculated from the market analysis.
- `RELATIVE_STRENGTH 1.0.0` is calculated for Sector vs Market and Underlying vs Sector.
- The results are passed to `TOP_DOWN_CANDIDATE 1.0.0` and produce a deterministic `QUALIFIED` LONG result.
- Added `scripts/top_down_fixture_smoke.py` as a credential-free operator smoke command.
- Added ADR-S5-010. Fixture/provider code remains test-only and cannot be selected by production DI.

## Tests
- Deterministic top-down fixture smoke: passed.
- Backend unit + integration suite: 227 passed.
- Python compile/import check: passed.
- Ruff: not available in this packaged environment; not reported as passed.

## Open operational dependency
A true EODHD end-to-end run still requires operator credentials and validated provider mappings for the selected broad-market, sector and underlying instruments. `scripts/top_down_live_smoke.py` remains the authoritative live smoke path.

## Next recommended unit
S5.15: live-configuration runbook + automated preparation/status workflow for one concrete US path (S&P 500 → validated Technology sector reference → one US underlying), ending with a live smoke invocation once credentials/mappings exist.
