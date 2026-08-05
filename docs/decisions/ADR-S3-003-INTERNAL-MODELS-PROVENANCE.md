# ADR-S3-003 – Interne Marktdatenmodelle und Provenance

## Status

Accepted – 2026-08-05

## Kontext

Providerdaten sind externe, nicht vertrauenswürdige Eingaben. Preise, Zeitpunkte, Qualität und Herkunft müssen vollständig nachvollziehbar sein.

## Entscheidung

Interne Modelle verwenden `Decimal`, explizite Währung, Handelstag, UTC-Abrufzeit, Providerherkunft, Qualitätsstatus, Warnungen und Cache-Status. Fehlende Werte werden als `None` modelliert und niemals stillschweigend ersetzt.

Provider-DTOs dürfen die Grenze des jeweiligen Adapterpakets nicht verlassen.

## Konsequenzen

- keine Blackbox und keine binären Rundungsannahmen,
- zusätzliche Metadaten in DTOs und Persistenz,
- striktes Mapping kann Providerantworten ablehnen,
- spätere Provider bleiben auf dasselbe interne Modell abbildbar.
