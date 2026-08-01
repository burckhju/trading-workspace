# Feature Architecture

> Verbindliche Struktur und Architektur für fachliche Features im Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-020 |
| Dokument | Feature_Architecture.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | Projektverantwortlicher |
| Freigabedatum | 2026-08-01 |

---

# Zweck

Dieses Dokument definiert die verbindliche Architektur eines fachlichen Features im **Trading Workspace**.

Es beschreibt:

- Ablageorte,
- Verantwortlichkeiten,
- Pflicht- und optionale Artefakte,
- Backend- und Frontendstruktur,
- Teststruktur,
- Dokumentationspflichten,
- Abhängigkeitsregeln,
- Freigabe- und Abnahmekriterien,
- Nachvollziehbarkeit und Modellversionierung.

Das Dokument ergänzt:

```text
docs/architecture/Source_Architecture.md
docs/architecture/BACKEND_ARCHITECTURE.md
docs/architecture/FRONTEND_ARCHITECTURE.md
docs/technical/FEATURE_LIFECYCLE.md
```

---

# Grundsatz

Ein Feature ist eine klar abgegrenzte fachliche Fähigkeit des Trading Workspace.

Beispiele:

```text
market
candidate
trade_plan
product
trade
observation
journal
performance
model
provider
notification
administration
```

Ein Feature besitzt:

- eine klar definierte fachliche Verantwortung,
- dokumentierte Anforderungen,
- nachvollziehbare Eingaben und Ausgaben,
- eine eindeutige technische Zuständigkeit,
- definierte Tests,
- dokumentierte Freigabekriterien.

Ein Feature darf keine autonome Handelsentscheidung treffen.

---

# Ablageorte eines Features

Ein Feature kann Artefakte in mehreren Bereichen besitzen:

```text
backend/app/features/<feature>/
frontend/src/features/<feature>/
docs/features/<feature>/
tests/<testart>/<feature>/
```

Nicht jeder Bereich muss von Beginn an existieren.

Ein Bereich wird nur angelegt, wenn dort tatsächlich Artefakte entstehen.

---

# Feature-Dokumentation

Die fachliche Dokumentation eines Features liegt unter:

```text
docs/features/<feature>/
```

Empfohlene Struktur:

```text
docs/features/<feature>/
├── FEATURE.md
├── REQUIREMENTS.md
├── DATA.md
├── API.md
├── UI.md
├── TESTS.md
├── DECISIONS.md
└── CHANGELOG.md
```

Nicht jedes Dokument ist zwingend als separate Datei erforderlich.

Kleine Features dürfen Inhalte in `FEATURE.md` zusammenfassen, solange alle erforderlichen Informationen enthalten bleiben.

---

# Pflichtinhalte der Feature-Dokumentation

Jedes Feature muss mindestens dokumentieren:

- Zweck,
- fachliche Verantwortung,
- Nicht-Zuständigkeiten,
- Benutzerrollen,
- Eingaben,
- Ausgaben,
- Regeln,
- Validierungen,
- Fehlerfälle,
- Datenquellen,
- Datenqualität,
- Nachvollziehbarkeit,
- Abhängigkeiten,
- Akzeptanzkriterien,
- Testfälle,
- offene Punkte,
- Freigabestatus.

---

# Backend-Struktur eines Features

```text
backend/app/features/<feature>/
├── api/
├── services/
├── domain/
├── repositories/
├── schemas/
├── validators/
├── events/
└── mappers/
```

Nicht jedes Unterverzeichnis muss vorhanden sein.

## Pflichtbereiche

Je nach Featuretyp sind typischerweise erforderlich:

- `services/`
- `domain/`
- `schemas/`

## Optionale Bereiche

- `api/`
- `repositories/`
- `validators/`
- `events/`
- `mappers/`

Ein Verzeichnis wird nur angelegt, wenn eine entsprechende Verantwortung vorhanden ist.

---

# Backend-Verantwortlichkeiten

## `api/`

Enthält:

- Routen,
- Transportvalidierung,
- Authentifizierungs- und Autorisierungsanbindung,
- Übersetzung in API-Antworten.

Nicht zulässig:

- Geschäftslogik,
- direkte SQL-Abfragen,
- direkte Providerzugriffe.

## `services/`

Enthält Application Services und koordiniert Anwendungsfälle.

## `domain/`

Enthält fachliche Regeln, Entities, Value Objects, Invarianten und Berechnungen.

## `repositories/`

Enthält Repositorycontracts und gegebenenfalls Persistenzadapter des Features.

## `schemas/`

Enthält API-, Service- oder Datentransfermodelle.

## `validators/`

Enthält eigenständige fachliche oder technische Validatoren.

## `events/`

Enthält featureinterne oder freigegebene featureübergreifende Events.

## `mappers/`

Enthält Mapping zwischen API-, Domain-, Persistenz- und Providerdarstellungen.

---

# Frontend-Struktur eines Features

```text
frontend/src/features/<feature>/
├── pages/
├── components/
├── hooks/
├── services/
├── types/
├── dialogs/
├── forms/
└── tables/
```

## Grundstruktur

- `pages/`
- `components/`
- `hooks/`
- `services/`
- `types/`

## Optionale Spezialisierungen

- `dialogs/`
- `forms/`
- `tables/`

Ein Verzeichnis wird nur angelegt, wenn entsprechender Inhalt vorhanden ist.

---

# Frontend-Verantwortlichkeiten

## `pages/`

Koordinieren Seiten, Routingparameter, Datenabfragen und Zustände.

## `components/`

Enthalten featurespezifische UI-Komponenten.

## `hooks/`

Kapseln wiederverwendbare UI-, Query- oder Mutationslogik.

## `services/`

Kapseln API-Aufrufe und technische Fehlerübersetzung.

## `types/`

Enthalten featureinterne Typen.

## `dialogs/`

Enthalten begrenzte Bestätigungs- oder Bearbeitungsdialoge.

## `forms/`

Enthalten strukturierte Eingabeabläufe.

## `tables/`

Enthalten featurespezifische Tabellen- und Listenansichten.

Das Frontend enthält keine authoritative Geschäftslogik.

---

# Tests

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

Zuordnung eines Features:

```text
tests/unit/<feature>/
tests/integration/<feature>/
tests/contract/<feature>/
tests/workflow/<feature>/
tests/performance/<feature>/
tests/e2e/<feature>/
```

Nicht jedes Feature benötigt alle Testarten.

Die erforderlichen Testarten ergeben sich aus Risiko, Architektur und Akzeptanzkriterien.

---

# Testpflichten

Ein Feature benötigt mindestens:

- Unit-Tests für fachliche Regeln,
- Integrationstests für Persistenz oder technische Integration,
- Contract-Tests bei API- oder Providerverträgen,
- Workflow-Tests bei mehrstufigen fachlichen Abläufen,
- E2E-Tests für kritische Benutzerabläufe.

Ein Fehlerfix soll einen Regressionstest enthalten.

---

# Abhängigkeiten

## Zulässig

```text
Frontend Feature
→ freigegebene REST-API
```

```text
Backend API
→ Application Service
→ Domain
→ Repository- oder Providercontract
→ Infrastrukturadapter
```

## Nicht zulässig

```text
Feature A
→ interne Implementierung von Feature B
```

Nicht zulässig sind direkte Zugriffe auf:

- interne Repositories,
- interne Domainmodelle,
- interne Services,
- interne Validatoren,
- interne Mapper,
- interne Frontendkomponenten,
- interne Hooks.

Featureübergreifende Kommunikation erfolgt ausschließlich über:

- freigegebene Contracts,
- Application Services,
- Domain- oder Integrationsevents,
- ausdrücklich freigegebene gemeinsame Frontendmodule.

---

# Shared-Nutzung

Gemeinsame Bausteine werden nicht vorschnell nach `shared` verschoben.

Voraussetzungen:

