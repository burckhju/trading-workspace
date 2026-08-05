# Sprint 3 – Bearbeitung der offenen Punkte

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | SPRINT_3_OPEN_POINTS_RESOLUTION.md |
| Dokumenttyp | Architecture Work Unit Review |
| Version | 1.1 |
| Status | 🟢 Closed by Architecture Review |
| Letzte Änderung | 2026-08-05 |

## 1. Erledigte Arbeiten

- Sprintumfang auf historische EOD-Tageskurse für bestehende Basiswert-Listings begrenzt.
- Intraday, Echtzeit, Fundamentaldaten, Optionsscheinmarktdaten und automatische Synchronisation als Nicht-Ziele festgelegt.
- Eigenständige Featuregrenze `market_data` definiert.
- Bestehende FT-Nummerierung erhalten und technische Querschnittsfähigkeit `TC-001` ergänzt.
- Capability-basierte Providercontracts festgelegt.
- Interne Modelle für Mapping, Tageskurse, Qualität und Provenance definiert.
- Datenownership zwischen FT-001, `market_data` und `providers/eodhd` festgelegt.
- Manuelles, validiertes EODHD-Symbol-Mapping beschlossen.
- Fachliche EOD-Persistenz vom technischen Cache getrennt.
- Cache-TTLs und Ausschluss von `stale-if-error` festgelegt.
- Retryklassifikation, Backoff und Gesamtdauer festgelegt.
- Lokales Rate-Limiting und tägliches Call-Budget definiert.
- Secret-Verwaltung und Redactionregeln definiert.
- Providerunabhängiger Fehlervertrag festgelegt.
- REST-API-Grenze und maximale Abfragezeiträume festgelegt.
- Unit-, Contract-, Integrations- und optionale Live-Tests spezifiziert.
- Single-Instance-Betriebsgrenze für Sprint 3 dokumentiert.
- Inkonsistente Zuordnung „FT-010 Data Providers“ im Tech Stack korrigiert.

## 2. Offene Punkte

Die zuvor freigabepflichtigen Punkte wurden im Architekturreview wie folgt geschlossen:

1. ADR-S3-001 bis ADR-S3-009 sind angenommen.
2. Historische EOD-Kurse werden fachlich persistiert.
3. Die Single-Instance-Betriebsgrenze ist bestätigt.
4. Tarif und produktives Tagesbudget bleiben verpflichtende Deploymentkonfiguration; es gibt keine hart codierte Produktionsannahme.
5. Provider-Mappings werden über eine administrative Backend-Funktion gepflegt; eine Frontendoberfläche bleibt außerhalb von Sprint 3.

Es bestehen keine architektonischen Blocker für den Implementierungsstart.

## 3. Risiken

| Risiko | Bewertung | Behandlung |
|---|---|---|
| Tarif- oder Limitabweichung bei EODHD | mittel | keine hart codierten Tarifannahmen; explizite Konfiguration |
| Mehrere Backendworker überschreiten lokales Budget | hoch | Sprint 3 auf eine koordinierte Instanz begrenzt |
| Falsches Provider-Mapping | hoch | manuelle Anlage, Providerprüfung, Status und Audit |
| Providerkorrekturen verändern Historie | mittel | Hashvergleich, kontrolliertes Update, Audit-Event |
| Cache verdeckt Aktualität | mittel | Cache-Status und Zeitpunkte in jedem Ergebnis |
| API-Key in Query-Logs | hoch | zentrale URL-Redaction und Security-Tests |
| Scope-Ausweitung auf Intraday/Echtzeit | hoch | explizite Nicht-Ziele und separate spätere ADRs |

## 4. Architekturentscheidungen

Zur Freigabe vorbereitet:

- ADR-S3-001 – Eigenständige Marktdaten-Fähigkeit
- ADR-S3-002 – Capability-basierte Providercontracts
- ADR-S3-003 – Interne Marktdatenmodelle und Provenance
- ADR-S3-004 – Separates Provider-Instrument-Mapping
- ADR-S3-005 – Fachliche EOD-Persistenz und getrennter technischer Cache
- ADR-S3-006 – Begrenzte Retry- und Fehlerstrategie
- ADR-S3-007 – Lokales Rate-Limiting und tägliches Call-Budget
- ADR-S3-008 – Backendseitige API-Key-Verwaltung
- ADR-S3-009 – Sprint-3-Datenumfang

Alle ADRs stehen seit dem Architekturreview vom 2026-08-05 auf `Accepted`. Es wurde weiterhin kein Produktivcode implementiert.

## 5. Nächster empfohlener Schritt

Implementierung der Arbeitseinheit 1: interne Modelle, capability-basierte Contracts und providerunabhängige Fehlerhierarchie einschließlich Unit-Tests und Dokumentation.
