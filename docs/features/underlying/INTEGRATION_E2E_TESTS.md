# FT-001 – Integrations- und E2E-Tests

## Ziel

Schritt 14 prüft die bereits freigegebenen Schichten im Zusammenspiel, ohne neue Fachlogik einzuführen.

## Backend-Integration

Die bestehende Integrationssuite bleibt Bestandteil von `tests/integration/backend`. Für die produktionsnahe FT-001-Datenbankintegration ist PostgreSQL verbindlich, weil das Modell PostgreSQL-spezifische Elemente wie JSONB und partielle Indizes verwendet. Die vollständige Ausführung erfolgt über Docker Compose und `scripts/run-e2e.sh`; dabei werden Migration, FastAPI-Anwendung und PostgreSQL gemeinsam gestartet.

Eine SQLite-Ersatzintegration ist ausdrücklich nicht zulässig, weil sie zentrale Datenbankregeln nicht realistisch abbilden würde.

## Browser-E2E

`tests/e2e/ft001-underlyings.spec.ts` deckt folgende Nutzerpfade ab:

- Basiswertliste laden, Primärnotierung anzeigen und Suche serverseitig übertragen
- Basiswert mit primärer Notierung anlegen
- Detailseite mit Notierungen, Verwendungen und Audit-Historie laden
- Verifikation mit der aktuell geladenen Optimistic-Locking-Version ausführen

Die Browsertests verwenden Playwright-Routing für deterministische API-Antworten. Damit prüfen sie React-Router, Views, Formulare, den realen API-Client und die HTTP-Verträge gemeinsam. Der zusätzliche Compose-Lauf bleibt für die echte Backend-/PostgreSQL-Verkettung maßgeblich.

## Ausführung

```bash
./scripts/check-backend.sh
./scripts/check-frontend.sh
./scripts/run-e2e.sh
```

## Ausführungsergebnis

Im Zielsystem wurden die Docker-Images erfolgreich gebaut und PostgreSQL, Backend und Frontend erreichten den Status `healthy`. Der Frontend-Produktionsbuild war erfolgreich.

Der erste Playwright-Lauf ergab:

```text
4 passed
1 failed
```

Die vier FT-001-Szenarien für Suche/Filter, Anlage, Detail/Audit/Verwendungen und Verifikation waren erfolgreich. Der einzige Fehlschlag betraf `foundation.spec.ts`, der noch die entfernte Sprint-0-Überschrift `Technisches Frontend-Grundgerüst` erwartete. Dieser Test wurde anschließend auf die aktuelle Startseite `Basiswerte` korrigiert.

Die vollständige Wiederholung nach dieser letzten Testkorrektur ist über `./scripts/run-e2e.sh` auszuführen und bildet den verbleibenden finalen Betriebsnachweis. Es besteht kein bekannter fachlicher oder Build-Fehler in FT-001.
