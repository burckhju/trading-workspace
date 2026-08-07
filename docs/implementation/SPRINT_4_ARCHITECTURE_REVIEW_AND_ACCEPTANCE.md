# Sprint 4 – Architecture Review und fachliche Abnahme FT-006 Marktanalyse

## Ergebnis

FT-006 erfüllt die für Sprint 4 definierte Architektur: Die Marktanalyse ist ein eigenständiges Feature und konsumiert ausschließlich interne, providerunabhängige Marktdatenverträge. Die Domain kennt weder EODHD noch HTTP-, Cache-, Retry- oder Persistenzdetails.

## Abnahme gegen Pflichtangaben

| Anforderung | Status | Umsetzung |
|---|---|---|
| Analyse-ID | erfüllt | `market_analyses.id` |
| Version | erfüllt | unveränderliche `market_analysis_runs.version` |
| Analysezeitpunkt | erfüllt | `analysis_time` |
| Basiswert | erfüllt | Referenz über `underlying_id` und Listing |
| Datenquelle | erfüllt | `data_sources` plus Snapshot-Provider-Metadaten |
| verwendete Marktdaten | erfüllt | unveränderlicher Snapshot, paginiert lesbar |
| Analysemodell | erfüllt | `model_id` und `model_version` |
| Eingabeparameter | erfüllt | vollständig aufgelöste Parameter pro Run |
| Ergebnisse | erfüllt | Metriken und Kriterien |
| Hinweise | erfüllt | persistierte Notes und Snapshot-Warnings |
| Qualitätsstatus | erfüllt | vom Lifecycle getrenntes `quality_status` |
| Reproduzierbarkeit | erfüllt | Input-Hash + Snapshot + Modellversion + `/verify` |

## Lifecycle

Die Zustandsmaschine wird in der Domain erzwungen. Historische Runs werden nach Abschluss nicht mutiert. `SUPERSEDED` wird als append-only Event modelliert. Retry verwendet ausschließlich den persistierten Snapshot und die ursprüngliche Modellversion und lädt keine aktuellen Marktdaten nach.

## API- und UI-Abnahme

Die REST API deckt Erzeugen, Ausführen, Lesen, Pagination, Filter, Snapshot, Retry, Supersede, Events und Reproduzierbarkeitsprüfung ab. Die Detailansicht zeigt Versionshistorie, Status, Qualitätsstatus, Hinweise, Kriterien, Parameter, Eingabe-Hash, Snapshot und Lifecycle-Historie. Lifecycle-Kommandos werden nur angeboten, wenn der ausgewählte Run fachlich dafür geeignet ist.

## Architekturverletzungen

Im Review wurden keine neuen direkten Providerabhängigkeiten, keine SQLAlchemy-Abhängigkeiten in der Analysis-Domain und keine Duplizierung der Market-Data-Fachlogik festgestellt. User Preferences und Request Identity bleiben außerhalb der Analysis-Domain.

## Verbleibende technische Gates

Die Backend-Suite und der Python-Compile-Check sind ausführbar. Frontend Typecheck, ESLint, Prettier, Vitest, Build und Playwright benötigen weiterhin eine vollständige npm-Installation. PostgreSQL Upgrade/Downgrade der neuesten Migrationen soll in CI oder einer lokalen PostgreSQL-Umgebung verifiziert werden.

## Abnahmeentscheidung

**FT-006 Marktanalyse ist fachlich und architektonisch für Sprint 4 abnahmefähig, vorbehaltlich der noch ausstehenden umgebungsabhängigen Frontend- und PostgreSQL-Quality-Gates.**

## Technischer Closeout 2026-08-06

Der nachgelagerte technische Closeout bestätigt 197 Backend-Tests und 87,20 % Coverage bei einem Mindest-Gate von 85 %. Die lokal nicht ausführbaren Frontend-, Python-Devtool-, PostgreSQL- und E2E-Gates sind im Dokument `SPRINT_4_TECHNICAL_CLOSEOUT.md` als externe Release-Blocker dokumentiert. Der aktuelle Stand ist daher Release Candidate `v0.4.0-market-analysis-rc.1`, nicht finaler Release.
