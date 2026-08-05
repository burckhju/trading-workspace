# ADR-S2-002 – Persistierte Handelsplatz- und Währungsreferenzen

## Status

Accepted – 2026-08-03

## Kontext

ADR-S1-007 definiert `TradingVenue` und `Currency` als eigenständige, von FT-001 nur referenzierte Objekte. Für Sprint 2 war festzulegen, ob die kontrollierten Referenzlisten in Dateien, im Anwendungscode oder in Datenbanktabellen geführt werden.

## Entscheidung

Handelsplätze und Währungen werden in persistierten Referenztabellen geführt.

- `trading_venues` enthält mindestens UUID, MIC, Name, ISO-Ländercode, IANA-Zeitzone, Aktivstatus und Referenzdatenversion.
- `currencies` verwendet den ISO-4217-Code als stabilen Schlüssel und enthält mindestens Name, Minor Unit, Aktivstatus und Referenzdatenversion.
- Die initialen kontrollierten Referenzdaten werden durch versionierte Alembic-Migrationen eingespielt.
- FT-001 besitzt ausschließlich lesenden Zugriff auf diese Referenzobjekte.
- Listings referenzieren Handelsplatz und Währung über nicht-nullbare Foreign Keys.
- Nur aktive Referenzwerte sind für neue Listings auswählbar.
- Bereits referenzierte, später deaktivierte Werte bleiben historisch sichtbar und werden nicht automatisch ersetzt.
- Freitext-Fallbacks sind unzulässig.

## Konsequenzen

- Datenbankseitige referenzielle Integrität verhindert unbekannte Handelsplätze und Währungen.
- Listing-Daten duplizieren keine Namen, Länder oder Zeitzonen.
- API, UI und Validierung verwenden dieselbe Datenquelle.
- Änderungen an den Referenzdaten erfolgen außerhalb des Schreibmodells von FT-001.
- Neue Referenzwerte erfordern bis zur Umsetzung verantwortlicher Features eine kontrollierte Referenzdatenmigration.

## Nutzerwirkung

Der Nutzer erhält durchsuchbare, kontrollierte Auswahllisten und kann keine fehlerhaften Freitextwerte speichern. Fehlt ein benötigter Referenzwert, kann das Listing nicht mit einem Ersatzfreitext angelegt werden; die Oberfläche muss den fehlenden Referenzwert verständlich ausweisen.

## Verbindliche initiale Referenzliste Sprint 2

Die erste kontrollierte Referenzdatenversion lautet `FT-001-V1` und enthält ausschließlich:

### Handelsplatz

| ID | MIC | Name | Land | Zeitzone | Aktiv |
|---|---|---|---|---|---|
| `00000000-0000-4000-8001-000000000001` | `XETR` | Xetra | `DE` | `Europe/Berlin` | ja |

### Währung

| Code | Name | Minor Unit | Aktiv |
|---|---|---:|---|
| `EUR` | Euro | 2 | ja |

Weitere Handelsplätze oder Währungen werden ausschließlich durch spätere kontrollierte Referenzdatenmigrationen ergänzt. FT-001 bietet keinen Freitext- oder Administrationspfad dafür an.
