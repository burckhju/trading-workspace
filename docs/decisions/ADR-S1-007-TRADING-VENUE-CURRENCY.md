# ADR-S1-007 – Referenzmodell für Markt und Währung

## Status

Accepted – 2026-08-03

## Kontext

Listings benötigen kontrollierte Referenzen auf Markt/Handelsplatz und Handelswährung. Freitext würde Dubletten, inkonsistente Codes und redundante Stammdaten erzeugen.

## Entscheidung

`TradingVenue` und `Currency` sind eigenständige Referenzobjekte. FT-001 besitzt diese Objekte nicht, sondern referenziert sie.

Ein Listing speichert fachlich:

- `trading_venue_id`,
- `currency_code`,
- `ticker`.

`TradingVenue` umfasst mindestens einen stabilen internen Identifier, MIC-Code, Namen, Land und Zeitzone. `Currency` verwendet einen kontrollierten ISO-4217-Code. Bis die verantwortlichen Features umgesetzt sind, nutzt FT-001 eine versionierte, kontrollierte Referenzliste; Freitexteingaben sind unzulässig.

## Konsequenzen

- Markt- und Währungsdaten werden nicht im Listing dupliziert.
- UI-Felder sind Auswahllisten mit Suche.
- Änderungen an Referenzdaten erfolgen außerhalb FT-001.
- Handelskalender und Standardwährung eines Markts werden nicht automatisch als Listing-Daten übernommen, wenn der Benutzer eine abweichende Handelswährung festlegt.
