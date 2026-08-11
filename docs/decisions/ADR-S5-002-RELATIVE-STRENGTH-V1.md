# ADR-S5-002 – Relative Strength Model 1.0

Status: Accepted – Sprint 5

## Decision

`RELATIVE_STRENGTH 1.0.0` compares aligned 60-trading-day returns:

`relative_performance = subject_return - reference_return`

Classification uses a ±2 percentage-point neutral zone:

- `> +0.02`: `POSITIVE`
- `-0.02 … +0.02`: `NEUTRAL`
- `< -0.02`: `NEGATIVE`

Sector-vs-market and underlying-vs-sector relative strength are REQUIRED in `TOP_DOWN_CANDIDATE 1.0.0`. For LONG V1 they must be `POSITIVE`. Inputs with fewer than 61 aligned observations are `NOT_EVALUABLE`.

The model is intentionally simple and explainable. Ratio-trend and multi-window variants are deferred to later model versions.
