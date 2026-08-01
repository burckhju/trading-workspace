# Coding Standards

> Projektweite Entwicklungs- und Codierungsrichtlinien des Trading Workspace

---

# Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-016 |
| Dokument | CODING_STANDARDS.md |
| Dokumenttyp | Development Standard |
| Version | 1.1 |
| Status | 🔵 Review |
| Letzte Änderung | 2026-08-01 |
| Freigegeben durch | noch offen |
| Freigabedatum | noch offen |

---

# Zweck

Dieses Dokument definiert die verbindlichen Entwicklungs- und Codierungsrichtlinien des **Trading Workspace**.

Es stellt sicher, dass Implementierungen unabhängig von Entwickler, Werkzeug oder ChatGPT-Sitzung

- lesbar,
- verständlich,
- testbar,
- wartbar,
- reproduzierbar,
- nachvollziehbar und
- sicher

bleiben.

Die Regeln gelten für Backend, Frontend, Datenbank, Tests, Infrastruktur und technische Dokumentation.

---

# Verbindlichkeit

Die Schlüsselwörter werden wie folgt verwendet:

- **MUSS**: verbindliche Anforderung,
- **DARF NICHT**: verbindliches Verbot,
- **SOLL**: begründete Standardvorgabe,
- **DARF**: zulässige Option.

Abweichungen von MUSS- oder DARF-NICHT-Regeln erfordern eine dokumentierte und freigegebene Architektur- oder Projektentscheidung.

---

# Grundprinzipien

## Lesbarkeit vor Kürze

Code wird primär für Menschen geschrieben.

Bevorzugt werden:

- eindeutige Namen,
- kleine Verantwortungsbereiche,
- explizite Datenflüsse,
- nachvollziehbare Fehlerbehandlung,
- geringe Kopplung.

Unnötig kompakter, verschachtelter oder impliziter Code ist zu vermeiden.

## Eine Verantwortung pro Baustein

Module, Klassen, Funktionen, Services und Komponenten besitzen jeweils eine klar erkennbare Verantwortung.

## Keine doppelte Implementierung

Fachliche Regeln, Berechnungen, Validierungen und Mappings dürfen nicht an mehreren Stellen unabhängig implementiert werden.

## Explizit statt implizit

Fachlich relevante Standardwerte, Umrechnungen, Filter, Grenzwerte und Modellannahmen müssen ausdrücklich benannt und dokumentiert werden.

## Deterministische Verarbeitung

Bei identischen Eingaben, Datenständen, Modellversionen und Konfigurationen muss eine Berechnung dasselbe Ergebnis liefern, sofern die Fachlogik keine ausdrücklich dokumentierte Zufallskomponente enthält.

---

# Projektstruktur

Die verbindliche Repository- und Quellstruktur wird in folgendem Dokument definiert:

```text
docs/architecture/Source_Architecture.md
```

Neue Hauptverzeichnisse oder abweichende Feature-Strukturen erfordern eine dokumentierte Architekturentscheidung.

---

# Benennung

## Allgemeine Regeln

Namen müssen den fachlichen oder technischen Zweck ausdrücken.

Nicht zulässig sind unklare Abkürzungen wie:

```text
tp
prd
mgr
proc
tmp
data2
new_data
```

Zulässig sind allgemein etablierte technische Abkürzungen, zum Beispiel:

```text
api
url
http
id
uuid
utc
sql
dto
```

## Python

| Artefakt | Konvention | Beispiel |
|---|---|---|
| Module und Dateien | `snake_case` | `trade_service.py` |
| Funktionen und Variablen | `snake_case` | `calculate_stop_distance()` |
| Klassen | `PascalCase` | `TradePlanService` |
| Konstanten | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Private Namen | führender Unterstrich | `_load_configuration()` |

## TypeScript

| Artefakt | Konvention | Beispiel |
|---|---|---|
| Variablen und Funktionen | `camelCase` | `calculateStopDistance()` |
| Typen und Interfaces | `PascalCase` | `TradePlan` |
| Konstanten | `UPPER_SNAKE_CASE` oder klar benanntes `camelCase` | `MAX_RETRY_COUNT` |
| React-Komponenten | `PascalCase` | `TradeCard.tsx` |
| React-Hooks | Präfix `use` | `useTradePlan.ts` |
| Testdateien | Suffix `.test` oder `.spec` | `TradeCard.test.tsx` |

