# Model Book

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | MODEL_BOOK.md |
| Dokumenttyp | Foundation |
| Version | 0.2 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-11 |

---

# Zweck

Das Model Book ist die zentrale, versionierte Übersicht aller Handels-, Bewertungs- und Analysemodelle.

# Mindestangaben je Modell

- Modell-ID und Name
- Version und Status
- Zweck und Nicht-Zweck
- Datenquellen und Datenstand
- Eingaben, Einheiten und Validierungen
- Regeln, Formeln, Parameter und Rundung
- Ergebnis und Interpretation
- Warnungen und Einschränkungen
- Test- und Vergleichsnachweise
- Freigabe und Gültigkeitszeitraum

# Grundregel

Modelländerungen erzeugen eine neue Version. Historische Zuordnungen werden nicht überschrieben.

# Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-08-01 | Sprint-0-Baseline angelegt |
| 0.2 | 2026-08-11 | FT-007 Modellgrenze und Nicht-Modell-Charakter dokumentiert |


## FT-007 TradePlan

FT-007 ist **kein automatisches Handels-, Scoring- oder Positionsgrößenmodell**. Es persistiert eine vom Benutzer formulierte, produktneutrale Planentscheidung als versionierten Snapshot. Die fachlich relevante Modellgrenze lautet:

`CandidateEvaluation → TradePlanVersion → spätere Risk/Product/Execution-Entscheidungen`

V1 ist LONG-only. Entry, Invalidation, Targets und Risk Assumptions sind Planparameter; sie erzeugen keine Order- oder Execution-Entscheidung. Eine spätere Candidate-Re-Evaluation verändert keine bestehende TradePlanVersion.

## Realisierte Bruttoergebnisse — Auswertungsdefinition

`realized-gross-sell-v1` ist eine versionierte lesende Auswertungsdefinition
tatsächlicher wirksamer SELLs. Sie verwendet die bestehende FT-010-Average-Cost-
Formel und ausdrücklich belegte Ausführungswährungen. Sie ist kein neues Handels-,
Scoring- oder Positionsgrößenmodell und aktiviert keine Modellversion.

[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
und der [freigegebene Quellen-/Periodenvertrag](../implementation/PERIOD_REALIZED_GROSS_READINESS.md)
definieren Population, Zeitraum/Zeitzone, korrigierten heutigen Wissensstand,
Kostenbasisquellen, unbekannte Werte und Decimal-/Anzeigenpräzision. Die
[technische Qualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
bleibt von Fachabnahme, Veröffentlichung und Zielbetrieb getrennt.
