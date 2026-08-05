# ADR-S1-010 – Formale Validierung von ISIN und WKN

## Status

Accepted – 2026-08-03

## Entscheidung

Eine angegebene ISIN muss nach Normalisierung:

- exakt zwölf alphanumerische Zeichen besitzen,
- das ISO-6166-Grundformat erfüllen,
- eine gültige Prüfziffer besitzen.

Eine angegebene WKN muss nach Normalisierung das für Version 1 freigegebene sechsstellige alphanumerische Format erfüllen. Für die WKN wird keine Prüfziffer geprüft.

Leere Eingaben werden als nicht angegeben behandelt. Formal ungültige Werte dürfen nicht gespeichert werden.

## Konsequenzen

- Validierung erfolgt im Frontend zur unmittelbaren Rückmeldung und verbindlich erneut im Backend.
- ISIN und WKN bleiben optionale Felder.
- Formatvalidierung bestätigt nicht die wirtschaftliche Richtigkeit oder Existenz des Instruments.
