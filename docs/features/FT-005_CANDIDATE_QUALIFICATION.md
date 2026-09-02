# FT-005 – Watchlisten und Kandidaten: Candidate Qualification V1

## Status

Technical Review – Sprint 5, 2026-08-10.

## Zweck

FT-005 unterstützt den Benutzer dabei, Basiswerte auf Grundlage versionierter Marktanalysen transparent als Trading-Kandidaten zu qualifizieren, weiterzuverfolgen oder zu verwerfen. FT-005 trifft keine Handelsentscheidung und erzeugt keinen TradePlan, keine Produktauswahl, keine Order und keine Positionsgröße.

Sprint 5 implementiert den Candidate-Qualification-Teil von FT-005. Ein generischer Watchlist-Vollausbau ist nicht Bestandteil der technischen Abnahme dieses Sprints.

## Fachliche Grenze

Die Analyse folgt dem freigegebenen Top-down-Prozess:

```text
Gesamtmarkt / Benchmark
        ↓
Sektor
        ↓
Basiswert
        ↓
Candidate Qualification
        ↓
Benutzer-Lifecycle
```

FT-006 besitzt die Analysefachlichkeit. FT-005 konsumiert ausschließlich gespeicherte, versionierte Analyseergebnisse und berechnet keine SMA-, Momentum- oder Providerlogik nach.

## Modelle V1

### Market Context 1.0.0

- LONG-only für Candidate Model V1.
- `FAVORABLE` und `CAUTIOUS` erfüllen das Market Gate; `CAUTIOUS` bleibt sichtbarer Warnkontext.
- `NEUTRAL` und `UNFAVORABLE` erfüllen das Market Gate nicht.
- fehlende Required-Inputs oder `INSUFFICIENT`-Qualität führen zu `NOT_EVALUABLE`.
- Primary Broad-Market-Referenzen werden semantisch aufgelöst; Provider-Symbole sind keine Domainregel.

### Relative Strength 1.0.0

- Methode: Renditedifferenz Subject minus Reference.
- Fenster: 60 Handelstage; für die Berechnung werden mindestens 61 synchronisierte Preisbeobachtungen benötigt.
- `> +2` Prozentpunkte: `POSITIVE`.
- `-2 .. +2` Prozentpunkte inklusive Grenzwerte: `NEUTRAL`.
- `< -2` Prozentpunkte: `NEGATIVE`.
- angewendet auf `Sector vs Market` und `Underlying vs Sector`.

### TOP_DOWN_CANDIDATE 1.0.0

Kein aggregierter Score.

Required:

- Market Context ist `FAVORABLE` oder `CAUTIOUS`;
- Sektor-Long-Trend ist `POSITIVE`;
- Sector Relative Strength ist `POSITIVE`;
- Underlying Long Trend ist `POSITIVE`;
- Underlying Medium Trend ist `POSITIVE`;
- Underlying Relative Strength vs Sector ist `POSITIVE`.

Warnings:

- Underlying Short Trend;
- Momentum, sofern vorhanden.

Informational:

- realisierte Volatilität;
- Range Position.

Qualification:

- mindestens ein sicher nicht erfülltes Required-Kriterium → `NOT_QUALIFIED`;
- sonst mindestens ein nicht bewertbares Required-Kriterium → `NOT_EVALUABLE`;
- sonst → `QUALIFIED`.

## FT-019 Governed Runtime Extension

Die vorstehenden V1-Regeln bleiben als historischer `TOP_DOWN_CANDIDATE/1.0`-Contract unverändert. FT-019 führt separat `TOP_DOWN_CANDIDATE/2.0` ein und macht ausschließlich die bestehende Required-Regel `TD-MARKET-001` über `market_context_allowed` fachlich governbar. Eine aktive 2.0-ModelVersion darf entweder nur `FAVORABLE` oder `FAVORABLE` plus `CAUTIOUS` zulassen; Details zu Schema-Versionierung, Fail-closed Runtime, Readiness und Provenance stehen in `FT-019_GOVERNED_CANDIDATE_RULE_SEMANTICS.md`.

