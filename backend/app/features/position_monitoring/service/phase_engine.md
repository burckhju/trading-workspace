# Position Phase V1

`POSITION_PHASE_V1` is a deterministic, read-only projection over existing position-aware analytics.
It does not persist phase state and does not mutate stops, alerts, executions, or positions.

## Policy

- `BUILDING`: fewer than 3 completed post-entry sessions, or short trend structure is not yet confirmed.
- `CONFIRMED`: at least 3 sessions and `latest_price > SMA20 > SMA50`.
- `TREND`: at least 10 sessions, `latest_price > SMA20 > SMA50 > SMA200`, and RSI14 >= 50.
- `PEAK_PROTECTION`: TREND requirements plus RSI14 >= 70 and latest price is no more than 1 ATR14 below `HighestHighSinceEntry`.

The engine consumes only `POSITION_ANALYTICS_V1` metrics plus the position-aware `HighestHighSinceEntry` and completed-session count. Unavailable, stale, insufficient, missing, or invalid inputs fail closed and return no phase.

The thresholds above are the explicit V1 policy contract. Later TrendScore/PeakScore work may supersede the rule representation, but must do so under a new policy version rather than silently changing V1 semantics.
