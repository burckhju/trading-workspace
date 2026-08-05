# Sprint 3 – Arbeitseinheit 2: Persistenz

## Status

Abgeschlossen am 2026-08-05.

## Umfang

Diese Arbeitseinheit implementiert ausschließlich die providerunabhängige Persistenz für:

- administrative Provider-Instrument-Mappings,
- fachlich persistierte, abgeschlossene EOD-Tageskurse,
- Repositorycontracts und SQLAlchemy-Adapter,
- eine eigene Market-Data-Unit-of-Work,
- die Alembic-Migration `20260805_0002`.

HTTP, EODHD, Cache, Retry, Rate-Limiting und REST-API sind nicht Bestandteil dieser Einheit.

## Tabellen

### `provider_instrument_mappings`

Die Tabelle trennt interne Listing-Identitäten von externen Providersymbolen. Pro Provider ist höchstens ein Mapping je Listing erlaubt. Zusätzlich ist die Kombination aus Provider, Providerbörsencode und Providersymbol eindeutig. Änderungen verwenden Optimistic Locking über `version`.

### `daily_prices`

Die Tabelle speichert abgeschlossene Tageskurse unabhängig vom Providerformat. Die fachliche Eindeutigkeit ist `(listing_id, trading_date, price_type)`. Dadurch kann ein erneuter Abruf denselben fachlichen Datensatz aktualisieren, statt Duplikate zu erzeugen.

Persistiert werden Preise, optionale Volumina, Währung, Provider-Provenance, Abrufzeitpunkt, Providerzeitpunkt, Qualitätsstatus und Warnungen. Technische Cacheinformationen werden bewusst nicht gespeichert.

## Idempotenz und Änderungserkennung

`apply_daily_price` vergleicht alle persistierten fachlichen und Provenance-Felder. `updated_at` wird nur verändert, wenn sich mindestens ein Wert tatsächlich geändert hat. Unveränderte Wiederholungsabrufe bleiben damit idempotent und erzeugen keine künstliche Änderung.

## Transaktionen

Repositories führen niemals `commit` aus. Die Transaktionsgrenze liegt ausschließlich in `SqlAlchemyMarketDataUnitOfWork`. Bei einer Exception innerhalb des Context Managers wird zurückgerollt.

## Qualitätssicherung

Erfolgreich ausgeführt:

- 24 Tests im Scope `features/market_data`,
- 10 Regressionstests für bestehende FT-001-Persistenz und Repositories,
- Python-Bytecode-Kompilierung der neuen Module.

Black, Ruff und MyPy konnten in der gelieferten Laufzeit nicht ausgeführt werden, weil die vorhandene Toolumgebung diese Module nicht enthält. Dies ist ein transparenter Quality-Gate-Rest und kein nachgewiesener Quellcodefehler.

## Architekturkonformität

- keine EODHD-Abhängigkeit in Domain oder Persistenzcontract,
- keine FastAPI-Abhängigkeit,
- keine Vermischung von technischem Cache und fachlicher Historie,
- Workspace-Scoping in allen Lesezugriffen,
- bestehende FT-001-Tabellen und Contracts bleiben unverändert.