- mehrere Features benötigen den Baustein,
- keine eindeutige Featureverantwortung,
- stabile Schnittstelle,
- keine interne Geschäftslogik eines Features,
- dokumentierte Entscheidung.

---

# Daten und Datenverantwortung

Jedes Feature muss dokumentieren:

- welche Daten es besitzt,
- welche Daten es nur liest,
- welche externen Datenquellen es verwendet,
- welche Datenqualität erwartet wird,
- welche Zeitstempel und Einheiten gelten,
- wie historische Daten behandelt werden.

Ein Feature darf Daten eines anderen Features nicht ohne freigegebenen Contract verändern.

---

# API-Verträge

API-Verträge müssen dokumentieren:

- Pfad,
- Methode,
- Eingaben,
- Ausgaben,
- Fehlercodes,
- Berechtigung,
- Versionierung,
- Rückwärtskompatibilität.

Breaking Changes erfordern eine dokumentierte Migrations- oder Versionsstrategie.

---

# Provider-Verträge

Ein Feature mit externen Datenquellen muss dokumentieren:

- Provider,
- verwendete Endpunkte oder Fähigkeiten,
- Datenfelder,
- Aktualität,
- Einheiten,
- Rate Limits,
- Fehlerfälle,
- Fallback-Verhalten,
- Datenqualitätsregeln.

Unsichere oder fehlende Daten dürfen nicht stillschweigend ersetzt werden.

---

# Modell- und Regelversionierung

Verwendet ein Feature ein fachliches Modell oder Regelwerk, müssen dokumentiert werden:

- Modellname,
- Modellversion,
- Regelversion,
- Eingaben,
- Parameter,
- Datenquelle,
- Ergebnis,
- Warnungen,
- Freigabestatus.

Eine fachlich relevante Änderung erzeugt eine neue Version.

Historische Trades bleiben mit der ursprünglich verwendeten Version verknüpft.

---

# Keine Blackbox

Nicht zulässig sind:

- versteckte fachliche Defaults,
- unversionierte Heuristiken,
- Ergebnisse ohne Eingabereferenz,
- automatische Modelländerungen,
- rückwirkendes Überschreiben historischer Ergebnisse.

---

# Benutzerentscheidung

Ein Feature darf Empfehlungen, Warnungen und Bewertungen anzeigen.

Es darf keine autonome Kauf-, Verkaufs-, Halte- oder Positionsgrößenentscheidung treffen.

Fachlich wirksame Aktionen müssen vom Benutzer ausgelöst oder bestätigt werden.

---

# Feature-Lifecycle

Jedes Feature folgt dem verbindlichen Lebenszyklus aus:

```text
docs/technical/FEATURE_LIFECYCLE.md
```

Phasen:

```text
1. Idee
2. Analyse
3. Spezifikation
4. Architekturprüfung
5. Freigabe zur Umsetzung
6. Implementierung
7. technische Prüfung
8. fachliche Prüfung
9. Abnahme
10. Veröffentlichung
11. Beobachtung
12. Verbesserungsvorschlag
```

---

# Definition of Ready

Ein Feature ist bereit zur Umsetzung, wenn:

- Problem und Ziel dokumentiert sind,
- Umfang und Nicht-Umfang feststehen,
- Akzeptanzkriterien prüfbar sind,
- Datenquellen und Modelle benannt sind,
- Architektur geprüft ist,
- Risiken bewertet sind,
- Verantwortlichkeit festgelegt ist,
- Umsetzung freigegeben ist.

---

# Definition of Done

Ein Feature ist abgeschlossen, wenn:

- Implementierung vollständig ist,
- Dokumentation aktualisiert ist,
- Tests erfolgreich sind,
- Typprüfung, Linting und Build erfolgreich sind,
- Migrationen geprüft sind,
- API- und Providerverträge dokumentiert sind,
- Datenquelle, Modellversion, Eingaben und Ergebnis nachvollziehbar sind,
- keine autonome Handelsentscheidung eingeführt wurde,
- technisches Review abgeschlossen ist,
- fachliche Prüfung abgeschlossen ist,
- Abnahme dokumentiert ist,
- offene Restpunkte dokumentiert sind.

