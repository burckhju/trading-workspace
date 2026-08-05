# ADR-S1-013 – Fachliche Vollständigkeit und Verifikation

## Status

Accepted – 2026-08-03

## Kontext

Datenqualität und fachlicher Lebenszyklus dürfen nicht in einem einzigen Statusfeld vermischt werden.

## Entscheidung

FT-001 führt zwei getrennte Statusdimensionen:

1. Lebenszyklusstatus: `ACTIVE` oder `INACTIVE`.
2. Datenqualitätsstatus: `DRAFT`, `COMPLETE` oder `VERIFIED`.

Regeln:

- `DRAFT`: Mindestdaten sind vorhanden, aber mindestens eine definierte Vollständigkeitsregel ist nicht erfüllt.
- `COMPLETE`: alle für operative Nutzung festgelegten Pflicht- und Vollständigkeitsregeln sind erfüllt.
- `VERIFIED`: ein vollständiger Datensatz wurde vom Benutzer ausdrücklich bestätigt.
- `INACTIVE` bleibt ausschließlich Lebenszyklusstatus und kann mit jedem Datenqualitätsstatus kombiniert sein.

Der Datenqualitätsstatus wird nicht als freie Benutzereingabe behandelt. `DRAFT` und `COMPLETE` werden regelbasiert ermittelt; der Übergang zu `VERIFIED` ist eine explizite Benutzeraktion. Jede relevante Änderung eines verifizierten Datensatzes setzt den Datenqualitätsstatus mindestens auf `COMPLETE` zurück.

## Konsequenzen

- Operative Neuauswahl ist nur für `ACTIVE` und mindestens `COMPLETE` zulässig.
- Historische Referenzen bleiben unabhängig von beiden Statusdimensionen erhalten.
- Listen und Details zeigen Lebenszyklus und Datenqualität getrennt.
