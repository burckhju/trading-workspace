# Frontend Architecture

> Technische Architektur des Frontends des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-019 |
| Dokument | FRONTEND_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument beschreibt die technische Architektur des Frontends.

Es definiert

- Aufbau
- Verantwortlichkeiten
- Komponenten
- Zustandsverwaltung
- Navigation
- Kommunikationsregeln

Die fachliche Logik wird nicht beschrieben.

Diese befindet sich ausschließlich in den Feature Books.

---

# Architekturprinzipien

Das Frontend folgt denselben Grundprinzipien wie das Backend.

- Feature First
- Component Based
- Single Responsibility
- Wiederverwendbarkeit
- Testbarkeit
- Klare Trennung zwischen Darstellung und Fachlogik

---

# Zielarchitektur

```text
Application

↓

Routing

↓

Feature Pages

↓

Feature Components

↓

Shared Components

↓

Services

↓

REST API
```

---

# Projektstruktur

```text
frontend/

src/

app/

features/

components/

layouts/

pages/

services/

hooks/

types/

assets/

styles/

utils/
```

---

# Application Layer

Verantwortlich für

- Initialisierung
- Routing
- globale Konfiguration
- Theme
- Benutzerkontext

Keine Geschäftslogik.

---

# Routing

Das Routing orientiert sich ausschließlich an Features.

Beispiele

```text
/

market

candidates

trade-plans

portfolio

journal

performance

models

settings
```

Nicht an technischen Komponenten.

---

# Feature Layer

Jedes Feature besitzt seinen eigenen Bereich.

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

Jedes Feature enthält ausschließlich seine eigene Oberfläche.

---

# Aufbau eines Features

```text
feature/

pages/

components/

dialogs/

forms/

tables/

hooks/

services/

types/

tests/
```

---

# Komponenten

Komponenten besitzen genau eine Verantwortung.

Beispiele

```text
TradeCard

TradeTable

StopEditor

ProductSearch

CandidateList
```

Nicht zulässig

```text
TradePageEverything
```

---

# Shared Components

Gemeinsam verwendete Komponenten.

Beispiele

- Buttons
- Tabellen
- Formulare
- Dialoge
- Icons
- Navigation
- Layouts

Keine fachliche Logik.

---

# Seiten

Seiten repräsentieren Arbeitsbereiche.

Beispiele

```text
Market

Candidates

Trade Plans

Portfolio

Journal

Performance

Administration
```

---

# Layouts

Layouts definieren ausschließlich den Seitenaufbau.

Beispiele

- Main Layout
- Dashboard Layout
- Dialog Layout

---

# Services

Frontend-Services kommunizieren ausschließlich mit der REST API.

Sie enthalten

- HTTP-Aufrufe
- Fehlerbehandlung
- Mapping

Keine Geschäftslogik.

---

# Zustandsverwaltung

Der Zustand wird in drei Ebenen getrennt.

## Global

- Benutzer
- Einstellungen
- Theme
- Sprache

---

## Feature

- aktuelle Kandidaten
- aktueller Trade
- aktuelle Suche

---

## Lokal

- Dialogstatus
- Formulare
- Filter

---

# Datenfluss

```text
REST API

↓

Service

↓

State

↓

Component

↓

View
```

Nicht umgekehrt.

---

# Formulare

Jedes Formular besitzt

- Validierung
- Fehlermeldungen
- Status
- Speichern
- Abbrechen

Validierung erfolgt

1. Frontend
2. Backend

---

# Tabellen

Alle Tabellen unterstützen mindestens

- Sortierung
- Filter
- Suche
- Pagination
- Export (falls vorgesehen)

---

# Dialoge

Dialoge dienen ausschließlich

- Eingaben
- Bestätigungen
- Detailansichten

Keine komplexen Workflows.

---

# Navigation

Die Hauptnavigation orientiert sich an den wichtigsten Arbeitsabläufen.

```text
Dashboard

↓

Market

↓

Candidates

↓

Trade Plans

↓

Portfolio

↓

Journal

↓

Performance

↓

Settings
```

Nicht an technischen Modulen.

---

# Dashboard

Das Dashboard zeigt ausschließlich

- offene Aufgaben
- Warnungen
- Erinnerungen
- heutige Entscheidungen
- aktive Trades

Das Dashboard ersetzt keine Fachansichten.

---

# Fehlerbehandlung

Alle Fehler besitzen dieselbe Darstellung.

Mindestens

- Titel
- Beschreibung
- Ursache
- mögliche Aktion

Keine technischen Stacktraces.

---

# Benachrichtigungen

Benachrichtigungen werden zentral verwaltet.

Beispiele

- Erfolg
- Warnung
- Information
- Fehler

---

# Designsystem

Alle UI-Elemente verwenden

- dieselben Farben
- dieselben Abstände
- dieselben Schriftgrößen
- dieselben Icons

Keine individuellen Designs pro Feature.

---

# Responsivität

Alle Oberflächen funktionieren mindestens auf

- Desktop
- Tablet

Eine mobile Optimierung ist optional und wird separat definiert.

---

# Barrierefreiheit

Das Frontend berücksichtigt

- Tastaturbedienung
- Fokussteuerung
- ausreichende Kontraste
- Screenreader-Unterstützung

---

# Performance

Das Frontend soll

- Komponenten lazy laden
- unnötige API-Aufrufe vermeiden
- große Tabellen virtualisieren
- Daten zwischenspeichern, sofern fachlich zulässig

---

# Tests

Jedes Feature besitzt

- Component Tests
- UI Tests
- Integration Tests

Die End-to-End-Tests befinden sich im gemeinsamen Testbereich.

---

# Nicht Bestandteil dieses Dokuments

Dieses Dokument beschreibt nicht

- konkrete Seitenlayouts
- Mockups
- Designrichtlinien
- Geschäftsregeln
- REST-Endpunkte

Diese Inhalte befinden sich in den jeweiligen Feature Books oder Referenzdokumenten.

---

# Zusammenfassung

Das Frontend des Trading Workspace folgt einer konsequent featureorientierten Architektur.

Features sind unabhängig, Komponenten wiederverwendbar und die Kommunikation mit dem Backend erfolgt ausschließlich über definierte Services.

Dadurch bleibt die Benutzeroberfläche modular, wartbar und konsistent.

---

# Siehe auch

## Foundation

- PROJECT
- ARCHITECTURE

## Feature Books

- FT-001 bis FT-013

## Technical

- BACKEND_ARCHITECTURE
- DEVELOPMENT_GUIDE
- CODING_STANDARDS

## Reference

- REQUIREMENTS
- MODEL_BOOK
- DATABASE
- API
- TEST_STRATEGY
- TRACEABILITY
