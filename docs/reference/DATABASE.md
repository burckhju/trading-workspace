# Database Reference

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | DATABASE.md |
| Dokumenttyp | Reference |
| Version | 0.1 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-01 |

---

# Zweck

Zentrale Referenz für Datenverantwortung, Schema, Migrationen, Einheiten, Zeitbezug und historische Stabilität.

# Verbindliche Regeln

- Schemaänderungen ausschließlich über versionierte Alembic-Migrationen
- fachliche IDs als UUID
- Zeitpunkte intern in UTC mit Zeitzoneninformation
- Geldwerte mit Decimal und dokumentierter Währung/Rundung
- historische Modell- und Tradezuordnungen werden nicht überschrieben
- Repositories kapseln Persistenz; Geschäftslogik bleibt in Domain und Services

# Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-08-01 | Sprint-0-Baseline angelegt |
