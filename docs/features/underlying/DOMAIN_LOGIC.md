# FT-001 Domänenlogik

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Sprint-Schritt | 5 – Domänenlogik |
| Status | Approved for Service Layer |
| Letzte Änderung | 2026-08-03 |

## Architekturprüfung

Die Domänenlogik ist unter `backend/app/features/market/domain/` vollständig von SQLAlchemy, FastAPI und Transaktionssteuerung getrennt. Persistenzmodelle bleiben reine Mappings. Repository- und Service-Layer treffen weiterhin keine impliziten fachlichen Entscheidungen.

## Umgesetzte Regeln

- ausschließlich `STOCK` als Underlying-Typ,
- Trimmen und Pflichtprüfung des Namens,
- kanonische ISIN-, WKN-, Ticker-, MIC- und Währungscode-Normalisierung,
- ISO-6166-Prüfziffer für ISIN,
- sechsstellige alphanumerische WKN-Prüfung,
- genau eine aktive primäre Notierung für operative Nutzung,
- Qualitätsableitung `DRAFT` beziehungsweise `COMPLETE`,
- Verifikation nur für vollständige Datensätze,
- Rückstufung `VERIFIED` auf `COMPLETE` bei relevanter Stammdatenänderung,
- getrennte Lifecycle-Übergänge `ACTIVE`/`INACTIVE`,
- monotone Versionserhöhung nur bei tatsächlicher Änderung,
- explizite erwartete Version zur Erkennung konkurrierender Änderungen,
- stabile fachliche Fehlercodes gemäß API-Fachvertrag.

## Abgrenzung

Nicht Bestandteil dieses Schritts sind Dublettenabfragen, Referenzdatenexistenz, Löschreferenzen, Transaktionssteuerung, Audit-Persistenz, Mapping zwischen Domain und SQLAlchemy, DTOs oder REST-Endpunkte. Diese Aufgaben verbleiben im Service Layer und den nachfolgenden Schritten.

## Abschlussreview

- Feature-Book-Regeln sind ohne Frameworkabhängigkeit abgebildet.
- Keine parallele Datenhaltung wurde eingeführt.
- Enum-Definitionen liegen nun in der Domain; der bisherige Persistence-Import bleibt als reiner Kompatibilitäts-Reexport erhalten.
- Zustandsübergänge sind unveränderlich modelliert und testbar.
- Schritt 5 ist für die Implementierung des Service Layers freigegeben.
