# ADR-S5-012 – Actionable Live Workflow

## Status
Accepted for Sprint 5 V1.

## Context
S5.15 exposed a read-only Candidate live-workflow with explicit `next_action` values. Operators still had to translate those action codes manually into unrelated administration endpoints. That created avoidable friction and risked duplicating semantic resolution logic in the frontend.

## Decision
Each blocked workflow step may expose structured `action_params` containing only identifiers already resolved by the backend. The Candidate UI deep-links to a dedicated top-down workflow administration page. That page invokes existing explicit administration APIs for assignments, provider mappings, price imports and FT-006 analysis runs.

No action is executed automatically. Provider symbols, listing choices, date ranges and semantic assignments remain explicit operator decisions. Missing primary listings deep-link to the existing underlying administration instead of introducing a second listing editor.

Inactive market references and sectors can be explicitly reactivated through dedicated administration endpoints. Reassignment remains a separate historized action and is not silently performed by reactivation.

## Consequences
- The frontend does not reproduce source-resolution rules.
- Every `next_action` has an actionable UI path.
- Provider symbols continue to require explicit entry/validation.
- Candidate evaluation remains disabled until the live workflow reports readiness.
- Historical assignments remain explicit; no hidden overlap replacement is introduced.
