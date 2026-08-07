# FT-006 Marktanalyse

## Zweck

FT-006 erstellt reproduzierbare, beschreibende Marktanalysen auf Basis bereits persistierter, providerunabhängiger EOD-Marktdaten. Das Modul trifft keine Handelsentscheidung und lädt während einer Berechnung keine externen Daten nach.

## Architektur

`app/features/analysis` enthält Domain, Application Service, Persistence und REST API. Die Domain kennt weder EODHD noch SQLAlchemy oder HTTP. Der Application Service liest interne `DailyPrice`-Objekte über einen Analyse-Read-Adapter und persistiert jede Ausführung als unveränderliche Version.

## Modell V1

- Modell-ID: `EOD_TREND_MOMENTUM`
- Version: `1.0.0`
- Preisfeld: `CLOSE` oder `ADJUSTED_CLOSE`
- SMA kurz, mittel und lang
- Momentum über explizite Fenster
- annualisierte realisierte Volatilität
- Position in der beobachteten Handelsspanne
- Datenvollständigkeit und Aktualität

Klassifikationen sind `POSITIVE`, `NEUTRAL`, `NEGATIVE` und `NOT_EVALUABLE`. Sie sind keine Kauf-, Verkaufs- oder Halteempfehlungen.

## Reproduzierbarkeit

Jede Version speichert:

- Analyse-ID und Versionsnummer
- UTC-Analysezeitpunkt
- Basiswert und Listing
- Modell-ID und Modellversion
- vollständig aufgelöste Parameter
- verwendete Providerherkünfte
- jede verwendete Marktdatenzeile
- Kennzahlen und Einzelkriterien
- Hinweise und Qualitätsstatus
- SHA-256-Hash der kanonischen Eingaben
- technische Correlation-ID

## Lebenszyklus

V1 persistiert abgeschlossene Ausführungen mit `COMPLETED`, `COMPLETED_WITH_WARNINGS` oder `NOT_EVALUABLE`. `DRAFT`, `RUNNING`, `FAILED` und `SUPERSEDED` sind im Domain-Vertrag reserviert und werden bei späterer asynchroner Orchestrierung verwendet.

## REST API

- `POST /api/v1/market-analyses`
- `GET /api/v1/market-analyses`
- `GET /api/v1/market-analyses/{analysis_id}`
- `POST /api/v1/market-analyses/{analysis_id}/runs`
- `GET /api/v1/market-analyses/{analysis_id}/runs/{version}`

Die Run-API arbeitet ausschließlich mit bereits persistierten EOD-Daten im angeforderten Zeitraum.

## Lifecycle-Ergänzung Sprint 4

Der Lebenszyklus wird durch eine explizite State Machine erzwungen. Terminale Runs bleiben unveränderlich. Eine Ablösung wird append-only über `market_analysis_events` dokumentiert.

Retry ist nur für `FAILED` und `NOT_EVALUABLE` zulässig und verwendet ausschließlich den persistierten Snapshot der Quellversion. Der Retry liest keine aktuellen Marktdaten und verwendet exakt dieselbe Modell-ID/-Version sowie dieselben aufgelösten Parameter.

Die Reproduzierbarkeit einer Version kann über `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/verify` technisch geprüft werden. Die Prüfung umfasst Eingabe-Hash, Modellversion, Kennzahlen, Kriterien, Qualitätsstatus und Hinweise.
