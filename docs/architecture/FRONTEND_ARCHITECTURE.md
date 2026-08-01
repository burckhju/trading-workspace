# Frontend Architecture

> Technische Architektur des Frontends des Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-019 |
| Dokument | FRONTEND_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | Projektverantwortlicher |
| Freigabedatum | 2026-08-01 |

---

# Zweck

Dieses Dokument beschreibt die verbindliche technische Architektur des Frontends des **Trading Workspace**.

Es definiert:

- Projektstruktur,
- Verantwortlichkeiten,
- Featureaufbau,
- Komponentenstruktur,
- Zustandsmanagement,
- API-Kommunikation,
- Validierung,
- Fehlerdarstellung,
- Nachvollziehbarkeit,
- Testbarkeit,
- zulässige Abhängigkeiten.

Das Frontend unterstützt den Benutzer bei Analyse, Planung, Überwachung und Auswertung.

Es trifft keine Handelsentscheidungen.

---

# Architekturreferenzen

Dieses Dokument konkretisiert:

```text
docs/foundation/ARCHITECTURE.md
docs/architecture/Source_Architecture.md
```

Bei Widersprüchen gilt:

1. freigegebene Projektentscheidung,
2. `docs/foundation/ARCHITECTURE.md`,
3. `docs/architecture/Source_Architecture.md`,
4. dieses Dokument,
5. Featuredokumentation.

Widersprüche müssen vor Freigabe dokumentiert und behoben werden.

---

# Architekturprinzipien

Das Frontend folgt diesen Grundsätzen:

- Feature-orientierte Struktur,
- klare Trennung von UI und Fachlogik,
- komponentenbasierte Entwicklung,
- typisierte Schnittstellen,
- geringe Kopplung,
- hohe Wiederverwendbarkeit,
- barrierearme Bedienung,
- transparente Darstellung,
- testbare Benutzerabläufe,
- keine autonome Handelsentscheidung.

---

# Systemrolle

Das Frontend ist die Benutzeroberfläche des Trading Workspace.

Es:

- zeigt Marktdaten und Analysen,
- unterstützt Kandidatenauswahl,
- erfasst Trade-Pläne,
- zeigt Produktauswahl,
- unterstützt Trade-Management,
- überwacht Depotinformationen,
- unterstützt Journalführung,
- zeigt Performanceauswertungen,
- macht Datenquelle, Modellversion, Eingaben, Ergebnisse und Warnungen sichtbar.

Das Frontend entscheidet nicht selbstständig über Käufe, Verkäufe, Halten oder Positionsgrößen.

---

# Projektstruktur

```text
frontend/
├── src/
│   ├── app/
│   ├── features/
│   ├── shared/
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   ├── services/
│   ├── types/
│   ├── hooks/
│   ├── styles/
│   ├── assets/
│   ├── utils/
│   ├── test/
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── playwright.config.ts
├── eslint.config.js
├── Dockerfile
├── .env.example
└── .nvmrc
```

Die vollständige Repositorystruktur wird in `Source_Architecture.md` definiert.

---

# Verantwortungsbereiche

## `src/app/`

Enthält anwendungsweite Initialisierung und zentrale Konfiguration.

Beispiele:

- Router,
- Provider,
- globale Fehlergrenzen,
- globale Zustandskonfiguration,
- Theme,
- App-Shell,
- Startkonfiguration.

`app` enthält keine featureinterne Geschäftslogik.

---

## `src/features/`

Enthält alle fachlichen Benutzeroberflächen.

Aktuell vorgesehene Features:

```text
administration
candidate
journal
market
model
notification
observation
performance
product
provider
trade
trade_plan
```

Jedes Feature besitzt eine klar abgegrenzte Verantwortung.

Ein Feature darf keine internen Komponenten oder Services eines anderen Features direkt importieren.

---

## `src/shared/`

`shared` ist kein allgemeines Sammelverzeichnis.

Es enthält ausschließlich zusammengehörige, wiederverwendbare Module, die

- von mehreren Features benötigt werden,
- keine eigene fachliche Verantwortung besitzen,
- aus mehreren Artefaktarten bestehen,
- eine stabile gemeinsame Schnittstelle besitzen.

Beispiele:

