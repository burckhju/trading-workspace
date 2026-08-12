# ADR-S6-004 – Amendment after Approval

Status: Accepted – Sprint 6

## Context

Entry, Stop, Target, Thesis oder Risikoannahmen können sich nach Approval ändern. Historische Approved-Stände dürfen nicht überschrieben werden.

## Decision

Ein Approved-Snapshot ist unveränderbar. Jede fachliche Änderung erzeugt eine neue DRAFT-Version mit `previous_version_id` und verpflichtendem `change_reason` bei Amendment aus einem Approved-Stand.

Die Amendment-Version benötigt ein neues explizites Approval. Wird sie Approved, bleibt der frühere Approved-Stand historisch erhalten und wird als superseded sichtbar.

## Consequences

- Historische Freigaben bleiben reproduzierbar.
- Änderungsgründe sind nachvollziehbar.
- Nachgelagerte Features müssen konkrete TradePlanVersionen statt nur die TradePlan-ID referenzieren.
