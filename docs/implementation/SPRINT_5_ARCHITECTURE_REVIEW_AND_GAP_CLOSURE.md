# Sprint 5 – Architecture Review & Gap Closure

## Reviewdatum

2026-08-10

## Ergebnis

Sprint 5 Candidate Qualification V1 ist fachlich und architektonisch konsistent mit der bestehenden Feature-Architektur und kann den Status **Technical Review** tragen. Eine finale Sprint-/Release-Abnahme wird noch nicht erklärt, weil mehrere umgebungsabhängige Quality Gates und ein echter Live-Provider-Pfad offen sind.

## Geprüfte Grenzen

| Bereich | Ergebnis |
|---|---|
| FT-005 vs FT-006 Ownership | erfüllt: Analysefachlichkeit bleibt in FT-006; FT-005 qualifiziert gespeicherte Analyseergebnisse |
| Handelsentscheidung | erfüllt: keine automatische Kauf-/Verkaufsentscheidung, kein TradePlan, keine Order/Positionsgröße |
| Candidate Score | erfüllt: V1 besitzt keinen aggregierten Score |
| Top-down-Prozess | erfüllt: Market → Sector → Underlying → Candidate |
| System vs Benutzerstatus | erfüllt: Qualification und Lifecycle getrennt |
| Re-Evaluation | erfüllt: immutable, versionierte CandidateEvaluation |
| Provenance | erfüllt auf Analyseebene: konkrete Run-IDs/Versionen werden gespeichert |
| Providergrenze | erfüllt: Domain enthält keine EODHD-Symbole oder HTTP-Logik |
| Source Resolution | erfüllt: semantische Referenzen werden serverseitig auf gespeicherte Analysen aufgelöst |
| Quality Handling | erfüllt: `INSUFFICIENT` Required-Quelle kann nicht zu `QUALIFIED` führen |
| Direction | erfüllt: Candidate Model 1.0 ist explizit LONG-only |
| Missing data | erfüllt: `NOT_EVALUABLE` statt falscher Ablehnung |

## Reviewkorrekturen

### Dokumentationsstatus

Das Product Backlog war noch auf einem Vor-Sprint-Stand (`FT-005` und `FT-006` jeweils `Not Started`). Es wurde auf den tatsächlichen Repository-Stand synchronisiert. Die frühere zirkuläre Abhängigkeit PB-012 ↔ PB-013 wurde entfernt: FT-006 ist Grundlage für die Sprint-5-Candidate-Qualifikation.

### ADR-Ablage

Sprint-5-ADRs waren zwischen `docs/adr` und `docs/decisions` verteilt. Sie wurden auf die bestehende Repository-Konvention `docs/decisions` vereinheitlicht und im Architekturindex indiziert.

### Feature-Dokumentation

`docs/features/FT-005_CANDIDATE_QUALIFICATION.md` wurde als verbindliche V1-Zusammenfassung ergänzt.

### Candidate Persistence Boundary

`CandidateService` enthielt direkte `select`-/`func`-Queries. Diese wurden im Review in `SqlAlchemyCandidateRepository` verschoben. Die Application-Schicht orchestriert damit wieder über einen Persistence-Adapter im etablierten Sprint-3/4-Muster; fachliche Logik blieb unverändert.

### Teststatus

Der Reviewlauf bestätigt:

```text
230 passed
```

mit `PYTHONPATH=backend python -m pytest -q`.

## Migrationskette

Sprint 5 ergänzt linear:

- `20260808_0006_top_down_candidates.py`
- `20260810_0007_top_down_source_resolution.py`

Ein echter PostgreSQL Upgrade-/Downgrade-Lauf bleibt ein externes Gate und wurde in dieser Umgebung nicht als bestanden markiert.

## API Review

Die normale Produktionsrichtung ist `POST /api/v1/candidates/{id}/evaluations/auto`: Der Client liefert keine fachlichen Klassifikationen. Das Backend bestimmt die gespeicherten Analysequellen selbst.

Der explizite Endpunkt `/evaluations` bleibt als kompatibler Pfad bestehen, akzeptiert aber nur konkrete gespeicherte Analyse-IDs und -Versionen; er akzeptiert keine vom Client erfundenen `FAVORABLE`-/`POSITIVE`-Klassifikationen.

## Frontend Review

Die Candidate-UI trennt Benutzerstatus und Systemqualifikation, zeigt Kriterien nach MARKET/SECTOR/UNDERLYING und enthält den geführten/actionable Live Workflow. Die automatische Bewertung bleibt deaktiviert, solange die serverseitige Readiness nicht erfüllt ist.

Die vollständige Frontend-Toolchain konnte im Reviewpaket nicht ausgeführt werden, weil `frontend/node_modules` fehlt. Dieses Gate bleibt offen.

## Scope-Gap: Watchlist

FT-005 heißt im Feature-Katalog „Watchlisten und Kandidaten“. Sprint 5 implementiert Candidate Qualification und den Lifecycle-Zustand `WATCHING`, aber **kein eigenständiges generisches Watchlist-Aggregat mit Listenverwaltung**. Das ist kein versteckter Implementierungsfehler, sondern ein noch offener Scope-Gap zwischen Feature-Gesamtname und Sprint-5-V1.

Vor einer Erklärung „FT-005 vollständig abgeschlossen“ muss entschieden werden, ob:

1. Candidate `WATCHING` für V1 die Watchlist-Anforderung ausreichend erfüllt, oder
2. ein separates Watchlist-Aggregat/Feature-Teil noch implementiert werden muss.

Bis dahin bleibt PB-012 im Status `Technical Review`.

## Noch offene Gates vor Sprint-Abschluss

1. Live-EODHD-Konfiguration und mindestens ein echter End-to-End-Pfad.
2. PostgreSQL Upgrade/Downgrade für Migrationen 0006/0007.
3. Ruff, Black, mypy und Coverage gemäß etablierten Backend-Gates.
4. Frontend Lint, TypeScript, Tests, Coverage und Build.
5. bestehende Smoke-/Playwright-/Integration-Gates in vollständiger Umgebung.
6. Entscheidung zum Watchlist-Restscope.
7. finale Dokumentations-/Architecture-Review-Nachkontrolle nach den Gates.
8. sauberer Git-Arbeitsstand und Release über PR/Branch Protection.

## Abnahmeentscheidung

**Candidate Qualification V1: fachlich/architektonisch reviewfähig und intern konsistent.**

**Sprint 5 als Gesamt-Sprint: noch nicht final abgeschlossen.** Die offenen Punkte oben sind ausdrücklich keine stillen Annahmen und dürfen für einen Release nicht übersprungen werden.