```text
shared/date-range/
shared/data-quality/
shared/audit-view/
shared/model-version/
```

Ein einzelner allgemeiner Hook, Typ oder technische Service gehört bevorzugt in das dafür vorgesehene globale Verzeichnis.

---

## `src/components/`

Enthält globale, fachlich neutrale UI-Komponenten.

Beispiele:

- Button,
- Dialog,
- Tabelle,
- Badge,
- Formularfeld,
- Ladeanzeige,
- Warnhinweis.

Komponenten in diesem Verzeichnis dürfen keine featurespezifische Geschäftslogik enthalten.

---

## `src/layouts/`

Enthält anwendungsweite Seitenlayouts.

Beispiele:

- Hauptnavigation,
- Seitenrahmen,
- Detailansicht,
- Dashboardlayout.

---

## `src/pages/`

Enthält globale Seiten, die keinem einzelnen Feature eindeutig gehören.

Featurespezifische Seiten verbleiben unter `src/features/<feature>/pages/`.

---

## `src/services/`

Enthält globale technische Services.

Beispiele:

- HTTP-Client,
- Authentifizierungsintegration,
- Telemetrie,
- Dateidownload,
- Feature-übergreifende technische API-Hilfen.

Fachliche API-Aufrufe gehören grundsätzlich in den Servicebereich des zuständigen Features.

---

## `src/types/`

Enthält globale technische oder ausdrücklich freigegebene gemeinsame Typen.

Featureinterne Typen verbleiben im jeweiligen Feature.

---

## `src/hooks/`

Enthält globale, fachlich neutrale Hooks.

Beispiele:

- `useDebounce`,
- `useMediaQuery`,
- `useDocumentTitle`.

Featureinterne Hooks verbleiben im jeweiligen Feature.

---

## `src/styles/`

Enthält globale Styles, Design Tokens und Theme-Grundlagen.

Featureinterne Styles sollen nahe am jeweiligen Feature oder der jeweiligen Komponente liegen.

---

## `src/assets/`

Enthält statische Assets.

Beispiele:

- Icons,
- Logos,
- Illustrationen,
- statische Dateien.

---

## `src/utils/`

Enthält kleine, fachlich neutrale Hilfsfunktionen.

`utils` ist kein Sammelverzeichnis für Geschäftslogik.

---

## `src/test/`

Enthält Frontend-Testinfrastruktur.

Beispiele:

- Test-Setup,
- globale Mocks,
- Test-Renderer,
- Frontend-spezifische Testhilfen.

Systematisch ausgeführte Tests liegen zentral unter `tests/`.

---

# Aufbau eines Frontend-Features

Ein Frontend-Feature kann folgende Struktur besitzen:

```text
feature/
├── pages/
├── components/
├── hooks/
├── services/
├── types/
├── dialogs/
├── forms/
└── tables/
```

Nicht jedes Unterverzeichnis muss vorhanden sein.

Grundstruktur:

- `pages/`
- `components/`
- `hooks/`
- `services/`
- `types/`

Optionale Spezialisierungen:

- `dialogs/`
- `forms/`
- `tables/`

Tests liegen zentral unter:

```text
tests/
```

---

# Komponentenregeln

Komponenten sollen:

- eine klare Verantwortung besitzen,
- kontrollierte Props verwenden,
- Seiteneffekte vermeiden,
- UI und Datenlogik trennen,
- verständliche Zustände darstellen,
- barrierearm bedienbar sein.

Nicht zulässig:

- fachliche Berechnungen in Präsentationskomponenten,
- direkte Provideraufrufe,
- direkte Datenbankzugriffe,
- versteckte globale Zustände,
- untypisierte Props,
- direkte Nutzung interner Komponenten anderer Features.

---

# Seiten

Eine Seite:

- koordiniert Featurekomponenten,
- liest Routingparameter,
- startet erforderliche Datenabfragen,
- zeigt Lade-, Fehler- und Leerzustände,
- orchestriert Benutzerinteraktionen.

Eine Seite enthält keine eigenständige fachliche Modelllogik.

---

# Hooks

Hooks kapseln:

- wiederverwendbare UI-Logik,
- Datenabfragen,
- Mutationen,
- Seiteneffekte,
- lokale technische Zustände.

