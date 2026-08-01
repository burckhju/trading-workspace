# Source Architecture

## Dokumentinformationen

| Eigenschaft | Wert |
|---|---|
| Dokument | SOURCE_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | Projektverantwortlicher |
| Freigabedatum | 2026-08-01 |

---

# Zweck

Dieses Dokument definiert die verbindliche Struktur des Quellcodes und der Projektdateien des **Trading Workspace**.

Ziele sind:

- eindeutige Verantwortlichkeiten
- geringe Kopplung
- hohe Wartbarkeit
- nachvollziehbare Erweiterbarkeit
- keine doppelte Implementierung

Die Struktur ist für alle zukünftigen Entwicklungen verbindlich.

---

# Architekturprinzipien

- Feature-orientierte Struktur
- Trennung von Fachlichkeit und Technik
- geringe Abhängigkeiten
- hohe Testbarkeit
- klare Verantwortlichkeiten

Jedes Artefakt besitzt genau einen fachlichen Eigentümer.

---

# Repositorystruktur

```text
trading-workspace/
├── backend/
├── frontend/
├── docs/
├── tests/
├── scripts/
├── docker/
├── .github/
├── README.md
├── .gitignore
├── .editorconfig
└── .dockerignore
```

---

# Backend

```text
backend/
├── app/
│   ├── core/
│   ├── shared/
│   ├── features/
│   ├── providers/
│   ├── database/
│   ├── events/
│   └── main.py
├── migrations/
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .env.example
└── .python-version
```

---

# Backend-Feature

```text
feature/
├── api/
├── services/
├── domain/
├── repositories/
├── schemas/
├── validators/
├── events/
└── mappers/
```

---

# Frontend

```text
frontend/
├── src/
│   ├── app/
│   ├── features/
│   ├── shared/
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   ├── services/
│   ├── types/
│   ├── hooks/
│   ├── styles/
│   ├── assets/
│   ├── utils/
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── eslint.config.js
├── Dockerfile
├── .env.example
└── .nvmrc
```

---

# Tests

```text
tests/
├── unit/
├── integration/
├── contract/
├── workflow/
├── performance/
├── e2e/
└── fixtures/
```

---

# Dokumentation

```text
docs/
├── foundation/
├── architecture/
├── technical/
├── implementation/
├── features/
└── reference/
```

---

# Zulässige Abhängigkeiten

Frontend → API → Application Service → Domain → Repository → Database

---

# Verbotene Abhängigkeiten

- Frontend → Database
- API → SQL
- Domain → Framework
- Direkte Zugriffe auf interne Bestandteile anderer Features

---

# Erweiterungen

Neue Features werden ausschließlich angelegt unter:

```text
backend/app/features/<feature>/
frontend/src/features/<feature>/
docs/features/<feature>/
tests/<testart>/<feature>/
```

---

# Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Struktur überarbeitet und Repository abgeglichen |
