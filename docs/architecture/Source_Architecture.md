# Source Architecture

> Verbindliche Struktur des Quellcodes des Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|------|------|
| Dokument | SOURCE_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.0 |
| Status | 🔵 Review |

---

# Zweck

Dieses Dokument definiert den vollständigen Aufbau des Source Codes.

Es beschreibt

- Repositorystruktur
- Module
- Pakete
- Abhängigkeiten
- Build-Struktur

Es beschreibt keine Geschäftslogik.

---

# Repository

```text
trading-workspace/

backend/

frontend/

docs/

tests/

scripts/

docker/

.github/
```

---

# Backend

```text
backend/

app/

core/

shared/

features/

providers/

database/

events/

main.py
```

---

# Core

```text
core/

config/

logging/

security/

exceptions/

middleware/

di/
```

Nur technische Infrastruktur.

---

# Shared

```text
shared/

types/

enums/

value_objects/

utils/

contracts/

validators/
```

Keine Fachlogik.

---

# Features

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

mappers/

tests/
```

---

# Frontend

```text
frontend/

src/

app/

features/

shared/

components/

layouts/

services/

types/

hooks/

styles/
```

---

# Feature Frontend

```text
feature/

pages/

components/

dialogs/

hooks/

services/

types/

tests/
```

---

# Tests

```text
tests/

unit/

integration/

contract/

workflow/

performance/

e2e/
```

---

# Dokumentation

```text
docs/

foundation/

features/

reference/

architecture/

technical/

implementation/
```

---

# Verbotene Abhängigkeiten

Nicht zulässig

```text
Feature

↓

Repository eines anderen Features
```

Nicht zulässig

```text
Frontend

↓

Database
```

Nicht zulässig

```text
Controller

↓

SQL
```

---

# Zulässige Abhängigkeiten

```text
Frontend

↓

API

↓

Service

↓

Domain

↓

Repository

↓

Database
```

---

# Erweiterungen

Neue Features werden ausschließlich

unter

```text
features/
```

angelegt.

---

# Zusammenfassung

Die Source Architecture bildet die technische Grundlage der gesamten Codebasis.

Alle Features folgen derselben Struktur.

Dadurch bleibt das Repository unabhängig von der Projektgröße konsistent und wartbar.
