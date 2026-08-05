# Sprint 3 – Arbeitseinheit 4: EODHD-Transportgrenze

## Umfang

Diese Arbeitseinheit implementiert ausschließlich die technische Transportgrenze zu EODHD:

- immutable, geschachtelte Settings mit `SecretStr`,
- HTTPS-Validierung und Transport-Timeouts,
- zentrale Redaction bekannter Credential-Parameter,
- injizierbarer asynchroner HTTPX-Client,
- providerunabhängige Übersetzung von Netzwerk-, Timeout- und HTTP-Fehlern,
- strikte EODHD-DTOs und versionierte Contract-Fixtures.

Nicht enthalten sind Domain-Mapping, fachlicher Adapter, Cache-Orchestrierung, Persistenz-Service und REST-API.

## Fehlervertrag

`401`, `403`, `404`, `429` und temporäre `5xx`-Antworten werden explizit übersetzt. Nur Timeout, Netzwerkfehler, `429`, `408`, `425`, `500`, `502`, `503` und `504` sind retryfähig. `Retry-After` wird für numerische Sekunden übernommen. Antwortkörper und URLs werden nicht Bestandteil öffentlicher Fehlermeldungen.

## Sicherheitsregeln

Der API-Key wird ausschließlich als `SecretStr` gehalten, erst unmittelbar beim Request gelesen und niemals in öffentliche Fehlermeldungen aufgenommen. Logging-Code muss URLs und Parameter vor Ausgabe über die Redaction-Helfer bereinigen.
