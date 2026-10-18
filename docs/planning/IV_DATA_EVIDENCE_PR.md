# PR-Entwurf: IV-Datenbasis nachvollziehbar aufbauen

Status: **zur Veröffentlichung und vollständigen CI freigegeben; Merge nur bei grünen Gates**.
Branch: `feat/iv-data-evidence`.
Basis: `ac4e9b4624a6f5a087e7c57be699ef188618a3d7` (PR #252, v1.5.3).
Der Nutzer hat am 12.10.2026 ausdrücklich zugestimmt, diesen neuen Stand als PR
zu veröffentlichen, die CI auszuführen und bei vollständig grünen Prüfungen zu
mergen. Keine PC-Installation und kein Telegramversand.

## Problem und Nutzen

Aktuell überschreibt die Last-success-Ablage ältere Optionsscheinkurse. Damit
lassen sich wiederkehrende Datenlücken, unbekannte Originalzeiten oder
Quellenwechsel nicht über mehrere Tage nachvollziehen. Zugleich fehlen explizit
belegte Ausübungs-/Quanto-Merkmale für eine belastbare IV-Bewertung.

Diese Änderung bewahrt regelmäßig begrenzte Stichproben aus ohnehin erlaubten
Abrufen auf und erlaubt versionierte manuelle Produktbelege. Sie schafft eine
prüfbare Datenbasis für spätere aktuelle IV und historische Auswertungen.

## Änderungen

- Dauerhaftes Erfassungsprotokoll: erste Erfassung je Route und festem UTC-
  Fünfminutenintervall, einschließlich Fehlern. Cache-Wiederholungen werden
  nicht als unterschiedliche Originalkursbelege gezählt.
- Quellen-/Identitätssegmente, getrennte Original-, Abruf- und Erfassungszeiten,
  Qualitätsklassen sowie explizite Lücken statt vermeintlicher Verfügbarkeit.
- Vollständige manuelle Belegrevisionen, an ISIN/Produktidentität und Bedingungen
  gebunden; unbekannte Werte bleiben nullable und können frühere Angaben widerrufen.
- Read-only Journal in Produktverwaltung und IV-Risikodetails; Belegeingabe in der
  Produktverwaltung. Lange Quellen/Fundstellen umbrechbar, keine reine Farbwarnung.
- IV-Bereitschaft V2 verwendet ausschließlich passende, zeitlich vorhandene Belege.
  Snapshotänderung zählt nicht als zusätzlicher Signal-/Bestätigungstag.
- Migration 0045 mit eindeutigen Stichproben/Revisionen, PostgreSQL-Schutz gegen
  Änderung/Löschung und falsche Zuordnung. Rückmigration mit Belegen wird abgelehnt.
- [Fachliche Dokumentation und Betriebsfolgen](../features/IV_DATA_EVIDENCE.md).

## Fachliche Grenzen und Auswirkungen

Kein neuer Anbieterzugriff, Collector, Backfill oder geänderte Zustimmung.
Keine erfundene IV, keine aktuelle Positionssensitivität und keine historischen
Perzentile/Ranks. Die Journalstichprobe beweist keine vollständige Handelszeit-
abdeckung. Zeitlich passende Basiswertkurse, IV-/Greek-Provenienz, Zinsen und
Dividenden bleiben offen. Manuell bestätigte Angaben sind keine automatische
Dokumentenprüfung. Amerikanische Ausübung/Quanto/andere Strukturprodukte bleiben
vom europäischen Modell ausgeschlossen.

Die Aufbewahrung wächst dauerhaft (maximal 288 Stichproben pro unveränderter Route
und UTC-Tag). Vorhandene Belege blockieren endgültiges Löschen des Produkts und
Rückmigration; kein automatisches Löschen. Original-Limits, Stops/Ziele,
Alarmhysterese und Benachrichtigungsverhalten bleiben erhalten.

## Tatsächlich ausgeführte Prüfungen am 12.10.2026

| Prüfung | Ergebnis |
|---|---|
| Backend Ruff, Black, mypy | Grün; mypy: 523 Quelldateien, Black: 909 Dateien |
| Gezielte Backend-Suite | **184 bestanden**, Exit 0: Journal/Retention, Belege/API, Migration auf SQLite, IV-Modell/Readiness und Risiko-/Alertregression |
| Produktbelege/API nach abschließender Speicherung des historischen Identitätsstands | **25 bestanden**, Exit 0 (Teilmenge der gezielten Suite) |
| JPMorgan-/Morgan-Stanley-Regressionssuite nach Fixture-Korrektur | **58 bestanden**, Exit 0 |
| `scripts/check-backend.sh` | Exit 1: 2442 bestanden, 2 fehlgeschlagen, 62 übersprungen, 56 Setupfehler; Coverage 83,41 % statt geforderter 85 %. Die zwei Fehler betrafen fehlende neue Journaltabellen in SQLite-Fixtures, anschließend korrigiert und durch obige 58 Fälle nachgeprüft. Setupfehler: fehlende PostgreSQL-Testverbindung. Kein vollständig grüner Backend-Gesamtlauf behauptet. |
| PostgreSQL-Trigger/Zuordnung/Unique-Constraints | Gegen den migrierten PostgreSQL-Test geschrieben; hier wegen fehlender Testdatenbank nicht ausgeführt. Temporäre PostgreSQL-Binary verfügbar, Initialisierung scheitert an nicht verfügbaren Dateibesitzrechten; keine Umgehung oder Änderung der PC-Installation. |
| Frontend Typecheck, ESLint, Prettier, Produktionsbuild | Grün, Exit 0; vorhandene Vite-Warnung zu großen Chunks |
| Acht neue UI-Tests | Alle acht als bestanden gemeldet; Prozess endet erst nach 60 Sekunden mit Exit 124. **Nicht als erfolgreich abgeschlossener Testlauf gewertet.** Ein weiterer Lauf mit Thread-Pool nach der Provenienzerweiterung endete ebenfalls per Timeout (30 Sekunden, Exit 124, vier Einzelfälle gemeldet). |
| `scripts/check-frontend.sh` | Statische Prüfungen grün; Vitest/Coverage nach 150 Sekunden Timeout, Exit 124. Vollständige Coverage offen; Ursache des lokalen Runner-Hängers nicht abschließend diagnostiziert. |
| `scripts/run-e2e.sh` | Exit 127, `docker: command not found`; kein Stack gestartet |
| Neuer E2E-Test | Playwright entdeckt den Test erfolgreich (Exit 0); API-/UI-Speicherung, Reload, leeres Journal, lange Quellen und 320/390/768/1440 px vorbereitet. Keine visuelle Abnahme behauptet. |
| `git diff --check` | Grün |

Lokale Umgebung: Python 3.12.14, Node 24.19.0. CI verwendet PostgreSQL 17 und die
im Repository festgelegte Node-Version. Testdaten waren ausschließlich synthetisch.
SQLite-Prüfungen ersetzen keine PostgreSQL-Sperr-/Triggerprüfung. Keine Live-
Anbieterwerte oder Bestandsdaten von JMBbot wurden gemessen.

Gezielte Backend-Suite aus dem Repository-Stamm:

```bash
PYTHONPATH=backend:. \
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false \
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml \
  tests/unit/backend/features/market_data/test_quote_history.py \
  tests/unit/backend/features/market_data/test_retained_quotes.py \
  tests/unit/backend/features/market_data/test_iv_data_migration.py \
  tests/unit/backend/features/product/test_valuation_evidence.py \
  tests/unit/backend/features/product/test_data_evidence_api.py \
  tests/unit/backend/features/position_monitoring/test_iv_readiness.py \
  tests/unit/backend/features/position_monitoring/test_risk_signals.py \
  tests/unit/backend/features/position_monitoring/test_risk_readers.py \
  tests/unit/backend/features/analysis/test_vanilla_iv.py \
  tests/integration/backend/test_position_risk.py \
  tests/integration/backend/test_iv_model.py
```

## Vor einem Merge

1. Freigabe für diesen konkreten Entwicklungsstand liegt vor; den geprüften
   Head-Commit und die vollständigen CI-Ergebnisse im PR nachweisen.
2. Vollständige unveränderte Gates ausführen: Backend inklusive PostgreSQL ≥85 %,
   Frontend ≥80 % Zeilen/Funktionen/Statements und ≥70 % Branches, E2E einschließlich
   neuer Mobilansichten sowie Image-/Rendererprüfungen und Versionsregeln.
3. Prüfschwerpunkte: erste fehlgeschlagene Stichprobe bleibt erhalten; keine
   verfälschten Originalzeiten; Belegrevisionen bleiben unverändert und gebunden;
   keine zusätzlichen Warnungen; Aufbewahrung und blockierte Löschung akzeptiert.
4. Merge nur mit passender Freigabe für diese Änderungen und grünen Gates.
   Installation/Migration auf JMBbot benötigt weiterhin eine eigene Freigabe.
