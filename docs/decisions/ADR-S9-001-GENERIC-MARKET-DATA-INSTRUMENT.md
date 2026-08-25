# ADR-S9-001 – Generische Market-Data-Instrument-Identität

**Status:** Accepted
**Datum:** 2026-08-25

## Kontext

FT-001 definiert `Underlying` und `Listing` bewusst für Aktien. `UnderlyingType` bleibt in V1 `STOCK`; ein `Listing` ist die Markt-/Ticker-/Währungsrepräsentation dieser Aktie. Die Top-down-Domäne besitzt dagegen eigenständige semantische `MarketReference`-Objekte für Indizes und Sektorindizes.

Die bisherige Source-Resolution verbindet `MarketReference` über `MarketReferenceListingAssignment` mit einem FT-001-`Listing`. Dadurch müssen DAX, S&P 500, Nasdaq-100 und spätere Referenzen indirekt die STOCK-only-Identität durchlaufen, obwohl sie keine Aktien sind. Provider-Mapping, DailyPrice und MarketAnalysis verwenden `listing_id` bislang zugleich als technische Market-Data-Identität.

## Entscheidung

Wir führen eine providerneutrale, asset-type-neutrale `MarketDataInstrument`-Identität ein. Sie bezeichnet ausschließlich die Fähigkeit eines internen Objekts, Provider-Mappings, Marktpreise und Analysen zu besitzen.

Ein `MarketDataInstrument` hat genau einen fachlichen Owner:

- `LISTING`: verweist auf ein FT-001-`Listing`.
- `MARKET_REFERENCE`: verweist auf eine semantische `MarketReference`.

Die Owner-Beziehung ist exklusiv. Provider-Symbole und Provider-Exchange-Codes bleiben Adapterdaten und werden nicht Teil der fachlichen Identität.

Der Runtime-Pfad für `MARKET_REFERENCE` löst Provider-Mappings direkt gegen diese neutrale Identität auf, persistiert Daily Prices mit `market_data_instrument_id` und führt FT-006 mit derselben Identität aus. Dafür werden weder synthetische `Underlying`- noch `Listing`-Datensätze erzeugt.

## Unveränderte Invarianten

- ADR-S1-001 bleibt gültig: `UnderlyingType` bleibt V1 `STOCK`.
- ADR-S1-002 bleibt gültig: `Underlying 1:n Listing` beschreibt Aktiennotierungen.
- `MarketReference` bleibt eine eigenständige, providerneutrale Top-down-Identität.
- FT-012-Learning-Referenzen auf `underlyings.id` behalten ihre bestehende Bedeutung und werden durch diese Entscheidung nicht umgedeutet.

## Evolution

Die Einführung erfolgt als Expand-and-Contract:

1. `market_data_instruments` wird angelegt und bestehende Listings sowie MarketReferences werden backfilled.
2. Provider-Mapping, DailyPrice und MarketAnalysis erhalten die neutrale Instrument-Identität; bestehende `listing_id`-Contracts bleiben während der Übergangsphase kompatibel.
3. Top-down Readiness, Provider-Mapping, Price-Ingestion und FT-006-Reference-Analyse verwenden `MarketReference -> MarketDataInstrument` statt der FT-001-Listing-Bridge.
4. Released Stock-Writer bleiben im Expand-Schritt kompatibel und werden separat auf die neutrale Identität migriert.
5. Erst nach vollständiger Consumer- und Writer-Validierung darf eine spätere Contract-Migration Legacy-Ownership verschärfen oder entfernen.

## Konsequenzen

DAX und andere Indizes benötigen kein synthetisches STOCK-Underlying. Neue analysierbare Asset-/Referenztypen können dieselbe Market-Data-Infrastruktur nutzen, ohne FT-001 fachlich zu erweitern. `MarketReferenceListingAssignment` kann für Historie und Kompatibilität bestehen bleiben, ist aber keine notwendige Readiness-Identität mehr.