Hooks dürfen nicht verwendet werden, um Backend-Fachlogik im Frontend nachzubauen.

---

# Services

Feature-Services kapseln:

- API-Aufrufe,
- Request- und Response-Mapping,
- technische Fehlerübersetzung,
- Abbruch und Wiederholung,
- Cache-Integration.

Sie enthalten keine authoritative Geschäftslogik.

---

# Typen

API-Typen, UI-Typen und Formulartypen dürfen getrennt werden, wenn sie unterschiedliche Verantwortlichkeiten besitzen.

Nicht zulässig:

- unkontrolliertes `any`,
- ungeprüfte externe Daten,
- implizite Einheiten,
- unklare optionale Felder.

Einheiten und Repräsentationen müssen erkennbar sein.

Beispiele:

```text
riskPercent
priceEur
timestampUtc
modelVersionId
```

---

# Zustandsmanagement

Es wird unterschieden zwischen:

- Serverzustand,
- lokalem UI-Zustand,
- Formularzustand,
- abgeleitetem Zustand,
- globalem Anwendungszustand.

## Serverzustand

Serverdaten werden über dafür vorgesehene Query- und Serviceabstraktionen geladen.

## Lokaler UI-Zustand

Beispiele:

- geöffneter Dialog,
- ausgewählte Registerkarte,
- lokale Sortierung,
- temporäre Eingabe.

## Abgeleiteter Zustand

Ableitbare Werte werden berechnet und nicht redundant gespeichert.

## Globaler Zustand

Globaler Zustand wird nur verwendet, wenn mehrere unabhängige Bereiche dieselbe Information benötigen.

Nicht zulässig:

- vollständige Duplizierung von Serverdaten im globalen Zustand,
- fachlich wirksame versteckte UI-Defaults,
- globale Zustände ohne klaren Eigentümer.

---

# Datenfluss

Der vorgesehene Datenfluss lautet:

```text
Benutzerinteraktion
→ Komponente oder Seite
→ Hook
→ Feature-Service
→ REST-API
→ Backend
```

Rückfluss:

```text
Backend-Ergebnis
→ Feature-Service
→ Hook
→ typisierter Zustand
→ Komponente
→ Benutzeranzeige
```

---

# API-Kommunikation

Das Frontend kommuniziert ausschließlich über die freigegebene REST-API.

Nicht zulässig:

- direkte Datenbankzugriffe,
- direkte Zugriffe auf externe Marktdatenprovider,
- Umgehung des zentralen HTTP-Clients,
- unversionierte API-Pfade,
- Verarbeitung unbekannter Daten ohne Prüfung.

API-Fehler werden in stabile Frontend-Fehlermodelle übersetzt.

---

# Fachlogik

Authoritative Geschäftslogik liegt im Backend.

Das Frontend darf:

- Eingabeformate prüfen,
- unmittelbares Benutzerfeedback geben,
- Anzeigezustände berechnen,
- Daten sortieren und filtern,
- Warnungen darstellen,
- ausdrücklich freigegebene rein visuelle Ableitungen erzeugen.

Das Frontend darf nicht:

- verbindliche Risiko- oder Handelsentscheidungen berechnen,
- Backend-Regeln eigenständig duplizieren,
- Modellversionen stillschweigend verändern,
- historische Ergebnisse neu interpretieren.

---

# Validierung

Validierung wird unterschieden in:

1. Eingabeformat,
2. Formularvollständigkeit,
3. fachliche Backend-Validierung,
4. Datenqualitätswarnung,
5. Berechtigungsprüfung.

Frontendvalidierung verbessert die Bedienung, ersetzt jedoch keine Backendvalidierung.

Fachliche Fehlermeldungen des Backends müssen erkennbar und verständlich dargestellt werden.

---

# Fehlerdarstellung

Jede Datenansicht benötigt definierte Zustände:

- Laden,
- Erfolg,
- leer,
- Warnung,
- fachlicher Fehler,
- technischer Fehler,
- keine Berechtigung.

Fehlermeldungen müssen:

- verständlich,
- handlungsorientiert,
- nicht technisch überladen,
- ohne vertrauliche Details

sein.

Stacktraces, Tokens und interne Serverinformationen dürfen nicht angezeigt werden.

---

# Datenqualität

