# Sprint 3 – Marktdaten-Infrastruktur und EODHD

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | SPRINT_3_SPECIFICATION.md |
| Dokumenttyp | Implementierungsreife Sprint-Spezifikation |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-05 |

## Zweck

Dieses Dokument schließt die offenen fachlichen und technischen Punkte vor der Implementierung von Sprint 3. Es ist gemeinsam mit den ADRs `ADR-S3-001` bis `ADR-S3-009` verbindliche Grundlage für das Architekturreview.

## 1. Sprintumfang

### 1.1 Im Sprint enthalten

Sprint 3 stellt folgende Fähigkeiten bereit:

1. providerunabhängiger Abruf historischer End-of-Day-Tageskurse für bestehende Listings aus FT-001,
2. Abruf des zuletzt verfügbaren abgeschlossenen EOD-Datensatzes,
3. Auflösung und Verwaltung der Zuordnung zwischen internem Listing und EODHD-Symbol,
4. EODHD-Adapter mit validierten Provider-DTOs und explizitem Mapping,
5. API-Key-Verwaltung über Backend-Secrets,
6. providerunabhängige Fehlerhierarchie,
7. begrenzte Retry-Strategie für transiente Fehler,
8. providerbezogenes Rate-Limiting und tägliches Verbrauchsbudget,
9. technischer Cache mit sichtbarer Herkunft und Aktualität,
10. fachliche Persistenz validierter EOD-Tageskurse,
11. Backend-Unit-, Contract- und Integrationstests,
12. Architektur-, Betriebs- und Mappingdokumentation.

### 1.2 Nicht Bestandteil

Nicht Bestandteil von Sprint 3 sind:

- Intraday-Kurse,
- Echtzeit- oder WebSocket-Daten,
- Fundamentaldaten,
- Nachrichten, Sentiment oder technische Indikatoren,
- Marktdaten für Optionsscheine,
- Corporate-Actions-Verarbeitung außer der transparenten Übernahme von `adjusted_close`,
- automatische Handelsentscheidungen, Signale oder Empfehlungen,
- automatische Änderung von FT-001-Stammdaten,
- Providerkonfiguration im Frontend,
- verteiltes Caching oder verteiltes Rate-Limiting,
- Hintergrund-Synchronisation ohne expliziten Anwendungsfall.

## 2. Feature- und Modulgrenze

Die technische Kennung lautet `market_data`.

`market_data` ist eine technische und fachliche Unterstützungsfähigkeit, jedoch kein neues Benutzerentscheidungsfeature im Katalog FT-001 bis FT-013. Die bestehende Nummerierung wird nicht verändert. Das spätere benutzerverwaltete Providerfeature bleibt separat.

Verantwortung:

```text
FT-001 underlying
- besitzt Basiswert und Listing
- besitzt Ticker, Handelsplatz und Währung
- wird niemals durch Providerdaten überschrieben

market_data
- besitzt Providerzuordnungen
- besitzt validierte Marktdaten und Abrufmetadaten
- konsumiert Listing-IDs
- entscheidet nicht über Trades

providers/eodhd
- besitzt ausschließlich EODHD-Transport, DTOs und Mapping
```

## 3. Interne Contracts

Die Contracts werden capability-basiert definiert.

```python
class HistoricalDailyPriceProvider(Protocol):
    async def get_daily_prices(
        self,
        request: DailyPriceRequest,
    ) -> MarketDataResult[tuple[DailyPrice, ...]]: ...

class LatestCompletedDailyPriceProvider(Protocol):
    async def get_latest_completed_daily_price(
        self,
        request: LatestDailyPriceRequest,
    ) -> MarketDataResult[DailyPrice | None]: ...

class ProviderInstrumentResolver(Protocol):
    async def validate_mapping(
        self,
        mapping: ProviderInstrumentMapping,
    ) -> MappingValidationResult: ...
```

Ein Adapter implementiert nur die Fähigkeiten, die der Provider tatsächlich unterstützt.

## 4. Interne Datenmodelle

### 4.1 ProviderInstrumentMapping

| Feld | Typ | Regel |
|---|---|---|
| id | UUID | interne Identität |
| workspace_id | UUID | bestehender V1-Workspace |
| listing_id | UUID | Referenz auf FT-001-Listing |
| provider | Enum | zunächst `EODHD` |
| provider_symbol | String | normalisiert, providerbezogen |
| provider_exchange_code | String | normalisiert, providerbezogen |
| status | Enum | `ACTIVE`, `INVALID`, `DISABLED` |
| validated_at | UTC datetime optional | letzter erfolgreicher Abgleich |
| validation_message | String optional | keine Secrets |
| created_at/updated_at | UTC datetime | Audit-Metadaten |
| version | Integer | Optimistic Locking |

