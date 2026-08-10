# ADR-S5-003 – Candidate Evaluation Snapshots and User Lifecycle

Status: Accepted – Sprint 5

## Decision

A Candidate is a long-lived user workflow object per workspace+underlying. Each re-evaluation creates an immutable, incrementing `CandidateEvaluation` version with model ID/version, qualification, quality, criterion results and explicit source provenance.

System qualification (`QUALIFIED`, `NOT_QUALIFIED`, `NOT_EVALUABLE`) is separate from user lifecycle (`IDENTIFIED`, `UNDER_REVIEW`, `WATCHING`, `READY_FOR_PLANNING`, `REJECTED`). `READY_FOR_PLANNING` does not create or approve a TradePlan. Rejection requires an explicit reason.

Candidate Model V1 has no aggregate score. REQUIRED rules decide qualification, WARNING rules are visible but non-blocking, and INFORMATIONAL rules are descriptive only. Realized volatility and range position are informational in V1; momentum and short-term trend are warnings.
