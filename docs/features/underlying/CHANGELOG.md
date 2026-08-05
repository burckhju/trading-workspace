# FT-001 Changelog

## 1.0 – 2026-08-03

- Initiales Feature Book erstellt.
- Aktien als einzige Basiswertart in Version 1 festgelegt.
- Optionsscheine als getrennte Produktobjekte abgegrenzt.
- Underlying und Listing getrennt.
- Single-Workspace-, Lösch- und Identifikatorentscheidungen übernommen.

## 1.1 – 2026-08-03

- ADR-S1-007 bis ADR-S1-013 übernommen.
- Markt- und Währungsreferenzen, Identifikatorvalidierung und workspacebezogene Eindeutigkeit finalisiert.
- Optimistische Nebenläufigkeitskontrolle und feldbasiertes Auditmodell festgelegt.
- Lebenszyklusstatus von Datenqualitätsstatus getrennt.
- Feature auf `Architecture Approved – Approved for Build` gesetzt.


## 1.2 – 2026-08-03

- ADR-S2-001 bis ADR-S2-003 als technische Konkretisierung akzeptiert.
- Persistierten Version-1-Workspace festgelegt.
- Persistierte Referenztabellen für Handelsplätze und Währungen festgelegt.
- Gemeinsames append-only Auditmodell mit JSONB-Feldänderungen festgelegt.
- Physisches Datenmodell einschließlich Constraints, Indizes, Beziehungen, Lösch- und Transaktionsregeln abgeschlossen.
- Implementierungsschritt 1 für das SQLAlchemy-Mapping freigegeben.

## 1.3 – 2026-08-03

- SQLAlchemy-Persistenzmodell für Workspace, Referenzdaten, Underlying, Listing und AuditEvent implementiert.
- Optimistic Locking für Underlying und Listing im Mapper vorbereitet.
- Sämtliche freigegebenen Constraints, Foreign-Key-Regeln und PostgreSQL-Indizes abgebildet.
- Architekturtests für Metadaten und PostgreSQL-DDL ergänzt.
- Implementierungsschritt 2 für die Alembic-Migration freigegeben.

## 1.4 – 2026-08-03

- Initiale Alembic-Revision `20260803_0001` für sämtliche FT-001-Tabellen implementiert.
- Feste Version-1-Workspace-ID und technischen Namen dokumentiert und migrationsseitig eingespielt.
- Referenzdatenversion `FT-001-V1` mit Xetra und EUR als kontrollierte Startliste eingespielt.
- Upgrade, Downgrade, Constraints, Indizes und Seed-Werte automatisiert getestet.
- PostgreSQL-Offline-DDL erfolgreich validiert.
- Implementierungsschritt 3 für die Repository-Implementierung freigegeben.

## 2026-08-03 – Sprint 2, Schritt 4

- Repository-Protocols und asynchrone SQLAlchemy-Adapter für FT-001 ergänzt.
- Workspace-isolierte Suche, Detail-, Eindeutigkeits- und Referenzdatenzugriffe umgesetzt.
- Audit-Repository als append-only Vertrag umgesetzt.
- Repository-Tests und `REPOSITORY.md` ergänzt.
- Implementierungsschritt 4 für die Domänenlogik freigegeben.

## 2026-08-03 – Sprint 2, Schritt 5

- SQLAlchemy-unabhängige Domain Entities für Underlying und Listing ergänzt.
- Normalisierung und formale Validierung von ISIN, WKN, Ticker und Codes umgesetzt.
- Primärnotierungs-, Qualitäts-, Lifecycle- und Versionsregeln implementiert.
- Stabile Domainfehler gemäß fachlichem API-Vertrag ergänzt.
- Domain-Architektur und Testabdeckung in `DOMAIN_LOGIC.md` dokumentiert.

## 2026-08-04 – Sprint 2 Schritt 6

- Service Layer mit Unit of Work für FT-001 ergänzt.
- Underlying- und Listing-Use-Cases transaktional orchestriert.
- Dubletten-, Referenzdaten-, Versions- und Löschschutzprüfungen ergänzt.
- Audit-Erzeugung atomar an Fachänderungen gekoppelt.
- Service-Layer-Tests und Architekturdokumentation ergänzt.

## 2026-08-04 – Sprint 2 Schritt 7

- Versionierte FT-001-REST-API unter `/api/v1` implementiert.
- Underlying-Suche, Detail, Anlage, Änderung, Statusaktionen und Löschung exponiert.
- Listing-Anlage, Änderung und atomarer Primärwechsel exponiert.
- Read-only Endpunkte für kontrollierte Handelsplätze und Währungen ergänzt.
- Domain- und Servicefehler in den zentralen API-Fehlervertrag übersetzt.
- REST-Contract-Tests und `REST_API.md` ergänzt.

## 2026-08-04 – Sprint 2 Schritt 8

