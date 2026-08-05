# Sprint 3 – Architekturreview und Implementierungsfreigabe

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument | SPRINT_3_ARCHITECTURE_REVIEW.md |
| Dokumenttyp | Architecture Review |
| Version | 1.0 |
| Status | 🟢 Approved |
| Reviewdatum | 2026-08-05 |

## 1. Reviewgegenstand

Geprüft wurden:

- `docs/features/market_data/SPRINT_3_SPECIFICATION.md`,
- `ADR-S3-001` bis `ADR-S3-009`,
- die bestehenden Architekturregeln aus Sprint 0 bis Sprint 2,
- die Abhängigkeitsgrenzen von FT-001,
- Konfiguration, Dependency Injection, Fehlerformat, Persistenz und Teststruktur.

Das Review umfasst noch keine Implementierung des EODHD-Adapters.

## 2. Reviewkriterien

| Kriterium | Ergebnis |
|---|---|
| Keine direkte EODHD-Abhängigkeit der Domain | erfüllt |
| Keine Breaking Changes an FT-001 | erfüllt |
| Trennung von Fachlogik und Infrastruktur | erfüllt |
| Nachvollziehbare Datenherkunft | erfüllt |
| Explizite Fehler- und Qualitätsmodelle | erfüllt |
| Testbarkeit ohne Live-Provider | erfüllt |
| Austauschbarkeit des Providers | erfüllt |
| Trennung von Persistenz und Cache | erfüllt |
| Geheimnisschutz | erfüllt |
| Begrenzter Sprintumfang | erfüllt |

## 3. Reviewfeststellungen

### 3.1 Featuregrenze

Die eigenständige Fähigkeit `features/market_data` ist konsistent mit der bestehenden Architektur. FT-001 bleibt Owner von Underlyings und Listings. Marktdaten referenzieren Listings nur über stabile IDs.

### 3.2 Providergrenze

Capability-basierte Contracts verhindern einen universellen Provider-Monolithen. EODHD-DTOs, Transportdetails und Fehlermeldungen bleiben innerhalb von `providers/eodhd`.

### 3.3 Datenmodell

`Decimal`, explizite Währung, Handelstag, UTC-Abrufzeit, Qualitätsstatus und Provenance erfüllen die Anforderungen an Nachvollziehbarkeit. Provideridentitäten werden nicht als fachliche Listingidentität verwendet.

### 3.4 Persistenz und Cache

Die fachliche Persistenz validierter EOD-Tageskurse wird bestätigt. Der technische Cache bleibt austauschbar und darf keine fachliche Historie ersetzen.

### 3.5 Betrieb

Die lokale Implementierung von Cache, Token-Bucket und Tagesbudget ist nur für genau eine koordinierte Backendinstanz freigegeben. Mehrere Worker oder Instanzen erfordern vorab ein zentrales Backend und eine neue Betriebsfreigabe.

### 3.6 Administration

Provider-Mappings werden über eine administrative Backend-Funktion gepflegt. Sprint 3 führt kein neues Rollenmodell ein. Die konkrete Autorisierung verwendet die vorhandene oder betriebliche Zugriffskontrolle und muss vor einer öffentlichen Bereitstellung abgesichert sein.

### 3.7 EODHD-Tarif

Der Tarif ist keine Architekturkonstante. Das produktive Tagesbudget muss in der Deploymentkonfiguration explizit gesetzt werden. Ohne diese Einstellung darf der EODHD-Adapter in einer Produktionsumgebung nicht aktiviert werden.

## 4. Entscheidungen

Die ADRs `ADR-S3-001` bis `ADR-S3-009` werden mit Datum 2026-08-05 auf `Accepted` gesetzt.

Zusätzlich bestätigt:

1. Historische EOD-Kurse werden fachlich persistiert.
2. Die Single-Instance-Betriebsgrenze gilt verbindlich für Sprint 3.
3. Das Entwicklungstagesbudget bleibt defensiv auf 20 Calls begrenzt.
4. Das Produktionstagesbudget ist eine verpflichtende Deploymentvariable.
5. Provider-Mappings werden administrativ über das Backend gepflegt.

## 5. Implementierungsreihenfolge

### Arbeitseinheit 1 – Domain und Contracts

- Paketstruktur `features/market_data` erstellen,
- Enums, Value Objects und interne Modelle implementieren,
- capability-basierte Protocols definieren,
- providerunabhängige Fehlerhierarchie implementieren,
- Unit-Tests und öffentliche Docstrings ergänzen.

### Arbeitseinheit 2 – Persistenz

- SQLAlchemy-Modelle für Mapping und EOD-Tageskurse,
- Repositorycontracts und Adapter,
- Alembic-Migration,
- Idempotenz, Hashvergleich und Optimistic Locking,
- Integrations- und Migrationstests.

### Arbeitseinheit 3 – Resilience-Infrastruktur

- Cachecontract und In-Memory-Backend,
- Clock, Sleeper und Zufallsquelle,
- Retrypolicy,
- Token-Bucket und Tagesbudget,
- deterministische Unit-Tests.

### Arbeitseinheit 4 – EODHD-Adapter

- Settings und Secret-Redaction,
- asynchroner HTTP-Client,
- interne EODHD-DTOs,
- Mapping auf interne Modelle,
- Fehlerübersetzung,
- Contract- und Mock-Server-Tests.

### Arbeitseinheit 5 – Application Service und API

- Anwendungsfälle für Mappingvalidierung, Import und Abfrage,
- administrative Mapping-API,
- API-DTOs ohne Providerdetails,
- Integration in DI und FastAPI-Router,
- API- und Workflowtests.

### Arbeitseinheit 6 – Dokumentation und Abschlussreview

- Betriebs-, Fehler-, Mapping- und Sicherheitsdokumentation,
- Traceability-Matrix,
- vollständige Backend-Qualitätsprüfung,
- Architekturreview gegen alle angenommenen ADRs.

## 6. Quality Gates

Jede Arbeitseinheit muss erfüllen:

- Ruff und Black ohne Befund,
- MyPy im bestehenden Strict-Modus,
- alle betroffenen Unit- und Integrationstests erfolgreich,
- keine Reduktion der vereinbarten Backend-Coverage,
- öffentliche Klassen und Contracts dokumentiert,
- Dokumentation und ADR-Verweise aktualisiert,
- keine echte EODHD-Verbindung im regulären Testlauf.

## 7. Freigabeergebnis

Sprint 3 ist für die Implementierung freigegeben. Die Implementierung beginnt mit Arbeitseinheit 1 – Domain und Contracts. HTTP-, EODHD-, Cache- oder Persistenzcode darf die internen Modelle und Contracts nicht vorwegnehmen.
