# ADR-S3-007 – Lokales Rate-Limiting und tägliches Call-Budget

## Status

Accepted – 2026-08-05

## Kontext

EODHD rechnet API-Nutzung in Calls ab und dokumentiert tarifabhängige Grenzen. Kurzfristige Parallelität und täglicher Gesamtverbrauch müssen unabhängig geschützt werden.

## Entscheidung

Sprint 3 kombiniert einen lokalen Token-Bucket mit einem konfigurierbaren täglichen Call-Budget und zehn Prozent Sicherheitsreserve. Der Reset erfolgt nach UTC. Die Standardentwicklungskonfiguration verwendet ein Budget von 20 Calls; Produktion muss den Wert explizit setzen.

Mehrsymbol- und Bulk-Endpunkte sind in Sprint 3 ausgeschlossen. Der Betrieb ist auf eine koordinierte Backendinstanz begrenzt.

## Konsequenzen

- versehentliche Kosten und Limitüberschreitungen werden reduziert,
- mehrere Prozesse sind ohne zentralen Limiter nicht freigegeben,
- Call-Kosten müssen je Adapteroperation erfasst werden,
- ein späteres Redis-Backend kann hinter derselben Schnittstelle ergänzt werden.
