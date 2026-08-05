# Sprint 3 – Arbeitseinheit 5: EODHD-Mapping und Adapter

## Status

Abgeschlossen.

## Umfang

- providerunabhängiges Mapping von EODHD-Tageskursen auf `DailyPrice`
- Implementierung der Capabilities `HISTORICAL_DAILY_PRICES` und `LATEST_COMPLETED_DAILY_PRICE`
- Auflösung freigegebener Provider-Mappings und interner Listing-Währungen über Ports
- capability-spezifische Cache-Keys und TTLs
- Orchestrierung von Tagesbudget, Token-Bucket und Retry
- sichtbare Provenance, Cachezustände, Retry-Anzahl und Providerkosten

## Architekturgrenzen

Der Adapter kennt EODHD-Transportdetails. Domain und Servicecontracts bleiben frei von EODHD, HTTPX und Persistenzimplementierungen. Provider-Symbole werden nicht als interne Listing-Identität verwendet.

Cache-Hits verursachen keine Providerkosten. Bei einem Cache-Miss wird jeder tatsächliche Provider-Versuch vor dem HTTP-Aufruf budgetiert und rate-limitiert. Abgelaufene Cachewerte werden verworfen und als `STALE_REJECTED` ausgewiesen.

## Qualitätsregeln

- EODHD-DTOs werden vor dem Mapping strukturell validiert.
- Interne OHLC-Regeln werden ausschließlich durch das Domainmodell erzwungen.
- Mappingfehler sind permanent und nicht retryfähig.
- Leere Providerantworten werden nicht erfunden, sondern als unvollständiges Resultat mit Warnung zurückgegeben.
- Der neueste Tageskurs wird aus einem begrenzten 14-Tage-Fenster bis zum angegebenen Stichtag bestimmt.

## Tests

- Mapper: gültige Konvertierung und widersprüchliche OHLC-Werte
- Adapter: historischer Abruf, Sortierung, Cache-Hit, Providerkosten und letzter abgeschlossener Tageskurs
- vollständige Unit- und EODHD-Contract-Suite: 140 Tests erfolgreich

## Noch offen

- Persistenzorchestrierung der abgerufenen Tageskurse
- Dependency-Injection-Lifecycle und produktive Settings
- Mappingvalidierungs-Capability
- REST-API und API-Fehlerübersetzung
- technische Metriken
