# Sprint 3 – Arbeitseinheit 1: Domain und Contracts

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Status | Implemented |
| Datum | 2026-08-05 |
| Scope | Providerunabhängige Domainmodelle, Contracts und Fehler |

## Umgesetzt

- Paketgrenze `backend/app/features/market_data`
- unveränderliche interne Modelle `ProviderInstrumentMapping` und `DailyPrice`
- explizite Enums für Provider, Capability, Mapping, Qualität, Cache und Preisart
- Requests und generisches `MarketDataResult`
- capability-basierte Protocols
- providerunabhängige Domain- und Servicefehler
- Unit-Tests für Normalisierung, OHLC-Regeln, UTC, Provenance und Fehler-Metadaten

## Architekturgrenzen

Diese Arbeitseinheit enthält bewusst keine Abhängigkeit auf:

- EODHD,
- HTTPX,
- FastAPI,
- SQLAlchemy,
- Cache- oder Retry-Implementierungen.

Provider-DTOs dürfen später ausschließlich im jeweiligen Adapterpaket existieren. Die hier definierten Modelle sind der interne Vertrag.

## Entscheidungen

- Geld- und Volumenwerte verwenden `Decimal`; binäre `float`-Eingaben werden abgelehnt.
- Zeitstempel müssen timezone-aware und bereits nach UTC normalisiert sein.
- Provider-Symbol und Exchange-Code werden getrimmt und großgeschrieben.
- Ein aktives Mapping benötigt einen erfolgreichen Validierungszeitpunkt.
- Fehlendes Volumen bleibt `None`.
- Resultate tragen Herkunft, Cachezustand, Qualitätsstatus, Retry-Anzahl und Providerkosten sichtbar mit.

## Nächste Arbeitseinheit

Persistenzmodelle, Repositorycontracts, Migration und Unit-of-Work für Provider-Mappings und validierte EOD-Tageskurse.
