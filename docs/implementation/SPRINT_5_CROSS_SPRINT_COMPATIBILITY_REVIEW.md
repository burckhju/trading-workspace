# Sprint 5 – Cross-Sprint Compatibility & Forward Constraints Review

## Reviewdatum

2026-08-10

## Ergebnis

Der Sprint-5-Stand passt grundsätzlich zur in Sprint 0/1 freigegebenen Domain Map, zum Prozessmodell und zu den technischen Mustern aus Sprint 2–4. Die Top-down-Erweiterung verändert die Roadmap nicht, präzisiert aber mehrere Übergaben für FT-007 bis FT-013.

Im Review wurde eine konkrete Inkonsistenz korrigiert: `UnderlyingType` hatte technisch zusätzlich `INDEX` und `SECTOR_INDEX` erhalten, obwohl FT-001/Domain Map Version 1 ausschließlich `STOCK` zulassen und die Entität Nicht-Aktien weiterhin ablehnt. Benchmarks und Sektorreferenzen besitzen bereits das separate `MarketReference`-Modell; daher wurden die zusätzlichen Underlying-Enumwerte entfernt.

## Kompatibilität mit bisherigen Sprints

| Baseline | Bewertung | Konsequenz |
|---|---|---|
| Sprint 0/1 – Systemgrenze | kompatibel | Candidate/Top-down trifft keine Handelsentscheidung |
| Sprint 2 – FT-001 Underlying | nach Korrektur kompatibel | Underlying bleibt STOCK; INDEX/SECTOR_INDEX gehören zu MarketReference |
| Sprint 3 – Provider/Market Data | kompatibel | Provider-Mappings bleiben Adapter-/Persistence-Thema; keine Provider-Symbole in Candidate-Domain |
| Sprint 4 – FT-006 Analysis | kompatibel | vorhandene Analyse-Runs/Criteria werden referenziert; keine SMA-/Momentum-Duplikation in FT-005 |
| Sprint 4 – Provenance | erweitert, nicht gebrochen | CandidateEvaluation friert konkrete Analyseversionen ein |
| Sprint 4 – API/Repository-Muster | kompatibel | CandidateService verwendet Persistence-Adapter statt direkter SQLAlchemy-Queries |

## Neue verbindliche Randbedingungen

### FT-007 TradePlan

- Candidate ist optionaler Ursprung; ein TradePlan darf weiterhin für einen manuell gewählten Basiswert entstehen.
- Bei Candidate-Ursprung wird die konkrete `CandidateEvaluation` referenziert, nicht nur der langlebige Candidate.
- Eine spätere Candidate-Re-Evaluation verändert einen bestehenden TradePlan nicht.
- `READY_FOR_PLANNING` ist keine Planfreigabe. Die TradePlan-Freigabe bleibt eine separate Benutzeraktion.
- TradePlan bleibt produktneutral; Warrant-spezifische Parameter gehören nicht in FT-007.
- Analyse-/Top-down-Logik wird nicht in FT-007 neu berechnet.
- Candidate Model 1.0 liefert ausschließlich LONG-Kontext; SHORT darf FT-007 nicht aus LONG-Ergebnissen ableiten.

### FT-008 Produktauswahl

- Voraussetzung bleibt FT-004 Warrant-Stammdaten + freigegebener FT-007 TradePlan.
- Produktauswahl darf den TradePlan nicht verändern.
- Candidate-/MarketContext-Ergebnisse sind Kontext, keine automatische Produktauswahl.
- Produktscore, falls später eingeführt, benötigt eigenes versioniertes Modell mit vollständiger Provenance.

### FT-009/010 Trade & Trade Management

- Keine Order aus Candidate oder TradePlan automatisch erzeugen.
- Keine Positionsgröße aus Candidate Qualification ableiten.
- Tatsächliche Ausführung bleibt explizite Benutzerbestätigung.
- Historische CandidateEvaluation/TradePlan/ProductSelection bleiben immutable Referenzen.

### FT-011/012 Learning

Für Exit Review, Journal und Performance müssen später mindestens folgende historische Entscheidungsstände zusammengeführt werden können:

`CandidateEvaluation → TradePlan-Version → UserProductSelection → Trade/Events → ExitReview`.

Die spätere Auswertung darf historische Ergebnisse nicht mit aktuellen Modellversionen rückwirkend neu interpretieren.

### FT-013 Model Governance

Sprint 5 erzeugt bereits governte Modellkandidaten:

- `MARKET_CONTEXT 1.0.0`
- `RELATIVE_STRENGTH 1.0.0`
- `TOP_DOWN_CANDIDATE 1.0.0`

FT-013 muss diese bestehenden IDs/Versionen übernehmen können, statt parallele Modellidentitäten einzuführen.

## Watchlist

Der generische Watchlist-Vollausbau bleibt ein echter FT-005-Restscope. Er blockiert FT-007 nicht, weil das Prozessmodell einen Candidate **oder** einen manuell gewählten Basiswert als Ursprung eines TradePlans zulässt. FT-005 als Gesamtfeature darf jedoch erst nach expliziter Watchlist-Scopeentscheidung als vollständig Released markiert werden.

## Roadmap-Auswirkung

Keine Umnummerierung oder Verschiebung der fachlichen Reihenfolge ist erforderlich. Die bestehende Reihenfolge bleibt sinnvoll:

`Market Discovery → TradePlan → Product Selection → Trade → Post Trade → Journal/Learning`.

Die Top-down-Erweiterung macht FT-006/FT-005 lediglich zu einer stärkeren vorgelagerten Informationsquelle. Sie darf nicht zu einer Querschnitts-Abhängigkeit werden, die spätere Features Analysefachlichkeit duplizieren lässt.

## Vor Start des nächsten Fachsprints

Sprint 5 bleibt bis zum technischen Closeout im Status Technical Review. Vor einem Sprint-5-Release sind weiterhin die dokumentierten Quality-/Live-/Migration-/Git-Gates abzuarbeiten. Parallel darf die **Analyse/Spezifikation** von FT-007 beginnen; eine Implementierungsfreigabe für FT-007 sollte aber erst erfolgen, wenn seine CandidateEvaluation-Handoff-Regel und Produktneutralität im Feature Book/ADR bestätigt sind.
