# Technology Stack

> Verbindliche technische Plattform des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-020 |
| Dokument | TECH_STACK.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument definiert die verbindliche technische Plattform des Trading Workspace.

Es beantwortet ausschließlich

- Welche Technologien werden verwendet?
- Welche Versionen sind freigegeben?
- Welche Bibliotheken sind Standard?
- Welche Alternativen sind ausdrücklich ausgeschlossen?

Dieses Dokument enthält keine Implementierungsdetails.

---

# Architekturübersicht

```text
Browser

↓

React Frontend

↓

REST API

↓

Python Backend

↓

PostgreSQL

↓

Externe Provider
```

---

# Grundprinzipien

Die Technologiewahl orientiert sich an folgenden Zielen:

- Langfristige Wartbarkeit
- Große Community
- Open Source
- Gute Dokumentation
- Hohe Testbarkeit
- Geringe Komplexität
- Plattformunabhängigkeit

---

# Betriebssystem

Entwicklung

- Windows
- Linux
- macOS

Deployment

- Linux

---

# Programmiersprachen

## Backend

Python

---

## Frontend

TypeScript

---

## Datenbank

SQL

---

## Konfigurationsdateien

YAML

JSON

ENV

---

# Backend

## Framework

FastAPI

---

## API

REST

---

## Datenvalidierung

Pydantic

---

## ORM

SQLAlchemy

---

## Migrationen

Alembic

---

## Hintergrundaufgaben

APScheduler

---

## HTTP Client

httpx

---

## Dependency Injection

FastAPI Dependency Injection

---

# Frontend

## Framework

React

---

## Sprache

TypeScript

---

## Build Tool

Vite

---

## Routing

React Router

---

## Tabellen

AG Grid oder TanStack Table

---

## Formulare

React Hook Form

---

## Validierung

Zod

---

## Icons

Lucide

---

## Styling

Tailwind CSS

---

# Datenbank

PostgreSQL

---

# Cache

Derzeit nicht vorgesehen.

Falls erforderlich

Redis

---

# Dateiformate

CSV

JSON

PDF

PNG

SVG

---

# Authentifizierung

Initial

lokale Benutzerverwaltung

Später optional

- OAuth
- OpenID Connect

---

# Logging

Python Logging

strukturierte Logs

---

# Konfiguration

Environment Variablen

.env Dateien

Keine Konfiguration im Code.

---

# Testing

## Backend

pytest

---

## API

pytest

httpx

---

## Frontend

Vitest

Testing Library

---

## End-to-End

Playwright

---

# Dokumentation

Markdown

Mermaid

OpenAPI

---

# Containerisierung

Docker

Docker Compose

---

# Reverse Proxy

Nginx

---

# CI/CD

GitHub Actions

---

# Versionsverwaltung

Git

GitHub

---

# Codequalität

Backend

- Ruff
- Black
- mypy

---

Frontend

- ESLint
- Prettier

---

# Sicherheitswerkzeuge

Abhängigkeitsprüfung

- pip-audit

JavaScript

- npm audit

---

# Monitoring

Anwendungslogs

Health Checks

Metriken (optional)

---

# Benachrichtigungen

Telegram

E-Mail

Weitere Provider können später ergänzt werden.

---

# Externe Datenprovider

Provider werden ausschließlich über Adapter angebunden.

Beispiele

- Börsendaten
- Produktdaten
- Historische Kurse

Die konkrete Auswahl ist im Feature **FT-010 Data Providers** definiert.

---

# Internationalisierung

Primäre Sprache

Deutsch

Interne Bezeichner

Englisch

---

# Zeitzonen

Intern

UTC

Anzeige

Benutzerkonfiguration

---

# Zahlenformate

Intern

Decimal

Anzeige

Länderspezifisch

---

# Unterstützte Browser

- Chrome
- Edge
- Firefox

Safari optional.

---

# Verbotene Technologien

Im Projekt werden nicht verwendet:

- PHP
- jQuery
- SOAP
- XML-basierte APIs
- Serverseitiges HTML-Rendering
- Geschäftslogik im Frontend

---

# Aktualisierung des Technologie-Stacks

Neue Technologien dürfen nur eingeführt werden, wenn

- ein fachlicher oder technischer Mehrwert nachgewiesen ist,
- keine unnötige Komplexität entsteht,
- bestehende Features nicht beeinträchtigt werden,
- die Architekturprinzipien eingehalten werden.

Technologieentscheidungen sind zu dokumentieren und zu versionieren.

---

# Zusammenfassung

Der Trading Workspace basiert auf einem modernen, stabilen und weit verbreiteten Technologie-Stack.

Die Auswahl der Technologien unterstützt die featureorientierte Architektur, eine hohe Testbarkeit sowie eine langfristig wartbare Softwarebasis.

---

# Siehe auch

## Foundation

- PROJECT
- ARCHITECTURE

## Technical

- BACKEND_ARCHITECTURE
- FRONTEND_ARCHITECTURE
- DEVELOPMENT_GUIDE
- CODING_STANDARDS

## Reference

- REQUIREMENTS
- MODEL_BOOK
- DATABASE
- API
- TEST_STRATEGY
- TRACEABILITY

## Feature Books

- FT-001 bis FT-013