Das Frontend muss Datenqualitätsinformationen sichtbar machen.

Beispiele:

- Datenstand,
- Quelle,
- Aktualität,
- unvollständige Felder,
- Providerwarnung,
- veraltete Daten,
- nicht verfügbare Kennzahl.

Unsichere Daten dürfen nicht wie bestätigte Daten dargestellt werden.

---

# Nachvollziehbarkeit

Für jede Empfehlung, Bewertung oder fachlich relevante Berechnung müssen darstellbar sein:

- Datenquelle,
- Datenstand,
- Modell oder Regelwerk,
- Version,
- Eingaben,
- Konfiguration,
- Ergebnis,
- Warnungen,
- Einschränkungen.

Die Darstellung muss so gestaltet sein, dass der Benutzer die Grundlage einer Empfehlung nachvollziehen kann.

---

# Benutzerentscheidung

Fachlich wirksame Aktionen müssen eindeutig vom Benutzer ausgelöst oder bestätigt werden.

Beispiele:

- Trade eröffnen,
- Produkt auswählen,
- Stop ändern,
- Teilverkauf erfassen,
- Trade schließen,
- Modellversion freigeben.

Warnungen und Empfehlungen dürfen eine Bestätigung unterstützen, aber nicht ersetzen.

---

# Featureübergreifende Kommunikation

Features kommunizieren ausschließlich über:

- freigegebene gemeinsame Contracts,
- globale technische Services,
- URL- und Routingparameter,
- ausdrücklich definierte gemeinsame Zustände,
- Backend-APIs.

Nicht zulässig:

```text
Feature A
→ interne Komponente von Feature B
```

```text
Feature A
→ interner Hook von Feature B
```

```text
Feature A
→ interner Service von Feature B
```

Gemeinsam benötigte Funktionalität muss in einen klar benannten gemeinsamen Bereich überführt werden.

---

# Routing

Routen werden zentral registriert.

Features liefern ihre Seiten und Routinginformationen über klar definierte Schnittstellen.

Routen sollen:

- stabil,
- lesbar,
- bookmarkfähig,
- berechtigungsprüfbar

sein.

Beispiele:

```text
/market
/candidates
/trade-plans
/trades/:tradeId
/journal
/performance
/models
```

---

# Formulare

Formulare müssen:

- typisiert,
- zugänglich,
- validiert,
- mit klaren Fehlermeldungen,
- mit expliziter Bestätigung fachlich wirksamer Aktionen

umgesetzt werden.

Eingegebene Werte dürfen nicht stillschweigend verändert werden.

Automatische Normalisierung muss sichtbar oder fachlich eindeutig sein.

---

# Tabellen

Tabellen müssen bei relevanten Daten unterstützen:

- Sortierung,
- Filterung,
- leere Zustände,
- Ladezustände,
- Fehlerzustände,
- Einheiten,
- Zeitstempel,
- Datenquelle,
- Warnkennzeichen.

Spalten mit fachlich relevanten Kennzahlen müssen eindeutig benannt und dokumentiert sein.

---

# Dialoge

Dialoge werden für klar begrenzte Interaktionen verwendet.

Kritische Änderungen benötigen:

- eindeutige Beschreibung,
- sichtbare Auswirkung,
- Abbrechen,
- bewusste Bestätigung.

Dialoge dürfen keine komplexen vollständigen Arbeitsabläufe verstecken, wenn eine eigene Seite verständlicher wäre.

---

# Barrierefreiheit

Das Frontend soll mindestens sicherstellen:

- vollständige Tastaturbedienung,
- sichtbare Fokuszustände,
- semantische HTML-Struktur,
- verständliche Beschriftungen,
- ausreichende Kontraste,
- nicht ausschließlich farbbasierte Statusanzeige,
- sinnvolle ARIA-Attribute, wenn erforderlich.

---

# Sicherheit

Das Frontend darf keine Geheimnisse enthalten.

Nicht zulässig:

- API-Schlüssel im Bundle,
- vertrauliche Backendkonfiguration,
- Berechtigungsentscheidung ausschließlich im UI,
- unsicheres Rendering externer Inhalte,
- unkontrollierte HTML-Injektion.

Berechtigungsprüfungen im Frontend dienen der Bedienung und ersetzen keine Backendprüfung.

