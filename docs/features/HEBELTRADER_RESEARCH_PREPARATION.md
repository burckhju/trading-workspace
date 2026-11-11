# Hebeltrader research preparation

## Auftrag, Umfang und Herkunft

Der Nutzer beauftragt am 11.11.2026, die historische Analyse auf alle 222
Empfehlungen auszudehnen, die EUR-Notierung der Optionsscheine unabhängig von der
Basiswertwährung zu berücksichtigen und die Analyse möglichst eigenständig mit
den vorhandenen Bausteinen von Trading Workspace fortzusetzen.

Dieser eng begrenzte Schnitt bereitet einen lokalen, versionierten
Forschungsdatensatz vor. Er bewertet Quellenvollständigkeit, Preisachsen,
Datumsbezug und Datenbedarf. Er berechnet keine historischen Renditen und
persistiert keine Observation, Evidence, Ausführung, Position oder Modellfreigabe.
Die Umsetzung der Analysevorbereitung ist vom Nutzerauftrag gedeckt; eine
fachliche Endabnahme, ein Merge, eine Veröffentlichung oder Installation sowie
eine produktive Regel- oder Provideraktivierung werden daraus nicht abgeleitet.

Geprüfte Basis: `d01c259f4b79fdfbdcec8743ececda035b69f9d1`, Software 1.5.46.
Der Arbeitsstatus bleibt im [Product Backlog](../planning/PRODUCT_BACKLOG.md).
Dieser Vertrag dokumentiert Eingaben und Akzeptanzkriterien, keine zweite
Feature-Statusliste.

## Wiederverwendung und Verantwortlichkeit

- Fachlicher Owner ist FT-012 / Learning: externe Quellen und ihre Herkunft.
- Der bestehende PDF-Import bleibt unverändert. Er verarbeitet PDFs mit
  Textschicht und verlangt vor Confirm bestehende Basiswert-/Produktidentitäten.
  Ein dateiinhaltlicher Hash ist kein fachlicher Korrektur-/Dublettenvertrag.
- Der neue lokale CLI-Einstieg konsumiert einen expliziten JSON-Quellensnapshot.
  Ein vorgelagerter XLSX-Export bleibt außerhalb dieses Schnitts und muss die
  Originalwerte, Blatt-/Zeilenreferenzen und den Workbook-Hash erhalten.
- Der CLI ist ein Dateiadapter, ohne DB, Netzwerk, Provider, Settings-/Secret-
  Discovery oder operative Seiteneffekte. Prüfregeln gehören zum Learning-Owner.
- Markt-/Produkt-UUIDs werden nicht erzeugt. Fehlende Identitäten bleiben offen.
- Marktzeitreihen, Listing-/Mapping-Evidence und Produktbedingungen können später
  über die bestehenden Owner/Contracts ergänzt werden; interne Repositories
  anderer Features werden hierfür nicht aus dem Learning-Feature angesprochen.

Maßgebliche Grenzen bleiben
[External Observation](EXTERNAL_HISTORICAL_OBSERVATIONS.md),
[ADR-POST-FT012-001](../decisions/ADR-POST-FT012-001-EXTERNAL-OBSERVATION-IMPORT-BOUNDARY.md),
[ADR-POST-FT012-002](../decisions/ADR-POST-FT012-002-EXTERNAL-OBSERVATION-IDENTITY-RESOLUTION.md),
[ADR-POST-FT012-003](../decisions/ADR-POST-FT012-003-HISTORICAL-OUTCOME-SEMANTICS.md)
und der
[Hebeltrader-Integrationsvertrag](HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md).

## Fachlicher Quellenvertrag v1

Der Aufrufer liefert eine vollständige, endliche Liste von Empfehlungen mit
stabiler Ausgabe-ID. Die CLI erwartet eine explizite Sollanzahl, damit kein
stillschweigender Teilbestand als vollständige Studie ausgegeben wird.

Je Empfehlung werden mindestens erhalten:

- Ausgabe-ID und Veröffentlichungsdatum; die Zeitpräzision bleibt `DATE_ONLY`.
  Aus einem Datum entsteht kein belegter Mitternachtszeitpunkt.
- Herkunft: SHA-256 der Quelle und eindeutige Blatt-/Zeilen- oder Dokumentreferenz.
- Basiswert-WKN, Notierungswährung und veröffentlichter Referenzkurs, beide
  Zielmarken sowie beide Stoppmarken.
- Produkt-WKN und Typ, eigene Notierungswährung, Referenzkurs, Ziele und Stopps.
- Basispreis und separat belegte Basispreiswährung; fehlende Angaben bleiben null.
- Fälligkeit oder ausdrücklich belegter Open-End-Status.

