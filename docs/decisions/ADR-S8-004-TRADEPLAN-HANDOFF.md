# ADR-S8-004 – Approved TradePlanVersion Handoff

## Status
Accepted for Sprint 8 after S8-00 review.

## Decision
A normal FT-008 ProductSelectionRun can start only from an `APPROVED` TradePlanVersion. FT-008 reads the immutable plan snapshot and never writes product attributes back into FT-007.

An amendment creates a new TradePlanVersion. Existing runs remain attached to the earlier version. A newly approved amended version requires a new run if product selection is needed.

## User impact
The user cannot accidentally select a product against a draft plan. If the approved plan changes, the application requires a fresh product evaluation instead of silently reusing an old selection.
