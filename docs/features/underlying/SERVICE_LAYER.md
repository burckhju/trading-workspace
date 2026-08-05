# FT-001 Service Layer

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Sprint-Schritt | 6 – Service Layer |
| Status | Approved for REST API |
| Letzte Änderung | 2026-08-04 |

## Architekturprüfung

Der Service Layer orchestriert die bereits akzeptierten Domainregeln und Repository-Verträge. Er besitzt keine FastAPI- oder DTO-Abhängigkeit. Fachliche Invarianten verbleiben in `domain`; Persistenzentscheidungen verbleiben in `persistence`.

## Umgesetzte Verantwortungen

- atomare Anlage von Underlying und primärer Notierung,
- Workspace- und Referenzdatenprüfung,
- normalisierte Dublettenprüfung für ISIN, WKN sowie Markt/Ticker,
- Mapping zwischen SQLAlchemy-Modellen und Domain Entities,
- Versionsprüfung vor schreibenden Operationen,
- Aktualisierung, Verifikation, Deaktivierung und Reaktivierung von Underlyings,
- Suche und Detailzugriff,
- Ergänzen und Bearbeiten von Listings,
- atomarer Wechsel der Primärnotierung,
- Löschschutz über einen erweiterbaren Usage-Repository-Vertrag,
- physische Löschung ausschließlich ohne fachliche Referenzen,
- unveränderliche Audit-Events in derselben Transaktion wie die Fachänderung,
- explizite Unit-of-Work-Transaktionsgrenzen.

## Transaktionsmodell

`SqlAlchemyMarketUnitOfWork` bündelt alle FT-001-Repositorys auf einer gemeinsamen `AsyncSession`. Services führen genau einen Commit nach erfolgreicher Fachänderung aus. Exceptions verlassen den Kontext ohne Commit und lösen einen Rollback aus. Repositorys selbst führen weiterhin weder Commit noch Rollback aus.

## Usage-Integration

Da noch kein referenzierendes Folgefeature implementiert ist, liefert `NoUsageRepository` derzeit keine Verwendungen. Der Vertrag `UsageRepository` ist die einzige Erweiterungsstelle. Sobald andere Features Underlyings referenzieren, müssen deren Usage-Adapter dort eingebunden werden; eine zweite Löschprüfung ist unzulässig.

## Audit-Regeln

Jede tatsächliche Änderung erzeugt mindestens einen Audit-Event. Underlying und Listing erhalten getrennte Events. No-op-Operationen erzeugen weder Versionsfortschreibung noch Audit-Event noch Commit. Löschereignisse enthalten den vorherigen Zustand, damit die Historie nach physischer Löschung verständlich bleibt.

## Abgrenzung

Nicht Bestandteil dieses Schritts sind REST-Pfade, HTTP-Statuscodes, Pydantic-DTOs, Dependency Injection in FastAPI und UI-Verhalten. Diese Entscheidungen folgen in den nächsten Schritten auf Basis dieses Service-Vertrags.

## Abschlussreview

- keine fachliche Regel wurde aus der Domain dupliziert,
- keine Repositoryoperation führt Transaktionssteuerung aus,
- Fachänderung und Audit sind atomar gekoppelt,
- alle workspacegebundenen Zugriffe bleiben isoliert,
- Listing-Use-Cases sind vollständig im Service Layer berücksichtigt,
- Schritt 6 ist für die REST-API-Implementierung freigegeben.