## Datenbank

Tabellen und Spalten verwenden `snake_case`.

Beispiele:

```text
trade
trade_event
trade_plan
created_at
model_version_id
```

## REST-API

Ressourcenpfade verwenden Pluralformen und `kebab-case`.

Beispiele:

```text
/api/v1/trades
/api/v1/trade-plans
/api/v1/model-versions
```

Aktionen werden nach Möglichkeit als Zustandsänderung einer Ressource modelliert und nicht als frei benannte Verben im Pfad.

---

# Fachliche IDs

Fachliche Objekte verwenden UUIDs.

Beispiele:

```text
trade_id
trade_plan_id
product_id
model_version_id
```

Fortlaufende Integer dürfen als rein technische Datenbankschlüssel verwendet werden, wenn sie nicht nach außen sichtbar sind und keine fachliche Identität darstellen.

---

# Datum, Zeit und Zeitzonen

Intern werden Zeitpunkte

- in UTC,
- mit Zeitzoneninformation und
- im ISO-8601-Format

gespeichert und übertragen.

Beispiel:

```text
2026-08-01T13:00:00Z
```

Lokale Zeitzonen werden ausschließlich für Anzeige oder ausdrücklich definierte fachliche Kalenderregeln verwendet.

Naive Datums- und Zeitwerte ohne Zeitzonenbezug sind für Zeitpunkte nicht zulässig.

---

# Zahlen, Geld und Prozentwerte

## Geldbeträge

Geldbeträge werden im Backend mit `Decimal` verarbeitet.

Binäre Gleitkommazahlen wie `float` dürfen nicht für fachliche Geldberechnungen verwendet werden.

Zusätzlich müssen bekannt sein:

- Währung,
- Rundungsregel,
- Anzahl Dezimalstellen,
- Zeitpunkt der Rundung.

## Prozentwerte

Die interne Repräsentation eines Prozentwertes muss pro Datentyp eindeutig definiert sein.

Zulässige Varianten sind beispielsweise:

```text
18.0 für 18 Prozent
```

oder

```text
0.18 für 18 Prozent
```

Innerhalb desselben Feldes oder Modells darf die Darstellung nicht wechseln.

API-Schema, Datenbankfeld und Dokumentation müssen die verwendete Einheit ausdrücklich benennen.

## Mengen und Kurse

Stückzahlen, Bezugsverhältnisse, Kurse und Kennzahlen müssen mit einer fachlich passenden Präzision verarbeitet werden.

Rundung darf erst an einer fachlich definierten Stelle erfolgen.

---

# Python-Standard

## Laufzeit und Typisierung

Das Backend verwendet Python 3.12.

Neue und geänderte Python-Funktionen müssen vollständig typisiert sein.

Die Typprüfung erfolgt im strikten Modus mit `mypy`.

Nicht zulässig sind:

- unbegründetes `Any`,
- dauerhaftes Unterdrücken von Typfehlern,
- unkommentierte `# type: ignore`,
- Rückgabewerte mit wechselnden, nicht modellierten Typen.

## Formatierung und Linting

Verbindliche Werkzeuge und Einstellungen werden in `backend/pyproject.toml` gepflegt.

Aktuell gelten:

```text
Black: Zeilenlänge 100
Ruff: Zeilenlänge 100
Ruff-Regelgruppen: E, F, I, UP, B, SIM, RUF
mypy: strict
```

Vor einem Commit müssen mindestens erfolgreich sein:

```bash
python -m black --check app ../tests
python -m ruff check app ../tests
python -m mypy app
```

Sofern das projektrelevante Prüfsystem abweichende Pfade kapselt, ist das Repository-Skript maßgeblich.

## Imports

Imports werden von Ruff sortiert.

Es gilt folgende Reihenfolge:

1. Python-Standardbibliothek,
2. externe Bibliotheken,
3. Projektimporte.

