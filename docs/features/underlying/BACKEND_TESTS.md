# FT-001 Backend-Testabschluss

## Status

Sprint 2, Schritt 10 ist abgeschlossen. Die Backend-Testbasis deckt Datenmodell, Migration, Repository, Domain, Service Layer, REST API, DTOs und Validierungen ab.

## Testebenen

- **Persistenz- und Migrationstests:** Tabellen, Constraints, Foreign Keys, partielle Indizes, Seed-Daten, Upgrade und Downgrade.
- **Repositorytests:** Workspace-Isolation, Suche, Eindeutigkeit und append-only Auditvertrag.
- **Domänentests:** Normalisierung, ISO-6166-Prüfziffer, Qualitätsstatus, Lifecycle, Primärnotierung und Optimistic Locking.
- **Servicetests:** atomare Anlage, Änderungen, Verifikation, Deaktivierung, Reaktivierung, Löschung, Audit-Kopplung, Listing-Änderungen und Primärwechsel.
- **API-/DTO-Tests:** versionierte Routen, Fehlervertrag, Statuscodes, Pagination, Header-Actor, Referenzdaten und PATCH-Semantik.
- **Validierungstests:** Längen, Wertebereiche, UUIDs, Enums, unbekannte Felder und Cross-Field-Regeln.

## Ergänzte kritische Fälle

- erfolgreiche physische Löschung erzeugt Listing- und Underlying-Lösch-Audits,
- referenzierte Basiswerte liefern strukturierte Verwendungsdetails,
- Verifikation wird nach relevanter Stammdatenänderung auf `COMPLETE` zurückgesetzt,
- Deaktivierung und Reaktivierung erhöhen die Version nachvollziehbar,
- Listing-No-op erzeugt weder Commit noch Audit,
- Primärnotierungswechsel aktualisiert beide Listings atomar,
- sämtliche Statusaktionen und Referenzdaten-Endpunkte besitzen Contract-Tests.

## Ergebnis

```text
89 passed
FT-001-Paketabdeckung: 92 %
```

Die verbleibenden nicht abgedeckten Zeilen betreffen überwiegend defensive Fehlerzweige sowie einzelne Dependency- und Session-Fehlerpfade. PostgreSQL-, Compose- und Browser-Nachweise sind in `INTEGRATION_E2E_TESTS.md` dokumentiert.

## Architekturreview

- Tests prüfen beobachtbares Verhalten und verbindliche Architekturregeln.
- Backend-Tests bleiben von Frontend- und Browserimplementierung getrennt; übergreifende Nachweise sind in Schritt 14 dokumentiert.
- Produktionscode wurde nur zur Beseitigung einer FastAPI-Deprecation-Warnung ohne Vertragsänderung angepasst.
- Testdaten verwenden ausschließlich den festgelegten Version-1-Workspace und die kontrollierten Referenzdaten.

## Ergänzung vor Frontend Views

Die Suite prüft zusätzlich die Weitergabe von Handelsplatz- und Währungsfiltern sowie Pagination und Antwortverträge der Audit- und Usage-Endpunkte. Gesamtstand: 89 erfolgreiche Tests.