Eindeutigkeit:

- `(workspace_id, listing_id, provider)` ist eindeutig.
- `(provider, provider_symbol, provider_exchange_code)` darf mehreren internen Listings nur nach expliziter Architekturfreigabe zugeordnet werden; in Sprint 3 ist die Kombination eindeutig.

### 4.2 DailyPrice

| Feld | Typ | Regel |
|---|---|---|
| listing_id | UUID | interne Instrumentreferenz |
| trading_date | date | Börsenhandelstag, kein UTC-Tag |
| open/high/low/close | Decimal | positiv, konsistente OHLC-Regeln |
| adjusted_close | Decimal optional | unverändert als Providerwert übernommen |
| volume | Decimal optional | nicht negativ |
| currency | ISO-4217 String | aus Listing; Abweichung ist Fehler |
| provider | Enum | Herkunft |
| provider_symbol | String | Provenance, keine Fachidentität |
| retrieved_at | UTC datetime | eigener Abrufzeitpunkt |
| source_updated_at | UTC datetime optional | nur falls Provider liefert |
| quality_status | Enum | `VALID`, `INCOMPLETE`, `SUSPICIOUS` |
| warnings | Tuple[String, ...] | explizite Qualitätswarnungen |

Validierung:

- `low <= open <= high`,
- `low <= close <= high`,
- bei vorhandenem `adjusted_close` muss der Wert positiv sein,
- fehlendes Volumen ist erlaubt und wird nicht durch `0` ersetzt,
- unbekannte Werte bleiben `None`,
- Preise werden als `Decimal` aus Strings oder exakten JSON-Zahlen erzeugt.

### 4.3 MarketDataResult

Jedes Ergebnis enthält:

- Daten,
- Provider,
- Capability,
- Request-Correlation-ID,
- `retrieved_at`,
- Cache-Status `HIT`, `MISS`, `BYPASS`, `STALE_REJECTED`,
- Qualitätsstatus,
- Warnungen,
- Retry-Anzahl,
- Verbrauchskosten in Provider-Calls, soweit bestimmbar.

## 5. Symbol-Mapping und Datenownership

Das Mapping wird in Sprint 3 manuell über eine administrative Backend-API angelegt und anschließend technisch gegen EODHD validiert. Die aufrufende Person muss administrativ berechtigt sein; Sprint 3 führt dafür kein neues fachliches Rollenmodell ein, sondern verwendet die bestehende beziehungsweise betriebliche Zugriffskontrolle.

Automatische Vorschläge dürfen später ergänzt werden, dürfen aber nie ohne Benutzer- oder Administratorfreigabe gespeichert werden.

Providerdaten dürfen keine Felder von Underlying oder Listing ändern. Insbesondere werden Ticker, ISIN, WKN, Handelsplatz, Name und Währung nicht automatisch überschrieben.

EODHD verwendet typischerweise eine Kombination aus Symbol und Exchange-Code. Diese Kombination bleibt ausschließlich Provideridentität. Der EODHD-Endpunkt für Börsensymbole kann zur Validierung verwendet werden.

## 6. Persistenz

Validierte historische Tageskurse werden fachlich persistiert.

Vorgesehene Eindeutigkeit:

```text
(workspace_id, listing_id, trading_date, price_type)
```

`price_type` ist in Sprint 3 fest `EOD` und verhindert spätere Schemaänderungen bei zusätzlichen Granularitäten.

Gespeichert werden zusätzlich:

- Provider und Provider-Symbol als Herkunft,
- Abrufzeit,
- Qualitätsstatus,
- Import- oder Request-Correlation-ID,
- `created_at` und `updated_at`,
- Hash der normalisierten Marktdaten zur Änderungserkennung.

Provider-Rohantworten werden nicht dauerhaft gespeichert. Contract-Fixtures enthalten anonymisierte beziehungsweise öffentliche Beispielantworten ohne API-Key.

Erneut gelieferte identische Tageswerte sind idempotent. Abweichende Werte aktualisieren den Datensatz kontrolliert und erzeugen ein Audit-Event mit alten und neuen normalisierten Werten.

## 7. Cache

Der technische Cache ist von der fachlichen Persistenz getrennt.

Sprint 3 verwendet ein injizierbares In-Memory-Backend. Die Schnittstelle erlaubt später Redis ohne Änderung der Application Services.

TTL-Regeln:

| Datenart | TTL |
|---|---|
| abgeschlossene historische Zeiträume | 24 Stunden |
| letzter abgeschlossener EOD-Datensatz während Börsentag | 15 Minuten |
| letzter abgeschlossener EOD-Datensatz nach erwarteter Provideraktualisierung | 60 Minuten |
| Mapping-Validierung erfolgreich | 24 Stunden |
| `not found` | 5 Minuten |
| Authentifizierungs- und Berechtigungsfehler | kein Cache |

