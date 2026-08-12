# ADR-S6-008 – LONG-only Scope for TradePlan V1

Status: Accepted – Sprint 6

## Context

Candidate Model 1.0 ist LONG-only. SHORT darf nicht implizit durch Spiegelung der LONG-Regeln eingeführt werden. Für manuell erzeugte TradePlans war die Richtungsgrenze noch offen.

## Decision

FT-007 V1 ist vollständig LONG-only, sowohl Candidate-originated als auch Manual-originated. `direction` bleibt ein explizites versioniertes Domainfeld mit dem einzigen zulässigen V1-Wert `LONG`.

SHORT benötigt eine eigene spätere Fachentscheidung, inklusive Entry-/Stop-/Target-/Risk-Validierungen und gegebenenfalls eigener Candidate-Modelle.

## Consequences

- V1 besitzt konsistente Validierungen.
- Kein impliziter SHORT-Support entsteht.
- Die spätere Erweiterung bleibt durch das explizite Direction-Feld möglich.