Wildcard-Imports sind nicht zulässig.

## Funktionen und Klassen

Funktionen sollen klein bleiben und eine erkennbare Verantwortung besitzen.

Klassen dürfen nicht als unspezifische Sammelstellen verwendet werden.

Große Serviceklassen sind nach fachlichen Verantwortungen aufzuteilen.

## Pydantic- und API-Modelle

Eingabe-, Ausgabe- und interne Domainmodelle werden getrennt, wenn sie unterschiedliche Verantwortungen besitzen.

API-Schemas dürfen nicht unkontrolliert als Persistenz- oder Domainmodelle wiederverwendet werden.

---

# TypeScript- und React-Standard

## Laufzeit und Werkzeugversionen

Das Frontend verwendet die in `frontend/package.json` festgelegten Versionen.

Aktuell:

```text
Node.js 22.16.0
npm 10.9.2
TypeScript 5.8.3
React 19.1.0
```

## TypeScript

TypeScript wird typgeprüft verwendet.

Nicht zulässig sind:

- unbegründetes `any`,
- unkontrollierte Typumwandlungen,
- dauerhaft unterdrückte Compilerfehler,
- fachliche Daten als unstrukturierte Objekte ohne Typdefinition.

Unbekannte externe Daten sind zunächst `unknown` und müssen vor Verwendung validiert oder eingegrenzt werden.

## ESLint

ESLint muss ohne Warnungen erfolgreich sein.

Verbindlicher Befehl:

```bash
npm run lint
```

Die Konfiguration verwendet typgeprüfte TypeScript-Regeln sowie die React-Hooks-Regeln.

## Prettier

Formatierung wird durch Prettier geprüft.

Verbindlicher Befehl:

```bash
npm run format
```

Automatische Formatierung erfolgt mit:

```bash
npm run format:write
```

## React-Komponenten

Komponenten

- zeigen Daten an,
- erfassen Benutzereingaben,
- koordinieren UI-Zustand und
- rufen freigegebene Services oder Hooks auf.

Fachliche Berechnungen dürfen nicht in React-Komponenten implementiert werden.

## React-Hooks

Hooks kapseln wiederverwendbare UI- oder Integrationslogik.

Hooks dürfen nicht dazu verwendet werden, fachliche Domainlogik aus dem Backend im Frontend nachzubauen.

## Zustandsbehandlung

Abgeleitete Werte sollen berechnet und nicht redundant im Zustand gespeichert werden.

Serverdaten und lokaler UI-Zustand müssen klar getrennt sein.

---

# Architekturregeln

## Backend

Die vorgesehene Abhängigkeitsrichtung lautet:

```text
API
→ Application Service
→ Domain
→ Repository-Abstraktion
→ Infrastruktur
```

Nicht zulässig:

- SQL oder konkrete Datenbankzugriffe in API-Endpunkten,
- Geschäftslogik in Repositories,
- Framework-Abhängigkeiten in der Domain,
- direkte Nutzung interner Bausteine anderer Features.

## Frontend

Das Frontend

- zeigt Informationen,
- validiert Eingabeformate,
- sendet Anfragen,
- zeigt Warnungen und Berechnungsergebnisse.

Das Frontend darf keine authoritative fachliche Berechnung enthalten, die vom Backend abweichen kann.

## Featureübergreifende Kommunikation

Features kommunizieren ausschließlich über ausdrücklich freigegebene:

- Contracts,
- Application Services,
- Domain- oder Integration-Events.

Direkte Zugriffe auf interne Repositories, Domainmodelle, Validatoren, Mapper oder interne Services eines anderen Features sind nicht zulässig.

---

# Trading-spezifische Regeln

## Keine Handelsentscheidung durch die Software

Trading Workspace trifft keine Handelsentscheidungen.

Der Code darf keine autonome Kauf-, Verkaufs-, Halte- oder Positionsgrößenentscheidung ausführen.

Die Software darf:

- Daten sammeln,
- Kennzahlen berechnen,
- Regeln auswerten,
- Kandidaten sortieren,
- Hinweise anzeigen,
- Warnungen erzeugen,
- benutzerdefinierte Kriterien prüfen.

