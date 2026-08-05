# ADR-S3-006 – Begrenzte Retry- und Fehlerstrategie

## Status

Accepted – 2026-08-05

## Kontext

Externe Provider können temporär fehlschlagen. Unkontrollierte Retries erhöhen Latenz und Verbrauch und dürfen permanente Fehler nicht verdecken.

## Entscheidung

Es gibt maximal drei Gesamtversuche mit exponentiellem Backoff und Full Jitter. Retries gelten nur für Netzwerkfehler, Timeouts, HTTP 429, 502, 503 und 504. `Retry-After` wird bis maximal 30 Sekunden respektiert. Die Gesamtdauer ist auf 45 Sekunden begrenzt.

EODHD- und HTTP-Fehler werden in eine providerunabhängige `MarketDataError`-Hierarchie übersetzt.

## Konsequenzen

- transiente Fehler werden kontrolliert abgefangen,
- permanente Fehler erscheinen früh und eindeutig,
- Tests benötigen injizierbare Clock, Sleeper und Zufallsquelle,
- einzelne Requests können bis zur Gesamtdauergrenze dauern.
