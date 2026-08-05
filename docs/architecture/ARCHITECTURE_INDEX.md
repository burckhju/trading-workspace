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

-   `adr/` -- Alle akzeptierten ADRs

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
