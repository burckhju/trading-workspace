# Development Guide

> Entwicklungsrichtlinie für den Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-015 |
| Dokument | DEVELOPMENT_GUIDE.md |
| Dokumenttyp | Guide |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument beschreibt den verbindlichen Entwicklungsprozess des Trading Workspace.

Es beantwortet nicht die Frage

> **Wie funktioniert die Software?**

sondern

> **Wie wird die Software entwickelt?**

Dieses Dokument ist die Arbeitsgrundlage für alle Entwickler und zukünftigen ChatGPT-Sitzungen.

---

# Entwicklungsphilosophie

Der Trading Workspace wird **featureorientiert** entwickelt.

Nicht

- nach Schichten,
- nicht nach Technologien,

sondern nach fachlichen Features.

Jedes Feature ist vollständig in sich abgeschlossen.

---

# Dokumentationsarchitektur

```text
Foundation

↓

Feature Books

↓

Reference Library

↓

Implementierung

↓

Tests
```

---

# Foundation

Die Foundation beschreibt das Projekt.

Sie wird selten geändert.

Dazu gehören

- README
- INDEX
- PROJECT
- ROADMAP
- TERMINOLOGY
- ARCHITECTURE

---

# Feature Books

Feature Books bilden die eigentliche Arbeitsgrundlage.

Jeder Entwicklungsauftrag bezieht sich genau auf ein Feature.

Beispiele

- FT-001 Market Analysis
- FT-005 Trade Management
- FT-006 Post Trade Observation

---

# Reference Library

Die Reference Library beschreibt technische Artefakte.

Beispiele

- MODEL_BOOK
- RULEBOOK
- DATABASE
- API

Sie dient als Nachschlagewerk.

---

# Entwicklungsregel

Die Entwicklung beginnt immer beim Feature.

Nicht bei

- Datenbank
- API
- Frontend
- Backend

---

# Standardablauf

Jede Entwicklung erfolgt in derselben Reihenfolge.

```text
Feature lesen

↓

Ist-Zustand analysieren

↓

Änderungsplan erstellen

↓

Implementierung

↓

Tests

↓

Dokumentation

↓

Übergabe
```

---

# Chat-Start

Jeder neue Chat beginnt mit

```text
1. Feature Book lesen

2. Betroffene Referenzdokumente lesen

3. Aktuellen Code analysieren

4. Änderungsplan erstellen
```

Nicht direkt mit der Implementierung beginnen.

---

# Änderungsplan

Vor jeder Implementierung wird ein kurzer Plan erstellt.

Beispiel

```text
Backend

↓

API

↓

Frontend

↓

Tests

↓

Dokumentation
```

---

# Arbeitsbereich

Ein Chat arbeitet grundsätzlich nur an

- einem Feature
- den dazugehörigen Referenzdokumenten
- den benötigten Codebereichen

Nicht am gesamten Projekt.

---

# Änderungen

Änderungen erfolgen ausschließlich innerhalb des aktuellen Features.

Andere Features werden nicht verändert.

Ausnahme

- gemeinsame Contracts
- gemeinsame Formate

Diese Änderungen benötigen eine Architekturentscheidung.

---

# Contracts

Contracts sind projektweit gültig.

Sie dürfen nicht stillschweigend geändert werden.

Vor Änderungen ist zu prüfen

- welche Features betroffen sind,
- welche APIs betroffen sind,
- welche Tests betroffen sind.

---

# Formate

Gemeinsame Formate

- IDs
- Datum
- Geld
- Preise
- JSON

werden ausschließlich zentral definiert.

---

# Implementierung

Ein Feature wird vertikal umgesetzt.

```text
Contract

↓

Backend

↓

API

↓

Frontend

↓

Tests
```

Nicht

erst Backend,

später Frontend.

---

# Tests

Zu jeder Änderung gehören mindestens

- Unit Tests
- Integrationstests

Falls vorhanden zusätzlich

- End-to-End-Tests

---

# Dokumentation

Nach jeder Änderung werden

- Feature Book
- Referenzdokumente
- Changelog

überprüft.

Nur tatsächlich betroffene Dokumente werden angepasst.

---

# Übergabe

Jeder Entwicklungsauftrag endet mit einer Übergabe.

Mindestens

- erledigte Arbeiten
- geänderte Dateien
- offene Punkte
- Testergebnisse
- bekannte Einschränkungen

---

# Chat-Rollen

## Architect

Verantwortlich für

- Architektur
- Dokumentation
- Entscheidungen

---

## Feature Developer

Verantwortlich für

- vollständige Umsetzung eines Features

---

## Backend Developer

Verantwortlich für

- Services
- Businesslogik
- Persistenz

---

## Frontend Developer

Verantwortlich für

- Benutzeroberfläche
- Benutzerführung

---

## Test Engineer

Verantwortlich für

- Testfälle
- Regression
- Qualität

---

## Reviewer

Verantwortlich für

- Code Review
- Dokumentationsreview
- Konsistenzprüfung

---

# Qualitätsregeln

Vor Abschluss eines Features wird geprüft

- Feature vollständig?
- Dokumentation aktuell?
- Tests erfolgreich?
- Referenzen korrekt?
- Keine Architekturverletzung?

---

# Verbotene Vorgehensweisen

Nicht zulässig

- Änderungen ohne Feature Book
- Änderungen ohne Tests
- Änderungen gemeinsamer Contracts ohne Prüfung
- Änderungen mehrerer Features in einem Entwicklungsauftrag
- automatische fachliche Entscheidungen

---

# Definition "Feature abgeschlossen"

Ein Feature gilt erst als abgeschlossen wenn

- Feature Book vollständig
- Referenzdokumente aktuell
- Implementierung abgeschlossen
- Tests erfolgreich
- Review abgeschlossen
- Übergabe erstellt

---

# Entwicklung über mehrere Chats

Die Zusammenarbeit erfolgt ausschließlich über das Repository.

Nicht über vorherige Chats.

Jeder neue Chat arbeitet mit

- Feature Book
- Referenzdokumenten
- aktuellem Code
- Tests

Dadurch bleibt jeder Entwicklungsauftrag unabhängig.

---

# Zusammenfassung

Der Trading Workspace wird konsequent featureorientiert entwickelt.

Feature Books bilden die Arbeitsgrundlage.

Reference-Dokumente bilden die technische Wahrheit.

Jeder Entwicklungsauftrag ist

- klein,
- nachvollziehbar,
- testbar,
- dokumentiert,

und kann unabhängig von anderen Features umgesetzt werden.

---

# Siehe auch

- PROJECT
- ARCHITECTURE
- FT-001 bis FT-013
- REQUIREMENTS
- MODEL_BOOK
- TRACEABILITY
