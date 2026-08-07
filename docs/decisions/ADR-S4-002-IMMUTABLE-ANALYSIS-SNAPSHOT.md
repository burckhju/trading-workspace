# ADR-S4-002 – Unveränderliche Analyse-Snapshots

## Status

Accepted – 2026-08-05

## Entscheidung

Jede Analyseausführung erhält eine fortlaufende Version und speichert sämtliche verwendeten Marktdatenzeilen, Parameter, Modellreferenz, Ergebnisse und einen deterministischen Eingabe-Hash. Abgeschlossene Versionen werden nicht überschrieben.

## Konsequenzen

Historische Ergebnisse bleiben auch nach späteren Marktdatenkorrekturen reproduzierbar. Erneute Berechnungen erzeugen neue Versionen und zusätzlichen Speicherbedarf.
