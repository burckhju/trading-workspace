# DYNAMIC_STOP_V1

`DYNAMIC_STOP_V1` is a read-only, indicative stop projection. It does not create, amend, submit, persist, or execute a broker stop.

The candidate is anchored to `HighestHighSinceEntry` and subtracts an ATR14 multiple. Inputs come from the existing position-aware analytics, phase, and score contracts.

Base ATR multiples:

- `BUILDING`: 3.0 ATR
- `CONFIRMED`: 2.5 ATR
- `TREND`: 2.0 ATR
- `PEAK_PROTECTION`: 1.5 ATR

Score tightening:

- `TREND` with TrendScore >= 80: 1.5 ATR
- `PEAK_PROTECTION` with PeakScore >= 75: 1.0 ATR

The projection returns the candidate stop, selected ATR multiple, current analysis price, distance to candidate, and whether the current analysis price is already at or below the candidate.

Data health is fail-closed. Missing or inconsistent analytics, phase, score, provenance, non-positive ATR, or a non-positive stop candidate produce no stop value.

This policy is not an order instruction, sell recommendation, alert, or execution automation. Changes to thresholds require a new policy version.
