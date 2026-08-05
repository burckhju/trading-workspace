# Sprint 2 – Schritt 14: Behebung der offenen CI-Punkte

## Behobene Punkte

1. `scripts/check-backend.sh` erkennt `python3` und `python`, bevorzugt eine vorhandene `backend/.venv` und richtet bei fehlenden Entwicklungswerkzeugen eine lokale virtuelle Umgebung aus `requirements-dev.txt` ein.
2. Die React-Komponenten behandeln asynchrone Aufrufe explizit. `load` ist stabil über `useCallback`, Navigationen und Event-Handler markieren beziehungsweise behandeln Promises korrekt.
3. Der `MarketApiClient` beschreibt Operationen als Funktionsproperties. Dadurch sind Mock- und Assertion-Zugriffe in Tests ohne `unbound-method`-Verstöße möglich.
4. Die Client-Tests werten `RequestInfo | URL` und Request-Bodies typensicher aus; unnötige Assertions und unsichere String-Konvertierungen wurden entfernt.
5. Der Foundation-E2E-Test prüft die aktuelle FT-001-Startseite `Basiswerte` statt der entfernten Platzhalteransicht `Technisches Frontend-Grundgerüst`.
6. Der Application-Test initialisiert seine API-Mocks pro Test reproduzierbar.

## Ausgeführte Prüfungen

- TypeScript Typecheck: erfolgreich
- ESLint mit `--max-warnings=0`: erfolgreich
- Vitest: 18 Tests erfolgreich
- Python-Kompilierung: erfolgreich
- Shell-Syntaxprüfung für `check-backend.sh`: erfolgreich

## Architekturreview

Die Änderungen korrigieren ausschließlich Prüf- und Ausführungsfehler. REST-Verträge, Domainregeln, Persistenzmodell und Featureumfang von FT-001 bleiben unverändert.