---

# Pflichtartefakte je Änderungstyp

## Neues Feature

Mindestens:

- Featurebeschreibung,
- Anforderungen,
- Architekturprüfung,
- Implementierung,
- Tests,
- Dokumentation,
- Review,
- Abnahme.

## Fehlerkorrektur

Mindestens:

- Fehlerbeschreibung,
- Reproduktionsschritte,
- Ursache,
- Korrektur,
- Regressionstest,
- Review,
- Abnahme.

## Modelländerung

Mindestens:

- bisherige Version,
- neue Version,
- Änderungsgrund,
- geänderte Regeln,
- Vergleich,
- Testdatensatz,
- fachliche Bewertung,
- Freigabe.

## Technische Änderung

Mindestens:

- technische Begründung,
- Risikoanalyse,
- Nachweis unveränderten Fachverhaltens,
- Tests,
- Review.

---

# Feature-Entscheidungen

Featurebezogene Architektur- oder Fachentscheidungen werden dokumentiert.

Empfohlener Ablageort:

```text
docs/features/<feature>/DECISIONS.md
```

Eine Entscheidung enthält mindestens:

- ID,
- Datum,
- Status,
- Kontext,
- Entscheidung,
- Begründung,
- Alternativen,
- Auswirkungen.

---

# Feature-Changelog

Wesentliche Änderungen werden in:

```text
docs/features/<feature>/CHANGELOG.md
```

oder in einem zentralen, eindeutig referenzierten Änderungsprotokoll dokumentiert.

Mindestens:

- Version,
- Datum,
- Änderung,
- betroffene Modell- oder Regelversion,
- Migrationshinweis.

---

# Status eines Features

Empfohlene Status:

```text
Draft
Review
Approved
Implemented
Verified
Released
Deprecated
```

Der Status muss eindeutig definiert und nachvollziehbar geändert werden.

`Implemented` bedeutet nicht automatisch `Verified` oder `Released`.

---

# Feature-Freigabe

Ein Feature kann freigegeben werden, wenn:

- Anforderungen bestätigt sind,
- Architektur konsistent ist,
- Implementierung geprüft ist,
- Tests erfolgreich sind,
- Dokumentation vollständig ist,
- Nachvollziehbarkeit gegeben ist,
- fachliche Abnahme dokumentiert ist,
- Modellversion freigegeben ist, falls betroffen.

---

# Nicht zulässig

Nicht zulässig sind:

- Featureimplementierung ohne dokumentierte Anforderungen,
- eigene abweichende Verzeichnisstruktur,
- parallele Featuretests außerhalb der zentralen Teststruktur,
- direkte interne Abhängigkeiten zwischen Features,
- unversionierte Modelländerungen,
- versteckte fachliche Defaultwerte,
- automatische Handelsentscheidungen,
- Freigabe ohne Tests und Abnahme,
- undokumentierte API- oder Datenmodelländerungen.

---

# Freigabekriterien dieses Dokuments

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn:

- die Pfade mit dem Repository übereinstimmen,
- Backend- und Frontendstruktur bestätigt sind,
- zentrale Testablage bestätigt ist,
- Pflicht- und optionale Artefakte akzeptiert sind,
- Lebenszyklus und Definition of Done abgestimmt sind,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

Bis dahin bleibt der Status `🔵 Review`.

---

# Siehe auch

- `docs/foundation/ARCHITECTURE.md`
- `docs/architecture/Source_Architecture.md`
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/technical/FEATURE_IMPLEMENTATION_TEMPLATE.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/foundation/TRACEABILITY.md`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Vollständiger Abgleich mit Repository, Source-, Backend- und Frontend-Architektur; zentrale Testablage, Pflichtartefakte, Lifecycle, Modellversionierung und Freigabekriterien vereinheitlicht |
