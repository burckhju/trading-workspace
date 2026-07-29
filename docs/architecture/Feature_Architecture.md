# Feature Architecture

> Standardarchitektur eines implementierbaren Features im Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument | FEATURE_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.0 |

---

# Zweck

Dieses Dokument definiert den technischen Aufbau eines Features.

Es beschreibt

- Verzeichnisstruktur
- Verantwortlichkeiten
- Schichten
- Abhängigkeiten
- Kommunikationsregeln

Alle Features verwenden diese Architektur.

---

# Grundprinzip

Ein Feature ist vollständig in sich abgeschlossen.

Es besitzt

- API
- Services
- Domain
- Persistenz
- Tests
- Dokumentation

---

# Featurestruktur

```text
FT-xxx/

FEATURE.md

implementation/

backend/

frontend/

tests/
```

---

# Backend

```text
backend/features/<feature>/

api/

services/

domain/

repositories/

schemas/

events/

validators/

mappers/

tests/
```

---

# Frontend

```text
frontend/features/<feature>/

pages/

components/

dialogs/

hooks/

services/

types/

tests/
```

---

# Dokumentation

```text
FEATURE.md

implementation/

API_CONTRACT.md

DOMAIN_MODEL_MAPPING.md

REPOSITORY_CONTRACT.md

VALIDATION_RULES.md

STATE_MACHINE.md

SEQUENCE_DIAGRAMS.md

TEST_CASES.md

IMPLEMENTATION_CHECKLIST.md
```

---

# Schichten

```text
Frontend

↓

REST API

↓

Application Service

↓

Domain

↓

Repository

↓

Database
```

---

# Domain

Die Domain enthält

- Entities
- Value Objects
- Aggregate
- Domain Services

Keine Frameworkabhängigkeiten.

---

# Services

Services koordinieren

- Domain
- Modelle
- Repositories
- Events

---

# Repository

Repositories kapseln

Persistenz.

Keine Geschäftslogik.

---

# API

Die API

- validiert
- autorisiert
- delegiert

Keine Berechnungen.

---

# Events

Jedes Feature veröffentlicht ausschließlich seine eigenen Events.

Andere Features konsumieren diese Events.

Direkte Abhängigkeiten werden minimiert.

---

# Tests

```text
Unit

↓

Integration

↓

API

↓

Workflow

↓

Performance
```

---

# Implementierungsreihenfolge

Für jedes Feature gilt dieselbe Reihenfolge.

```text
Domain

↓

Repository

↓

Service

↓

API

↓

Frontend

↓

Tests
```

---

# Feature-Grenzen

Ein Feature darf niemals

direkt

auf Datenbanken anderer Features zugreifen.

Kommunikation erfolgt über

- Services

oder

- Events.

---

# Erweiterungen

Neue Features müssen diese Struktur unverändert übernehmen.

Es entstehen keine Sonderlösungen pro Feature.

---

# Zusammenfassung

Dieses Dokument definiert die technische Standardarchitektur aller Features.

Dadurch besitzen FT-001 bis FT-013 denselben Aufbau und können unabhängig entwickelt, getestet und gewartet werden.
