# ADR-S6-007 – TradePlan Provenance and Snapshot Policy

Status: Accepted – Sprint 6

## Context

Die spätere Entscheidungskette muss CandidateEvaluation → TradePlanVersion → Product Selection → Execution reproduzieren können, ohne FT-005/FT-006-Fachlogik zu kopieren.

## Decision

Jede TradePlanVersion speichert ihre eigenen versionierten Eingaben, Actor, Zeitpunkte, Lifecycle-/Approval-Kontext und Vorgängerbezug. Candidate-originated TradePlans referenzieren die konkrete immutable CandidateEvaluation; deren gespeicherte Analyse-IDs und Modellversionen bleiben Source of Truth.

FT-007 berechnet Market Context, Relative Strength, Trend, Momentum oder Candidate Qualification nicht neu. Bestehende Audit-/Request-Identity-Infrastruktur wird wiederverwendet.

## Consequences

- Provenance bleibt transitiv und ohne Datenkopien nachvollziehbar.
- Keine zweite Analyse- oder Audit-Wahrheit entsteht in FT-007.
- Historische TradePlanVersionen sind unabhängig von späteren Re-Evaluationen interpretierbar.
