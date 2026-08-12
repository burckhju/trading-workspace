# Sprint 6 – FT-007 Specification and Definition-of-Ready Review

## Status

Approved for Build – 2026-08-11.

## Ausgangsbasis

Geprüft wurden Sprint-5-Repository-Stand, Product Backlog, Module & Feature Catalog, Requirements, Model Book, Traceability, Domain Map, Trading Process Model, Architecture Index, FT-005/FT-006-Dokumentation, Sprint-5-ADRs sowie die nachgelieferte `SPRINT_6_TRANSITION_BASELINE.md`.

Die zuvor fehlende Transition-Baseline ist nun im Repository synchronisiert. Sie ist Approved und nennt `v0.5.0-candidate-qualification` als Ausgangsrelease.

## Accepted Architecture Baseline

1. `TradePlan` ist die langlebige Aggregate-Identität.
2. `TradePlanVersion` ist ein immutable fachlicher Snapshot.
3. Candidate-originated referenziert Candidate + konkrete immutable CandidateEvaluation.
4. Manual-originated referenziert ein Underlying.
5. FT-007 V1 ist vollständig LONG-only.
6. Lifecycle: DRAFT → READY_FOR_REVIEW → APPROVED; zusätzlich ABANDONED und SUPERSEDED.
7. Approval ist versionsgenau, explizit und auditierbar.
8. Änderungen nach Approval erzeugen neue DRAFT-Versionen.
9. Entry, Invalidation, Targets und Risk Assumptions sind produktneutral.
10. FT-007 erzeugt keine Position Size, Order Quantity oder Execution.
11. FT-005/FT-006-Berechnungen werden nicht dupliziert.
12. Bestehende Audit-, Provenance-, Repository-, UoW-, API-, DI- und Frontend-Patterns werden wiederverwendet.

## Definition of Ready

| Kriterium | Status | Nachweis |
|---|---|---|
| Nutzerproblem und Nutzen beschrieben | ✅ | `FT-007_TRADEPLAN.md` |
| Scope / Non-Scope freigegeben | ✅ | Feature Spec + Transition Baseline |
| Aggregate Ownership | ✅ | ADR-S6-001 |
| Identity / Versioning | ✅ | ADR-S6-001 |
| CandidateEvaluation Handoff | ✅ | ADR-S6-002 |
| Manueller Ursprung | ✅ | ADR-S6-002 |
| LONG-only Scope | ✅ | ADR-S6-008 |
| Lifecycle | ✅ | ADR-S6-003 |
| Approval | ✅ | ADR-S6-003 |
| Amendment | ✅ | ADR-S6-004 |
| Entry | ✅ | Feature Spec |
| Stop / Invalidation | ✅ | Feature Spec |
| Targets | ✅ | Feature Spec |
| Risk Boundary | ✅ | ADR-S6-005 |
| Position Sizing Non-Scope | ✅ | ADR-S6-005 |
| Product Neutrality | ✅ | ADR-S6-006 |
| Provenance / Snapshot | ✅ | ADR-S6-007 |
| Audit | ✅ | Feature Spec + ADR-S6-007 |
| ADRs Accepted | ✅ | ADR-S6-001…008 |
| Testbare Akzeptanzkriterien | ✅ | Feature Spec |
| Blockierende Fachentscheidungen | ✅ keine | Review 2026-08-11 |

## Architekturkorrektur aus S6-01

Die frühere Domain-Map-Formulierung, ein TradePlan könne später einen Warrant referenzieren, wird korrigiert. Product Selection gehört FT-008 und referenziert die konkrete Approved-TradePlanVersion; der TradePlan bleibt produktneutral.

## Nächste Implementation Unit

`S6-02 TradePlan Domain`:

- Domain Types / Enums;
- TradePlan und TradePlanVersion Aggregate-Verhalten;
- EntryPlan, InvalidationPlan, Target, RiskAssumptions;
- Lifecycle- und Approval-Validierungen auf Domain-Ebene;
- Amendment-Regeln;
- reine Unit Tests ohne Persistence/API.

Migration, Repository, API und Frontend bleiben für S6-02 weiterhin Non-Scope.
