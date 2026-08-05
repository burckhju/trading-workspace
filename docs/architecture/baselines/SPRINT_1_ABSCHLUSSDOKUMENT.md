# Trading Workspace

# Sprint 1 Abschlussdokument

## Fachliche Architektur -- Architecture Baseline

**Projekt:** Trading Workspace\
**Sprint:** Sprint 1 -- Fachliche Architektur\
**Status:** Abgeschlossen\
**Freigabestatus:** Architecture Approved -- Approved for Build\
**Version:** 1.0\
**Datum:** 03.08.2026

------------------------------------------------------------------------

## 1. Ziel des Sprints

Sprint 1 hatte das Ziel, die fachliche Architektur des Trading Workspace
vollständig zu spezifizieren. Es wurde bewusst keine Implementierung
durchgeführt. Alle Architekturentscheidungen wurden vor der technischen
Umsetzung getroffen und dokumentiert.

## 2. Erreichte Ergebnisse

-   Domänenmodell
-   Trading-Prozessmodell
-   Moduldefinition
-   Fachliche Regeln
-   ADRs (Architecture Decision Records)
-   Feature Book FT-001 Basiswertverwaltung
-   Traceability
-   Architekturreview

## 3. Wesentliche Architekturentscheidungen

-   Architektur vor Implementierung
-   Fachliche Regeln vor technischem Design
-   Single Source of Truth
-   Keine doppelte Datenerfassung
-   Keine Blackbox
-   Vollständige Nachvollziehbarkeit
-   Dokumentation, APIs und Datenmodell bleiben synchron

### Fachliche Entscheidungen

-   Version 1 unterstützt Aktien als Basiswerte.
-   Version 1 unterstützt Optionsscheine als Produkte.
-   Basiswert und Börsennotierung sind getrennte fachliche Objekte.
-   FT-001 besitzt das Feature `underlying`.
-   Version 1 ist Single User / Single Workspace.
-   Referenzierte Basiswerte werden deaktiviert, nicht gelöscht.
-   UUID ist die technische Primäridentität.
-   Änderungen werden vollständig auditiert.

## 4. Beschlossene ADRs

-   ADR-S1-001 bis ADR-S1-013
-   Status aller ADRs: **Accepted**

## 5. Definition of Done

Sprint 1 gilt als abgeschlossen, weil:

-   Domänenmodell vollständig spezifiziert ist.
-   Fachliche Regeln dokumentiert sind.
-   Architekturentscheidungen getroffen wurden.
-   FT-001 vollständig spezifiziert ist.
-   Keine offenen Architekturblocker mehr bestehen.

## 6. Nicht Bestandteil von Sprint 1

-   Datenbankmodell
-   Alembic-Migrationen
-   REST-API
-   Backend-Implementierung
-   Frontend
-   Tests
-   Providerintegration

## 7. Übergabe an Sprint 2

Sprint 2 implementiert ausschließlich FT-001 auf Basis der freigegebenen
Architecture Baseline.

## 8. Architecture Baseline

Mit Abschluss von Sprint 1 werden eingefroren:

-   Domänenmodell
-   Trading-Prozessmodell
-   Moduldefinition
-   Fachliche Regeln
-   ADRs
-   FT-001 Feature Book

Diese Baseline ist die verbindliche Grundlage für alle folgenden
Sprints.

------------------------------------------------------------------------

**Freigabe:** Architecture Approved -- Approved for Build
