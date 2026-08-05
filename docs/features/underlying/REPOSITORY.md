# FT-001 – Repository

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Implementierungsschritt | 4 – Repository |
| Version | 1.0 |
| Status | Approved for Domain Logic |
| Datum | 2026-08-03 |

## Architekturprüfung

Die Repository-Schicht setzt ausschließlich Datenzugriffsoperationen auf dem freigegebenen SQLAlchemy-Modell um. Sie enthält keine fachlichen Entscheidungen, keine Transaktions-Commits und keine HTTP-Abhängigkeiten. Die spätere Service-Schicht besitzt die Transaktionsgrenze.

## Verträge und Adapter

Unter `app/features/market/persistence/repositories.py` bestehen Protocol-Verträge und asynchrone SQLAlchemy-Adapter für Workspace, Referenzdaten, Underlyings, Listings und Audit-Events.

Alle fachobjektbezogenen Abfragen sind explizit durch `workspace_id` isoliert. Suchabfragen unterstützen Name, ISIN, WKN und Listing-Ticker sowie Lifecycle-Filter und stabile Pagination. Detailabfragen können Listings samt Handelsplatz und Währung eager laden.

## Schreibverhalten

`add`, `delete` und `flush` sind reine Persistenzprimitive. Kein Repository führt `commit` oder `rollback` aus. Dadurch können Underlying-, Listing- und Auditänderungen später in einer gemeinsamen Service-Transaktion atomar ausgeführt werden.

Das Audit-Repository ist append-only: Es bietet ausschließlich `append`, chronologische Lesezugriffe und `flush`; Update- und Delete-Operationen existieren absichtlich nicht.

## Abgrenzung

Nicht enthalten sind Normalisierung, Dublettenentscheidung, Primärnotierungsinvarianten, Versionsfortschreibung, Löschfreigabe, Domain Entities, Services, DTOs oder API-Endpunkte.

## Architekturreview Schritt 4

- Workspace-Isolation in allen relevanten Abfragen: erfüllt.
- Keine Geschäftslogik im Repository: erfüllt.
- Keine Repository-eigenen Transaktionsgrenzen: erfüllt.
- Referenzdaten nur lesbar: erfüllt.
- Audit-Zugriff append-only: erfüllt.
- SQLAlchemy bleibt innerhalb der Persistenzschicht: erfüllt.
- Ausschließlich FT-001 umgesetzt: erfüllt.

**Ergebnis:** Schritt 4 ist abgeschlossen und für Schritt 5 „Domänenlogik“ freigegeben.
