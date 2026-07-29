# SP-004 Core

## Ziel

SP-004 vervollständigt den technischen Backend-Core. Der Core enthält ausschließlich
querschnittliche Infrastruktur und keine Geschäftslogik.

## Umgesetzter Umfang

### Dependency Injection

`ApplicationContainer` besitzt die processweiten technischen Abhängigkeiten einer
FastAPI-Anwendungsinstanz:

- unveränderliche Anwendungskonfiguration
- zentraler Datenbankmanager
- kontrollierte Freigabe der verwalteten Ressourcen

FastAPI-Dependencies stellen Container, Settings und Datenbankmanager requestbezogen
bereit. Feature-Code muss dadurch nicht direkt auf `application.state` zugreifen.

### Logging-Kontext

Die Request-ID wird mit `contextvars` an den aktuellen asynchronen Ausführungskontext
gebunden. Der JSON-Formatter ergänzt sie automatisch in allen Logeinträgen, die innerhalb
dieses Kontexts erzeugt werden. Nach Abschluss des Requests wird der vorherige Kontext
wiederhergestellt.

### Bestehende Core-Komponenten

Die in SP-002 und SP-003 begonnenen Core-Bereiche bleiben Bestandteil des technischen
Cores:

- zentrale Environment-Konfiguration
- strukturiertes Logging
- zentrale Exception Handler
- Request-Kontext-Middleware
- Application Factory und Lifespan-Verwaltung

## Abgrenzung

Nicht Bestandteil von SP-004 sind:

- Authentifizierung und lokale Benutzerverwaltung
- Autorisierung, Rollen und Rechte
- Passwort-Hashing oder Tokenformate
- Audit Logging fachlicher Aktionen
- Shared Types, Enums, Value Objects oder Utilities
- Fachlogik der Features FT-001 bis FT-013

Die Projektdokumente nennen lokale Benutzerverwaltung als initiale Zielrichtung, legen
aber kein Passwortverfahren, Tokenformat, Sessionmodell oder Rollenmodell fest. Eine
Implementierung wäre daher eine neue Architekturentscheidung und wird nicht vorweggenommen.

## Validierung

- 14 Unit- und Integrationstests erfolgreich
- Python-Syntaxprüfung für Anwendung und Tests erfolgreich
- bestehende SP-002- und SP-003-Tests unverändert erfolgreich
