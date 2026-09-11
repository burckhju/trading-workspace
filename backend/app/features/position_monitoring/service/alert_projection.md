# POSITION_ALERT_V1

Read-only operational attention projection over `DYNAMIC_STOP_V1`.

## Policy

- `CRITICAL`: dynamic stop is breached (`latest_price <= candidate_stop`).
- `ATTENTION`: no stop breach, but phase is `PEAK_PROTECTION`.
- `NORMAL`: dynamic stop is available and neither condition applies.
- unavailable upstream data fails closed and produces no alert level.

## Boundaries

This projection does not persist `Alert` truth, mutate stops, recommend a sale, create broker orders, or automate execution. Existing persisted alerts remain owned by the Alert feature.

## UI language

Technical API enums remain stable. User-facing labels in the Operational Workspace are German, including data-health states and position-signal explanations.
