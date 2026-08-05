# Sprint 3 – Arbeitseinheit 7: Dependency Injection und Provider-Lifecycle

## Status

Abgeschlossen.

## Umfang

Diese Arbeitseinheit verdrahtet die bereits implementierten, providerunabhängigen
Marktdatenbausteine mit dem optionalen EODHD-Provider. Sie führt keine öffentliche
REST-API ein.

## Prozessweite Ressourcen

Der `ApplicationContainer` besitzt bei aktiviertem EODHD-Provider genau eine
Instanz der folgenden technischen Ressourcen:

- `httpx.AsyncClient`,
- EODHD-Transportclient,
- In-Memory-TTL-Cache,
- Retry-Policy,
- Token-Bucket-Limiter,
- tägliches Call-Budget,
- EODHD-Market-Data-Adapter.

Der gemeinsame HTTP-Client wird beim Application-Shutdown vor dem
`DatabaseManager` geschlossen.

## Deaktivierter Betrieb

Bei `EODHD__ENABLED=false` wird keine Providerressource erzeugt. Ein API-Key ist
in diesem Modus nicht erforderlich und die Anwendung bleibt vollständig
startfähig.

Bei `EODHD__ENABLED=true` ist ein API-Key zwingend. Eine fehlende Konfiguration
führt beim Aufbau des Containers zu einem stabilen
`MarketDataConfigurationError`.

## Paid-Account-Konfiguration

Tageslimit, absolute Sicherheitsreserve, Requests pro Minute, Burst-Kapazität,
Endpunktkosten, Cache-TTLs und Retryparameter sind Deploymentkonfiguration.
Die absolute Reserve wird beim Aufbau des generischen Budgets vom Tageslimit
abgezogen. Damit bleibt der vorhandene Budgetbaustein rückwärtskompatibel.

## Datenbankports

Der EODHD-Adapter verwendet zwei SQLAlchemy-gestützte Read-Ports:

- `SqlAlchemyMappingReader`,
- `SqlAlchemyListingCurrencyReader`.

Beide öffnen kurzlebige, verwaltete Sessions und geben ausschließlich interne
Werte zurück. SQLAlchemy-Modelle verlassen die Persistenzgrenze nicht.

## Transaktionsgrenze

`ApplicationContainer.daily_price_import_service()` erzeugt pro Nutzung eine
verwaltete Session, eine `SqlAlchemyMarketDataUnitOfWork` und einen
`DailyPriceImportService`. Repositories behalten weiterhin keine
Commit-Verantwortung.

## Qualitätssicherung

- 153 Backend-Unit-, Contract- und ausgewählte Integrationstests erfolgreich.
- Python-Bytecode-Kompilierung erfolgreich.
- Black, Ruff und MyPy waren in der gelieferten Laufzeitumgebung nicht
  installiert und bleiben Merge-Gates der standardisierten Python-3.12-Umgebung.

## Nicht Bestandteil

- öffentliche REST-API,
- API-Fehlerabbildung,
- Metriken,
- verteiltes Cache-/Rate-Limit-Backend,
- EODHD User-API-Synchronisation.
