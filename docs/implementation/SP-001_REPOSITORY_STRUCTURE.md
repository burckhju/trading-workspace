# SP-001 Repositorystruktur

## Ziel

Aufbau der verbindlichen Repositorystruktur für den Trading Workspace ohne Fachlogik und ohne Implementierung der Features FT-001 bis FT-013.

## Umgesetzte Grundlage

Die Struktur folgt primär `docs/architecture/Source_Architecture.md`, da dieses Dokument die vollständige und verbindliche Source-Code-Struktur definiert.

Ergänzend berücksichtigt wurden:

- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`
- `docs/architecture/Feature_Architecture.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`

## Abgrenzung

- Keine Backend- oder Frontend-Bootstrap-Implementierung
- Keine Datenbankkonfiguration
- Keine Core- oder Shared-Implementierung
- Keine Docker-Konfiguration
- Keine CI-Konfiguration
- Keine Fachlogik
- Keine Feature-Innenstruktur und keine Implementierung von FT-001 bis FT-013

## Verbindliche Architekturentscheidungen

### Backend-Verzeichnisse

`core`, `shared`, `features`, `providers`, `database` und `events` liegen gemäß `Source_Architecture.md` unter `backend/app/`.

### Feature-Domain-Schicht

Die Backend-Feature-Schicht heißt verbindlich `domain/`. Abweichende Verweise auf `models/` wurden in den betroffenen Architekturdokumenten korrigiert.

### Backend-Einstiegspunkt

Der verbindliche Einstiegspunkt ist `backend/app/main.py`. Die Datei wird erst im Arbeitspaket SP-002 Backend Bootstrap implementiert und ist daher nicht Bestandteil von SP-001.
