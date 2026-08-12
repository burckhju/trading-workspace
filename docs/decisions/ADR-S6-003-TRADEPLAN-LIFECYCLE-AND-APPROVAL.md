# ADR-S6-003 – TradePlan Lifecycle and Approval

Status: Accepted – Sprint 6

## Context

`READY_FOR_PLANNING` aus FT-005 ist keine TradePlan-Freigabe. FT-007 benötigt daher einen eigenen Benutzer-Lifecycle mit explizitem Approval.

## Decision

V1 verwendet `DRAFT`, `READY_FOR_REVIEW`, `APPROVED`, `ABANDONED` und `SUPERSEDED`. `REJECTED` wird ohne getrennte Reviewer-Rolle nicht eingeführt.

Approval ist eine explizite Benutzeraktion auf genau eine immutable TradePlanVersion und speichert Actor, Zeitpunkt und Audit-Kontext. Automatisches Approval ist verboten.

Zulässige Kernübergänge sind DRAFT → READY_FOR_REVIEW, READY_FOR_REVIEW → APPROVED, READY_FOR_REVIEW → DRAFT sowie Abandon aus nicht finalisierten Zuständen. Amendment eines Approved-Plans erzeugt eine neue DRAFT-Version.

## Consequences

- Benutzerentscheidung bleibt klar vom Systemstatus getrennt.
- Approval ist versionsgenau auditierbar.
- Lifecycle bleibt für V1 klein und testbar.
