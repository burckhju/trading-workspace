# ADR-S3-009 – Sprint-3-Datenumfang

## Status

Accepted – 2026-08-05

## Kontext

Der Begriff Marktdaten umfasst EOD, Intraday, Echtzeit, Fundamentaldaten, Corporate Actions und weitere Datenarten. Eine gleichzeitige Umsetzung würde Contracts und Persistenz vorzeitig überladen.

## Entscheidung

Sprint 3 beschränkt sich auf historische End-of-Day-Tageskurse und den letzten abgeschlossenen EOD-Datensatz für bestehende Basiswert-Listings. Intraday, Echtzeit, Fundamentaldaten, Nachrichten und Optionsscheinmarktdaten sind Nicht-Ziele.

`adjusted_close` wird optional und transparent gespeichert, aber Sprint 3 führt keine eigene Corporate-Actions-Berechnung durch.

## Konsequenzen

- klar testbarer und abnehmbarer Umfang,
- keine Echtzeitversprechen,
- spätere Datenarten erhalten eigene Contracts und ADRs,
- Nutzer müssen erkennen können, dass der letzte Wert ein abgeschlossener Tageswert ist.