Stale-Daten werden in Sprint 3 bei Providerfehlern nicht automatisch ausgeliefert. `stale-if-error` ist bewusst ausgeschlossen.

## 8. Retry

Maximal drei Gesamtversuche einschließlich Erstversuch.

Retryfähig:

- Netzwerkverbindungsfehler,
- Connect-, Read- und Pool-Timeout,
- HTTP 429,
- HTTP 502, 503 und 504.

Nicht retryfähig:

- HTTP 400, 401, 403, 404,
- Validierungs- und Mappingfehler,
- fehlende Konfiguration,
- Währungs- oder Instrumentkonflikte.

Backoff:

```text
base_delay = 0.5 Sekunden
exponentiell: 0.5, 1.0 Sekunden
full jitter: [0, berechnete Verzögerung]
Retry-After hat Vorrang, begrenzt auf 30 Sekunden
maximale Gesamtdauer eines Provideraufrufs: 45 Sekunden
```

Clock, Zufallsgenerator und Sleeper sind injizierbar.

## 9. Rate-Limiting und Budget

Sprint 3 verwendet zwei Schutzebenen:

1. lokaler Token-Bucket für kurzfristige Lastspitzen,
2. tägliches konfiguriertes Call-Budget mit Sicherheitsreserve.

EODHD dokumentiert ein allgemeines Tageslimit von 100.000 API-Requests; einzelne Pläne, insbesondere der kostenlose Zugang, können deutlich niedrigere Grenzen besitzen. Die Anwendung darf deshalb keinen festen Tarifwert voraussetzen.

Konfiguration:

```text
requests_per_second = 5
burst_capacity = 10
daily_call_budget = explizit erforderlich
daily_safety_reserve_percent = 10
budget_reset_timezone = UTC
```

Das Tagesbudget wird standardmäßig auf `20` gesetzt, damit eine Entwicklungskonfiguration nicht versehentlich einen kostenpflichtigen Umfang voraussetzt. Produktion muss den Wert explizit konfigurieren.

Ein Symbolabruf wird als mindestens ein Provider-Call verbucht. Mehrsymbol- oder Bulk-Operationen sind in Sprint 3 ausgeschlossen, weil EODHD deren Kosten anders berechnet.

## 10. API-Key und Secrets

Der API-Key wird ausschließlich über `TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY` oder ein kompatibles Secret-Backend geliefert.

Regeln:

- der Key ist ein Pydantic-`SecretStr`,
- der Key wird nie serialisiert oder geloggt,
- URL-Queryparameter werden vor Logging redigiert,
- Tests prüfen Redaction,
- der Key ist nicht Teil von Exceptions, Cache-Keys oder Metriklabels,
- die Anwendung darf ohne Key starten,
- der EODHD-Adapter erhält dann den Status `DISABLED_CONFIGURATION`,
- ein tatsächlicher EODHD-Aufruf liefert einen kontrollierten Konfigurationsfehler.

## 11. Fehlervertrag

Interne Fehlercodes:

| Code | retryable | API-Status |
|---|---:|---:|
| `MARKET_DATA_CONFIGURATION_ERROR` | nein | 503 |
| `MARKET_DATA_AUTHENTICATION_FAILED` | nein | 502 |
| `MARKET_DATA_ACCESS_DENIED` | nein | 502 |
| `MARKET_DATA_RATE_LIMITED` | ja | 503 |
| `MARKET_DATA_TIMEOUT` | ja | 504 |
| `MARKET_DATA_PROVIDER_UNAVAILABLE` | ja | 503 |
| `MARKET_DATA_NOT_FOUND` | nein | 404 |
| `MARKET_DATA_INVALID_RESPONSE` | nein | 502 |
| `MARKET_DATA_MAPPING_FAILED` | nein | 422 |
| `MARKET_DATA_BUDGET_EXHAUSTED` | nein | 503 |

Providerantworten und technische Ursachen werden intern protokolliert, aber nicht ungefiltert an den Client gegeben.

## 12. REST-API-Grenze

Sprint 3 stellt eine Backend-API bereit, jedoch keine neue Frontendansicht.

Vorgesehene Endpunkte:

```text
GET  /api/v1/market-data/listings/{listing_id}/daily-prices
GET  /api/v1/market-data/listings/{listing_id}/daily-prices/latest
PUT  /api/v1/market-data/listings/{listing_id}/provider-mappings/eodhd
GET  /api/v1/market-data/listings/{listing_id}/provider-mappings
GET  /api/v1/market-data/providers/status
```

