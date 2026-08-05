# ADR-S3-008 – Backendseitige API-Key-Verwaltung

## Status

Accepted – 2026-08-05

## Kontext

Der EODHD-Key ist ein Secret und darf nicht in Repository, Frontend, Logs, Fehler, Cache-Keys oder Metriken gelangen.

## Entscheidung

Der Key wird als Pydantic-`SecretStr` aus Umgebungsvariablen oder einem späteren kompatiblen Secret-Backend geladen. Die Anwendung darf ohne Key starten; der Adapter ist dann deaktiviert und meldet bei Nutzung einen kontrollierten Konfigurationsfehler.

HTTP-Logging redigiert Authentifizierungsparameter vollständig. Security-Tests prüfen die Redaction.

## Konsequenzen

- lokale Entwicklung ohne Providerzugriff bleibt möglich,
- Fehlkonfiguration wird erst bei Statusprüfung oder Nutzung sichtbar,
- ein späterer Secret Manager erfordert keine Fachlogikänderung,
- technische Diagnose muss ohne Ausgabe des Keys auskommen.
