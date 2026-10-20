# PR-Vorbereitung: IV-Datenprüfung und hypothetische Vanilla-Szenarien

Status: **zur CI-Prüfung freigegeben; Merge nur bei vollständig grünen Gates**.
Freigabe des Nutzers vom 12.10.2026: „Prüfungen durchführen und bei grün mergen.“
Basis: `81fd99082d6a0be5cba2d884b28946db01680dc0` (v1.5.3).
Branch: `feat/iv-risk-foundation`.

## Problem und Nutzen

Die Risikoübersicht kennt realisierte Volatilität, aber keine qualifizierte
aktuelle IV, Vega oder IV-Historie. Last-success-Quotes, unbekannte Originalzeiten
und unvollständige Produktmerkmale reichen nicht für eine belastbare Inversion.
Ein Zahlenwert ohne diese Unterscheidung würde Scheingenauigkeit erzeugen.

Diese erste Stufe macht die Blocker pro Position sichtbar und auditierbar.
Ein getrennter Rechner erklärt den IV-Einfluss unter ausdrücklich eingegebenen
Annahmen, einschließlich vollständiger kombinierter Verlustszenarien.

## Änderungen

- Versionierte IV-Datenbereitschaft im Risiko-API-Vertrag, nullable Kennzahlen,
  konkrete Gründe und unveränderte Originalzeiten/Quellen.
- Speicherung in bestehenden unveränderlichen Risikosnapshots. Quote-/Quellen-/
  Qualitätswechsel werden unterscheidbar; reine Empfangszeitänderungen nicht.
  Alte Payloads bleiben lesbar. Keine Datenbankmigration.
- Strikt hypothetischer BSM-Rechner für europäische Vanilla-Calls/Puts,
  gleichlautende Währungen, kein Quanto, kontinuierliche Dividendenrendite.
  Explizite Zinsen/Dividenden, Verhältnis-Konvention und Prozentpunkt-Einheiten.
- Wahl zwischen IV-Annahme und Inversion eines hypothetischen Preises mit
  Preisgrenzen, begrenzter Bisektion und Zeitwert-/Vega-Konditionsprüfung.
- Vollständige kombinierte Neubewertung von Spot/IV/Zeit; isolierte Effekte und
  kleine lokale Näherung separat. Modell-gegen-Modell, kein Verkaufserlös.
- Kompakte IV-Übersicht, aufklappbare Quellen/Grenzen, Modelllabor mit pro Position
  erhaltenen Sitzungseingaben und Schutz vor veralteten Antworten.
- Fachkonzept und Primärquellen in
  [IMPLIED_VOLATILITY.md](../features/IMPLIED_VOLATILITY.md).

## Bewusste Grenzen

Keine aktuelle reale Positions-IV oder Positionssensitivität freigeschaltet,
keine qualifizierte IV-Historie, kein Rank/Perzentil, kein Ereignisfeed und keine
IV-Alerts. Stattdessen explizit `null`/„nicht verfügbar“. Das Modelllabor ist keine
Lösung der Live-Datenlücke. Amerikanische Ausübung, FX/Quanto, diskrete Dividenden
und strukturierte Produkte benötigen einen eigenen qualifizierten Ausbau.

Neue Audit-Evidenz kann die Zahl der Snapshots erhöhen, zählt aber nicht als
weiterer Bestätigungstag. Keine Änderung der Stop-/Zielauswertung oder der
Benachrichtigungsregeln. Keine neuen Providerzugriffe, Einwilligungen, Konfiguration,
Versionserhöhung, Installation oder Telegram-Sendung. Veröffentlichung des Branches
und Merge nach erfolgreichen Prüfungen sind seit 12.10.2026 ausdrücklich freigegeben.