Die endgültige Entscheidung und Bestätigung verbleibt beim Benutzer.

## Nachvollziehbarkeit jeder Empfehlung und Berechnung

Für jede fachlich relevante Empfehlung, Bewertung oder Berechnung müssen mindestens nachvollziehbar sein:

- Datenquelle,
- Datenstand oder Abrufzeitpunkt,
- Modell oder Regelwerk,
- Modell- beziehungsweise Regelversion,
- Eingaben,
- relevante Konfiguration,
- Ergebnis,
- Warnungen und Einschränkungen.

Diese Informationen müssen speicherbar und für spätere Auswertung referenzierbar sein.

## Keine Blackbox

Nicht zulässig sind:

- versteckte fachliche Defaultwerte,
- nicht dokumentierte Heuristiken,
- unversionierte Bewertungslogik,
- Ergebnisse ohne Eingabereferenz,
- Überschreiben historischer Berechnungsergebnisse ohne Versionierung.

## Modellversionierung

Eine fachlich relevante Änderung an einem Handelsmodell oder Regelwerk erzeugt eine neue Version.

Bereits geplante, eröffnete oder abgeschlossene Trades bleiben mit der ursprünglich verwendeten Modellversion verknüpft.

Historische Ergebnisse dürfen nicht stillschweigend mit einer neueren Modellversion neu interpretiert werden.

## Datenqualität

Fehlende, veraltete, widersprüchliche oder unvollständige Marktdaten müssen erkannt und sichtbar gemacht werden.

Unsichere Daten dürfen nicht stillschweigend durch plausible Werte ersetzt werden.

## Benutzerbestätigung

Fachlich wirksame Zustandsänderungen müssen eindeutig vom Benutzer ausgelöst oder bestätigt werden.

Beispiele:

- Trade eröffnen,
- Stop ändern,
- Teilverkauf erfassen,
- Trade schließen,
- Modellversion freigeben.

---

# Geschäftslogik

Geschäftslogik liegt in der Domain- oder Application-Service-Schicht des zuständigen Features.

Nicht zulässig sind fachliche Berechnungen in:

- API-Controllern,
- Repositories,
- Datenbankmigrationen,
- React-Komponenten,
- allgemeinen Hilfsmodulen ohne fachliche Zuordnung.

Ein fachlicher Algorithmus muss einen eindeutigen Eigentümer besitzen.

---

# Repositories

Repositories kapseln Persistenzzugriffe.

Sie dürfen:

- lesen,
- speichern,
- aktualisieren,
- löschen,
- fachlich neutrale Abfragen bereitstellen.

Sie dürfen keine fachlichen Entscheidungen oder Berechnungsmodelle enthalten.

---

# Services

Ein Service besitzt eine klar benannte Verantwortung.

Nicht zulässig ist eine Klasse, die gleichzeitig beispielsweise

- Trade-Planung,
- Produktsuche,
- Import,
- Statistik und
- Benachrichtigung

implementiert.

Services müssen so geschnitten sein, dass ihre Verantwortung aus Name, Schnittstelle und Tests erkennbar ist.

---

# API

Die API-Schicht

- authentifiziert,
- autorisiert,
- validiert Transportdaten,
- ruft Application Services auf,
- übersetzt Ergebnisse in API-Antworten.

Sie enthält keine eigenständige Geschäftslogik und keine direkten SQL-Abfragen.

---

# Validierung

Es wird unterschieden zwischen:

- syntaktischer Eingabevalidierung,
- fachlicher Validierung,
- Datenqualitätsprüfung,
- Berechtigungsprüfung.

Syntaktische API-Validierung ersetzt keine fachliche Validierung.

Fachliche Validierungsfehler müssen einen stabilen Fehlercode besitzen.

---

# Fehlerbehandlung

## Fehlerstruktur

API-Fehler verwenden eine konsistente Struktur, mindestens:

```json
{
  "code": "TRADE_PLAN_INVALID",
  "message": "Der Trade-Plan ist fachlich ungültig.",
  "details": []
}
```

`code` ist stabil und maschinenlesbar.