## Candidate und Lifecycle

Ein Candidate ist langlebig pro Workspace und Underlying. Systemqualifikation und Benutzerentscheidung bleiben getrennt.

System:

- `QUALIFIED`
- `NOT_QUALIFIED`
- `NOT_EVALUABLE`

Benutzer-Lifecycle:

- `IDENTIFIED`
- `UNDER_REVIEW`
- `WATCHING`
- `READY_FOR_PLANNING`
- `REJECTED`

`READY_FOR_PLANNING` erzeugt oder genehmigt keinen TradePlan. `REJECTED` erfordert einen expliziten Grund.

Jede Re-Evaluation erzeugt einen unveränderlichen, hochzählenden `CandidateEvaluation`-Snapshot.

## Provenance

Die normale automatische Evaluation löst serverseitig auf:

```text
Candidate / Underlying
  → gültiger Primary Broad-Market Benchmark
  → gültiger Sector
  → Sector Reference
  → MarketReference → Listing
  → neueste abgeschlossene FT-006-Runs bis as_of
  → MarketContext / Relative Strength
  → CandidateEvaluation
```

Die Evaluation speichert konkrete Analyse-ID, Analyseversion, Modell-ID und Modellversion für Market, Sector und Underlying. Historische Evaluationen werden nicht auf neuere Analysen umgebogen.

## Providerneutrale Referenzdaten

Sprint 5 ergänzt:

- `MarketReference` (`INDEX`, `SECTOR_INDEX`);
- `UnderlyingBenchmarkAssignment`;
- `UnderlyingSectorAssignment`;
- `SectorReferenceAssignment`;
- `MarketReferenceListingAssignment`.

Zuordnungen sind zeitlich gültig und dürfen für denselben fachlichen Scope nicht mehrdeutig überlappen. Provider-Symbole werden weiterhin über die bestehende Market-Data-/Provider-Mapping-Infrastruktur gepflegt.

## REST API

Candidate:

- `POST /api/v1/candidates`
- `GET /api/v1/candidates`
- `POST /api/v1/candidates/{candidate_id}/status`
- `GET /api/v1/candidates/{candidate_id}/evaluations`
- `POST /api/v1/candidates/{candidate_id}/evaluations/auto`
- `POST /api/v1/candidates/{candidate_id}/evaluations` als expliziter kompatibler Analysequellen-Pfad
- `GET /api/v1/candidates/{candidate_id}/live-workflow`

Top-down-Referenzadministration liegt unter `/api/v1/top-down-reference-data`.

## Live Workflow

Der Live Workflow ist read-only hinsichtlich der Statusermittlung und nennt pro Blocker den nächsten expliziten Operator-Schritt. Es gibt keine stillen Writes und keine geratenen Provider-Symbole. Die Candidate-UI kann über strukturierte `action_params` auf die vorhandene Administration verlinken.

## Tests

Der Stand des S5.17-Reviews umfasst 230 erfolgreiche Backend-Tests einschließlich:

- Candidate Domain und Lifecycle;
- Migrationen `0006` und `0007`;
- Top-down-Domainmodelle;
- Source Resolution und Orchestration;
- Reference Administration;
- Guided/Actionable Live Workflow;
- deterministischer End-to-End-Fixture-Pfad durch Market Data → FT-006 → Top-down → Candidate.

## Offene Release-/Sprint-Gates

- echte Live-Konfiguration mit validierten Provider-Mappings und Credentials;
- PostgreSQL Upgrade/Downgrade der Sprint-5-Migrationen in realer PostgreSQL-Umgebung;
- Ruff/Black/mypy/Coverage gemäß Repository-Gates, sofern Toolchain verfügbar;
- Frontend TypeScript/Lint/Vitest/Coverage/Build mit vollständiger npm-Installation;
- bestehende Playwright-/E2E-Gates;
- generischer Watchlist-Vollausbau, falls FT-005 als gesamtes Feature statt Candidate Qualification V1 abgeschlossen werden soll;
- sauberer Git-/PR-/Branch-Protection-Releaseprozess im echten Repository.
