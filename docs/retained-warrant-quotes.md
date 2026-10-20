# Erfolgreiche Optionsscheinkurse aufbewahren

Stand: 14.09.2026. Entscheidung: Die letzte geprüfte Kursbeobachtung bleibt bis zu
einem nachfolgenden erfolgreichen Abruf in PostgreSQL erhalten. Ein fehlender neuer
Kurs ist kein Grund, vorhandene Informationen aus der indikativen Auswertung zu entfernen.

## Verhalten

- Der bestehende `WarrantListingQuoteProvider` erhält einen gemeinsamen Speicheradapter.
  Frankfurt, Vontobel und Stuttgart behalten ihre eigenen Parser, Berechtigungen,
  Abruflimits und gemeinsam genutzten HTTP-Caches. Keine zusätzliche Provider-Architektur.
- `warrant_quote_observations` enthält je Workspace, Listing und Provider die letzte
  geprüfte Beobachtung. Migration `20260914_0038` enthält keine Benutzerdaten.
- Kurszeitpunkt (`quote_observed_at`) und erfolgreicher Abruf (`quote_retrieved_at`)
  werden unverändert gespeichert. `quote_assessed_at` bezeichnet die aktuelle Auswertung.
  Ein unbekannter Kurszeitpunkt bleibt unbekannt, auch bei einem Schlusskurs.
- Leere Antworten, HTTP-Fehler, Zeitüberschreitungen und ungültige neue Daten löschen
  keinen vorhandenen Erfolg. Auch ein zeitlich zurückliegender neuer Datensatz darf
  den gespeicherten jüngeren Kurs nicht verdrängen. Schreibvorgänge werden je Listing
  über dessen Datenbankzeile serialisiert; kein HTTP-Aufruf hält eine DB-Sperre.
- Bei Rückgriff auf PostgreSQL meldet die Bewertung `quote_retained=true` und den
  begrenzten Fehlercode in `quote_refresh_error`. Original-ISIN, WKN soweit geliefert,
  Provider-Identifier, Platzcode/MIC, Kursart, Währung und Zeitstempel bleiben erhalten.
  `analysis_usable`/`monitoring_usable` können true bleiben; `execution_usable` bleibt false.
- Es gibt keine altersabhängige Löschung. Die Oberfläche zeigt Kursalter in Sekunden,
  Minuten, Stunden oder Tagen, Originalzeitpunkt, erfolgreichen Abruf und Auswertung.
  Die Entscheidung über die Aussagekraft der indikativen Auswertung liegt beim Nutzer.
- Ein deaktiviertes Produkt/Listing, deaktivierter Anbieter oder eine geänderte bzw.
  ungültige Zuordnung erlaubt keine Nutzung einer alten Identität. Der alte Datensatz
  bleibt gespeichert, wird jedoch nicht dem geänderten Instrument zugerechnet.
- Basiswert-Tageskurse werden bereits als `DailyPriceModel` gespeichert. Diese Änderung
  betrifft die bisher nur im Prozess gehaltenen Optionsscheinkurse.

Die Aufbewahrung ersetzt weder eine fehlende erste Beobachtung noch einen Datenvertrag.
Ein Provider-Fallback darf keinen Basiswertkurs als Produktkurs verwenden. Es werden
keine neuen Abonnements, Stream-Anmeldungen oder kostenpflichtigen Abrufe aktiviert.

## Installation und Prüfung

```bash
git switch main
git pull --ff-only
bash scripts/start-linux.sh --frankfurt
```

Der bestehende Startpfad baut die Images und führt Alembic aus. Falls manuell nötig:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  alembic upgrade head
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '{quote_storage, last_error, lanes}'
curl -fsS \
  http://localhost:8000/api/v1/position-monitoring/trades/dd8338bd-a092-42c0-94c0-c068a9094f77/product-valuation \
  | jq '{status, selected_source, provider_identity, reference_price,
         quote_observed_at, quote_retrieved_at, quote_assessed_at,
         quote_age_seconds, quote_retained, quote_refresh_error,
         analysis_usable, monitoring_usable, execution_usable}'
```

`quote_storage` soll `DATABASE_LAST_SUCCESS_WITH_ORIGINAL_TIMESTAMPS` melden.
Nach mindestens einem erfolgreichen Abruf unter der neuen Version kann ein regulärer
Backend-Neustart erfolgen. Die Datenbank muss ihr bestehendes Volume behalten.
Die Beobachtung überlebt den Neustart; bei erneutem Provider-Erfolg darf der erfolgreiche
Abrufzeitpunkt voranschreiten, der Kurszeitpunkt nur entsprechend der Quelle.
Bei einem Fehler bleiben die gespeicherten Zeiten erhalten und der Fehler wird angezeigt.
Keine Provider-Störung absichtlich im produktiven Depot erzeugen: Restart-/404-/Leerantwort-
und Wiederherstellungsszenarien sind durch Regressionstests abgedeckt.

Die alte Version hatte keine dauerhafte Kurstabelle. Bereits vor diesem Deployment aus
allen Prozess-Caches verlorene Beobachtungen lassen sich dadurch nicht rekonstruieren.

## Unvollständige ISIN korrigieren

Im übermittelten Depotbericht gehört `DE000PK72H6` (11 Zeichen) zu **BNP PAR.EHG CALL26
DCO**, einem BNP-Optionsschein auf **Deere & Company**, 1.400 Stück. Produkt-ID:
`2407218c-126c-4e15-b788-bb2895db5510`; Trade-ID:
`ca3f2dc2-fbe4-4f16-8518-42d6c85af3ce`. Die WKN ist nicht hinterlegt.
Die fehlerhafte Kennung gehört zum Optionsschein, nicht zur Deere-Aktie.

1. Die vollständige ISIN und gegebenenfalls WKN aus der Brokerabrechnung oder einem
   offiziellen Produktdokument entnehmen. Aus den elf Zeichen lässt sich die richtige
   Produktidentität nicht eindeutig rekonstruieren; keine Prüfziffer automatisch anhängen.
2. **Produkte · Optionsscheine** öffnen, **BNP PAR.EHG CALL26 DCO** auswählen und
   **Kennungen korrigieren** öffnen.
3. Verifizierte ISIN, optional WKN und den Beleg der Korrektur eintragen, speichern.
   Dies korrigiert ausschließlich Erfassungsfehler desselben Produkts. Ein Produktwechsel
   gehört nicht in diese Funktion.
4. Der nächste automatische Katalog-/Discovery-Lauf kann die neue Identität prüfen.
   Für diesen BNP-Optionsschein war keine Anbieterzuordnung vorhanden. Bereits bestehende
   aktive Zuordnungen werden bei einer Korrektur dagegen bewusst auf INVALID gesetzt
   und benötigen eine explizite erneute Anbieterprüfung; widersprüchliche Mappings werden
   nicht automatisch überschrieben.

API: `PATCH /api/v1/warrants/{warrant_id}/identifiers`, Body:
`expected_version`, `isin`, `wkn` (oder null), `evidence`.
Format/Prüfziffer, Eindeutigkeit im Workspace und Versionskonflikte werden geprüft.
Eine Audit-Zeile dokumentiert Alt-/Neuwert, Beleg und Version. Produkt-ID, Bedingungen,
Trades, Positionen und Ausführungshistorie werden nicht neu angelegt oder verändert.