`message` ist verständlich und darf keine vertraulichen technischen Details offenlegen.

## Exceptions

Exceptions dürfen nicht stillschweigend verschluckt werden.

Breite Exception-Behandlung wie `except Exception` ist nur an technischen Systemgrenzen zulässig und muss

- protokollieren,
- einen kontrollierten Fehler liefern oder
- die Exception nach technischer Ergänzung erneut auslösen.

## Frontend-Fehler

Benutzer erhalten verständliche Meldungen mit einer sinnvollen nächsten Aktion.

Interne Stacktraces, Zugangsdaten oder technische Geheimnisse dürfen nicht angezeigt werden.

---

# Logging und Auditierbarkeit

## Technisches Logging

Logs müssen strukturiert und auswertbar sein.

Sie sollen je nach Kontext enthalten:

- Zeitstempel,
- Log-Level,
- Korrelations-ID,
- Benutzer- oder Systemakteur,
- Feature,
- Aktion,
- Ergebnis,
- technische Fehlerkennung.

## Fachliches Audit

Fachlich relevante Zustandsänderungen benötigen ein nachvollziehbares Audit-Ereignis.

Beispiele:

```text
TRADE_OPENED
STOP_CHANGED
PRODUCT_CHANGED
PARTIAL_SALE_RECORDED
TRADE_CLOSED
MODEL_VERSION_APPROVED
```

Events werden als bereits eingetretene Tatsachen benannt.

## Vertrauliche Informationen

Nicht protokolliert werden dürfen:

- Passwörter,
- Tokens,
- API-Schlüssel,
- vollständige Sessiondaten,
- unnötige personenbezogene Daten,
- vertrauliche Broker-Zugangsdaten.

---

# Kommentare und Dokumentation im Code

Kommentare erklären primär **warum** eine Lösung erforderlich ist.

Sie dürfen nicht lediglich den Code in natürlicher Sprache wiederholen.

Öffentliche oder komplexe Schnittstellen benötigen eine angemessene Dokumentation.

Besonders zu dokumentieren sind:

- fachliche Formeln,
- Rundungsregeln,
- Einheiten,
- Annahmen,
- Grenzfälle,
- externe Provider-Einschränkungen,
- nicht offensichtliche Sicherheitsentscheidungen.

Veraltete Kommentare sind Fehler und müssen mit der Implementierung aktualisiert oder entfernt werden.

---

# Tests

## Grundsatz

Neue oder geänderte Fachlogik benötigt automatisierte Tests.

Ein Bugfix muss nach Möglichkeit einen Test enthalten, der den Fehler vor der Korrektur reproduziert.

## Testarten

Die zentrale Teststruktur umfasst:

```text
tests/unit/
tests/integration/
tests/contract/
tests/workflow/
tests/performance/
tests/e2e/
tests/fixtures/
```

## Unit-Tests

Unit-Tests prüfen isolierte fachliche oder technische Einheiten.

Sie müssen schnell, deterministisch und unabhängig von externen Diensten sein.

## Integrationstests

Integrationstests prüfen das Zusammenspiel mehrerer technischer Komponenten, insbesondere Datenbankzugriffe und API-Integration.

## Contract-Tests

Contract-Tests sichern Verträge zu externen Datenprovidern sowie interne API-Verträge.

## Workflow-Tests

Workflow-Tests prüfen fachliche Abläufe über mehrere Komponenten oder Features.

## E2E-Tests

E2E-Tests prüfen ausgewählte kritische Benutzerabläufe.

## Testdaten

Testdaten gehören in Tests oder Fixtures und nicht in den Produktivcode.

Produktionsdaten oder echte Zugangsdaten dürfen nicht für automatisierte Tests verwendet werden.

## Qualitätsbefehle

Backend:

```bash
bash scripts/check-backend.sh
```

Frontend:

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

Die Repository-Skripte und CI-Workflows sind maßgeblich, falls sie die Einzelbefehle kapseln.

---

# Sicherheitsregeln

## Geheimnisse

Geheimnisse werden ausschließlich über dafür vorgesehene Umgebungsvariablen oder Secret-Stores eingebunden.

Sie dürfen nicht in

