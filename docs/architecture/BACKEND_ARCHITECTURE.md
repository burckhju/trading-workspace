# Backend Architecture

> Technische Architektur des Backends des Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-018 |
| Dokument | BACKEND_ARCHITECTURE.md |
| Dokumenttyp | Technical Architecture |
| Version | 1.1 |
| Status | 🟢 Approved |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | Projektverantwortlicher |
| Freigabedatum | 2026-08-01 |

---

# Zweck

Dieses Dokument beschreibt die verbindliche technische Architektur des Backends des **Trading Workspace**.

Es definiert:

- Systemgrenzen,
- Schichten,
- Verantwortlichkeiten,
- zulässige Abhängigkeiten,
- Featurestruktur,
- Kommunikation,
- Persistenz,
- Providerintegration,
- Fehlerbehandlung,
- Transaktionen,
- Logging,
- Auditierbarkeit,
- Testbarkeit.

Fachliche Regeln, Modelle und konkrete Anwendungsfälle werden in den jeweiligen Feature- und Referenzdokumenten beschrieben.

---

# Architekturreferenzen

Dieses Dokument konkretisiert die übergreifende Architektur aus:

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

Ein Widerspruch muss vor einer Freigabe dokumentiert und behoben werden.

---

# Architekturprinzipien

Das Backend folgt diesen Grundsätzen:

- Feature-orientierte Struktur,
- Clean Architecture,
- Domain-orientierte Modellierung,
- Dependency Inversion,
- geringe Kopplung,
- hohe Kohäsion,
- explizite Schnittstellen,
- zentrale technische Infrastruktur,
- vollständige Testbarkeit,
- nachvollziehbare Berechnungen,
- versionierte fachliche Modelle,
- keine autonome Handelsentscheidung.

Die Software unterstützt den Benutzer, trifft jedoch keine Kauf-, Verkaufs-, Halte- oder Positionsgrößenentscheidung.

---

# Systemkontext

Das Backend stellt die fachlichen und technischen Dienste des Trading Workspace bereit.

Es kommuniziert mit:

- dem Frontend über eine versionierte REST-API,
- PostgreSQL über die Persistenzschicht,
- externen Marktdaten- und Produktprovidern über Provideradapter,
- Benachrichtigungsdiensten über Provideradapter,
- technischen Betriebsdiensten über definierte Infrastrukturkomponenten.

Das Frontend greift niemals direkt auf Datenbank oder externe Provider zu.

---

# Zielarchitektur

```text
Frontend
   │
   ▼
REST API
   │
   ▼
Application Service
   │
   ▼
Domain
   │
   ▼
Repository-Abstraktion
   │
   ▼
Persistenzadapter
   │
   ▼
Database
```

Externe Systeme werden parallel über Infrastrukturadapter angebunden:

```text
Application Service oder Domain Contract
   │
   ▼
Provider-Abstraktion
   │
   ▼
Provideradapter
   │
   ▼
Externes System
```

Provider liegen nicht hinter der Datenbank und sind keine Persistenzschicht.

---

# Projektstruktur

```text
backend/
├── app/
│   ├── core/
│   ├── shared/
│   ├── features/
│   ├── providers/
│   ├── database/
│   ├── events/
│   └── main.py
├── migrations/
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── .env.example
└── .python-version
```

Die vollständige Repositorystruktur wird in `Source_Architecture.md` festgelegt.

---

# Verantwortungsbereiche

## `app/core/`

Enthält zentrale technische Infrastruktur.

Beispiele:

- Konfiguration,
- Dependency Injection,
- Authentifizierung,
- Autorisierung,
- Middleware,
- zentrale Fehlerbehandlung,
- technisches Logging,
- Sicherheitskomponenten.

`core` enthält keine fachliche Geschäftslogik.

---

## `app/shared/`

Enthält fachlich neutrale und featureübergreifend wiederverwendbare Bausteine.

Beispiele:

- Identifier,
- Value Objects,
- Basistypen,
- generische Validatoren,
- technische Contracts,
- gemeinsame Enumerationen,
- allgemeine Hilfsfunktionen.

`shared` ist kein Sammelverzeichnis.

Ein Baustein darf nur nach `shared` verschoben werden, wenn:

- mehrere Features ihn benötigen,
- er keine interne Verantwortung eines Features enthält,
- seine Schnittstelle stabil und ausdrücklich freigegeben ist.

---

## `app/features/`

Enthält alle fachlichen Funktionen.

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

Jedes Feature besitzt eine klar abgegrenzte fachliche Verantwortung.

Ein Feature darf keine internen Implementierungsdetails eines anderen Features direkt verwenden.

---

## `app/providers/`