Geld-/Preiswerte werden aus Dezimalzeichenfolgen mit `Decimal` verarbeitet;
nicht endliche oder nicht positive Quellkurse werden abgelehnt. Die Quellwerte
werden weder gerundet noch durch plausible Schätzungen ersetzt. Eine fehlende
Basispreiswährung wird nicht aus der Produkt- oder Basiswertwährung hergeleitet.

Der wirtschaftliche Schlüssel enthält Ausgabe-ID, Basiswert-WKN und Produkt-WKN.
Zusätzlich kennzeichnet ein kanonischer Fingerprint die genaue Quellenversion.
Doppelte Ausgabe-IDs oder Wirtschaftsschlüssel innerhalb einer Eingabe verhindern
eine vollständige Ausgabe. Der Fingerprint ist keine automatische Freigabe einer
Quellenkorrektur im produktiven Import.

## Währung und Produktarten

Die Optionsschein-Notierung wird gemäß Nutzerangabe als EUR geprüft. Abweichende
Rohangaben erzeugen einen Konflikt, keine stille Überschreibung.

`underlying_currency`, `derivative_currency` und `strike_currency` sind drei
unabhängige Felder. Ein EUR-Optionsschein auf einen USD-Basiswert ist zulässig.
Eine abweichende Basispreis- und Basiswertwährung verlangt Vertragsklärung, nicht
automatisch eine Kurskorrektur. EUR-Produktpreise werden nicht erneut mit EUR/USD
umgerechnet. Die Aussage über die Notierungswährung bedeutet keine wirtschaftliche
Unabhängigkeit vom Basiswert oder von Wechselkursen.

Call-Optionsscheine und Turbo-Long-Produkte bleiben getrennte Arten. Turbos
benötigen zusätzliche KO-/Finanzierungs-/Restwert-Evidence. Eine Fälligkeit vor
der Veröffentlichung ist ein Quellenkonflikt. Ein erreichtes Fälligkeitsdatum
belegt weder wertlosen Verfall noch einen konkreten Abrechnungsbetrag.

## Stichtage und Ergebnisse

Der bestehende Pilot bleibt an seinen ursprünglichen Stichtag und seine genaue
Modellversion gebunden. Der neue Datenschnitt hat einen expliziten, separat
übergebenen Stichtag. Für den aktuellen Auftrag ist 10.11.2026 vorgesehen.

Bei Veröffentlichung am oder nach dem neuen Stichtag kann keine abgeschlossene
Folgesitzung aus dem Datum allein angenommen werden. Kalender, letzte Handels-
und Abrechnungstage und exakte Veröffentlichungszeit bleiben eigene Datenbedarfe.

Alle Empfehlungen bleiben in der Vorbereitung erhalten. Der Quellenstatus
unterscheidet verwendbare Quellangaben und Reviewbedarf. Der historische
Ergebnisstatus bleibt `NOT_COMPUTED`; fehlende Kurse sind weder Nullrenditen noch
Verluste. Vorhandene alte Resultate dürfen später nur separat mit Modellversion,
Stichtag und Datenfingerprint verknüpft werden, nicht als neu berechnet erscheinen.

Die Vorbereitung weist getrennte Bedarfe aus:

1. Basiswert: verifizierte Identität, konkretes Listing/Währung/Preiseinheit,
   Kalender, rohe OHLC und Kapitalmaßnahmen im erforderlichen Fenster.
2. Produkt: eigene EUR-Geld-/Briefhistorie mit Originalzeit, Handelsplatz,
   Qualität und Identität sowie historisch gültige Vertrags-/Settlementdaten.

Das Repository-EODHD-Angebot für Aktien ist kein Nachweis deutscher
Optionsschein-Historien. Gespeicherte Live-Quotes sind kein rückwirkender Backfill.
Die Datenbedarfsgruppen nach WKN und Währung sind noch keine verifizierten Listings.

## Abgrenzung bestehender Forschungs- und Regelstände

Der ursprüngliche Sechs-/14-Fälle-Pilot, die Forschung in PR #197 und
`HEBELTRADER_CONFIRMED_BASELINE/1.0.0` sind getrennte Modell-/Regelstände.
Diese Vorbereitung erklärt keinen davon zum Ersatz eines anderen. Insbesondere
werden weder die 25%-Z1-/Peak-Protection-Annahmen von #197 noch Pilotvarianten zu
operativ bestätigten Regeln. #187, #197 und #207 bleiben eigenständig.

## Akzeptanzkriterien und technische Prüfung

