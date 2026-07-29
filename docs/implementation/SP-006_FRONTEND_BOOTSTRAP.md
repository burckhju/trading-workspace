# SP-006 Frontend Bootstrap

## Ziel

SP-006 stellt das lauffähige technische Grundgerüst des React-Frontends bereit. Der Stand enthält keine fachlichen Arbeitsbereiche und keine Implementierung der Features FT-001 bis FT-013.

## Implementierter Umfang

- React- und TypeScript-Einstiegspunkt
- Vite-Build- und Development-Server-Konfiguration
- React-Router-Bootstrap mit technischer Start- und 404-Seite
- neutrales Application Layout
- Tailwind-CSS-Integration und globale Basisstile
- validierte Environment-Konfiguration für Backend-URL und Development-Port
- Vitest- und Testing-Library-Bootstrap
- ESLint- und Prettier-Konfiguration
- npm-Skripte für Entwicklung, Build, Test, Linting und Formatprüfung

## Architekturgrenzen

Die vorhandenen Feature-Verzeichnisse bleiben leer. Es wurden weder fachliche Routen noch Feature-Komponenten, Formulare, Tabellen oder Services erstellt. Der zentrale API-Basiswert wird nur konfiguriert; ein HTTP-Client wird erst eingeführt, sobald ein verbindlicher API-Vertrag vorliegt.

## Konfiguration

Die Anwendung verwendet ausschließlich Vite-Environment-Variablen:

- `VITE_API_BASE_URL`: absolute HTTP- oder HTTPS-URL des Backends
- `VITE_DEV_SERVER_PORT`: gültiger TCP-Port für Development und Preview

Eine Beispielkonfiguration befindet sich in `frontend/.env.example`.

## Befehle

Aus `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run test
npm run lint
npm run format
```

## Versionsfreigabe

Die verbindlichen Projektdokumente nennen Technologien, aber keine konkreten freigegebenen Versionen. Für einen installierbaren Bootstrap wurden kompatible Versionsbereiche eingetragen. Vor einem produktiven Release müssen diese formal bestätigt und durch eine erzeugte Lockdatei fixiert werden.

## Validierung in der Ausführungsumgebung

Die bereitgestellte npm-Registry beantwortete Abrufe selbst für Standardpakete wie `react` mit HTTP 404. Daher konnten `npm install`, Frontend-Build, Vitest, ESLint und Prettier in dieser Umgebung nicht ausgeführt und keine verlässliche Lockdatei erzeugt werden. Dateistruktur, JSON-Konfigurationen und vorhandene Backend-Regressionstests wurden lokal geprüft.
