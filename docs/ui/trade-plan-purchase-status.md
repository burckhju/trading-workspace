# TradePlans: Planfreigabe und Kaufstatus

Die Übersicht `/trade-plans/overview` zeigt zwei getrennte Zustände. `APPROVED`
ist eine Planfreigabe, kein Nachweis eines erfassten Kaufs.

Der neue Bereich **Kaufstatus · alle Planversionen** liest die tatsächlich mit dem
Plan verknüpften Trades. Grau bedeutet **Noch kein Kauf erfasst**, Grün **Kauf erfasst ·
Position offen**, Blau **Kauf erfasst · abgeschlossen**, Gelb **Nur stornierte Käufe**
oder **Kaufstatus ungeklärt**. Farbe wird immer durch Text ergänzt. Grün bestätigt hier
nur die Kaufbuchung und den offenen Bestand, nicht die Qualität oder Attraktivität
von Kursdaten und nicht eine Handelsempfehlung.

Käufe früherer Versionen bleiben sichtbar. Der Status der aktuellen Version wird
separat gezeigt, sobald ein Trade zu einer anderen Version gehört. Ein neuer
Planentwurf setzt die Kaufhistorie also nicht zurück. Jeder Trade zeigt den tatsächlich
gekauften Optionsschein (aktuelle Stammdaten), seine Planversion, Kaufdatum und Link.
Ein Teilverkauf bleibt offen; ein vollständiger Verkauf zeigt zusätzlich das
Schließungsdatum. Stornierte Buchungen bleiben Historie und werden nicht als offener
Bestand gezählt. Mehrere Trades werden nicht auf einen beliebig ausgewählten reduziert.

Der Filter **Nach Kaufstatus filtern** wirkt auf den Gesamtstatus des Plans.
**Übersicht aktualisieren** lädt den Zustand neu; ein Ladefehler zeigt keine alten
Statuskarten als aktuell an. **Trade verwalten / Nachkauf** navigiert zum exakten
Trade und bucht nichts. Die Produktauswahl bleibt als eigene Navigation erreichbar;
bestehende Dublettensperren und Bestätigungen bleiben unverändert.

## Datenherkunft und Grenzen

Eine zusätzliche mengenbasierte Abfrage für alle angezeigten Plans nutzt ausschließlich
`trades.trade_plan_id`, `trade_plan_version_id` und `workspace_id`. Kein Matching über
Ticker, Optionsscheinname oder Basiswert. Ein externer Kauf ohne Planbezug startet
keinen Plan automatisch. Es wird keine neue persistierte Statusspalte eingeführt.

Nicht stornierte Trades benötigen einen wirksamen BUY-Eintrag und eine konsistente
Positionsprojektion; supersedierte Ausführungen zählen nicht als zusätzlicher Kauf.
Fehlende Kauf-/Positionsdaten sind **ungeklärt**, nicht **noch nicht gekauft**.
Ein offener Trade bleibt im Gesamtstatus sichtbar, auch wenn daneben geschlossene,
stornierte oder ungeklärte Trades existieren; die einzelnen Zustände werden genannt.

Die Kauf-/Schließungsdaten stammen aus der effektiven Positionsprojektion: bevorzugt
`opened_on` / `closed_on`, bei älteren zeitgenauen Buchungen aus `opened_at` / `closed_at`.
`created_at` oder der Erfassungszeitpunkt werden nicht als Kaufdatum verwendet.
Datumskorrekturen wirken über die bestehende Neuberechnung der Position. Fehlende
Metadaten werden nicht aus einer anderen Produktauswahl ergänzt.

Die Antwort von `GET /api/v1/trade-plans` enthält zusätzlich `execution` mit Gesamtstatus,
Status der aktuellen Version und einzelnen Trades. Ein älteres Backend ohne dieses
Feld erscheint als ungeklärt, nie automatisch ungekauft. API-Fehler werden angezeigt.

Keine Migration über `20260912_0036` hinaus. Installation mit Backend- und Frontend-
Neubau über `scripts/start-linux.sh`; die Anzeige verändert keine vorhandenen Trades.
Regressionen: Status-/Versionslogik, API-Serialisierung, echte PostgreSQL-Kauf-/Teilverkauf-/
Verkauf-/Storno-Abfolge und Isolation; Frontend-Statusfarben, Filter, Aktualisierung,
Fehlerfall, Datum/Identität; Browserdarstellung mit ausdrücklich synthetischen API-Fixtures.