- Dedizierte Pydantic-DTOs für sämtliche FT-001-Requests und -Responses ergänzt.
- Manuelle Request-Extraktion sowie UUID-, Enum- und Datetime-Serialisierung aus den Routern entfernt.
- Getrennte Summary-, Detail-, Such-, Listing- und Referenzdatenverträge eingeführt.
- Explizite Response Models und benannte OpenAPI-Schemas für alle fachlichen Endpunkte ergänzt.
- PATCH-Semantik für ausgelassene gegenüber explizit geleerten Identifikatoren abgesichert.
- DTO-Vertragstests und `DTOS.md` ergänzt.

## Sprint 2 – Schritt 9 Validierungen

- Feldlängen und sichere Wertebereiche an das physische Datenmodell angeglichen.
- Versions- und Pagination-Grenzen ergänzt.
- Leere PATCH-Operationen durch Cross-Field-Validierung verhindert.
- Währungscodes auf drei Buchstaben begrenzt.
- Validierungsarchitektur und Schichtabgrenzung dokumentiert.

## Sprint 2 – Schritt 10 Backend-Tests

- Backend-Testabdeckung gegen Feature Book und akzeptierte ADRs vollständig überprüft.
- Servicefälle für Suche, Verifikation, Reaktivierung, Löschung, Listing-Änderung und atomaren Primärwechsel ergänzt.
- REST-Contract-Tests für Statusaktionen, Löschung, Listing-Änderung, Referenzdaten und Verwendungsdetails ergänzt.
- FT-001-Paketabdeckung auf 92 % erhöht; vollständige Backend-Suite mit 86 Tests erfolgreich.
- FastAPI-Deprecation-Warnung für HTTP 422 ohne Änderung des öffentlichen Vertrags beseitigt.
- `BACKEND_TESTS.md` als Abschlussnachweis ergänzt.

## Sprint 2 – Schritt 11 React API Client

- Typisierten FT-001-API-Client unter `frontend/src/features/market/` ergänzt.
- Sämtliche Underlying-, Listing- und Referenzdatenoperationen auf `/api/v1` abgebildet.
- Zentralen API-Fehlervertrag als `MarketApiError` und Transportfehler separat modelliert.
- Actor-Header, AbortSignal und PATCH-Nullsemantik unterstützt.
- Client-Vertragstests und `REACT_API_CLIENT.md` ergänzt.
- Lokale Testausführung wegen eines fehlenden npm-Proxy-Artefakts dokumentiert.

## 2026-08-04 – UI-Backend-Vertragserweiterung vor Schritt 12

- Primärnotierungs-Summary für Listenantworten ergänzt.
- Serverseitige Filter für Handelsplatz und Währung ergänzt.
- Paginierte Audit-Historie für Underlying und Listings ergänzt.
- Verwendungsübersicht auf Basis desselben Usage-Vertrags wie der Löschschutz ergänzt.
- Listing-Antworten um Handelsplatz-MIC und -Name erweitert.
- React API Client und Typen synchronisiert.

## 2026-08-04 — Sprint 2 Step 12

- Added FT-001 React list, creation, detail, and edit views.
- Added server-side search/filter UI for lifecycle, trading venue, and currency.
- Added detail sections for identifiers, listings, usages, and audit history.
- Added verify, deactivate, reactivate, and delete actions using optimistic-lock versions.
- Documented frontend-view architecture in `FRONTEND_VIEWS.md`.

## 2026-08-04 — Sprint 2 Schritt 13

- Komponenten- und Interaktionstests für Basiswertliste, Detail und Formular ergänzt.
- Serverseitige Suche sowie Handelsplatz- und Währungsfilter abgesichert.
- Primärnotierungsdarstellung ohne N+1-Detailzugriffe geprüft.
- Audit-, Verwendungs-, Status-, Lösch-, Anlage- und Bearbeitungspfade getestet.
- Optimistic-Locking-Versionen und bestätigte destruktive Aktionen abgesichert.
- Frontend-Testarchitektur und verbleibende npm-Registry-Einschränkung in `FRONTEND_TESTS.md` dokumentiert.

## 2026-08-04 — Sprint 2 Schritt 14

- Playwright-E2E-Pfade für Suche, Anlage, Detail, Audit, Verwendungen und Verifikation ergänzt.
- Browsertests prüfen Views, React Router, Market API Client und HTTP-Verträge gemeinsam.
- PostgreSQL als verbindliche Integrationsdatenbank bestätigt; kein fachlich unzureichender SQLite-Ersatz eingeführt.
- Ausführungsweg über `scripts/run-e2e.sh` und die Laufzeitgrenzen in `INTEGRATION_E2E_TESTS.md` dokumentiert.

## 2026-08-04 — Sprint 2 Schritt 15

- Repository- und Feature-Status auf den tatsächlichen implementierten Sprint-2-Stand aktualisiert.
- Vollständige Traceability von Anforderungen und ADRs bis Implementierung und Tests ergänzt.
- Backend-, Frontend- und E2E-Dokumentation mit den realen Ausführungsergebnissen synchronisiert.
- Veraltete Sprint-0-Aussagen und überholte npm-Ausführungsvorbehalte entfernt.
- `SPRINT_2_CLOSEOUT.md` und `STEP15_REVIEW.md` als Abschlussnachweise ergänzt.
- Release-Readiness-Prüfung für Umgebungen mit `python3` ohne `python`-Alias portabel gemacht.