1. Identische Eingaben und Stichtage ergeben identische Ergebnisbytes.
2. Jede übergebene eindeutige Empfehlung erscheint genau einmal; eine falsche
   Sollanzahl oder ein Duplikat wird vor einer Ausgabe abgelehnt.
3. USD-Basiswert plus EUR-Produkt ist zulässig; eine Produktwährungsabweichung
   bleibt sichtbar. Fehlende Strike-Währung wird nicht ergänzt.
4. Quellenwerte, Versionfingerprint und Herkunft bleiben nachvollziehbar.
5. Historische Ergebnisse werden nicht erfunden. Datums-/Fälligkeitskonflikte
   und Turbo-Anforderungen bleiben fallbezogen sichtbar.
6. Die Bedarfsgruppen deduplizieren ausschließlich identische WKN-/Währungsachsen
   und erhalten alle zugehörigen Empfehlungs-IDs.
7. Netzwerk-, Datenbank-, Provider-, Secret- und Ausführungsabhängigkeiten fehlen.
   Die CLI überschreibt keinen existierenden Ausgabeordner.
8. Tests verwenden ausschließlich synthetische Empfehlungen. Private PDFs,
   Tabellen, Einstiegs-/Ziel-/Stopplisten oder Ergebnisarchive werden nicht in das
   öffentliche Repository oder in CI hochgeladen.

Es gelten unverändert Ruff, Black, strict mypy und die Backend-/Coverage-Gates
aus `scripts/check-backend.sh`. Tests laufen in einer neuen, eindeutig lokalen
Wegwerfumgebung ohne produktive Zugangsdaten. Keine Migration, Frontendänderung,
Schedule, Providerzustimmung oder Installation gehört zu diesem Schnitt.

### Nachtrag zur tatsächlichen CI-Umgebung vom 11.11.2026

Der erste PR-Lauf scheitert in allen vier E2E-Jobs vor den Tests: `ubuntu-latest`
liefert Ubuntu 26.04, während das vorhandene Frontend Playwright 1.55.0 pinnt.
Für die notwendige Qualifikation wird ausschließlich der Runner dieser vier
Jobs auf das von genau dieser Playwright-Version unterstützte `ubuntu-24.04`
festgelegt. Browser-/Anwendungsversionen, Testbefehle, Gategrenzen, Retry- und
Uploadregeln bleiben erhalten. Der versionsgenaue Beleg und der fehlgeschlagene
Ausgangslauf stehen im Qualifikationsnachweis; ein neuer Lauf muss den Fix
tatsächlich bestätigen.

## JSON-Eingabeschema und lokaler CLI

Der Eingabevertrag heißt `hebeltrader-research-input-v1`. Das oberste Objekt
enthält genau `schema_version`, `source` und `cases`. `source` enthält den
Originaldateinamen und den SHA-256-Hash der ursprünglichen Quelle. Der Adapter
liest nur die JSON-Datei: er dokumentiert diesen deklarierten Quellenhash und
berechnet zusätzlich selbst den Hash der tatsächlich eingelesenen JSON-Bytes.
Er behauptet nicht, die ursprüngliche Arbeitsmappe erneut gehasht zu haben.

Jeder Fall enthält alle im Beispiel gezeigten Schlüssel. Fehlende Angaben werden
als JSON-`null` übergeben. Preise und Basispreis sind Dezimalzeichenfolgen mit
Punkt als Dezimaltrennzeichen, niemals JSON-Gleitkommazahlen. Die gelieferte
Schreibweise bleibt erhalten; die Prüfung verwendet `Decimal`. Preise müssen
positiv und endlich sein. Ein Basispreis von `0` ist zulässig. Ein negatives,
nicht endliches oder syntaktisch ungültiges Geldfeld verhindert die Ausgabe.
Strukturelle Fehler, unbekannte Schlüssel und ungültige Datumswerte werden
ebenfalls vor dem Anlegen des Ausgabeordners abgelehnt.

`derivative_type` ist `WARRANT_CALL`, `WARRANT_PUT`, `TURBO_LONG` oder `UNKNOWN`.
`derivative_type_raw` erhält die ursprüngliche Typbezeichnung. Unbekannte Typen,
fehlende Angaben und fallbezogene fachliche Konflikte bleiben mit stabilen
Issue-Codes sichtbar. WKNs und Währungen werden nicht still normalisiert.
Mindestens eine eindeutige Herkunft muss vorliegen: `source_sheet` zusammen mit
positiver `source_row`, oder eine nicht leere `source_document`-Referenz.
Fehlt sie, wird der Fall mit `SOURCE_LOCATOR_MISSING` zur Quellenprüfung erhalten.
Eine PDF-Referenz aus einer Tabelle ist keine Behauptung, das PDF selbst gelesen
oder seine Inhalte geprüft zu haben. `open_end` ist `true`, `false` oder `null`.

