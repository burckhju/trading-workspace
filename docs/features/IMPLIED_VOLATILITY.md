# Implizite Volatilität: erste Ausbaustufe

Stand der Analyse: 12.10.2026. Entwicklungsbasis: `main`,
`81fd99082d6a0be5cba2d884b28946db01680dc0`, Version **1.5.3**.
PR #248 (`d0fa679`) ist darin enthalten, ebenso #250/#251. Das beweist **kein**
Update der Anwendung auf JMBbot. Dessen zuletzt vom Nutzer bestätigter Stand
bleibt v1.5.2/`baee6f8`; PC, lokale Datenbank, Bind-Mount und aktueller Providerstatus
waren aus dieser Entwicklungsumgebung nicht zugänglich. Die Diagnosen vom
06./07.10. werden ausdrücklich nicht als aktuelle Messungen behandelt.

Weiterentwicklung: [Produktbelege und Kurs-Erfassungsprotokoll](IV_DATA_EVIDENCE.md).
Die folgende Bestandsaufnahme beschreibt ausdrücklich die Ausgangslage vor V1;
neue manuelle Produktbelege und die ergänzende Stichprobenablage sind dort dokumentiert.

## Bestandsaufnahme und Entscheidung

Die folgenden Feststellungen betreffen nachprüfbare Codeverträge und Tests,
nicht das gesamte kommerzielle Angebot eines Datenanbieters.