---

# Logging und Telemetrie

Frontend-Telemetrie darf erfassen:

- technische Fehler,
- Ladezeiten,
- fehlgeschlagene API-Aufrufe,
- anonyme Nutzungsereignisse, sofern freigegeben.

Nicht erfasst werden dürfen:

- Passwörter,
- Tokens,
- Broker-Zugangsdaten,
- unnötige personenbezogene Daten,
- vollständige vertrauliche Formulareingaben.

---

# Teststrategie

Alle systematisch ausgeführten Tests liegen zentral unter:

```text
tests/
├── unit/
├── integration/
├── contract/
├── workflow/
├── performance/
├── e2e/
└── fixtures/
```

Frontend-Testinfrastruktur kann unter `frontend/src/test/` liegen.

## Unit-Tests

Prüfen:

- Komponenten,
- Hooks,
- Mappings,
- Formatierung,
- lokale Zustandslogik.

## Integrationstests

Prüfen:

- Komponenten mit Services,
- Routerintegration,
- Formularabläufe,
- Fehlerzustände.

## Contract-Tests

Prüfen:

- API-Schemas,
- Request- und Response-Mapping,
- stabile Fehlercodes.

## Workflow- und E2E-Tests

Prüfen kritische Benutzerabläufe.

Beispiele:

- Kandidat prüfen,
- Trade-Plan anlegen,
- Produkt auswählen,
- Trade eröffnen,
- Stop ändern,
- Trade schließen,
- Journal auswerten.

---

# Qualitätsprüfungen

Verbindliche Frontend-Prüfungen:

```bash
npm run typecheck
npm run lint
npm run format
npm run test:coverage
npm run build
```

E2E:

```bash
npm run e2e
```

Das Repository-Skript `scripts/check-frontend.sh` ist maßgeblich, sofern es die Prüfungen kapselt.

---

# Performance

Das Frontend soll:

- unnötige Neuberechnungen vermeiden,
- große Tabellen kontrolliert rendern,
- Datenabfragen nicht duplizieren,
- API-Aufrufe abbrechen können,
- Ladezustände früh sichtbar machen,
- Code-Splitting sinnvoll verwenden.

Performanceoptimierung darf Lesbarkeit und Korrektheit nicht verschlechtern.

---

# Erweiterbarkeit

## Neues Feature

Neue fachliche Oberflächen werden angelegt unter:

```text
frontend/src/features/<feature>/
```

## Neue globale Komponente

Nur bei fachlich neutraler Wiederverwendung:

```text
frontend/src/components/
```

## Neues Shared-Modul

Nur wenn mehrere Artefaktarten zusammengehören und mehrere Features es benötigen:

```text
frontend/src/shared/<module>/
```

## Architekturänderung

Neue globale Verzeichnisse, Zustandsmodelle oder Abhängigkeitsrichtungen erfordern eine dokumentierte Architekturentscheidung.

---

# Nicht Bestandteil dieses Dokuments

Dieses Dokument definiert nicht:

- konkrete Seitenlayouts einzelner Features,
- konkrete API-Endpunkte,
- konkrete Geschäftsregeln,
- konkrete Modellparameter,
- konkrete UI-Texte.

Diese Inhalte befinden sich in den jeweiligen Feature-, API-, Modell- und UX-Dokumenten.

---

# Freigabekriterien

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn:

- die Struktur mit dem Repository übereinstimmt,
- `Source_Architecture.md` als Referenz bestätigt ist,
- `shared/` und globale technische Verzeichnisse eindeutig abgegrenzt sind,
- Feature- und Teststruktur vereinheitlicht sind,
- API- und Zustandsregeln akzeptiert sind,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

Bis dahin bleibt der Status `🔵 Review`.

---

# Siehe auch

- `docs/foundation/ARCHITECTURE.md`
- `docs/architecture/Source_Architecture.md`
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/architecture/Feature_Architecture.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/reference/API.md`
- `docs/reference/TEST_STRATEGY.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/foundation/TRACEABILITY.md`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Abgleich mit Repository und Source Architecture; Präzisierung von Shared-Struktur, Featureaufbau, Zustandsmanagement, API-Kommunikation, Nachvollziehbarkeit und Teststrategie |
