# Sprint 3 – Arbeitseinheit 3: Resilience-Infrastruktur

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Status | Implemented |
| Datum | 2026-08-05 |
| Scope | Technischer Cache, Retry, Rate-Limiting und Tagesbudget |

## Umgesetzt

- providerunabhängige Clock- und Sleeper-Protocols,
- produktive Implementierungen `SystemClock` und `AsyncioSleeper`,
- generischer, asynchron geschützter In-Memory-TTL-Cache,
- explizite Unterscheidung zwischen Cache-Miss, Hit und verworfenem Stale-Eintrag,
- Retry-Policy mit höchstens drei Gesamtversuchen,
- exponentielles Backoff mit Full Jitter,
- priorisierte und auf 30 Sekunden begrenzte `Retry-After`-Behandlung,
- maximales Provider-Aufrufbudget von 45 Sekunden,
- lokaler Token-Bucket mit kontinuierlicher Auffüllung,
- tägliches UTC-Call-Budget mit konfigurierbarer Sicherheitsreserve,
- stabiler Fehler `MARKET_DATA_BUDGET_EXHAUSTED`,
- deterministische Unit-Tests mit manueller Clock und sofortigem Test-Sleeper.

## Architekturgrenzen

Die Komponenten liegen unter `backend/app/providers/shared` und kennen keinen konkreten Providertransport. Sie importieren weder EODHD noch HTTPX, FastAPI oder SQLAlchemy.

Der technische Cache ist kein Repository und verändert keine fachlich persistierten EOD-Daten. Abgelaufene Werte werden entfernt und niemals automatisch als Fallback ausgeliefert.

Rate-Limiter und Tagesbudget sind ausdrücklich prozesslokal. Der freigegebene Sprint-3-Betrieb bleibt auf eine koordinierte Backendinstanz begrenzt.

## Verhaltensregeln

- Nur `MarketDataError` mit `retryable=True` wird wiederholt.
- `Retry-After` überschreibt das berechnete Jitter-Backoff, wird aber auf 30 Sekunden begrenzt.
- Ein Retry wird nicht begonnen, wenn bereits seine Wartezeit das Gesamtbudget überschreiten würde.
- Der Token-Bucket wartet asynchron und blockiert keinen Thread.
- Das tägliche Budget wird atomar verbraucht und bei Wechsel des UTC-Datums zurückgesetzt.
- Die Sicherheitsreserve reduziert das nutzbare Budget; sie ist kein nachträglicher Warnwert.
- Call-Kosten müssen positiv sein und werden später vom Adapter je Operation angegeben.

## Tests

Gezielte Resilience- und Market-Data-Tests:

```text
39 passed
```

Vollständige Backend-Unit-Suite:

```text
122 passed
```

Die Bytecode-Kompilierung war erfolgreich. Black, Ruff und MyPy sind in der verfügbaren Laufzeitumgebung nicht installiert und konnten nicht ausgeführt werden.

## Offene Integration

Die Komponenten werden erst in späteren Arbeitseinheiten über Settings und Dependency Injection verdrahtet. Insbesondere fehlen noch:

- EODHD-HTTP-Client,
- Übersetzung konkreter HTTP- und Netzwerkfehler,
- capability-spezifische Cache-Keys und TTL-Auswahl,
- technische Metriken,
- Lifecycle-Verkabelung im Application Container.

## Nächste Arbeitseinheit

EODHD-Transportgrenze: Settings, Secret-Redaction, HTTP-Client, Provider-DTOs, Fehlermapping und Contract-Fixtures. Der fachliche Adapter folgt erst nach validiertem Transport und Mapping.
