# ADR-S6-005 – Risk / Position-Sizing Boundary

Status: Accepted – Sprint 6

## Context

TradePlan benötigt Risikoannahmen, darf aber keine autonome Positionsgrößen- oder Orderentscheidung einführen.

## Decision

FT-007 darf Plan-Risikoannahmen speichern, validieren und transparente arithmetische Ableitungen anzeigen. FT-007 erzeugt keine Position Size, Portfolio Allocation, Order Quantity oder Execution-Entscheidung.

## Consequences

- Risiko bleibt Bestandteil der Planung, nicht der Ausführung.
- Spätere Decision-Support-/Position-Sizing-Funktionen benötigen eine eigene Spezifikation und Governance.
