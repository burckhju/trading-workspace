# Architecture Index

## Zweck

Dieses Dokument ist das zentrale Inhaltsverzeichnis der
Architektur-Dokumentation des Projekts **Trading Workspace**.

------------------------------------------------------------------------

## Architektur

### Domain Model

-   `domain/` -- Domänenmodell und fachliche Kernobjekte

### Trading Process

-   `process/` -- Trading-Prozessmodell

### Architecture Decision Records

-   `decisions/` -- Verbindliche Architecture Decision Records
-   `adr/` -- Legacy-Ablage; neue ADRs werden nicht mehr hier angelegt

### Reviews

-   `reviews/` -- Architekturreviews und Review-Protokolle

### Baselines

-   `baselines/`
    -   `SPRINT_1_ABSCHLUSSDOKUMENT.md`
    -   zukünftige Sprint-Baselines

------------------------------------------------------------------------

## Features

-   `features/underlying/` -- FT-001 Basiswertverwaltung
-   weitere Feature Books folgen in späteren Sprints

------------------------------------------------------------------------

## Roadmap

-   `roadmap/` -- Produkt-Roadmap und Sprintplanung

------------------------------------------------------------------------

## Gültigkeit

Die Sprint-1-Architecture-Baseline ist die verbindliche Referenz für
alle Implementierungen ab Sprint 2.

Architekturänderungen erfolgen ausschließlich über neue oder geänderte
ADRs und müssen mit den betroffenen Feature Books synchronisiert werden.


## Sprint-2-Entscheidungen

- `decisions/ADR-S2-001-PERSISTED-WORKSPACE.md`
- `decisions/ADR-S2-002-PERSISTED-REFERENCE-DATA.md`
- `decisions/ADR-S2-003-AUDIT-EVENT-PERSISTENCE.md`
- `features/underlying/PHYSICAL_DATA_MODEL.md`
- `features/underlying/SQLALCHEMY_MODEL.md`
- `features/underlying/ALEMBIC_MIGRATION.md`
- `features/underlying/REST_API.md`


## Sprint-5-Entscheidungen

- `decisions/ADR-S5-001-TOP-DOWN-MARKET-DISCOVERY.md`
- `decisions/ADR-S5-002-RELATIVE-STRENGTH-V1.md`
- `decisions/ADR-S5-003-CANDIDATE-EVALUATION-AND-LIFECYCLE.md`
- `decisions/ADR-S5-007-SEMANTIC-TOP-DOWN-SOURCE-RESOLUTION.md`
- `decisions/ADR-S5-008-TOP-DOWN-REFERENCE-ADMINISTRATION.md`
- `decisions/ADR-S5-009-TOP-DOWN-LIVE-READINESS-AND-EODHD-REFERENCE-HINTS.md`
- `decisions/ADR-S5-010-DETERMINISTIC-TOP-DOWN-E2E-FIXTURE.md`
- `decisions/ADR-S5-011-GUIDED-LIVE-CONFIGURATION-WORKFLOW.md`
- `decisions/ADR-S5-012-ACTIONABLE-LIVE-WORKFLOW.md`
- `features/FT-005_CANDIDATE_QUALIFICATION.md`
- `implementation/SPRINT_5_ARCHITECTURE_REVIEW_AND_GAP_CLOSURE.md`

## Sprint-6-Entscheidungen – FT-007 TradePlan

- `../planning/SPRINT_6_TRANSITION_BASELINE.md`
- `../features/FT-007_TRADEPLAN.md`
- `../decisions/ADR-S6-001-TRADEPLAN-IDENTITY-AND-VERSIONING.md`
- `../decisions/ADR-S6-002-TRADEPLAN-ORIGIN-AND-CANDIDATE-EVALUATION-HANDOFF.md`
- `../decisions/ADR-S6-003-TRADEPLAN-LIFECYCLE-AND-APPROVAL.md`
- `../decisions/ADR-S6-004-AMENDMENT-AFTER-APPROVAL.md`
- `../decisions/ADR-S6-005-RISK-POSITION-SIZING-BOUNDARY.md`
- `../decisions/ADR-S6-006-PRODUCT-NEUTRALITY.md`
- `../decisions/ADR-S6-007-PROVENANCE-AND-SNAPSHOT-POLICY.md`
- `../decisions/ADR-S6-008-LONG-ONLY-SCOPE.md`
- `../implementation/SPRINT_6_FT007_SPECIFICATION_AND_DOR_REVIEW.md`

- `../implementation/SPRINT_6_FT007_IMPLEMENTATION_TRACEABILITY.md`
- `../implementation/SPRINT_6_ARCHITECTURE_REVIEW.md`
- `../implementation/SPRINT_6_TECHNICAL_CLOSEOUT.md`


## Sprint-7A-Entscheidungen – FT-002 Trading Venues

- `../features/FT-002_TRADING_VENUES.md`
- `../decisions/ADR-S7-001-TRADING-VENUE-IDENTITY-SOURCE-OF-TRUTH-AND-RECONCILIATION.md`
- `../implementation/SPRINT_7A_FT002_ARCHITECTURE_REVIEW_AND_GAP_CLOSURE.md`
- `../implementation/SPRINT_7A_TECHNICAL_CLOSEOUT.md`

## Sprint 8 / FT-008 Product Selection

- `docs/decisions/ADR-S8-001-PRODUCT-SELECTION-RUN-AND-DECISION-BOUNDARY.md`
- `docs/decisions/ADR-S8-002-HISTORICAL-PRODUCT-REFERENCE.md`
- `docs/decisions/ADR-S8-003-UNIVERSE-AND-ELIGIBILITY.md`
- `docs/decisions/ADR-S8-004-TRADEPLAN-HANDOFF.md`
- `docs/decisions/ADR-S8-005-WARRANT-MARKET-DATA-BOUNDARY.md`
- `docs/decisions/ADR-S8-006-EVALUATION-AND-COMPARISON.md`
- `docs/decisions/ADR-S8-007-PROVIDER-CAPABILITY-AND-SELECTION-POLICY.md`
- `docs/implementation/SPRINT_8_FT008_RULE_CATALOG.md`

- S8-12 E2E and release-readiness evidence: `S8_12_IMPLEMENTATION_REPORT.md`
- FT-008 release-readiness gate: `docs/implementation/SPRINT_8_FT008_RELEASE_READINESS.md`