## Nachgewiesene Prüfungen (12.10.2026)

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Ruff, Black, mypy entsprechend Backend-Skript | Erfolgreich; 901 Python-Dateien formatgeprüft, 519 App-Dateien typgeprüft |
| Gezielte Backend-Suite | **128 bestanden**, Exit 0; neue Modell-/API-/Readiness-Tests plus bestehende Risiko-/Quellen-/Zustandsprüfungen und zwei Umgebungsnachtests |
| Gesamtes `scripts/check-backend.sh` | **Nicht erfolgreich**: 2406 bestanden, 62 übersprungen, 56 Setupfehler ohne PostgreSQL-Testdatenbank und 2 fehlgeschlagene Tests wegen fehlendem `socksio` im vorgegebenen SOCKS-Proxy-Umfeld. Gemessene Abdeckung 83,22 %, geforderte 85 % nicht erreicht. |
| Proxy-Nachtests | `socksio==1.0.0` ausschließlich in der temporären Testumgebung installiert; beide betroffenen Bestandstests danach bestanden (in den 128 enthalten). Projektabhängigkeiten unverändert. Gesamtprüfung wurde dadurch nicht nachträglich grün. |
| TypeScript, ESLint, Prettier | Erfolgreich im aktuellen Frontend-Skriptlauf |
| `npm run build` | Erfolgreich, Exit 0; bestehender Vite-Hinweis auf große Chunks bleibt |
| `scripts/check-frontend.sh` | **Nicht erfolgreich**: nach statischen Prüfungen in Vitest/Coverage hängen geblieben, nach 180 Sekunden abgebrochen (Exit 124); keine vollständige Coverage-Freigabe |
| Neue UI-/Service-Tests | Sieben Testfälle als bestanden gemeldet, aber Runner ohne regulären Abschluss; **nicht als erfolgreicher Testlauf gezählt**. Auch der unveränderte `services/risk.test.ts` meldete vier Tests und endete erst durch Timeout (60 Sekunden, Exit 124). |
| Lokaler Browser | Chromium-Installation/Start in dieser Umgebung nicht nutzbar; expliziter Start der heruntergeladenen Binary endete mit SIGSEGV. Keine visuelle Desktop-/Mobilabnahme behauptet. |
| `scripts/run-e2e.sh` | **Nicht ausführbar**, Exit 127: `docker: command not found`. Kein Stack gestartet. |
| E2E-Erweiterung | Test für 320/390/768/1440 px, Überlauf, Modelllabor und unveränderte Position geschrieben; Ausführung offen. |
| `git diff --check` | Erfolgreich |

Die gezielte Backend-Suite lässt sich aus dem Repository-Stamm wiederholen:

```bash
PYTHONPATH=backend:. \
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
backend/.venv/bin/python -m pytest -q -c backend/pyproject.toml \
  tests/unit/backend/features/analysis/test_vanilla_iv.py \
  tests/unit/backend/features/position_monitoring/test_iv_readiness.py \
  tests/unit/backend/features/position_monitoring/test_risk_signals.py \
  tests/unit/backend/features/position_monitoring/test_risk_readers.py \
  tests/integration/backend/test_iv_model.py \
  tests/integration/backend/test_position_risk.py \
  tests/unit/backend/providers/gettex_delayed/test_gettex_delayed_adapter.py::test_candidate_files_use_current_and_previous_quarter_hours \
  tests/unit/backend/test_dependency_injection.py::test_enabled_eodhd_builds_and_closes_shared_runtime
```

Die CI-Regeln verlangen PostgreSQL 17, Backend-Coverage ≥85 %, Frontend-Coverage
≥80 % Zeilen/Funktionen/Statements und ≥70 % Branches sowie den Docker-/Playwright-
E2E-Lauf. Vor Merge müssen diese vollständigen Gates erfolgreich sein. Zeitlimits,
einzelne grüne Testzeilen oder übersprungene PostgreSQL-Tests ersetzen diese Gates nicht.

## Review-Schwerpunkte und verbleibende Abnahme

1. Fachliche Abgrenzung und Einheiten: unabhängige QuantLib/Haug-Referenzpreise,
   Call/Put-Vega, Verhältnis/Stückzahl genau einmal, keine implizite FX-Umrechnung.
2. Snapshotfrequenz und gespeicherte Quellen-/Zeitqualität; keine Gewichtung als
   historische Verteilung und keine zusätzliche Warnbestätigung durch Polling.
3. Gesamte CI einschließlich PostgreSQL sowie reale Desktop-/Mobilansicht und
   Überlauf prüfen. Die neue Stufe bis dahin als Draft behandeln.
4. PC-Stand und Live-Providerdaten separat read-only verifizieren, sobald ein
   autorisierter Zugriff bzw. aktuelle Diagnose vorliegt; kein Deployment hieraus ableiten.

Die aktuellen vollständigen CI-Ergebnisse werden im PR nachgewiesen. Die lokale
Prüftabelle bleibt als Protokoll der eingeschränkten Entwicklungsumgebung erhalten;
ein erfolgreicher CI-Lauf ersetzt keine nachträglich behauptete lokale Ausführung.
