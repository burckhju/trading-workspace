# ADR-S2-001 – Persistiertes Workspace-Referenzobjekt

## Status

Accepted – 2026-08-03

## Kontext

ADR-S1-004 verlangt für Version 1 genau einen technisch angelegten, in der UI unsichtbaren Workspace sowie eine konsistente Workspace-Zuordnung aller workspacegebundenen Fachobjekte. Für das physische Datenmodell war noch festzulegen, ob der Workspace nur als Anwendungskonstante oder als persistiertes Referenzobjekt geführt wird.

## Entscheidung

Der Version-1-Workspace wird als persistiertes technisches Referenzobjekt in der Tabelle `workspaces` geführt.

- Die Workspace-ID ist eine unveränderliche UUID.
- Der initiale Version-1-Workspace wird migrationsseitig mit einer festen, dokumentierten UUID angelegt.
- Workspacegebundene Tabellen referenzieren `workspaces.id` über einen nicht-nullbaren Foreign Key.
- Der Version-1-Workspace darf durch FT-001 weder angelegt, geändert noch gelöscht werden.
- Der Workspace bleibt vollständig unsichtbar; es gibt keine Auswahl oder Verwaltung in der Benutzeroberfläche.
- Fehlt der technische Workspace, dürfen keine workspacegebundenen Schreiboperationen durchgeführt werden.

## Konsequenzen

- Die Datenbank verhindert unbekannte Workspace-Zuordnungen.
- Eindeutigkeitsregeln können verbindlich innerhalb des Workspace formuliert werden.
- Alle Audit-Events und FT-001-Aggregate referenzieren denselben Datenraum.
- Eine spätere Mehr-Workspace-Erweiterung kann das bestehende Identitätsmodell erweitern, statt es zu ersetzen.
- Migration und Systemstart müssen die Existenz des Version-1-Workspace sicherstellen.

## Nutzerwirkung

Es entsteht keine zusätzliche Bedienhandlung. Der Nutzer sieht weder Workspace-Auswahl noch Workspace-Verwaltung. Er profitiert indirekt von konsistenten Suchergebnissen, Dublettenprüfungen und Historienzuordnungen.

## Verbindliche Implementierungskonkretisierung Sprint 2

Für die initiale Migration gelten folgende feste Werte:

- Workspace-ID: `00000000-0000-4000-8000-000000000001`
- Technischer Name: `Trading Workspace V1`

Diese Werte sind installationsübergreifend stabil. Der Name ist weiterhin nicht Bestandteil der Benutzeroberfläche.