Enthält technische Adapter zu externen Diensten.

Beispiele:

- Marktdatenanbieter,
- Produktdatenanbieter,
- historische Kursquellen,
- Benachrichtigungsdienste,
- spätere Broker- oder Importadapter.

Provideradapter implementieren Contracts, die von Application Services oder der Domain benötigt werden.

Fachliche Providerverwaltung als Benutzerfunktion gehört weiterhin zum Feature `app/features/provider/`.

---

## `app/database/`

Enthält zentrale technische Datenbankinfrastruktur.

Beispiele:

- Engine- und Sessionverwaltung,
- Basisklassen,
- Transaktionsunterstützung,
- gemeinsame Datenbankabhängigkeiten.

Fachspezifische Repositoryinterfaces und Persistenzadapter verbleiben beim zuständigen Feature.

---

## `app/events/`

Enthält ausschließlich gemeinsam verwendete technische Eventinfrastruktur oder ausdrücklich freigegebene featureübergreifende Eventcontracts.

Featureinterne Events verbleiben im jeweiligen Feature.

---

## `migrations/`

Enthält versionierte Alembic-Migrationen.

Datenbankschemaänderungen erfolgen ausschließlich über Migrationen.

Manuelle, nicht dokumentierte Schemaänderungen sind nicht zulässig.

---

# Aufbau eines Backend-Features

Ein Backend-Feature kann folgende Struktur besitzen:

```text
feature/
├── api/
├── services/
├── domain/
├── repositories/
├── schemas/
├── validators/
├── events/
└── mappers/
```

Nicht jedes Unterverzeichnis muss von Beginn an existieren.

Ein Verzeichnis wird erst angelegt, wenn das Feature die entsprechende Verantwortung tatsächlich benötigt.

Tests liegen nicht innerhalb des Features, sondern zentral unter:

```text
tests/
```

---

# API-Schicht

## Verantwortung

Die API-Schicht:

- definiert Routen,
- validiert Transportdaten,
- authentifiziert und autorisiert,
- ruft Application Services auf,
- übersetzt Ergebnisse in API-Antworten,
- verwendet stabile Fehlercodes.

## Nicht zulässig

- fachliche Berechnungen,
- direkte SQL-Abfragen,
- direkte Datenbankzugriffe,
- direkte Aufrufe externer APIs,
- Transaktionssteuerung,
- interne Logik anderer Features.

API-Schemas sind Transportmodelle und nicht automatisch Domain- oder Persistenzmodelle.

---

# Application Services

Application Services koordinieren fachliche Anwendungsfälle.

Sie:

- steuern Workflows,
- koordinieren Domainobjekte,
- verwenden Repository- und Providercontracts,
- steuern fachliche Transaktionsgrenzen,
- erzeugen fachliche oder Integrationsevents,
- stellen Nachvollziehbarkeitsinformationen zusammen.

Ein Service besitzt eine klar benannte Verantwortung.

Große Sammelservices sind nicht zulässig.

---

# Domain

Die Domain enthält die fachlichen Regeln des zuständigen Features.

Sie kann enthalten:

- Entities,
- Value Objects,
- fachliche Services,
- Invarianten,
- Berechnungen,
- Bewertungen,
- fachliche Ereignisse.

Die Domain ist unabhängig von:

- HTTP,
- FastAPI,
- SQLAlchemy,
- konkreten Datenbanken,
- konkreten Providern,
- Dateisystemen,
- Benutzeroberflächen.

## Keine autonome Handelsentscheidung

Domainlogik darf Regeln auswerten, Kennzahlen berechnen und Warnungen erzeugen.

Sie darf keine autonome Handelsentscheidung treffen oder ausführen.

Die endgültige Entscheidung verbleibt beim Benutzer.

---

# Repositories

## Repository-Abstraktionen

Repositoryinterfaces gehören zum verantwortlichen Feature.

Sie definieren fachlich benötigte Persistenzoperationen.

## Persistenzadapter

Konkrete Implementierungen verwenden die zentrale Datenbankinfrastruktur.

## Erlaubt

- Laden,
- Speichern,
- Aktualisieren,
- Löschen,
- fachlich neutrale Abfragen,
- Mapping zwischen Persistenz- und Domainmodell.

## Nicht erlaubt

- fachliche Entscheidungen,
- Bewertungslogik,
- Workflowsteuerung,
- Providerzugriffe,
- eigenständige Transaktionsgrenzen.

---

# Provider

## Providercontracts

Ein Providercontract beschreibt, welche externe Fähigkeit ein Feature benötigt.

Beispiele:

- aktuelle Marktdaten laden,
- historische Kurse laden,
- Produktdaten suchen,
- Benachrichtigung versenden.