- Quellcode,
- Tests,
- Beispieldaten,
- Logs,
- Screenshots oder
- Dokumentation

eingecheckt werden.

## Eingaben

Alle externen Eingaben gelten als nicht vertrauenswürdig und müssen an der zuständigen Systemgrenze validiert werden.

## Abhängigkeiten

Neue Abhängigkeiten müssen

- erforderlich,
- aktiv gepflegt,
- lizenzrechtlich vertretbar und
- sicherheitlich geprüft

sein.

Eine neue Bibliothek darf nicht allein zur Vermeidung weniger Zeilen eigenen, verständlichen Codes aufgenommen werden.

---

# Konfiguration und Defaultwerte

Konfiguration wird zentral und typisiert verwaltet.

Fachlich wirksame Defaultwerte müssen

- dokumentiert,
- versioniert,
- getestet und
- in der Benutzeroberfläche nachvollziehbar

sein.

Geheime Werte gehören nicht in `.env.example`.

`.env.example` enthält ausschließlich sichere Platzhalter und eine vollständige Beschreibung der erforderlichen Variablen.

---

# Datenbankänderungen

Schemaänderungen erfolgen ausschließlich über versionierte Migrationen.

Migrationen müssen

- reproduzierbar,
- überprüfbar,
- vorwärts ausführbar und
- hinsichtlich Datenverlust bewertet

sein.

Manuelle Schemaänderungen ohne Migration sind nicht zulässig.

---

# Pull Requests und Reviews

Jede Änderung muss je nach Umfang enthalten:

- Implementierung,
- automatisierte Tests,
- Dokumentationsanpassung,
- Migrationsanpassung,
- nachvollziehbare Begründung.

Vor Freigabe müssen mindestens geprüft werden:

- Architektur eingehalten,
- Coding Standards eingehalten,
- Typprüfung erfolgreich,
- Linting erfolgreich,
- Formatprüfung erfolgreich,
- Tests erfolgreich,
- Dokumentation aktuell,
- keine unnötige Duplikation,
- keine toten Schnittstellen,
- keine Geheimnisse enthalten,
- Auswirkungen auf Nachvollziehbarkeit und Modellversionierung bewertet.

Ein Review darf nicht allein auf erfolgreichen CI-Prüfungen beruhen.

---

# Nicht zulässig

Insbesondere nicht zulässig sind:

- autonome Handelsentscheidungen,
- Geschäftslogik im Frontend,
- Geschäftslogik im Repository,
- SQL in API-Endpunkten,
- direkte interne Zugriffe zwischen Features,
- duplizierte fachliche Modelle,
- versteckte fachliche Defaultwerte,
- unversionierte Modelländerungen,
- nicht dokumentierte APIs,
- unbegründetes `Any`,
- Geldberechnung mit binären Gleitkommazahlen,
- Zugangsdaten im Repository,
- produktive Änderungen ohne nachvollziehbaren Test oder Review.

---

# Abnahme

Dieses Dokument kann auf `🟢 Approved` gesetzt werden, wenn

- die Regeln mit den tatsächlichen Werkzeugkonfigurationen übereinstimmen,
- widersprüchliche Architekturdokumente angepasst wurden,
- die verbindlichen Prüfbefehle ausführbar sind,
- Freigabeverantwortung und Freigabedatum eingetragen wurden.

---

# Siehe auch

- `docs/architecture/Source_Architecture.md`
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/architecture/FRONTEND_ARCHITECTURE.md`
- `docs/technical/DEVELOPMENT_GUIDE.md`
- `docs/technical/FEATURE_LIFECYCLE.md`
- `docs/foundation/REQUIREMENTS.md`
- `docs/foundation/MODEL_BOOK.md`
- `docs/foundation/TRACEABILITY.md`

---

# Änderungshistorie

| Version | Datum | Änderungen |
|---|---|---|
| 1.0 | 2026-07-22 | Erstversion |
| 1.1 | 2026-08-01 | Abgleich mit Tool-Konfigurationen; Präzisierung von Architektur-, Qualitäts-, Sicherheits-, Nachvollziehbarkeits- und Trading-Regeln |
