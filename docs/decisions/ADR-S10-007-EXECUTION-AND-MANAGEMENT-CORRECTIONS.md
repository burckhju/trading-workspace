# ADR-S10-007 – Execution and Management Correction Semantics

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
ADR-S9-005 already requires immutable execution corrections, but the released implementation does not yet persist the full effectiveness relation. FT-010 introduces SELL and management history, increasing the impact of factual recording errors.

## Decision
A confirmed historical record is never silently overwritten when correcting a factual mistake.

For ExecutionRecord corrections:

- original record remains stored,
- a traceable replacement/correction relation is created,
- only effective records contribute to Position/P&L projection,
- derived state is rebuilt from effective history.

For TradeManagementEvent corrections, the same historical principle applies where an already confirmed event must be factually corrected: the original remains auditable and the effective replacement is explicit.

Correction is distinct from deleting a draft before confirmation.

## Consequences
Persistence must model effectiveness/supersession without breaking released FT-009 data. Repository contracts must support effective-history queries and audit retrieval of superseded records.

Tests must prove that corrections cannot create impossible intermediate Position states or erase original facts.

## User impact
If the user corrects a wrongly entered quantity, price, stop or management fact, the current view becomes correct while the audit history still shows what was originally recorded and how it was corrected.
