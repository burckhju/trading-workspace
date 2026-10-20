# IV-Datenbasis: Produktbelege und Kurs-Erfassungsprotokoll

Stand: 12.10.2026. Entwicklungsbasis: `ac4e9b4624a6f5a087e7c57be699ef188618a3d7`
(PR #252, v1.5.3). Diese Stufe erweitert die
[IV-Grundlage](IMPLIED_VOLATILITY.md), ohne deren hypothetisches Bewertungsmodell
zu verändern. Entwicklung ausschließlich in separater Arbeitskopie; kein Zugriff
auf JMBbot, kein Deployment, keine aktuelle Messung der dortigen Anbieter.

## Bestandsaufnahme und Abgrenzung

| Bereich | Bisher | Diese Stufe | Weiterhin offen |
|---|---|---|---|
| Produktmerkmale | Versionierte Call/Put-Bedingungen, Strike, Verhältnis, Datum; Ausübung/Quanto/Konvention unbekannt | Versionierte, ausdrücklich manuell geprüfte Dokumentbelege | Prüfung realer Bestandsprodukte anhand ihrer Emittentenunterlagen; kein automatischer Dokumentparser |
| Kursaufbewahrung | Letzte erfolgreiche Quote wird überschrieben | Zusätzlich dauerhaftes Protokoll bereits erlaubter Abrufe einschließlich Fehlern | Kein autonomer Collector, keine rückwirkende Historie |
| Verfügbarkeit | Momentaufnahme und Quellenstatus | Erfasste Intervalle, beobachtete UTC-Tage, unterschiedliche Kursbelege, konkrete Fehler je Route | Keine vollständige Handelszeitabdeckung oder aktuelle PC-Diagnose |
| IV und Greeks | Nicht ingestiert; IV-Modelllabor getrennt | Unverändert unbekannt; Produktblocker können anhand eines Belegs entfallen | Zeitlich passender Basiswertkurs, Anbieter-IV samt Provenienz oder qualifizierte eigene Inversion |
| Historische IV-Kennzahlen | Keine qualifizierte IV-Historie | Weiterhin nicht verfügbar | Einheitliche Kursbasis, Modell, Laufzeit-/Moneyness-Kontext, ausreichend regelmäßige Stichprobe |

**Nutzen:** Nach einer später freigegebenen Installation gehen die tatsächlich
anfallenden Datenbelege nicht mehr verloren. Quellenprobleme werden messbar, und
fehlende Produktmerkmale können nachvollziehbar ergänzt werden. Das erhöht die
Verfügbarkeit belegter Eingaben; es verspricht weder zusätzliche Anbieterabdeckung
noch bereits vorhandene historische IV-Werte.

## Produktbelege

In der Optionsscheinverwaltung: „Produktmerkmale für IV mit Beleg erfassen“.
Zunächst gespeicherte Belege laden, dann konkrete Fundstelle, Prüfzeitpunkt mit
Zeitzone und Prüfnotiz angeben. Die Bestätigung bezieht sich auf die ausgewählte
ISIN und die angezeigte Bedingungsversion. Es gibt keine vorbelegten Annahmen zu
Vanilla, europäischer Ausübung, fehlender Quanto-Eigenschaft oder Verhältnis.

- Explizit erfassbar: Vanilla/anderes strukturiertes Produkt, europäische/
  amerikanische/andere Ausübung, Quanto ja/nein/unbekannt, Verhältnis-Konvention
  **Basiswerteinheiten je Schein**, optional genaue Bewertungszeit am Laufzeitende.
- Die genaue Zeit wird nur akzeptiert, wenn ihr Datum in der angegebenen Zeitzone
  dem gespeicherten Fälligkeitsdatum entspricht. Abweichende Bewertungs- und
  Zahlungstage sind damit **noch nicht unterstützt**; keinen Zahlungszeitpunkt als
  Optionsablauf eintragen. Unbekannt bleibt unbekannt.
- Quelle: Dokumentreferenz, optionale HTTP(S)-URL ohne eingebettete Zugangsdaten,
  Prüfnotiz, Prüfzeitpunkt; separat serverseitige Erfassungszeit, Akteur-ID und
  Revision. Die URL wird niemals automatisch abgerufen. Dokumente selbst werden
  nicht archiviert; unveränderter Dokumentinhalt ist ohne Datei/Hash nicht bewiesen.
- Herkunft `MANUAL_DOCUMENT_REVIEW` bedeutet eine dokumentierte Nutzerangabe,
  keine unabhängige Anbieterprüfung und keine kryptographische Identitätsprüfung
  des Akteurs. Das bestehende lokale API-Akteursmodell bleibt unverändert.
- Jede Speicherung ist eine vollständige neue Revision. `null` widerruft eine
  frühere Feststellung; ältere Werte werden nicht stillschweigend weiterverwendet.
- Bindung an Produkt-ID, ISIN, WKN, Emittent-ID, Basiswert-ID und Bedingungen-ID.
  Diese Angaben werden auch als lesbarer Identitätsstand je Revision gespeichert.
  Änderungen an diesen Angaben machen den letzten Beleg unpassend. Kein Rückgriff
  auf einen älteren passenden Beleg. Umbenennung allein ändert keine Produktfakten.
- Erwartete Produktversion und Belegrevision verhindern veraltete Schreibzugriffe;
  der Produktdatensatz wird während des Schreibens gesperrt. Neue Dokumentbelege
  ändern die Produktversion selbst nicht und verändern damit keine Kursroute.
- Risikoauswertungen verwenden nur zum Auswertungszeitpunkt vorhandene Belege.
  Alte Snapshots bleiben unverändert. Neue Belegrevisionen können neue Snapshots
  erzeugen, aber keinen zusätzlichen Bestätigungstag für Trend-/Volatilitätsalarme.

`IV_READINESS_V2` entfernt ausschließlich belegte Produktlücken. Amerikanische
Ausübung, andere strukturierte Produkte und Quanto bleiben für das europäische
Modell ausdrücklich ausgeschlossen. Gleiche Währung allein belegt keine passende
Basiswertwährung. Zinsen, Dividenden und sonstige FX-Eigenschaften sind weiterhin
eigene fehlende Eingaben. Alle realen IV-/Vega-/Szenariowerte und das IV-Risikoniveau
bleiben `null`, der Status bleibt `NOT_EVALUABLE`.

## Kurs-Erfassungsprotokoll

Der vorhandene `RetainedWarrantQuoteProvider` erfasst nach Abschluss eines ohnehin
zulässigen Abrufs zusätzlich eine Stichprobe. Netzwerkanfragen halten keine
Datenbanksperre. Beim Speichern werden Route und Produktidentität erneut geprüft;
Notierungssperre und Unique Constraint serialisieren konkurrierende Erfassungen.

**Stichprobenregel:** `FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1`. Je Workspace,
Notierung, Provider, Routenidentität und festem UTC-Fünfminutenintervall bleibt die
erste gespeicherte abgeschlossene Erfassung erhalten. Auch der erste Fehler zählt;
ein späterer Erfolg darf ihn nicht ersetzen. Die bestehende Last-success-Ablage
wird weiterhin mit späteren gültigen Erfolgen aktualisiert. Ein Routenwechsel
beginnt ein eigenes Segment, auch innerhalb desselben Intervalls.

Die Stichprobe enthält:

- Produkt/ISIN, Provider und vollständige Routenkennung;
- serverseitige Erfassungszeit, UTC-Intervall und UTC-Tag;
- ursprünglichen `retrieved_at` getrennt von `quote.observed_at`;
- validierte vollständige Quote mit Kursseiten, Währung, Quellenmodus,
  Referenztyp, Feed-Verzögerung und bestehender Altersgrenze, soweit vorhanden;
- Qualitätsklasse, begrenzten Diagnosecode und Cache-Status.

Fehlgeschlagene oder verworfene Antworten liefern keine gültige Quote im Journal.
Bei einer vorhandenen Antwort bleibt deren Abrufzeit erhalten; bei einer Exception
kann sie unbekannt sein. Die Erfassungszeit ersetzt niemals einen unbekannten
Original- oder Abrufzeitpunkt. Ein zurückgegebener alter Last-success-Fallback wird
nicht nochmals als erfolgreicher neuer Kurs gespeichert. Ungeprüfte Fehlertexte
oder Antwortkörper werden nicht gespeichert.

Qualitätsklassen: Geld/Brief innerhalb der **unveränderten** Altersgrenze,
einseitig, nur Referenzkurs, unbekannte Originalzeit, widersprüchliche Zeiten,
zu alt, unbekannte Altersgrenze, Abruf/Validierung fehlgeschlagen, kein Kurs.
Diese Klassen sind keine Risikostufen und kein Ausführbarkeitsnachweis.
Referenzkurse bleiben auch bei bekanntem Datum Referenzkurse. Gültige Geld-/Briefpaare
werden nicht automatisch zu Mid-, IV- oder Verkaufspreisen umgedeutet.

Identische Kursdaten zählen trotz erneuter Cache-/Bewertungszeit nicht als neue
Kursbelege. Ein Fingerprint ignoriert Bewertungszeit und Retention-Marker, enthält
aber Originalzeit, Preise, Kursbasis und Route. Auch dieses Maß ist kein Nachweis
separater Marktticks: Bei unbekannter Originalzeit kann deren Identität unklar bleiben.

Der GET liest nur gespeicherte Daten. Er schaltet keine Quellen frei, ändert keine
Zustimmung und ruft keinen Anbieter auf. UI-Fenster: 7/14/31 Kalendertage;
API: 1–31. Zähler umfassen alle gespeicherten Stichproben des Fensters, Details die
letzten 50. Nicht erfasste Intervalle sind unbekannt. Deaktivierte/nicht zugeordnete
Routen ohne aufgerufenen Wrapper sind keine fehlgeschlagenen Stichproben; dafür
bleibt die vorhandene Quellenübersicht zuständig.

Es gibt bewusst **keinen Verfügbarkeitsprozentsatz**: Ein verifizierter Session- und
Feiertagskalender sowie ein vollständiger, dokumentierter Erfassungsplan fehlen.
Die erste Erfassung eines Intervalls kann von der Nutzung abhängen. Die Stichprobe
beseitigt Mehrfachgewichtung innerhalb des Intervalls, aber keine Auswahlverzerrung
durch Zeiten ohne Abruf. Sie wird nicht für IV-Perzentil/Rank oder als qualifizierte
synchrone Produkthistorie verwendet. Keine Rückrechnung mit erfundenen Daten.

## API, Speicherung und Betriebsfolgen

- `GET /api/v1/warrants/{id}/valuation-evidence`
- `POST /api/v1/warrants/{id}/valuation-evidence`: Produkt-/Belegrevision,
  Bedingungen-ID, vollständige nullable Fakten und `CONFIRM_DOCUMENT_REVIEW`.
- `GET /api/v1/market-data/warrants/{id}/quote-history?days=7`

Migration **0045** ergänzt `warrant_valuation_evidence` und `warrant_quote_samples`.
PostgreSQL-Trigger verhindern UPDATE/DELETE und prüfen Workspace-/Produktzuordnung.
Unique Constraints sichern Belegrevision und Stichprobenintervall ab. RESTRICT-
Fremdschlüssel verhindern, dass eine endgültige Produkt-/Bedingungs-/Notierungslöschung
Belege verliert; der bestehende Löschpfad meldet einen Konflikt. Das betrifft auch
automatisch erfasste Kursbelege. Eine Rückmigration verweigert die Löschung, sobald
Belege vorhanden sind. Kein automatisches Bereinigen, Backfill oder Umschreiben.

Pro unveränderter Route entstehen höchstens 288 Stichproben pro UTC-Tag; tatsächliche
Anzahl und Speicherbedarf hängen von Abrufen, Produkten und Routenwechseln ab.
Die Datenmenge wächst dauerhaft. Vor breitem Betrieb sind Volumen/Backup-Laufzeit
zu beobachten; Archivierung wäre eine eigene, ausdrücklich freizugebende Stufe.
Die neue Ablage ist Teil derselben Transaktion wie Last-success: Ein Datenbankfehler
wird nicht als erfolgreiche Erfassung verschwiegen.

Keine Änderung von Stop-/Zielregeln, Alarmtypen, Telegram-Zustellung, Providerbudgets,
Zustimmungen oder Altersgrenzen. Migration und PC-Installation sind nicht ausgeführt.

## Nächste datenabhängige Schritte

1. Nach gesonderter Installationsfreigabe vorhandene autorisierte Abrufe über mehrere
   Handelstage beobachten und Belege der tatsächlich gehaltenen ISINs prüfen.
2. Pro Provider anhand des Journals unterscheiden: Zugriffs-/Drosselungsproblem,
   fehlender Zeitstempel, Referenz-/einseitige Kurse oder fehlende Instrumentabdeckung.
   Ein erneuter Abruf repariert keine semantisch fehlende Originalzeit.
3. Synchronen Basiswert-Feed und genaue Währungs-/Dividenden-/Zinsgrundlage qualifizieren.
   Erst dann aktuelle eigene IV samt Spannen/kleinem Vega und Modellausschlüssen
   freischalten; Anbieter-IV/Greeks nur mit dokumentierter Einheit, Kursseite und Modell.
4. Neue kostenlose oder kostenpflichtige Datenquellen erst mit einer Stichprobe der
   benötigten ISINs, Feld-/Zeitnachweis und erlaubter Speicherung bewerten. Ein Angebot
   für US-Börsenoptionen beweist keine deutsche Optionsscheinabdeckung.
5. Historische Kennzahlen erst mit qualifizierter einheitlicher Stichprobe, definierter
   Abdeckung und getrennten Quellen-/Modellsegmenten; die Vorgaben aus der IV-Grundlage
   zu Laufzeit/Moneyness, Gleichständen, konstanten Reihen und Ausreißern gelten weiter.
