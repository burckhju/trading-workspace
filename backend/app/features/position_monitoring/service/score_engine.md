# POSITION_SCORE_V1

`TrendScore` and `PeakScore` are deterministic, read-only 0-100 projections over existing `POSITION_ANALYTICS_V1` inputs. They do not create new market-data or execution truth and do not mutate stops, alerts, positions, or orders.

## TrendScore

Five transparent components contribute 20 points each: at least 10 completed post-entry sessions, latest price above SMA20, SMA20 above SMA50, SMA50 above SMA200, and RSI14 at least 50.

## PeakScore

Four transparent components contribute 25 points each: full trend structure (`latest > SMA20 > SMA50 > SMA200`), at least 10 completed post-entry sessions, RSI14 at least 70, and latest price within one ATR14 below `HighestHighSinceEntry`. A latest price above the recorded completed-session peak does not satisfy the near-peak component because the evaluation-day candle is intentionally excluded from `HighestHighSinceEntry`.

## Data health

Scoring is fail-closed. If position analytics are unavailable, stale, insufficient, missing, or erroneous, scores are not emitted. The response preserves the upstream quality status and reason.

## Scope

This policy is an explainable foundation only. It does not define Dynamic Stop behavior, stop mutation, sell recommendations, alerts, or execution automation.
