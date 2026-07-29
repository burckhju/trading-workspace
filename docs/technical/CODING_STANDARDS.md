# Coding Standards

> Projektweite Entwicklungs- und Codierungsrichtlinien des Trading Workspace

---

# Änderungshistorie

| Version | Datum | Änderungen |
|----------|------------|----------------|
| 1.0 | 2026-07-22 | Erstversion |

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument-ID | DOC-016 |
| Dokument | CODING_STANDARDS.md |
| Dokumenttyp | Guide |
| Version | 1.0 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-07-22 |

---

# Zweck

Dieses Dokument definiert die verbindlichen Entwicklungs- und Codierungsrichtlinien des Trading Workspace.

Es stellt sicher, dass sämtliche Entwickler und ChatGPT-Sitzungen denselben Stil und dieselben Konventionen verwenden.

---

# Grundprinzipien

Der Quellcode soll

- lesbar,
- verständlich,
- testbar,
- wartbar,
- reproduzierbar

sein.

Code wird für Menschen geschrieben.

---

# Projektstruktur

```text
backend/
frontend/
tests/
docs/
scripts/
docker/
```

Keine zusätzlichen Hauptverzeichnisse ohne Architekturentscheidung.

---

# Backendstruktur

```text
backend/app/

core/

features/

domain/

repositories/

services/

api/

schemas/

events/

utils/
```

Featurebezogene Implementierungen gehören grundsätzlich unter

```text
features/
```

---

# Frontendstruktur

```text
frontend/src/

app/

features/

components/

layouts/

pages/

services/

types/

hooks/
```

Gemeinsam genutzte Komponenten gehören ausschließlich nach

```text
components/
```

---

# Tests

```text
tests/

unit/

integration/

e2e/

fixtures/
```

Testdaten gehören niemals in den Produktivcode.

---

# Benennung

## Python

```text
snake_case
```

Beispiele

```python
trade_service.py

calculate_stop()

trade_plan
```

---

## TypeScript

```text
camelCase
```

Beispiele

```typescript
tradePlan

calculateStop()
```

---

## React

Komponenten

```text
PascalCase
```

Beispiele

```text
TradeCard

ProductTable

StopEditor
```

---

## Datenbank

Tabellen

```text
snake_case
```

Beispiele

```text
trade

trade_event

trade_plan
```

---

## REST

Ressourcen

```text
kebab-case
```

Beispiele

```text
/api/v1/trade-plans

/api/v1/trade-events
```

---

# IDs

Alle fachlichen Objekte verwenden UUID.

Beispiele

```text
trade_id

trade_plan_id

product_id
```

Keine Integer als fachliche IDs.

---

# Datumsformate

Intern

UTC

ISO-8601

Beispiel

```text
2026-07-22T09:30:00Z
```

---

# Geldbeträge

Immer

```text
Decimal
```

Keine Float-Werte.

---

# Prozentwerte

Immer

```text
Decimal
```

Nicht

```text
0.18
```

sondern

```text
18.0
```

Die Darstellung wird zentral definiert.

---

# Namen

Keine Abkürzungen.

Nicht

```text
tp
```

sondern

```text
trade_plan
```

Nicht

```text
prd
```

sondern

```text
product
```

---

# Kommentare

Kommentare erklären

**warum**

nicht

**was**

Der Code soll möglichst selbsterklärend sein.

---

# Logging

Jede fachliche Aktion wird protokolliert.

Mindestens

- Zeitpunkt
- Benutzer
- Feature
- Aktion
- Ergebnis

---

# Fehlerbehandlung

Alle Fehler besitzen dieselbe Struktur.

```json
{
  "code": "",
  "message": "",
  "details": []
}
```

Keine unstrukturierten Fehlermeldungen.

---

# Events

Events werden ausschließlich im Perfekt benannt.

Beispiele

```text
TRADE_OPENED

STOP_CHANGED

PRODUCT_CHANGED

PARTIAL_SALE_CREATED

TRADE_CLOSED
```

Nicht

```text
OPEN_TRADE

STOP_CHANGE
```

---

# Services

Ein Service besitzt genau eine fachliche Verantwortung.

Nicht zulässig

```text
TradeService

+

ProductSearch

+

Import

+

Statistics
```

in derselben Klasse.

---

# Repository

Repositories enthalten ausschließlich

- Lesen
- Schreiben
- Löschen
- Aktualisieren

Keine Geschäftslogik.

---

# Geschäftslogik

Geschäftslogik gehört ausschließlich in

```text
services/
```

---

# Domain

Berechnungslogik gehört ausschließlich in die fachliche Domain-Schicht eines Features:

```text
domain/
```

Nicht in

- Controller
- Repository
- Frontend

---

# API

Die API

- validiert,
- autorisiert,
- delegiert.

Keine Geschäftslogik.

---

# Frontend

Das Frontend

- zeigt Daten an,
- validiert Eingaben,
- sendet Requests.

Keine fachlichen Berechnungen.

---

# Feature-Regel

Ein Feature besitzt

- eigene Services
- eigene API
- eigene Tests
- eigene Dokumentation

Features kommunizieren ausschließlich über definierte Schnittstellen.

---

# Dokumentation

Jede neue Funktion benötigt

- Feature Book
- Requirements
- Tests

Vor der Implementierung.

---

# Pull-Request-Regeln

Jede Änderung muss enthalten

- Implementierung
- Tests
- Dokumentationsanpassung

---

# Review-Checkliste

Vor jeder Freigabe wird geprüft

- Architektur eingehalten
- Coding Standards eingehalten
- Tests erfolgreich
- Dokumentation aktuell
- Keine Redundanzen
- Keine toten Schnittstellen

---

# Nicht zulässig

- Geschäftslogik im Frontend
- Geschäftslogik im Repository
- Direktzugriffe zwischen Features
- Duplizierte Modelle
- Hartkodierte Konstanten
- Nicht dokumentierte APIs

---

# Zusammenfassung

Diese Coding Standards definieren die projektweit verbindlichen Entwicklungsregeln.

Sie sorgen dafür, dass sämtliche Implementierungen unabhängig vom Entwickler oder von der verwendeten ChatGPT-Sitzung konsistent, wartbar und nachvollziehbar bleiben.

---

# Siehe auch

- DEVELOPMENT_GUIDE
- ARCHITECTURE
- REQUIREMENTS
- MODEL_BOOK
- DATABASE
- API
- TRACEABILITY
