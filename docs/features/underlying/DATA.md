# FT-001 Fachliches Datenmodell

## Underlying

| Feld | Pflicht | Regel |
|---|---:|---|
| id | ja | UUID, global eindeutig und unveränderlich |
| workspace_id | ja | unsichtbarer Version-1-Workspace |
| type | ja | ausschließlich `STOCK` |
| name | ja | getrimmt, nicht leer |
| isin | nein | kanonisch normalisiert, formal gültig und workspaceweit eindeutig |
| wkn | nein | kanonisch normalisiert, formal gültig und workspaceweit eindeutig |
| lifecycle_status | ja | `ACTIVE` oder `INACTIVE` |
| quality_status | ja | `DRAFT`, `COMPLETE` oder `VERIFIED` |
| version | ja | monoton steigende Version für optimistisches Locking |
| created_at | ja | unveränderlicher Erstellungszeitpunkt |
| updated_at | ja | Zeitpunkt letzter Änderung |
| data_origin | ja | in FT-001 zunächst `MANUAL` |

## Listing

| Feld | Pflicht | Regel |
|---|---:|---|
| id | ja | UUID |
| underlying_id | ja | genau ein Underlying |
| trading_venue_id | ja | kontrollierte Referenz auf `TradingVenue` |
| ticker | ja | kanonisch normalisiert |
| currency_code | ja | kontrollierter ISO-4217-Code |
| lifecycle_status | ja | `ACTIVE` oder `INACTIVE` |
| is_primary | ja | genau eine aktive primäre Notierung je operativem Underlying |
| version | ja | Version für optimistisches Locking |
| created_at | ja | Erstellungszeitpunkt |
| updated_at | ja | letzte Änderung |
| data_origin | ja | zunächst `MANUAL` |

## TradingVenue-Referenz

FT-001 liest eine versionierte kontrollierte Referenzliste. Mindestens benötigt werden interner Identifier, MIC-Code, Name, Land und Zeitzone. FT-001 ändert diese Referenzdaten nicht.

## Currency-Referenz

FT-001 liest kontrollierte ISO-4217-Währungscodes. Freitextwährungen sind unzulässig.

## Normalisierung und Validierung

- ISIN: trimmen, Leerzeichen und Bindestriche entfernen, Großschreibung; zwölf alphanumerische Zeichen und gültige ISO-6166-Prüfziffer.
- WKN: trimmen, Leerzeichen entfernen, Großschreibung; sechs alphanumerische Zeichen.
- Ticker: trimmen und Großschreibung; fachlich relevante Sonderzeichen bleiben erhalten.
- MIC- und Währungscode: trimmen und Großschreibung.
- Leere Zeichenfolgen gelten als nicht angegeben.
- Keine weitergehende stillschweigende Korrektur fachlich ungültiger Kennungen.

## Eindeutigkeit

- `(workspace_id, isin)` eindeutig, sofern ISIN vorhanden.
- `(workspace_id, wkn)` eindeutig, sofern WKN vorhanden.
- `(workspace_id, trading_venue_id, ticker)` eindeutig.

## Statusregeln

- `ACTIVE/INACTIVE` beschreibt den Lebenszyklus.
- `DRAFT/COMPLETE/VERIFIED` beschreibt die Datenqualität.
- Operative Neuauswahl erfordert `ACTIVE` und mindestens `COMPLETE`.
- Relevante Änderung eines `VERIFIED`-Datensatzes setzt ihn auf `COMPLETE` zurück.

## Audit und Löschung

- Jede erfolgreiche fachliche Änderung erzeugt einen unveränderlichen feldbasierten Audit-Event.
- Physische Löschung ist nur ohne fachliche Referenzen zulässig und wird ebenfalls auditiert.
- Andernfalls erfolgt ein Statuswechsel auf `INACTIVE`.
- Provider-Symbole werden später in separaten Zuordnungen modelliert.


## Physische Spezifikation

Die verbindliche physische Ausprägung, Constraints, Indizes, Foreign Keys, Löschregeln und Transaktionsgrenzen sind in `PHYSICAL_DATA_MODEL.md` dokumentiert und durch ADR-S2-001 bis ADR-S2-003 begründet.
