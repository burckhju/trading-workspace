# ADR-S6-001 – TradePlan Identity and Versioning

Status: Accepted – Sprint 6

## Context

FT-007 benötigt eine langlebige Planidentität und gleichzeitig unveränderbare historische Entscheidungsstände. Approved-Pläne müssen später von Product Selection und Learning referenziert werden können.

## Decision

`TradePlan` ist die langlebige Aggregate-Identität. Fachliche Planinhalte liegen in monoton nummerierten, immutable `TradePlanVersion`-Snapshots. Thesis, Direction, Entry, Invalidation, Targets und Risk Assumptions gehören zur Version. Workspace, Underlying und Origin gehören zur langlebigen Identität.

Ein historischer Versions-Snapshot wird nicht in-place geändert. Concurrency wird nach bestehendem Repository-/Optimistic-Locking-Muster abgesichert.

## Consequences

- Historische Entscheidungen sind stabil referenzierbar.
- Product Selection kann eine konkrete Approved-Version referenzieren.
- Änderungen erzeugen zusätzliche Versionen statt Updates historischer Inhalte.
- Persistenz benötigt getrennte Identitäts- und Versionstabellen.
