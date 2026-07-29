# SP-002 Backend Bootstrap

## Ziel

SP-002 stellt einen startfähigen, rein technischen FastAPI-Bootstrap bereit. Das Arbeitspaket enthält keine Fachlogik und keine Implementierung der Features FT-001 bis FT-013.

## Implementierter Umfang

- ASGI-Einstiegspunkt `backend/app/main.py`
- testbare Application Factory
- zentral validierte Environment-Konfiguration
- strukturiertes JSON-Logging
- zentraler Fehlervertrag und Exception Handler
- Request-ID-Middleware und technisches Access Logging
- Lifespan-Hooks für Start und Stopp
- technischer Liveness-Endpunkt `GET /health`
- Backend-Paket- und Werkzeugkonfiguration
- Unit- und Integrationstests für den Bootstrap

## Konfiguration

Alle Variablen verwenden das Präfix `TRADING_WORKSPACE_`.

| Variable | Bedeutung |
|---|---|
| `APPLICATION_NAME` | Anzeigename der API |
| `ENVIRONMENT` | `development`, `test` oder `production` |
| `DEBUG` | FastAPI-Debugmodus |
| `LOG_LEVEL` | Python-Loglevel |
| `DOCUMENTATION_ENABLED` | Aktiviert `/docs` und `/openapi.json` |

Eine lokale Vorlage liegt unter `backend/.env.example`. Produktivwerte werden nicht im Repository gespeichert.

## Lokaler Start

Aus dem Verzeichnis `backend/`:

```bash
python -m uvicorn app.main:app
```

## Abgrenzung

Nicht Bestandteil von SP-002 sind:

- Datenbankverbindungen und Migrationen (SP-003)
- fachliche Core-Komponenten (SP-004)
- Shared-Fachtypen (SP-005)
- Feature-Router und Feature-Services
- Authentifizierung und Autorisierung
- externe Provider
- Docker- und CI-Konfiguration

## Offener Architekturpunkt

Die verbindlichen Dokumente nennen keine freigegebenen konkreten Versionsnummern für Python und Backend-Bibliotheken. Die in `backend/pyproject.toml` gesetzten kompatiblen Versionsbereiche sind deshalb für einen reproduzierbaren Bootstrap technisch notwendig, müssen aber vor einem produktiven Release durch eine formale Versionsfreigabe bestätigt oder durch eine Lockdatei präzisiert werden.
