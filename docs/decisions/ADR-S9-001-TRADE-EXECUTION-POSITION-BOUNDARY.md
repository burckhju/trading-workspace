# ADR-S9-001 – Trade, ExecutionRecord and Position Boundary

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
FT-009 models `Trade`, `ExecutionRecord` and `Position` as separate concepts.

V1 uses one Position per Trade and one or more effective PURCHASE ExecutionRecords per Trade/Position.

A Trade is the stable identity of the real trading case. An ExecutionRecord is an immutable historical execution fact. A Position is the derived current holding state.

`Trade = ExecutionRecord`, `ExecutionRecord = Position` and `Order = Position` are prohibited models.

## Consequences
Additional purchases create additional immutable ExecutionRecords while keeping the same Trade and Position. Later position changes never rewrite earlier execution history.

## User impact
The user can see what was actually purchased at each point in time while still seeing one understandable current position.
