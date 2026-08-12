# Requirements

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | REQUIREMENTS.md |
| Dokumenttyp | Foundation |
| Version | 0.2 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-11 |

---

# Zweck

Dieses Dokument ist die zentrale Ablage für projektweite Anforderungen des Trading Workspace. Featurebezogene Anforderungen werden unter `docs/features/<feature>/` konkretisiert und von hier referenziert.

# Projektweite Anforderungen

- Trading Workspace trifft keine Handelsentscheidungen.
- Alle Entscheidungen verbleiben beim Benutzer.
- Fachliche Berechnungen müssen Datenquelle, Modell, Version, Eingaben und Ergebnis nachvollziehbar machen.
- Historische Trades bleiben mit der ursprünglich verwendeten Modellversion verknüpft.
- Es gibt keine versteckten fachlichen Defaultwerte oder unversionierten Heuristiken.
- Informationen werden zentral gespeichert und nicht mehrfach unabhängig gepflegt.

# Änderungshistorie

| Version | Datum | Änderung |
|---|---|---|
| 0.1 | 2026-08-01 | Sprint-0-Baseline angelegt |
| 0.2 | 2026-08-11 | FT-007 TradePlan Implementierungsanforderungen synchronisiert |


## FT-007 TradePlan – projektweite Anforderungen

- `TradePlan` ist die langlebige fachliche Identität; fachliche Änderungen werden als immutable `TradePlanVersion` historisiert.
- Ursprung ist entweder ein manuell gewähltes Underlying oder eine konkrete immutable `CandidateEvaluation`; ein `latest`-Fallback ist unzulässig.
- FT-007 V1 ist vollständig LONG-only.
- Approval ist eine separate, explizite und versionsgenaue Benutzeraktion mit Actor, Zeitpunkt und Correlation-ID.
- Ein Approved-Stand wird nicht in-place geändert; Amendments erzeugen eine neue Version und erhalten die Lineage.
- FT-007 bleibt produktneutral und erzeugt weder Position Size noch Order Quantity noch Execution.
- Provenance, Lifecycle-Events und Approval müssen für historische Versionen reproduzierbar bleiben.