Regeln:

- maximaler Zeitraum pro Historienanfrage: 10 Jahre,
- `from` und `to` sind inklusive,
- Standardzeitraum: letzte 365 Kalendertage,
- die API gibt ausschließlich interne DTOs zurück,
- ein expliziter `refresh=true` darf den Cache umgehen, unterliegt aber Rate-Limit und Budget,
- keine API nimmt einen API-Key entgegen.

## 13. EODHD-spezifische Festlegungen

Verwendete Fähigkeiten:

- End-of-Day Historical Data API,
- Exchange Symbols API zur Mappingvalidierung,
- optional User API ausschließlich zur technischen Verbrauchsbeobachtung, sofern der Tarif sie erlaubt.

EODHD gibt EOD-Historien symbolbezogen aus; ein Symbolrequest zählt im allgemeinen Kostenmodell als ein API-Call. Die Aktualisierungszeit kann je Börse variieren; EODHD beschreibt Aktualisierungen typischerweise einige Stunden nach Börsenschluss und für große US-Börsen teilweise früher. Deshalb wird Datenaktualität nicht aus der lokalen Uhr allein abgeleitet.

Der API-Key wird trotz providerseitiger Queryparameter-Authentifizierung ausschließlich im EODHD-Client ergänzt und vor Logs vollständig redigiert.

## 14. Testumfang

### Unit

- Modelle und OHLC-Regeln,
- Decimal-Konvertierung,
- Mapping aller EODHD-Felder,
- Fehlerübersetzung,
- Retryklassifikation und Backoff,
- Rate-Limiter und Tagesbudget,
- Cache-Key, TTL und Cache-Status,
- Secret-Redaction.

### Contract

Versionierte JSON-Fixtures für:

- gültige EOD-Historie,
- leere Liste,
- optionale Werte,
- unbekannte Zusatzfelder,
- ungültige Datentypen,
- semantisch ungültiges OHLC,
- Fehlerantworten und HTTP-Status.

### Integration

- lokaler Mock-HTTP-Server,
- Timeout und Retry,
- `Retry-After`,
- Cache-Hit/Miss/Bypass,
- idempotente Persistenz,
- Korrektur eines historischen Datensatzes mit Audit-Event,
- DI-Lifecycle,
- REST-Fehlervertrag.

Live-Tests sind mit `@pytest.mark.live_provider` markiert, standardmäßig deaktiviert und niemals CI-Voraussetzung.

## 15. Betriebsgrenzen

Sprint 3 unterstützt einen Backendprozess beziehungsweise eine einzelne koordinierte Instanz. Mehrere Worker würden unabhängige In-Memory-Caches und Limiter besitzen und sind bis zur Einführung eines zentralen Backends nicht freigegeben.

Metriken:

- Requests je Provider und Capability,
- Providerlatenz,
- Retry-Anzahl,
- Rate-Limit-Ereignisse,
- Budgetverbrauch,
- Cache-Hit-Rate,
- Mapping- und Qualitätsfehler.

Keine Metrik enthält Symbol und Benutzerkennung gemeinsam als hochkardinale Labels.

## 16. Abnahmekriterien vor Implementierungsstart

- ADR-S3-001 bis ADR-S3-009 sind freigegeben.
- REST-DTOs und Providercontracts sind reviewt.
- EODHD-Tarif und produktives Tagesbudget sind als Deploymentkonfiguration bekannt.
- Single-Instance-Betriebsgrenze ist akzeptiert.
- Die fachliche Persistenz historischer EOD-Kurse ist bestätigt.

## 17. Externe Referenzen

Geprüft am 2026-08-05:

- EODHD, *End-of-Day Historical Stock Market Data API*
- EODHD, *API Limits: calls, requests, consumption*
- EODHD, *Financial Exchanges API – Exchange Symbols*
- EODHD, *Quick Start with Financial Data APIs*
- EODHD, *User API*

Providerlimits und Tarifmerkmale bleiben Deploymentkonfiguration und werden vor Produktivbetrieb erneut verifiziert.


## 16. Architekturfreigabe

Die Spezifikation und die ADRs `ADR-S3-001` bis `ADR-S3-009` wurden am 2026-08-05 im Architekturreview angenommen.

Freigegebene Betriebsgrenzen:

- historische EOD-Kurse werden fachlich persistiert,
- Sprint 3 wird mit genau einer koordinierten Backendinstanz betrieben,
- das produktive EODHD-Tagesbudget muss vor Deployment explizit gesetzt werden,
- Provider-Mappings werden über eine administrative Backend-Funktion gepflegt,
- Intraday-, Echtzeit- und Optionsscheinmarktdaten bleiben ausgeschlossen.
