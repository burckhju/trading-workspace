# FT-001 – Alembic-Migration

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Implementierungsschritt | 3 – Alembic-Migration |
| Version | 1.0 |
| Status | Approved for Repository Implementation |
| Datum | 2026-08-03 |

## Architekturprüfung

Die Migration `20260803_0001_ft001_initial_schema.py` setzt ausschließlich das freigegebene physische Datenmodell und die SQLAlchemy-Mappings aus Schritt 1 und 2 um. Sie führt keine Repository-, Domain-, Service- oder API-Logik ein.

Die Migration ist die erste lineare Alembic-Revision des Projekts:

- Revision: `20260803_0001`
- Vorgänger: keiner
- Dialekt: PostgreSQL
- DDL: transaktional

## Angelegte Tabellen

Die Upgrade-Richtung erzeugt in referenziell sicherer Reihenfolge:

1. `workspaces`
2. `trading_venues`
3. `currencies`
4. `underlyings`
5. `listings`
6. `audit_events`

Alle Foreign Keys, Löschregeln, Checks, Unique Constraints, Suchindizes und partiellen Unique Indizes entsprechen `PHYSICAL_DATA_MODEL.md` und dem SQLAlchemy-Metadatenmodell.

## Seed-Daten

Die Migration legt deterministische, installationsübergreifend identische Startdaten an.

### Version-1-Workspace

- ID: `00000000-0000-4000-8000-000000000001`
- Name: `Trading Workspace V1`

### Referenzdatenversion `FT-001-V1`

- Handelsplatz: Xetra (`XETR`), ID `00000000-0000-4000-8001-000000000001`, Land `DE`, Zeitzone `Europe/Berlin`
- Währung: Euro (`EUR`), Minor Unit `2`

Die Seed-Daten werden im selben Upgrade wie das Schema angelegt. Dadurch existiert nach erfolgreichem Upgrade kein Zwischenzustand ohne den verpflichtenden Workspace oder ohne die initialen Referenzen.

## Downgrade

Der Downgrade entfernt Indizes und Tabellen in umgekehrter, fremdschlüsselsicherer Reihenfolge. Ein Downgrade ist destruktiv und entfernt damit auch alle FT-001-Nutzdaten. Er ist ausschließlich für kontrollierte Entwicklungs- und Wiederherstellungsszenarien vorgesehen.

## Validierung

Automatisierte Tests prüfen:

- lineare initiale Revision,
- feste Workspace- und Referenzdatenwerte,
- Anlage aller sechs Tabellen,
- Anlage aller acht expliziten Indizes,
- Einspielung der drei Seed-Datensätze,
- fremdschlüsselsichere Downgrade-Reihenfolge.

Zusätzlich wurde `alembic upgrade head --sql` erfolgreich gegen den PostgreSQL-Dialekt erzeugt. Das Offline-SQL enthält alle Tabellen, partiellen Unique Indizes und Seed-Inserts.

## Abgrenzung

Nicht enthalten:

- Repositorys oder Datenzugriffsmethoden,
- fachliche Mutationen und Invarianten,
- API- oder DTO-Implementierung,
- Verwaltung zusätzlicher Referenzdaten,
- produktive Rollen- und Berechtigungsvergabe für append-only Auditdaten.

Der append-only Zugriffsschutz wird in Repository- und Betriebsberechtigungskonzepten ergänzt. Die Migration stellt bereits sicher, dass Audit-Events nicht über Aggregate-Foreign-Keys kaskadierend entfernt werden.

## Architekturreview Schritt 3

- Migration entspricht dem freigegebenen Datenmodell: erfüllt.
- SQLAlchemy-Mapping und DDL bleiben synchron: erfüllt.
- Seed-Werte sind ausdrücklich entschieden und dokumentiert: erfüllt.
- Keine zufälligen oder installationsabhängigen IDs: erfüllt.
- Upgrade ist atomar und deterministisch: erfüllt.
- Downgrade-Reihenfolge respektiert alle Abhängigkeiten: erfüllt.
- Keine Repository- oder Fachlogik vorgezogen: erfüllt.
- Ausschließlich FT-001 umgesetzt: erfüllt.

**Ergebnis:** Schritt 3 ist abgeschlossen und für Schritt 4 „Repository“ freigegeben.