## Provideradapter

Ein Adapter kapselt:

- Authentifizierung beim Anbieter,
- HTTP- oder Protokollzugriff,
- Fehlerübersetzung,
- Rate Limits,
- Retryregeln,
- Datenmapping,
- technische Telemetrie.

## Datenqualität

Providerdaten gelten als externe, nicht vertrauenswürdige Eingaben.

Sie müssen validiert werden auf:

- Vollständigkeit,
- Aktualität,
- Einheit,
- Zeitstempel,
- Plausibilität,
- Providerstatus.

Fehlende oder unsichere Daten dürfen nicht stillschweigend ersetzt werden.

---

# Mappings

Mapper übersetzen zwischen:

- API-Schema,
- Domainmodell,
- Persistenzmodell,
- Providerdarstellung.

Mappinglogik ist von Geschäftslogik zu trennen.

`mappers/` ist optional und wird nur angelegt, wenn eigenständige Mappingverantwortung vorhanden ist.

---

# Validierung

Validierung erfolgt auf mehreren Ebenen:

1. API: Format und Transportstruktur,
2. Schema: Typen und Feldgrenzen,
3. Application Service: Anwendungsfall und Berechtigung,
4. Domain: fachliche Invarianten,
5. Provideradapter: externe Datenqualität.

Jede Ebene prüft ausschließlich ihre Verantwortung.

Fachliche Fehler erhalten stabile, maschinenlesbare Fehlercodes.

---

# Abhängigkeitsregeln

## Zulässig

```text
API
→ Application Service
→ Domain
→ Repository- oder Providercontract
→ Infrastrukturadapter
```

## Nicht zulässig

```text
Domain
→ FastAPI
```

```text
Domain
→ SQLAlchemy
```

```text
API
→ konkrete Datenbankimplementierung
```

```text
Feature A
→ interne Implementierung von Feature B
```

```text
Frontend
→ Repository oder Database
```

Featureübergreifende Kommunikation erfolgt ausschließlich über:

- freigegebene Contracts,
- Application Services,
- Domain- oder Integrationsevents.

---

# Dependency Injection

Konkrete Infrastrukturimplementierungen werden an der Anwendungsgrenze verdrahtet.

Domain und Application Services hängen von Abstraktionen ab.

Nicht zulässig sind:

- globale versteckte Serviceinstanzen,
- direkte Erzeugung konkreter Provider in Domaincode,
- direkte Erzeugung konkreter Repositories in API-Endpunkten.

---

# Transaktionen

Application Services definieren fachliche Transaktionsgrenzen.

Repositories:

- nehmen an einer bestehenden Transaktion teil,
- öffnen keine unabhängigen fachlichen Transaktionen,
- führen keine versteckten Commits durch.

Externe Provideraufrufe und Datenbanktransaktionen müssen so koordiniert werden, dass inkonsistente Zwischenzustände vermieden oder nachvollziehbar behandelt werden.

---

# Events

## Fachliche Events

Events werden als eingetretene Tatsachen in der Vergangenheitsform benannt.

Beispiele:

```text
TRADE_OPENED
STOP_CHANGED
PRODUCT_CHANGED
PARTIAL_SALE_RECORDED
TRADE_CLOSED
OBSERVATION_COMPLETED
JOURNAL_FINALIZED
MODEL_VERSION_APPROVED
```

## Regeln

Events:

- besitzen ein eindeutiges Schema,
- sind versionierbar,
- enthalten einen Zeitstempel,
- enthalten eine Korrelations-ID,
- enthalten nur erforderliche Daten,
- ersetzen keine beliebigen direkten Funktionsaufrufe.

Events dürfen nicht verwendet werden, um unklare Verantwortlichkeiten zu verdecken.

---

# Fehlerbehandlung

Fehler werden an der zuständigen Schicht erzeugt und an Systemgrenzen kontrolliert übersetzt.

Eine API-Fehlerantwort enthält mindestens:

```json
{
  "code": "TRADE_PLAN_INVALID",
  "message": "Der Trade-Plan ist fachlich ungültig.",
  "details": []
}
```

Interne Stacktraces oder vertrauliche Daten dürfen nicht an das Frontend übertragen werden.

Exceptions dürfen nicht stillschweigend verschluckt werden.

---

# Konfiguration

Konfiguration wird zentral, typisiert und umgebungsabhängig verwaltet.

Zulässige Quellen:

- Umgebungsvariablen,
- sichere Konfigurationsdateien ohne Geheimnisse,
- Secret-Stores in Zielumgebungen.

Nicht zulässig:

- fachlich wirksame versteckte Defaults,
- API-Schlüssel im Quellcode,
- produktive Zugangsdaten in `.env.example`,
- verstreute Konfigurationslogik.

---

# Sicherheit

Sicherheitsverantwortung umfasst:

- Authentifizierung,
- Autorisierung,
- Rollen und Rechte,
- Eingabevalidierung,
- Geheimnisverwaltung,
- Audit Logging,
- Schutz vertraulicher Daten.

Berechtigungsprüfungen erfolgen an den zuständigen Anwendungsgrenzen und dürfen nicht allein dem Frontend überlassen werden.

---

# Logging und Audit

## Technisches Logging

Technische Logs enthalten nach Möglichkeit:

- Zeitstempel,
- Log-Level,
- Korrelations-ID,
- Feature,
- Operation,
- Dauer,
- Ergebnis,
- Fehlerkennung.

## Fachliches Audit

Fachlich relevante Zustandsänderungen werden als Auditereignis dokumentiert.

Mindestens nachvollziehbar:

- Akteur,
- Zeitpunkt,
- Feature,
- Aktion,
- betroffene fachliche ID,
- vorheriger und neuer Zustand oder Referenz,
- verwendete Modellversion,
- Ergebnis.

Nicht protokolliert werden:

- Passwörter,
- Tokens,
- API-Schlüssel,
- vollständige Sessiondaten,
- unnötige personenbezogene Daten.

---

# Nachvollziehbarkeit von Berechnungen

Für jede fachlich relevante Berechnung oder Empfehlung müssen referenzierbar sein:

- Datenquelle,
- Datenstand,
- Modell oder Regelwerk,
- Version,
- Eingaben,
- Konfiguration,
- Ergebnis,
- Warnungen,
- Einschränkungen.

Historische Trades bleiben mit der ursprünglich verwendeten Modellversion verknüpft.

Neue Modellversionen überschreiben keine historischen Ergebnisse.

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

## Zuordnung

- Unit-Tests prüfen Domain, Services und Mapper isoliert.
- Integrationstests prüfen Datenbank- und Infrastrukturzusammenspiel.
- Contract-Tests prüfen API- und Providerverträge.
- Workflow-Tests prüfen fachliche Abläufe über mehrere Komponenten.
- Performance-Tests prüfen definierte Laufzeit- und Lastanforderungen.
- E2E-Tests prüfen vollständige Benutzerabläufe.

Externe Provider werden in Unit- und regulären Integrationstests kontrolliert ersetzt.

Echte externe Systeme werden nur in ausdrücklich gekennzeichneten, kontrollierten Tests verwendet.

---

# Erweiterbarkeit

## Neue Features

Neue fachliche Funktionen werden angelegt unter:

```text
backend/app/features/<feature>/
```

## Neue Provider

Neue technische Provideradapter werden angelegt unter:

```text
backend/app/providers/<provider>/
```

oder in einer später ausdrücklich freigegebenen providerspezifischen Struktur.

## Neue Modelle

Neue Modellversionen werden registriert und versioniert.

Bestehende Modellversionen werden nicht überschrieben.

## Architekturänderungen

Eine Änderung an Schichten, Abhängigkeitsrichtung oder Datenverantwortung erfordert eine dokumentierte Architekturentscheidung.

---

# Nicht Bestandteil dieses Dokuments

Dieses Dokument definiert nicht:

- konkrete REST-Endpunkte,
- konkrete Datenbanktabellen,
- einzelne Geschäftsregeln,
- konkrete Modellparameter,
- konkrete Providerverträge,
- Bedienoberflächen.

Diese Inhalte befinden sich in den jeweiligen Feature-, API-, Datenbank-, Modell- und Referenzdokumenten.

---

# Freigabekriterien

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn:

- die Struktur mit dem Repository übereinstimmt,
- `Source_Architecture.md` als Referenz bestätigt ist,
- Feature- und Teststruktur vereinheitlicht sind,
- Provider- und Persistenzverantwortung bestätigt sind,
- die Abhängigkeitsregeln akzeptiert sind,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

Bis dahin bleibt der Status `🔵 Review`.

---

# Siehe auch

- `docs/foundation/ARCHITECTURE.md`
- `docs/architecture/Source_Architecture.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`
- `docs/architecture/Feature_Architecture.md`
- `docs/technical/CODING_STANDARDS.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/reference/API.md`
- `docs/reference/DATABASE.md`
- `docs/reference/TEST_STRATEGY.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/foundation/TRACEABILITY.md`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Abgleich mit Repository und Source Architecture; Korrektur von Schichtenmodell, Providerrolle, Featurestruktur, Testablage, Nachvollziehbarkeit und Freigabekriterien |
