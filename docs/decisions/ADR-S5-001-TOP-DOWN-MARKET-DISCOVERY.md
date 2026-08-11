# ADR-S5-001 – Top-down Market Discovery Architecture

Status: Accepted – Sprint 5

## Decision

Candidate qualification follows `market → sector → underlying → candidate`. Market, sector, relative-strength and underlying analysis belong to FT-006/Market Analysis. FT-005 Candidate Management consumes versioned results and does not recalculate price-derived analysis.

`MARKET_CONTEXT 1.0.0` uses the primary benchmark. For LONG, positive long+medium trend is structural support; a negative short trend downgrades the context to `CAUTIOUS`. A negative long or medium trend is `UNFAVORABLE`. `FAVORABLE` and `CAUTIOUS` satisfy Candidate Model V1, with a warning for `CAUTIOUS`.

The initial benchmark roles are DAX as Germany broad-market context, S&P 500 as US broad-market context, and Nasdaq-100 as secondary US growth/technology context. Concrete provider/index-series adapters are outside FT-005 and must not be hard-coded into candidate rules.
