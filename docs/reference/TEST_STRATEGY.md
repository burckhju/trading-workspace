# Test Strategy

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | TEST_STRATEGY.md |
| Dokumenttyp | Reference |
| Version | 0.1 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-01 |

---

# Zweck

Zentrale Referenz für Testarten, Testablage und Qualitätsnachweise.

# Teststruktur

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

# Grundregeln

- neue Fachlogik benötigt automatisierte Tests
- Fehlerkorrekturen sollen einen Regressionstest enthalten
- externe Provider werden in regulären Tests kontrolliert ersetzt
- Tests sind deterministisch und verwenden keine produktiven Geheimnisse
- die Repository-Skripte und CI-Workflows sind die verbindlichen Prüfeinstiege

# Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-08-01 | Sprint-0-Baseline angelegt |
