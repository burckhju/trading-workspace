# ADR-S9-004 – Position Derivation and Additional Purchases

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
An initial purchase creates the first open Position for a Trade. An additional purchase creates a new immutable PURCHASE ExecutionRecord and updates the same Position.

For effective purchase executions, position quantity, total cost and average entry price are derived deterministically using decimal arithmetic.

Fees, commissions, taxes and transaction costs are excluded from Sprint 9 V1 cost basis.

## Consequences
One Trade can accumulate multiple purchases without creating artificial duplicate positions. Historical purchase prices remain unchanged.

## User impact
The user can record a later purchase with the same minimal input and immediately see updated quantity and average entry price.
