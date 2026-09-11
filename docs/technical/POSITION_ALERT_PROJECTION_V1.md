# Position Alert Projection V1

`POSITION_ALERT_V1` is a read-only operational attention projection built on `DYNAMIC_STOP_V1`.

It distinguishes critical stop breaches, peak-protection attention, normal state, and fail-closed upstream data health. It does not persist Alert records, mutate stops, recommend a sale, or automate execution.

The Operational Workspace renders the projection in German while API enum values remain stable for technical consumers.
