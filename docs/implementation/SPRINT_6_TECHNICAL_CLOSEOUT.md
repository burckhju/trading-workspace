# Sprint 6 – FT-007 Technical Closeout

## Ergebnis

**Sprint 6 / FT-007 funktional abgeschlossen – Release-Gates auf finalem Closeout-Stand zu bestätigen.**

## Gelieferter Umfang

FT-007 liefert einen produktneutralen, versionierten LONG-TradePlan mit manuellem oder CandidateEvaluation-basiertem Ursprung, Thesis, Entry, Invalidation, Targets, Risk Assumptions, Lifecycle, explizitem Approval, Amendment-Lineage, Provenance/Audit, REST API und Frontend.

## Architekturstatus

Der Sprint-6 Architecture Review ist **Accepted** und enthält keine blockierenden Findings. Die ADRs S6-001 bis S6-008 bleiben verbindliche Architekturgrundlage.

## Bereits nachgewiesene Gates

- Frontend Typecheck: grün
- ESLint: grün
- Prettier: grün
- Frontend Unit/Component: 59/59 grün
- Coverage: Statements 91.42 %, Branches 77.60 %, Functions 83.47 %, Lines 91.42 %
- Production Build: grün
- E2E: 8/8 Playwright-Szenarien grün

## Finaler Release-Gate

Auf diesem Closeout-Artefakt sind vor Release-Tag nochmals auszuführen:

```bash
# Backend – gemäß bestehendem CI-/Testskript des Repositorys
# anschließend:
./scripts/check-frontend.sh
./scripts/run-e2e.sh
```

Ein Release-Tag wird erst gesetzt, wenn diese finalen Läufe grün sind.

## Deployment-Konvention

Im Docker/E2E-Setup ist der externe Browserpfad `/api/api/v1/...` erwartbar: der erste `/api`-Prefix gehört zum Nginx-Gateway und wird beim Proxying entfernt; FastAPI routet anschließend unter `/api/v1/...`. Dies ist eine Deployment-/Gateway-Konvention und kein doppelter Backend-Routenprefix.

## Bereinigung

Die temporäre FT-007 Request-URL-Diagnostik aus der E2E-Fehlersuche wurde zum Closeout entfernt; der deterministische Unified Route Dispatcher bleibt erhalten.

## Folgepfad

Nach grünen finalen Release-Gates: Sprint-6 Release Baseline festschreiben und Transition zu Sprint 7 / Reference Data Completion (FT-002 + FT-003) vorbereiten.
