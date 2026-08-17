# ADR-S10-005 – TradeManagementEvent Boundary and V1 Event Types

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
The Domain Map assigns Trade Event ownership to FT-010. The Trading Process Model requires immutable management history, while actual sales are economic executions. Combining both semantics in one generic event class would create ambiguity and risk duplicate economic truth.

## Decision
`TradeManagementEvent` is separate from `ExecutionRecord`.

V1 management-event types are:

- `STOP_CHANGED`
- `TARGET_CHANGED`
- `THESIS_UPDATED`
- `MANAGEMENT_NOTE`

BUY and SELL are ExecutionRecords and are not persisted again as independent economic TradeManagementEvents.

A read model/UI timeline may merge both streams chronologically for presentation.

Management events never rewrite TradePlanVersion, ProductSelection or historical execution facts.

Product change is not a V1 management-event type.

## Consequences
FT-010 requires its own event domain/persistence/repository contract while preserving shared audit/UoW conventions. Typed event payload validation is required; an unvalidated arbitrary payload is insufficient for core event semantics.

## User impact
The user gets one understandable timeline of what actually happened and how the trade was managed, while planned values and real executions remain distinguishable.
