# ADR-S4-001 – Marktanalyse als eigenständige Feature-Grenze

## Status

Accepted – 2026-08-05

## Entscheidung

Marktanalyse wird als `app/features/analysis` implementiert. Die Domain konsumiert ausschließlich providerunabhängige Werte und kennt keine Provideradapter, HTTP-Clients oder ORM-Modelle. Die technische Verdrahtung erfolgt außerhalb der Domain.

## Konsequenzen

Providerwechsel beeinflussen das Analysemodell nicht. Externe Nachladungen sind kein Bestandteil einer Analyseausführung. Neue Modelle werden über Modell-ID und semantische Version eingeführt.
