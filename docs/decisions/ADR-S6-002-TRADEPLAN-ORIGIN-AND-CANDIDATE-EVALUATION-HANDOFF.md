# ADR-S6-002 – TradePlan Origin and CandidateEvaluation Handoff

Status: Accepted – Sprint 6

## Context

Ein TradePlan kann aus FT-005 oder direkt aus einem Underlying entstehen. Candidate-Re-Evaluationen dürfen bestehende Pläne nicht verändern.

## Decision

TradePlan besitzt `origin_type = CANDIDATE_EVALUATION | MANUAL`.

Bei Candidate-Ursprung werden Candidate-ID und konkrete immutable CandidateEvaluation-ID am TradePlan festgehalten. Die Evaluation muss zum Candidate, Workspace und Underlying passen. Eine spätere Re-Evaluation wird nicht automatisch übernommen.

Bei manuellem Ursprung wird ausschließlich das Underlying referenziert; Candidate-Referenzen bleiben leer.

## Consequences

- FT-005 und FT-007 bleiben lose gekoppelt.
- Provenance ist reproduzierbar.
- Es gibt kein `latest CandidateEvaluation`-Lookup zur historischen Interpretation eines TradePlans.
