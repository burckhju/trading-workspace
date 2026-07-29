# Backend Architecture

> Technische Architektur des Backends des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-018 |
| Dokument | BACKEND_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument beschreibt die technische Architektur des Backends.

Es definiert

- Aufbau
- Verantwortlichkeiten
- Schichten
- Kommunikationswege
- Designprinzipien

Es beschreibt keine Geschäftslogik.

Diese befindet sich ausschließlich in den Feature Books.

---

# Architekturprinzipien

Das Backend basiert auf folgenden Prinzipien:

- Feature First
- Clean Architecture
- Domain Driven Design
- Dependency Injection
- Testbarkeit
- Erweiterbarkeit
- geringe Kopplung

---

# Zielarchitektur

```text
REST API

↓

Application Layer

↓

Feature Layer

↓

Domain Models

↓

Repositories

↓

Database

↓

External Provider
```

---

# Projektstruktur

```text
backend/

app/

core/

features/

shared/

api/

database/

providers/

events/

tests/
```

---

# Core

Der Core enthält ausschließlich technische Infrastruktur.

Beispiele

- Konfiguration
- Logging
- Authentifizierung
- Dependency Injection
- Fehlerbehandlung

Der Core enthält keine Geschäftslogik.

---

# Features

Jedes Feature besitzt einen eigenen Bereich.

```text
features/

market/

candidate/

trade_plan/

product/

trade/

observation/

journal/

performance/

model/

provider/

notification/

administration/
```

Features dürfen keine Implementierungsdetails anderer Features kennen.

---

# Aufbau eines Features

```text
feature/

api/

services/

domain/

repositories/

schemas/

validators/

events/

tests/
```

Jedes Feature ist technisch möglichst unabhängig.

---

# API Layer

Verantwortung

- Routing
- Request Validation
- Authorization
- Response Mapping

Nicht zulässig

- Berechnungen
- Datenbankzugriffe
- Geschäftsregeln

---

# Service Layer

Verantwortung

- Geschäftslogik
- Workflowsteuerung
- Koordination mehrerer Modelle

Ein Service besitzt genau eine fachliche Verantwortung.

---

# Domain Models

Domain Models enthalten

- Berechnungen
- Bewertungen
- Entscheidungslogik

Sie sind unabhängig von

- HTTP
- Datenbank
- Framework

---

# Repository Layer

Repositories kapseln ausschließlich den Datenzugriff.

Erlaubt

- Create
- Read
- Update
- Delete

Nicht erlaubt

- Geschäftslogik
- Berechnungen

---

# Database Layer

Die Datenbank ist ausschließlich Persistenz.

Sie kennt keine Fachlogik.

---

# Provider Layer

Der Provider Layer kapselt externe Systeme.

Beispiele

- Börsendaten
- Produktdaten
- Historische Kurse
- Benachrichtigungsdienste

Features kommunizieren niemals direkt mit externen APIs.

---

# Shared Layer

Gemeinsam genutzte Komponenten.

Beispiele

- Value Objects
- Datumsfunktionen
- Geldbeträge
- Identifier
- Enumerationen

Nur fachlich neutrale Komponenten gehören in diesen Bereich.

---

# Event Layer

Features kommunizieren bevorzugt über Events.

Beispiele

```text
TRADE_OPENED

STOP_UPDATED

PRODUCT_SWITCHED

TRADE_CLOSED

OBSERVATION_COMPLETED

JOURNAL_FINALIZED
```

Events reduzieren direkte Abhängigkeiten zwischen Features.

---

# Abhängigkeitsregeln

Erlaubt

```text
API

↓

Service

↓

Model

↓

Repository
```

Nicht erlaubt

```text
Repository

↓

Service

↓

API
```

oder

```text
Frontend

↓

Repository
```

---

# Fehlerbehandlung

Alle Fehler werden zentral behandelt.

Jede Ausnahme besitzt

- Fehlercode
- Nachricht
- Kontext
- Zeitstempel

---

# Konfiguration

Konfiguration erfolgt ausschließlich zentral.

Beispiele

- Datenbank
- Provider
- API Keys
- Feature Flags
- Logging

Keine Konfiguration im Quellcode.

---

# Transaktionen

Geschäftliche Transaktionen werden ausschließlich im Service Layer gesteuert.

Repositories öffnen keine eigenen Transaktionen.

---

# Validierung

Mehrstufige Validierung

1. API
2. Schema
3. Service
4. Domain Model

Jede Ebene prüft ausschließlich ihre eigene Verantwortung.

---

# Sicherheit

Sicherheitsprüfungen erfolgen zentral.

Beispiele

- Authentifizierung
- Autorisierung
- Rollen
- Rechte
- Audit Logging

---

# Logging

Alle fachlichen Aktionen werden protokolliert.

Mindestens

- Benutzer
- Feature
- Aktion
- Ergebnis
- Dauer

---

# Testbarkeit

Jede Schicht muss unabhängig testbar sein.

Abhängigkeiten werden injiziert.

Externe Provider werden gemockt.

---

# Erweiterbarkeit

Neue Features werden hinzugefügt, ohne bestehende Features verändern zu müssen.

Neue Provider werden ergänzt, ohne bestehende Services anzupassen.

Neue Modelle werden registriert, ohne vorhandene Modelle zu ändern.

---

# Nicht Bestandteil dieses Dokuments

Dieses Dokument beschreibt nicht

- Datenmodelle
- REST-Endpunkte
- Geschäftsregeln
- SQL
- Framework-spezifische Implementierungen

Diese Inhalte befinden sich in den entsprechenden Referenzdokumenten.

---

# Zusammenfassung

Das Backend des Trading Workspace folgt einer konsequent featureorientierten Clean Architecture.

Geschäftslogik, Datenzugriff, Kommunikation und Infrastruktur sind klar voneinander getrennt.

Dadurch bleibt das System modular, testbar, wartbar und für eine parallele Entwicklung durch mehrere Entwickler oder ChatGPT-Sitzungen geeignet.

---

# Siehe auch

## Foundation

- PROJECT
- ARCHITECTURE

## Feature Books

- FT-001 bis FT-013

## Reference

- DEVELOPMENT_GUIDE
- CODING_STANDARDS
- REQUIREMENTS
- MODEL_BOOK
- DATABASE
- API
- TEST_STRATEGY
- TRACEABILITY
