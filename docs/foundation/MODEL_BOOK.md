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