Das folgende vollständige Beispiel ist ausschließlich synthetisch; der
Null-Hash ist ein Platzhalter und keine echte Quellenprüfung:

```json
{
  "schema_version": "hebeltrader-research-input-v1",
  "source": {
    "filename": "synthetic_recommendations.xlsx",
    "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
  },
  "cases": [
    {
      "issue_id": "2026-SYNTHETIC-001",
      "publication_date": "2026-01-05",
      "source_sheet": "Recommendations",
      "source_row": 2,
      "source_document": null,
      "underlying_name": "Synthetic Company",
      "underlying_wkn": "A00001",
      "underlying_currency": "USD",
      "underlying_reference_price": "100.00",
      "underlying_target_1": "120.00",
      "underlying_target_2": "130.00",
      "underlying_stop_1": "90.00",
      "underlying_stop_2": "85.00",
      "derivative_wkn": "B00001",
      "derivative_type": "WARRANT_CALL",
      "derivative_type_raw": "Synthetic call warrant",
      "derivative_currency": "EUR",
      "derivative_reference_price": "1.20",
      "derivative_target_1": "1.80",
      "derivative_target_2": "2.40",
      "derivative_stop_1": "0.85",
      "derivative_stop_2": "0.70",
      "strike": "95.00",
      "strike_currency": "USD",
      "maturity_date": "2027-12-31",
      "open_end": false
    }
  ]
}
```

Im vorhandenen Backend-Python-Umfeld, vom Repository-Stamm aus:

```bash
PYTHONPATH=backend python -m app.tools.prepare_hebeltrader_research \
  --input /absoluter/pfad/recommendations.json \
  --out /absoluter/pfad/neuer_ausgabeordner \
  --cutoff 2026-11-10 \
  --expected-count 222
```

Für das synthetische Ein-Fall-Beispiel lautet die Sollanzahl `1`. Alle vier
Argumente sind erforderlich. Ein vorhandener Ausgabeordner, auch ein leerer,
wird verweigert. Die drei Dateien sind `manifest.json`, `cases.csv` und
`data_requests.json`. Validierung und vollständige Aufbereitung erfolgen vor
dem Anlegen des Ausgabeordners. Das Manifest wird zuletzt geschrieben.

Das Manifest bindet Eingabeschema, Vorbereitungsversion, expliziten Stichtag,
Soll-/Istanzahl, Quellenhash, tatsächlichen Inputhash und sämtliche erhaltenen
Quellensnapshots an die Befunde. Die CSV enthält eine Zeile je Empfehlung mit
Originalwerten, `DATE_ONLY`, Quellenstatus, Fingerprint, Issues und
`historical_result_status=NOT_COMPUTED`. `USABLE_SOURCE` bedeutet lediglich,
dass die gelieferten Quellfelder die Vorbereitungsprüfung bestanden haben,
nicht dass Markt- oder Produktdaten bereits qualifiziert sind.
Die Formatprüfung erwartet sechs Großbuchstaben/Ziffern für die WKN und drei
Großbuchstaben für Währungen; sie verifiziert kein Wertpapier- oder ISO-Verzeichnis.
Im CSV stehen fehlende Angaben als leere Zellen; im maßgeblichen JSON-Snapshot
bleiben sie ausdrücklich `null` und von gelieferten leeren Zeichenfolgen unterscheidbar.

Die Datenbedarfsdatei führt getrennte Gruppen für Basiswert und Produkt mit
WKN, gelieferter Währung und allen betreffenden Ausgabe-IDs. Unbekannte WKNs
werden nicht als gemeinsame Identität dedupliziert. Jede Gruppe ist ausdrücklich
`UNVERIFIED_LISTING`. Das angegebene historische Fenster beginnt frühestens bei
der ersten Veröffentlichung vor dem Stichtag. Existiert keine solche
Veröffentlichung, bleibt `from_date=null` mit `NO_POST_PUBLICATION_WINDOW`.
Regelabhängige Vorlaufdaten benötigen eine spätere explizite Regel-/Kalenderdefinition.
Produktgruppen erhalten zusätzlich die separat deklarierte erforderliche
Notierungswährung EUR, ohne abweichende Quellwerte zu überschreiben.

Identische Eingabebytes und Argumente erzeugen identische Ergebnisbytes. Die
Ausgabedateien enthalten keinen Laufzeitstempel, keine zufällige ID, keinen
absoluten Eingabepfad und keine behauptete Ausführung oder Rendite.
