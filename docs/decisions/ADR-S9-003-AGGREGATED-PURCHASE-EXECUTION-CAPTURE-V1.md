# ADR-S9-003 – Aggregated Purchase Execution Capture V1

## Status
Accepted for Sprint 9 specification after S9-00 review.

## Decision
Sprint 9 V1 records an aggregated user-confirmed purchase execution using quantity and actual average purchase price per unit.

Individual broker order objects, order lifecycle and broker fill legs are not required in V1.

The system calculates gross amount and stores execution time separately from recording time.

## Consequences
The V1 workflow remains low-input and broker-neutral. Future broker/fill detail can be added without redefining the historical aggregated execution fact.

## User impact
The normal purchase form requires quantity and actual purchase price; execution time is changed only when backdating is necessary.
