# FT-001 React API Client – Sprint 2 Schritt 11

## Status

Approved for Frontend Views.

## Architekturprüfung

Der Client bildet ausschließlich die in Schritt 7 bis 9 freigegebenen REST- und DTO-Verträge ab. Er liegt featureorientiert unter `frontend/src/features/market/` und besitzt keine UI-, Formular- oder fachliche Zustandslogik. Der Workspace wird weiterhin ausschließlich serverseitig bestimmt.

## Struktur

```text
frontend/src/features/market/
├── index.ts
├── services/
│   ├── client.ts
│   ├── http.ts
│   └── client.test.ts
└── types/
    └── api.ts
```

`services/http.ts` ist der eine technische Transportpfad des Features. `services/client.ts` stellt die fachlich benannten API-Operationen bereit. `types/api.ts` enthält die TypeScript-Abbildung der stabilisierten Request-, Response- und Fehlerverträge.

## Unterstützte Operationen

- Basiswerte suchen und als Detail laden,
- Basiswert mit primärer Notierung anlegen,
- Basiswert ändern, verifizieren, deaktivieren, reaktivieren und löschen,
- Listings ergänzen und ändern,
- Primärnotierung setzen,
- kontrollierte Handelsplätze und Währungen lesen.

Alle Pfade verwenden ausschließlich `/api/v1`. Suchparameter werden auf die serverseitigen Namen `q`, `lifecycle_status`, `offset` und `limit` abgebildet. Die erwartete Version wird gemäß REST-Vertrag im Body beziehungsweise bei DELETE als Queryparameter übertragen.

## Fehlervertrag

Fachliche HTTP-Fehler werden als `MarketApiError` mit HTTP-Status und unverändertem zentralen Fehlerpayload bereitgestellt. Netzwerkfehler, ungültiges JSON und nicht vertragskonforme Fehlerantworten werden separat als `MarketTransportError` behandelt. Abgebrochene Requests behalten den nativen `AbortError`, damit Views veraltete Ladevorgänge gezielt verwerfen können.

## Actor-Header

Ändernde Operationen akzeptieren optional `actorId` und `actorName` und übertragen sie als `X-Actor-ID` und `X-Actor-Name`. Der Client interpretiert diese Header ausdrücklich nicht als Authentifizierung oder Berechtigung.

## Vertragsregeln

- keine hardcodierten Handelsplatz- oder Währungslisten,
- keine Workspace-ID im Clientvertrag,
- keine automatische Wiederholung konkurrierender Schreiboperationen,
- keine Normalisierung oder fachliche Validierung im Client,
- `undefined` bleibt „nicht übertragen“, während `null` bei optionalen Identifikatoren „entfernen“ bedeutet,
- keine direkte Nutzung von `fetch` außerhalb des Feature-Transports für FT-001.

## Tests

Die Clienttests prüfen URL- und Querybildung, HTTP-Methoden, JSON-Bodies, Actor-Header, PATCH-Nullsemantik, Listingpfade, DELETE 204, Referenzdatenendpunkte sowie die Trennung von API- und Transportfehlern.

Die Testausführung war in der bereitgestellten Laufzeit blockiert, weil `npm ci` ein im konfigurierten Paket-Proxy nicht verfügbares Lockfile-Artefakt (`yocto-queue@0.1.0`) mit HTTP 404 erhielt. Der Quellstand und die Tests wurden dennoch vollständig erstellt; eine erfolgreiche Ausführung erfordert eine funktionierende npm-Registry beziehungsweise einen vollständigen Dependency-Cache.

## Abschlussreview

- ausschließlich FT-001 umgesetzt,
- REST-, DTO- und Validierungsverträge unverändert übernommen,
- genau ein Feature-Client und ein HTTP-Transport,
- keine UI oder React Views vorgezogen,
- Referenzdaten nicht dupliziert,
- Fehler- und Nebenläufigkeitsverträge typisiert,
- freigegeben für Schritt 12 „Frontend Views“ unter Vorbehalt der ausstehenden CI-Ausführung im verfügbaren npm-Umfeld.

## Vertragserweiterung vor Frontend Views

Der Client unterstützt nun serverseitige Filter über `tradingVenueId` und `currencyCode` sowie `getUnderlyingAuditEvents` und `getUnderlyingUsages`. Die zugehörigen TypeScript-Typen bilden Primärnotierung, Audit-Historie und Verwendungen vollständig ab.