Ergänzende öffentliche Primärquellenprüfung: EODHD dokumentiert tatsächlich
[historische US-Aktienoptionen mit IV und Greeks](https://eodhd.com/marketplace/unicornbay/options),
einschließlich `volatility`, `volatility_change`, `volatility_pctchange`, `vega`,
Bid/Ask und Datumsfeldern. Das ist **kein Nachweis für die Abdeckung deutscher
Emittenten-Optionsscheine**, keine bestehende Anbindung im Projekt und keine
bestätigte Nutzungsfreigabe. Eine exemplarische
[Börse-Stuttgart-Produktseite](https://www.boerse-stuttgart.de/de-de/produkte/hebelprodukte/optionsscheine/stuttgart/vy6qpm/)
weist IV (Geldkurs), Vega und einen Kennzahlenzeitpunkt als Felder aus, lieferte
im gelesenen Webauszug bei IV/Vega jedoch keine Zahlen. Außerdem zeigt sie die
Notwendigkeit getrennter Angaben zu amerikanischer Ausübung, Strike-Währung,
Quanto und letztem Bewertungstag. Das betrifft ein anderes Produkt und wird
nicht als Messung für DE000JZ91459 oder als aktuelle ausführbare Quote verwendet.
Für die genannte JPMorgan-ISIN wurde keine ausreichend belegte aktuelle offizielle
IV-/Greek-/Historienversorgung nachgewiesen. Keine Web-Suchergebnisse werden als
Kursdaten in die Anwendung übernommen.

| Bereich | Vorhanden / bestätigt im Code | Fehlt oder begrenzt die IV-Auswertung |
|---|---|---|
| Produkt (`product/domain/models.py`, `service/risk_reference.py`) | ISIN/WKN, Emittent-/Basiswert-ID, versionierte Bedingungen: Call/Put, Strike, Strike-Währung, Fälligkeitsdatum, Verhältnis; Notierungswährung separat | `WARRANT` beweist keinen Vanilla-Payoff. Ausübungsart, genaue Bewertungszeit am Fälligkeitstag, FX/Quanto und explizite Verhältnis-Konvention werden nicht gespeichert. Vorhandene `exercise_style`/`quanto`-Readerfelder sind immer unbekannt. |
| Kursvertrag (`market_data/domain/models.py`) | Getrennte Geld-/Brief-/Referenzkurse, Originalzeit und Abrufzeit, Quelle, Route, Verzögerung, Altersgrenze, retained/error; positive endliche Preise und ungekreuzte Paare werden geprüft | Keine Anbieter-IV und keine Greeks samt Einheiten/Modellprovenienz. Ein Mid ist nur aus einem gültigen Paar möglich; kein ausführbarer Preis. |
| Frankfurt (`providers/frankfurt_quotes/schema.py`, `public.py`) | Eigene Bid-/Ask-Zeitfelder in der Normalisierung; Last Trade/Previous Close ausdrücklich getrennt; Drosselungs-/Zeit-/Qualitätsregeln | Keine IV/Greeks/Historie im integrierten Vertrag; Referenzkurse können aktuelle IV nicht belegen. |
| gettex (`providers/gettex_delayed/parser.py`, `adapter.py`) | Verzögerte dateibasierte Quotes, ISIN, Zeit, Währung, Geld/Brief, Volumina; ungültige Einzelzeilen isoliert | Keine IV/Greeks. Eine verzögerte Datei ist keine IV-Historie. |
| Stuttgart (`providers/stuttgart_delayed`) | Schema- und Altersprüfungen für verzögerte Quotes | Keine IV-/Greek-Felder im internen Quotevertrag. Lokaler Datenordner nicht verfügbar. |
| JPMorgan, Morgan Stanley, Vontobel (`providers/issuer_*`, jeweilige Adapter) | Produkt-/Routenbindung, Kursseiten und Herkunft; unbekannte Originalzeit bleibt unbekannt | Weder IV/Greeks noch eine qualifizierte IV-Historie werden ingestiert. Ob eine Produktseite weitere Daten zeigt, ist damit nicht belegt. Zustimmungen wurden nicht geändert. |
| EODHD (`providers/eodhd/warrant_quote.py`) | Basiswert-EOD mit Handelstag, OHLC/Adjusted Close und eigenem Abrufzeitpunkt | Optionsschein-Bid/Ask bewusst nicht aktiviert (dokumentierter US-Aktienumfang kein Optionsscheinnachweis). EOD-Tag/source_updated_at ist kein nachgewiesener synchroner Basiswert-Kurszeitpunkt. |
| Persistenz (`market_data/service/risk_read.py`, `retained_quotes.py`) | Letzte erfolgreiche Quote für die aktuell bestätigte Route; Identitäts-/Zeitprüfung | Last-success-Speicherung überschreibt ältere Quotes. `history_observations=1` bedeutet keine Zeitreihe. |
| Bewertung (`analysis/domain`, `position_monitoring/service`) | Realisierte 20-Tages-Volatilität, SMA, ATR; deskriptiver Produktvergleich mit strengen Synchronitätsregeln | Keine vorhandene BSM-/IV-/Vega-Funktion. Standardreader liefert keine synchronisierten Intraday-Paare. Kein Ereignisfeed im Risikolesepfad. |
| Warnungen (`risk_signals.py`, `risk_alerts.py`) | Bestätigungstage für Trendwechsel, Hysterese, persistente Zustände, identische Sitzung zählt nicht erneut, Alert-/Outbox-Deduplizierung | Diese Regeln sind nicht für IV kalibriert. Die 0,40/0,35-Schwellen betreffen realisierte Volatilität. |

**Folgerung:** Eine aktuelle Positions-IV wäre mit dieser Datenbasis nur durch
stillschweigende Annahmen möglich. V1 zeigt deshalb die konkrete Datenbereitschaft,
speichert ihre Evidenz und bietet einen **getrennten hypothetischen Modellrechner**.
Sie behauptet keine aktuelle Sensitivität einer realen Position. Kein Freischalten
von historischen Kennzahlen, IV-Crush-Alarmen oder Wahrscheinlichkeiten.

## Implementierter Umfang

1. `IvReadiness` ergänzt Risiko-Vorschau und gespeicherte Auswertungen. Status
   bleibt `NOT_EVALUABLE`; IV, Veränderung, Rank, Perzentil, Vega, Positionswirkung,
   Ereignis und Positionsverlustszenario bleiben `null`. Auch `risk_level` ist
   `null`, nicht „niedrig“. Zu jedem Hindernis gibt es einen Code mit UI-Erklärung.
2. Vorhandene Provenienz bleibt in `product`, `listing`, `quote_evidence` und
   `input_prices` erhalten. Originalkurszeit wird nie durch Empfangszeit ersetzt.
   Unbekannte Session-/Feiertagskalender werden als Grenze ausgewiesen; Marktschluss
   oder bekannte Feedverzögerung verlängern die bestehenden Altersgrenzen nicht.
   Eine spätere sessiongerechte Bewertung benötigt einen belegten Handelskalender.
3. Audit in bestehenden append-only `position_risk_snapshots`, keine Migration:
   neue Quote, Route, Kursseite oder Qualitätsklasse erzeugt eine neue Eingangskennung.
   Reine Abruf-/Bewertungszeitänderungen und laufende Alterssekunden zählen nicht;
   ein Überschreiten der Altersgrenze zählt. Originalkurse/Quelltexte bleiben erhalten.
   Dies kann mehr Snapshots als bisher erzeugen; es ist **kein regelmäßig abgetasteter
   IV-Historiencollector**. Es wird nichts gelöscht oder rückwirkend ergänzt.
4. Alte Payloads ohne `iv` bleiben lesbar (`iv=null`). Eine identische Auswertung
   kann den bereits gespeicherten Snapshot mit dessen ursprünglichem Zeitstempel
   zurückliefern; GET liefert eine neue ungespeicherte Vorschau. In der UI zeigt die
   Auswertungshistorie Quelle, Kursart und Originalzeit.
5. Der neue stateless POST
   `/api/v1/position-monitoring/risk/iv/model-preview` verarbeitet ausschließlich
   `basis=HYPOTHETICAL_ASSUMPTIONS`. Kein Providerabruf, kein Datenbankzugriff,
   kein Schreiben an Positionen/Stops/Ziele/Alerts. Der vorhandene Button zum
   Speichern einer Risikoauswertung speichert Datenbereitschaft, **nicht** Laborwerte.
6. Das UI-Modelllabor verlangt eigene Werte und eine ausdrückliche Modellauswahl.
   Beispielwerte sind als solche bezeichnet und werden nicht aus dem Portfolio
   abgeleitet. Eingaben werden pro Position/Schema-Version in der Browsersitzung
   erhalten; Ergebnisse verschwinden bei Eingabeänderung. Alte Netzwerkantworten
   werden verworfen. Kein Diagramm mit erfundenen Nullpunkten.

Zusätzliche IV-Evidenz-Snapshots zählen nicht als neue Trend-Bestätigungstage.
Die bestehende Alert-Engine erhält **keine IV-Signale**. Aktivierung,
Mindestbestätigung, Hysterese, Auflösung, Outbox und Stop-/Zielbedeutung bleiben
unverändert; Integrationstests prüfen denselben Zustandsverlauf und keine neuen
Alerts/Notifications durch reine Quellen-/Qualitätswechsel.

## Modell, Einheiten und Grenzen

Modellversion: **`BSM_CONTINUOUS_YIELD_ACT365_V1`**. Ausschließlich hypothetische
europäische Vanilla-Calls/Puts, gleiche Produkt-/Basiswert-/Strike-Währung,
kein Quanto, keine diskreten Dividenden. Amerikanische Ausübung, Turbos,
Knock-outs, Inline, Discount und unbekannte Klassifikation werden abgewiesen.
Insbesondere wird kein amerikanischer Schein pauschal europäisch angenähert.

Für Preis je Basiswerteinheit, mit stetigem Zins `r` und stetiger Dividendenrendite
`q`, Jahresbruch `T = Restkalendertage / 365`, Volatilität `sigma` als Dezimalbruch:

```text
d1 = [ln(S/K) + (r - q + sigma²/2) T] / (sigma sqrt(T))
d2 = d1 - sigma sqrt(T)
C = S exp(-qT) N(d1) - K exp(-rT) N(d2)
P = K exp(-rT) N(-d2) - S exp(-qT) N(-d1)
Vega_dezimal = S exp(-qT) phi(d1) sqrt(T)
Preis_je_Schein = Preis_je_Basiswerteinheit × Bezugsverhältnis
Vega_je_Schein_je_Prozentpunkt = Vega_dezimal × Bezugsverhältnis / 100
```

Die Verhältnis-Konvention muss `UNDERLYING_UNITS_PER_WARRANT` sein, etwa `0,1`
Basiswerteinheiten je Schein; die inverse Konvention wird nicht automatisch
umgedeutet. Eingabeprozente werden genau einmal durch 100 geteilt. Beispiel:
35 % = 0,35; 35 % → 30 % = −5 Prozentpunkte, relativ ca. −14,29 %.
Vega 0,02 EUR je Schein/Prozentpunkt ergibt lokal `0,02 × (−5) = −0,10 EUR`
je Schein. Erst die Positionswirkung wird mit der Stückzahl multipliziert.
Es findet keine FX-Umrechnung statt; USD-Werte werden als USD, nicht EUR, ausgegeben.

Der Rechner verwendet entweder eine IV-Annahme **oder** eine hypothetische
Preisannahme je Schein, nie beides. Bei Preisannahme löst er die IV durch begrenzte
Bisektion; diese Herkunft heißt `HYPOTHETICAL_PRICE_INVERSION`, ausdrücklich
kein Anbieterwert und keine aktuelle Markt-IV. Für reale Quotes wäre zusätzlich
die weiter unten beschriebene Qualifikation zwingend.

Numerischer Bereich (Implementierungsgrenzen, keine Risikoschwellen):

| Größe | Bereich / Behandlung |
|---|---|
| Spot, Strike | 1e−8 bis 1e8; Null-Strike-Produkte nicht unterstützt |
| Verhältnis | 1e−8 bis 1e4 |
| IV | 0,0001 % bis 500 %, positiv; fehlende Lösung ist Fehler, nicht 0 % |
| Zins / Dividendenrendite | −20 % bis 100 % / 0 % bis 100 %, ausdrücklich eingegeben |
| Restlaufzeit | >0 bis 3650 Kalendertage; Szenario bis einschließlich Fälligkeit |
| Basiskursänderung | −99 % bis +500 %, relativ |
| IV-Änderung | −500 bis +500 Prozentpunkte; Ziel-IV muss im Modellbereich liegen |
| Stückzahl | >0 bis 1e9 (hypothetischer Positionsmultiplikator) |
| Solver | 64 Bisektionen, Preisrestfehler max(1e−12, obere Preisgrenze × 1e−10) |
| Modellpreisgrenzen | Call: max(S e−qT − K e−rT, 0) bis S e−qT; Put entsprechend; jeweils × Verhältnis |
| Schlechte Kondition | Nähe zur Preisgrenze innerhalb obiger Toleranz oder Vega ≤1e−8 Währungseinheiten/Schein/pp: keine IV-Lösung bzw. Sensitivität nicht verfügbar |

Die Berechnung nutzt endliche double-Werte nach Decimal-Eingabevalidierung,
`erfc` für Normalverteilungs-Schwänze und Put-Call-Parität für den inneren Wert.
Ausgaben sind Modellwerte, keine Zusage dieser Dezimalgenauigkeit am Markt.
Referenztests verwenden publizierte QuantLib-Testfälle, nicht nur Rückrechnung
mit derselben eigenen Implementierung.

Alle Szenarien vergleichen **Modellpreis gegen Modellpreis**, nicht gegen
Einstandskurs, Geldkurs oder einen hypothetischen Verkaufserlös. Der kombinierte
Effekt wird vollständig mit neuem Spot, neuer IV und neuer Restzeit berechnet.
Isolierte Spot-, IV- und Zeiteffekte werden ebenfalls separat neu bewertet;
wegen Wechselwirkungen sind sie nicht additiv. An der Fälligkeit gilt der
Vanilla-Payoff. Zins und Dividendenrendite bleiben im Szenario konstant.

Die lokale Vega-Näherung wird nur ergänzend bei höchstens fünf Prozentpunkten
IV-Änderung und höchstens 25 % relativer Änderung der Ausgangs-IV angezeigt.
So gilt ein kleiner Prozentpunkt-Schritt bei sehr niedriger Ausgangs-IV nicht
irrtümlich als klein. Diese Begrenzungen und der Hinweis unter sieben Tagen
Restlaufzeit sind konservative numerische **Heuristiken**, keine empirischen
Handelsregeln und keine Genauigkeitsgarantie. Größere Änderungen werden weiterhin
vollständig berechnet, ohne lineare Extrapolation. Auch kleines oder fehlendes
Vega beweist kein geringes Gesamtpositionsrisiko.

BSM unterstellt kontinuierliche Dynamik, konstante Parameter und friktionslose
Bewertung. Reale Sprünge, Smile/Skew, Laufzeitstruktur, diskrete Dividenden,
Emittentenrisiko und Hedging-/Ausführungskosten sind nicht modelliert. Höhere IV
erhöht unter sonst gleichen Bedingungen den theoretischen Vanilla-Call-/Putwert;
daraus folgt weder eine Richtungsprognose noch eine Bewertung als günstig/teuer.
Zeitablauf und IV-Änderung sind getrennt; kürzere Restzeit bedeutet nicht niedrigere IV.

## Nächste Datenstufe: Freischaltkriterien

Vor einer echten aktuellen IV/Sensitivität sind mindestens zu belegen:

- Versionierte Vanilla-Klassifikation, Ausübungsart, Verhältnis-Konvention,
  Emittent, genaues Bewertungs-/Fälligkeitsinstant, Währungen und FX/Quanto.
- Originalkurszeiten **beider** Instrumente, jeweilige Abrufzeit und qualifizierte
  Kursseite. Kein Adjusted Close als Spot. Synchronität zunächst so strikt wie
  bestehender Produktvergleich; jede spätere Toleranz muss zur Route/Verzögerung
  passen und separat bestätigt werden, keine stille Lockerung.
- Kursalter einschließlich belegter Sessions, Feiertage, Verzögerung und
  Marktschluss; aktuelle Abrufqualität unabhängig vom Last-success-Datensatz.
- Zinskurve/Dividendenannahmen mit Quelle, Stichtag und Modellversion. Europäisch
  oder amerikanisch und kontinuierlich oder diskret strikt getrennt modellieren.
- Anbieter-IV/Greeks nur mit Prozent-/Dezimal-, Vega-/Verhältnis- und Währungsbasis,
  Kursseite, Modell und Bewertungszeit. Unbekannte Herkunft bleibt unqualifiziert.
- Bei eigener IV-Inversion Bid- und Ask-IV als mögliche Preisspanne prüfen;
  Mid nur bei gültigem Paar. Große IV-Spanne/kleines Vega als Unsicherheit, nicht
  als präziser Einzelwert. Referenzpreise werden nicht zur aktuellen IV hochgestuft.

Eine künftige Historientabelle muss Originaldaten, Qualität und Ableitungen
append-only samt eindeutiger Beobachtungs-ID speichern. Schlüssel der Vergleichsbasis:
ISIN/Terms, Quelle/Route, Kursseite, Währung, Modell/-version und Bewertungsannahmen.
Quellen-, Kursseiten- und Modellwechsel bilden sichtbare Segmente. Jede Beobachtung
speichert auch Spot, Moneyness und Restlaufzeit. Keine vermischten Modellreihen.

## Historische Kennzahlen: vorgeschlagener Entwurf, noch nicht implementiert

Rank und Perzentil sind unterschiedliche beschreibende Statistiken:

- `Rank = 100 × (IV_aktuell − Minimum) / (Maximum − Minimum)`.
  Liegt aktuell außerhalb des historischen Bereichs, Rohwert und Bereichsbruch
  offen anzeigen, nicht unbemerkt auf 0/100 beschneiden. Historische Extremwerte
  können den Rank stark verzerren.
- `Perzentil = 100 × (Anzahl kleiner + 0,5 × Anzahl gleich) / n` (Midrank).
  Gleichstände werden somit ausdrücklich behandelt.

Vorgeschlagene konfigurierbare Datenpolitik vor Freischaltung:
252 abgeschlossene **belegte** Handelssitzungen vor dem aktuellen Stichtag,
ein qualifizierter Wert pro Sitzung am fest definierten Snapshot-Zeitpunkt
(Quellenzeitzone, Zeitfenster und Kursseite versionsfest speichern). Mehrfachabrufe
derselben Beobachtung zählen einmal; der letzte qualifizierte Wert bis zum Cutoff
gewinnt, spätere Werte nicht rückwirkend einschleusen. Fehlende Sitzungen bleiben
Lücken. Mindestens 200 eindeutige Sitzungen und 80 % Abdeckung des Fensters, keine
stillschweigende Verkürzung auf beliebige vorhandene Daten. Unverifizierter Kalender
blockiert Abdeckungsbehauptungen.

Konstante Reihen: Rank wegen Nullnenner nicht verfügbar; Perzentil und Änderung
ebenfalls nicht als belastbaren Kontext freigeben (möglicherweise eingefrorener
Feed), Ursache klären. Widersprüchliche Duplikate, Zeitreisen, nichtpositive oder
nichtendliche IV und Qualitätsfehler werden mit Grund ausgeschlossen. Extreme,
aber valide Werte **nicht** automatisch trimmen/winsorisieren; markieren und
Rank-Verzerrung erläutern. Wechsel der Vergleichsbasis blockiert eine übergreifende
Kennzahl, solange keine gesondert qualifizierte vergleichbare Reihe existiert.

Ein Einzelschein ist selbst bei sauberer Abtastung keine konstante Markt-IV:
Moneyness und Laufzeit ändern sich. Für belastbaren Marktvergleich ist perspektivisch
eine definierte konstante Laufzeit/Moneyness oder eine qualifizierte Oberfläche
nötig. Änderungen etwa über 1/5/20 Sitzungen benötigen genau diese qualifizierten
Endpunkte; kein Vorwärtsschreiben fehlender Werte. V1 implementiert weder Sampler
noch Perzentil-/Rank-Algorithmus und testet ausdrücklich deren Nichtverfügbarkeit.
Die Algorithmus-/Abdeckungstests gehören zur tatsächlichen Freischaltung.

## Ereignisse und Hinweise: späterer Ausbau

Ereignisse brauchen Basiswertidentität, offiziellen Quelllink, Datum/Zeitzone,
Bekanntgabezeitpunkt, Bestätigungsstatus und Aktualität. Fehlender Feed bedeutet
„kein belegtes Ereignis“, nicht „kein Ereignisrisiko“. Ein häufiges Ansteigen der
IV vor Ereignissen und Absinken danach ist eine Tendenz, keine Garantie.
Ebenso sind inverse Aktienkurs-/IV-Beziehung und Normalisierung extremer IV
nicht universell; Zielniveau, Zeitpunkt und Regime sind unbekannt.

Künftige IV-Hinweise erst nach qualifizierten Vergleichsdaten, Mindestdauer,
Hysterese und deduplizierten Signalereignissen; Datenlücken lösen keine Warnung
als Entwarnung auf. Bestehende Alert-/Outbox-Infrastruktur verwenden, neue
versionierte IV-Policy gesondert aktivieren. Keine pauschale „IV >40 %“-Regel,
keine Handelsentscheidung und keine Wahrscheinlichkeit aus Rank/Perzentil.

## Fachquellen und unabhängige Referenzen

Am 12.10.2026 gelesen; die Ableitungen und die Implementierungsgrenzen oben
sind eigene Spezifikation, keine von den Quellen empfohlene Handelsstrategie.

1. [OCC / Options Industry Council: Vega](https://www.optionseducation.org/advancedconcepts/vega)
   – lokale Empfindlichkeit pro IV-Prozentpunkt, Abhängigkeit von Preis und Annahmen,
   mögliche Änderungen vor Nachrichten. Das Optionswissen wird nur auf bestätigte
   Vanilla-Payoffs übertragen, nicht auf beliebige Zertifikate.
2. [OCC / OIC: Black-Scholes Formula](https://www.optionseducation.org/advancedconcepts/black-scholes-formula)
   – theoretische Modellwerte, relevante Inputs und frühe Ausübung bei amerikanischen
   Optionen (typischerweise Binomialmodell); Marktpreise werden nicht garantiert.
3. [Martin Haugh, Columbia: The Black-Scholes Model](https://www.columbia.edu/~mh2078/FoundationsFE/BlackScholes.pdf)
   – kontinuierliche Dividendenrendite, Formeln, IV-Fläche, Put-Call-Parität, Vega und
   Modellgrenzen. Insbesondere Vega in Dezimaleinheiten erfordert Division durch 100.
4. [QuantLib v1.40: European option tests](https://github.com/lballabio/QuantLib/blob/v1.40/test-suite/europeanoption.cpp)
   – unabhängige numerische Preisreferenzen (`testValues`, nach Haug); Tests verwenden
   dieselben Jahresbrüche, nicht versehentlich QuantLibs Actual/360 als Actual/365.
5. [Cboe: Term Structure Data](https://www.cboe.com/tradable_products/vix/term_structure)
   – Laufzeitstruktur; ein konstanter 30-Tage-Index ist eine andere Datenbasis als
   ein auslaufender Einzelschein. Keine VIX-Daten als Ersatz für dessen IV importiert.
6. [Cboe: Volatility Surfaces](https://datashop.cboe.com/volatility-surfaces)
   – definierte Snapshot-Zeitpunkte und konstante Laufzeit-/Delta-Bezüge; dient der
   Konzeptabgrenzung, begründet keinen vorhandenen Datenzugang oder Nutzungsanspruch.

## Prüfung und Betriebsgrenzen

Die zugehörige PR-Vorbereitung enthält die tatsächlich ausgeführten Prüfungen
und Umgebungsblocker. Gezielte Tests: Prozent/Dezimal/Prozentpunkte, Verhältnis,
Stückzahl/Währung, Call/Put-Monotonie, unabhängige Preisfälle, Solvergrenzen,
Zeitwert/Vega, Fälligkeit, Null-/Zeit-/Quellenqualität, Speicherung/Deduplizierung,
alte Payloads, HTTP-Vertrag, UI-Fehlwerte und ungültige/überholte Modellantworten.
Der bestehende E2E-Test prüft zusätzlich die vollständige IV-Ansicht bei
320/390/768/1440 px einschließlich seitlichen Überlaufs und Positionsunverändertheit.

Keine Deployment-, Versions-, Anbieterfreigabe-, Consent- oder Telegramänderung.
Programm-, Git- und Zustandsordner auf dem PC einschließlich des bestehenden
Stuttgart-Bind-Mounts wurden nicht berührt. Es wurde ausschließlich eine separate
Entwicklungsarbeitskopie verwendet. Keine zusätzlichen Programmordner pro Release.
