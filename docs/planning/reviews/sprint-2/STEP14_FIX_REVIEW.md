# Step 14 execution fix review

## Anlass

Die Ausführung auf dem Zielsystem zeigte zwei konkrete Probleme:

1. `scripts/check-backend.sh` setzte den Befehl `python` voraus, obwohl auf dem System nur `python3` verfügbar war.
2. Zwei JSX-Bedingungen verwendeten `error && ...` bei einem State vom Typ `unknown`. Dadurch war der Ausdruck selbst vom Typ `unknown` und nicht als `ReactNode` zulässig.

## Korrekturen

- `scripts/check-backend.sh` ermittelt portabel zuerst `python3` und fällt nur bei Bedarf auf `python` zurück.
- `UnderlyingDetailPage` und `UnderlyingFormPage` prüfen Fehler explizit mit `error !== null`.

## Verifikation

- Backend: 89 Tests erfolgreich.
- TypeScript-/Frontend-Build konnte in dieser Laufzeit wegen des bekannten Registry-Proxy-Fehlers für `yocto-queue@0.1.0` nicht erneut ausgeführt werden.
- Die gemeldeten TypeScript-Ursachen wurden direkt an den betroffenen Ausdrücken behoben.
