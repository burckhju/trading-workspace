# UX-4 — Konsolidierter Visualisierungsvertrag

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Analyse- und Darstellungsvertrag, 0.1 |
| Status | Draft zur Abstimmung; keine Implementierungs- oder Integrationsabnahme |
| Datum | 31.10.2026, Europe/Vienna |
| Geprüfter Main | `1883f7f330719453958f8be1dd51d48db816662e`, `v1.5.35` |
| Auftrag | UX4-A; Vorbereitung eigenständiger UX4-B/C/D-Aufträge |
| Freigabe | Offen; kein Merge, Release oder PC-Update beauftragt |

## Zweck und Geltungsbereich

Dieser Vertrag legt fest, wie **vorhandene, fachlich qualifizierte Antworten** als
Diagramm, Kennzahl oder Evidenzansicht dargestellt werden. Er führt weder ein neues
Finanzmodell noch einen gemeinsamen Backend-DTO ein. Die Feldnamen unten sind
vorhandene Verträge oder ausdrücklich als Voraussetzung bezeichnete Lücken.

Die [Inventur](ux4-visualization-inventory.md) trennt vorhandene Anzeigen,
Backend-Fähigkeiten ohne Anzeige und noch fehlende Daten. Die eigenständigen
Startprompts für [UX4-B](ux4-b-position-price-history-prompt.md),
[UX4-C](ux4-c-performance-visualization-prompt.md) und
[UX4-D](ux4-d-quality-lifecycle-prompt.md) verwenden diesen Vertrag. Prüfplanung
und Nachweisgrenzen stehen in der [UX4-A-Qualifikation](../implementation/UX4_A_QUALIFICATION.md).

Maßgeblich bleiben die vorhandenen Fach-Owner, ADRs und deren versionierte
Antworten. Dieser Draft ersetzt keine fachliche Freigabe dieser Owner. Der
[Product Backlog](../planning/PRODUCT_BACKLOG.md) bleibt die zentrale
Arbeitsstatusquelle; UX4-A erklärt keine übergeordnete Fähigkeit für fertig.
Der Abgleich mit allen fünf Master-Dokumenten aus Draft #313 und dem
UX-3-Hinweisvertrag aus Draft #314 ist in der
[Koordinationsinventur](ux4-visualization-inventory.md) an exakte Heads gebunden.
Diese Dokumentationsstände sind keine produktive gemeinsame Komponente und
keine Integrationsfreigabe.

## V01 — Fachliche Berechnung und Darstellung getrennt halten

- Trade/Position besitzt wirksame Ausführungen, Average Cost, Positionsprojektion
  und den vorhandenen historischen Währungsresolver. Performance verwendet
  dessen Ergebnisse für Berichtsgrundgesamtheit, Periodenzuordnung, qualifizierte
  Geldbeträge, Summen und Abschlussstatistik; kein zweiter Währungsresolver.
- Market Data besitzt Kursidentität, persistierte Historie und Quellenqualität;
  Market Analysis besitzt EOD-Vergleich, Normalisierung und Analysekennzahlen.
  Position Monitoring besitzt Risiko-, Frische-, Preisbindungs- und Signalregeln.
- UX-1 stellt sichere Ableitungen und Herkunft bereit. UX-4 formatiert, ordnet,
  filtert zur Darstellung und zeichnet die vorhandenen Werte. UX-4 berechnet
  keine neuen Renditen, Kostenbasen, FX-Werte, kumulierten Geldbeträge, Zeitbuckets,
  Risikoscores, Freshness-Schwellen oder Wahrscheinlichkeiten.
- Die Umwandlung eines belegten Decimalstrings in eine endliche Plotkoordinate
  ist nur Darstellung. Quelle, Rohwert, serverseitiger Anzeigewert und fachliche
  Klassifikation bleiben erhalten. Ein nicht darstellbarer Wert bleibt in der
  Evidenztabelle und erhält eine Erklärung; er verschwindet nicht still.
- Bestehende `portfolioTotals` sind eine begrenzte Bestandsanzeige je Währung.
  Sie werden nicht zum Rechen-Owner neuer Performancecharts erklärt. Ebenso
  wird der lokale Geldformatter nicht als Ersatz für die vom Performance-Owner
  gelieferten Rundungen verwendet.

## V02 — Identität und Herkunft gehören zur Aussage

Jede Darstellung muss ihren tatsächlich verfügbaren Kontext erhalten:

| Kontext | Vorhandener Nachweis | Darstellungsregel |
| --- | --- | --- |
| Position / Trade | `trade_id`, `position_id`, Produkt-ID; Projektions-/Kostenbasis im jeweiligen DTO | Keine Antwort eines anderen Trades, Produkts oder Korrekturstands übernehmen. |
| Positionshistorie | `series.id`, Produkt/Listing, Provider, Preisart, Währung, Quellmodus und Quellenbelege | Serien nicht anhand bloß gleichen Produktnamens oder gleicher Währung verschmelzen. |
| EOD-Vergleich | `identity.key`, Instrument-/Listing-ID, Mapping-ID/-Version des gelesenen Verwaltungsstands, `return_basis`, `price_field`, `model_version` | Index, ETF/Proxy und Aktie unterscheiden; belegte Vergleichbarkeit entscheidet der Owner. Aktuelle Mappingdaten sind kein historischer Mappingbeleg pro Punkt. |
| Performance | Berichtsart, Zeitraum, `report_timezone`, Berichtswährung, `basis.id`, Definition | Summary, Counts, Rows, Statistik und Quellen aus genau derselben akzeptierten Antwort. |
| Historischer Ursprung | Plan-, Evaluation-, Analyse-, Review-, Journal-, Evidence- und Lessonversion | Kein Austausch durch eine aktuelle Version desselben Objekts. |
| Aktuelle Qualität | `assessed_at`/Bewertungszeit, Kurszeit, Abrufzeit, Retention und Grundcodes | Ein späterer Abruf macht einen alten Kurs nicht frisch. |

Fehlender Nachweis wird als fehlend bezeichnet. Ein neuer gemeinsamer
Snapshot, eine neue Identitätsauflösung oder ein neues Cross-Feature-Aggregat
benötigt einen eigenen Owner-Vertrag; ein UI-Wrapper erzeugt diesen nicht.

## V03 — Fehlend, null, null Euro und leer unterscheiden

Die folgende Tabelle beschreibt **Darstellungsbedeutungen**, keine neue globale
Status-Enum. Die existierenden Status-/Reasoncodes bleiben erhalten.

| Sachverhalt | Darstellung | Unzulässige Umdeutung |
| --- | --- | --- |
| Belegter Wert exakt `0` | Null mit Einheit; neutrale Klassifikation nur gemäß Owner | Als fehlend ausblenden oder wegen Rundung als Gewinn/Verlust umklassifizieren |
| Fehlender Wert `null` | „Nicht verfügbar“ bzw. fachlicher Grund, kein Punkt/Balken | `0`, `0 %`, Null-Euro-Balken, leere Quelle als Erfolg |
| Nicht berechenbar | „Nicht berechenbar“ und vorhandener Grund | Teilwerte zu einem vollständigen Ergebnis ergänzen |
| Mathematisch nicht definiert | Präziser Grund, etwa „Keine Verlusttrades“ | Infinity, NaN, Ersatznull oder Höchstscore |
| Fachlich leere Auswahl | „Keine passenden Beobachtungen/Trades“ | Datenladefehler als fachliche Leere ausgeben |
| Teilweise qualifiziert | Belegte Teilwerte und Abdeckung ausdrücklich als Teilbestand | „Gesamt“, vollständige Linie oder Kennzahl des unbekannten Gesamtbestands |
| Nicht geprüft / unbekannt | So benennen; optional zum bestehenden Nachweis verlinken | „Unauffällig“, „gesund“ oder „abgeschlossen“ |
| Laden / Readfehler | Eigener Zustand; keine fremde oder überholte Antwort anzeigen | Alter Erfolg als aktueller Stand |

Die existierende leere Performance-Gesamtsumme darf der Owner als `0` liefern.
Das ist **kein** Ersatz für fehlende Einzelergebnisse und begründet bei `EMPTY`
keine berechenbare Trefferquote, keinen Durchschnitt oder Median.

## V04 — Zeitachsen erhalten die belegte Präzision

1. Positionskurse liegen auf der nachgewiesenen Originalkurszeit. `retrieved_at`,
   `received_at`, `captured_at` (Stichproben-/Speicherzeit) und `assessed_at`
   sind getrennte Angaben; Retention kann `captured_at=null` haben.
   Unbekannte Quellzeitzone oder fehlendes Datum wird nicht anhand des Browser-
   oder Abrufzeitpunkts ergänzt.
2. Der vorhandene Positionsplot verwendet UTC. Achse, Tooltip und Tabelle nennen
   den Zeitzonenbezug; Intraday und mehrtägige Bereiche erhalten passende Labels.
   Eine Änderung der Anzeigezone ändert keine gespeicherten Ereignisse.
3. EOD-Daten tragen `trading_date`, keine belegte Intraday-Uhrzeit (`observed_at`
   ist im Chartvertrag `null`). Eine interne Tageskoordinate ist kein Kurs um
   Mitternacht und wird nicht so beschriftet. Provider-Updatezeit ist separat.
4. Ausführungen mit `DATE_ONLY` behalten tatsächliches Datum und bekannte
   Originalzeitzone/Präzision. Keine erfundene Uhrzeit, kein frei gewählter
   Mittags-/Mitternachtsmarker, kein Verschieben zum nächsten Kurs.
   Im Performancebereich sind eine ausdrücklich datierte Kategorie mit
   Originalzone, die Ereignisliste oder das unverändert gelieferte mögliche
   Zeitintervall zulässig. Sichere Zugehörigkeit zur ganzen Berichtsperiode
   belegt keine Zugehörigkeit zu einem kleineren Tagesbucket.
5. Performance verwendet die vom Owner ausgewerteten Datumsgrenzen und
   `report_timezone`. Grenzfälle, Sommerzeitwechsel und unentscheidbare
   Tagesintervalle werden nicht lokal neu klassifiziert. UI-Seiten-/Zeilenfilter
   ändern diese Grundgesamtheit nicht.
6. Snapshotzeit, fachlicher Ereigniszeitpunkt und historische Wissensbasis bleiben
   getrennt. Ein heute gelesenes EOD-Archiv ist kein Beweis, welche Daten einer
   damaligen Entscheidung bekannt waren; dafür sind die gespeicherten
   Analyse-/Plan-/Evaluationversionen erforderlich.

## V05 — Kurspunkte, Lücken und Abdeckung

- `PositionPricePlot` bleibt ein Plot tatsächlich gespeicherter Einzelpunkte:
  `line={false}`, keine Glättung, Interpolation, Forward-Fill, Backfill aus
  aktuellen Quotes oder synthetische Kurslinie aus Kauf-/Verkaufspreisen.
- `TimeSeriesChart` darf weiterhin belegte EOD-Beobachtungen verbinden. Diese
  Verbindung erzeugt keine Zwischenwerte; es gibt keinen Tooltip oder Export
  mit interpoliertem Preis. `connectNulls={false}`, vom Owner gemeldete Lücken
  und fehlende Vergleichsdaten bleiben erhalten. Rein leere Plotkoordinaten
  zur Linienunterbrechung sind keine Marktbeobachtungen.
- Durch vorhandene Evidenz belegbare Provider-/Listing-/Mapping-/Preisart-/
  Währungswechsel werden nicht zu einer einheitlichen Kursserie geglättet.
  EOD-DailyPrice besitzt keine historische Mappingrevision oder Provider-
  Exchangeversion; diese Lücke bleibt sichtbar, statt die heutige Mapping-ID
  rückwirkend jedem Punkt zuzuordnen. Fehlende adjustierte Schlusswerte werden
  im EOD-Chart nicht durch `close` ersetzt.
- Angeforderter Bereich, tatsächlich belegter erster/letzter Kurs, Anzahl der
  Beobachtungen, ausgeschlossene Beobachtungen und gelieferte Coveragegründe
  bleiben erkennbar. Ein oder zwei Punkte rechtfertigen keine Trendbehauptung.
- Keine vollständige Handelssitzungsabdeckung, Ausfallquote oder Zahl fehlender
  Kurse ohne verifizierten Kalender und erwartete Frequenz. Ein Wochenende ist
  nicht automatisch ein Providerfehler. Die aktuellen groben Gap-Hinweise sind
  keine lückenlose Handelskalenderprüfung.
- Keine zusätzliche oder stille UI-Kürzung, Glättung oder Stichprobe bei vielen
  Punkten. Die vorhandene serverseitige Samplingpolicy bleibt bestehen. Bestehende
  Grenzen, Ablehnungen und paginierte Evidenz beibehalten; ein anderer
  Umfangsvertrag wäre mit dem Owner abzustimmen.

## V06 — Kauf-/Verkaufsereignisse

Ein Preisachsenmarker benötigt die bestehende serverseitige Freigabe
`plottable`, belegte Ereigniszeit und passende Währung/Identität. UX-4 macht
einen ausgeschlossenen Marker nicht lokal zulässig.

BUY und SELL verwenden unterscheidbare Formen und Text, nicht nur Farbe. Der
Tooltip/die erreichbare Tabelle nennt Ereignisart, tatsächliches Datum samt
Präzision, Menge, Ausführungspreis, Währungsherkunft und Ereignisbezug. Erfasste
Ausführungspreise sind ausdrücklich **keine Marktbeobachtungen**.

Zeitgleiche Buchungen bleiben einzeln nachvollziehbar. Korrigierte/ersetzte
Ausführungen und stornierte Trades folgen dem bestehenden Effektivitätsvertrag;
die Grafik rekonstruiert die Historie nicht aus Rohbuchungen selbst.
Nicht plottbare Ereignisse bleiben mit Ausschlussgrund in der Ereignisliste.
Ein reines Datumsereignis darf dort stehen, ohne auf einer Intradaypreisachse
zu erscheinen. Die Marker erhöhen weder Kurspunktzahl noch Kursabdeckung.

## V07 — Preisachsen, Einheiten und Währungen

- Jede Achse/Kennzahl nennt Fachgröße und Einheit, bei Kursen zusätzlich die
  Preisart: Produktpreis in konkreter
  Währung, Indexpunkte, Prozent, Basis 100, Stück, Tage, Sekunden oder Scorepunkte.
  Kalender-/Berichtstage, tatsächlich beobachtete Handelssitzungen und Anzahl
  gespeicherter Beobachtungen sind verschieden; Fenster nicht pauschal „Tage“
  nennen. Auch Samples, Originalkurspunkte, Ausführungen und Stückzahl unterscheiden.
  Keine gemeinsame Geldachse verschiedener Währungen und keine zweite Achse,
  die eine unbelegte Vergleichbarkeit suggeriert.
- Produktkurs und Basiswertkurs bleiben getrennt. Gleiche Währung allein
  qualifiziert weder Stop-/Zieloverlay noch Regelabstand. Eine historische
  explizite Preisbindung und der zuständige Owner sind erforderlich.
- Normalisierter EOD-Vergleich und Veränderung in Prozent sind nur bei
  `comparison_status === 'READY'` erlaubt. Werte kommen bereits aus dem
  Vergleichsservice; native Währungen bleiben sichtbar, `fx_adjusted=false`
  bedeutet keine Währungsbereinigung.
- Die Performanceoberfläche bleibt fest auf EUR. Fremdwährungslinks werden
  entsprechend dem vorhandenen Guard behandelt, nicht still zu EUR umbenannt.
  Nicht-EUR-Ausführungen sind ohne bestehenden qualifizierten Vertrag kein
  EUR-Ergebnis. Keine neue FX-Quelle oder Konvertierung.
- Geldsortierung, Signum und Klassifikation verwenden vorhandene exakte
  Ergebnisse. Ein gerundetes `0,00` kann aus einem positiven oder negativen
  Rohwert stammen; dessen Ownerklassifikation bleibt erhalten.

## V08 — Performance: zwei strikt getrennte Grundgesamtheiten

| Vertrag | Beobachtungseinheit / Zeitraum | Zulässige Visualisierung aus vorhandenen Daten |
| --- | --- | --- |
| `realized-gross-sell-v2` | Jeder wirksame SELL-Beitrag im Berichtszeitraum; auch Teilverkäufe weiterhin offener Trades | Einzelbeiträge mit Ausführungsbezug und getrennten ungeklärten Fällen; Summary unverändert vom Owner |
| `closed-trade-gross-v1` | Ein vollständiges Lebenszeitergebnis je Trade; tatsächlicher wirksamer Vollabschluss-SELL bestimmt die Periodenzugehörigkeit | Bestehende Abschlusskennzahlen, qualifizierte Tradeergebnisse und disjunkte Abdeckungsgruppen |
| `closed-trade-statistics-v1` | Vollständiger Abschlussbericht, `summary.status=COMPLETE`, `counts.qualified > 0` | Vier bestehende Backendstatistiken samt N, Definition, `basis.id`, Gründen und Rohwertdetails |

Frühere Teilverkäufe außerhalb des Abschlusszeitraums gehören zum gesamten
Tradeergebnis des Abschlussberichts. Sie werden nicht nach dem aktuellen
Zeitraum abgeschnitten. Ein offener Trade mit Teilverkauf kann im SELL-Bericht
vorkommen, ohne zu den abgeschlossenen Trades zu zählen.

| Kennzahl | Verbindliche bestehende Definition / Grenze |
| --- | --- |
| Realisierter Bruttobeitrag | Average-Cost-Beitrag einer wirksamen SELL-Ausführung aus der bestehenden Projektion, historisch währungsqualifiziert durch Performance; vor Gebühren, Kommissionen und Steuern |
| Vollständiges Tradeergebnis | Unverändertes vollständiges Ownerergebnis aller wirksamen Lebenszeit-SELLs, nur bei vollständig qualifizierter Geldherkunft des gesamten Trades; bekannte SELL-Teilbeträge eines ungeklärten Trades bleiben bloße Quellen |
| Trefferquote | Exakt positive vollständige Tradeergebnisse / N × 100; neutrale Trades gehören zum Nenner |
| Durchschnitt | Bestehende vollständige ungerundete `summary.total / N`; keine Rekonstruktion aus Zeilen oder Anzeigewerten |
| Median | Mittlerer Rohbetrag; bei geradem N Mittelwert der beiden mittleren Rohbeträge, vom Backend geliefert |
| Profit-Faktor brutto | Summe positiver Rohbeträge / Absolutbetrag der Summe negativer Rohbeträge; keine Verluste ⇒ nicht definiert; vorhandene Verluste ohne Gewinne ⇒ 0 |
| Ungeklärte Ergebnisse | Existierende Gründe/Zähler/Zeilen; keine monetäre Ersatznull und keine Klassifikation als Verlust oder neutral |

Bei `PARTIAL`/`NOT_COMPUTABLE` bleiben alle vier Statistiken nicht berechenbar;
bei `EMPTY` bleiben sie ohne Wert. Eine neue Statistik nur des bekannten
Teilbestands ist nicht Teil von UX4-C. Die gelieferten `raw`-/`display`-Werte,
Minor Units und `ROUND_HALF_EVEN` bleiben unangetastet.

`statistics.population` ist bei COMPLETE die positive Zahl qualifizierter
Trades, bei EMPTY `0`, bei PARTIAL/NOT_COMPUTABLE `null`.
`statistics.report_basis_id` muss zu `report.basis.id` und
`statistics.report_status` zu `summary.status` passen. Lokale Filter, Seiten
und Grafikfenster verändern diese Population nicht.

Eine erste Zeitdarstellung darf einzelne bereits gelieferte Beiträge zeigen.
Tages-/Monatssummen, kumuliertes PnL, Equity-/Depotkurve, Rendite, Drawdown,
Sharpe, Nettoergebnis oder Benchmarkvergleich benötigen zusätzliche
Owner-Verträge und Daten. Auch eine optisch einfache kumulierte Linie ist
eine neue Finanzberechnung und in diesem Auftrag nicht erlaubt.

## V09 — Kennzahlendefinitionen nicht über gleiche Labels vereinheitlichen

Die Inventur dokumentiert konkrete Unterschiede:

- Produktauswahl: `spread_percent_mid` relativ zu `(bid+ask)/2`.
  Positionsbewertung: `spread_percent` relativ zu `bid`.
  Herkunft und Nenner müssen im jeweiligen Label/Detail erkennbar bleiben.
- FT-006-Anteile/Volatilität/Momentum können als Bruch vorliegen; RSI und
  Positionsscores haben andere Skalen. Keine ungeprüfte pauschale `%`-Beschriftung.
- Realisierte historische Volatilität, implizite Volatilität und hypothetische
  Laboreingaben sind verschiedene Aussagen. Nicht verfügbare IV-/Greekdaten
  werden nicht aus Scores oder historischen Schwankungen ergänzt.
- Trend-/Peak-Scores sind regelbasierte Punkte, keine Erfolgswahrscheinlichkeit.
  Plan-Risikoannahmen sind Nutzertexte, keine berechnete Positionsgröße.
- Die bestehende DynamicStop-Projektion enthält keine explizite Währung,
  Listingidentität oder `PriceBinding`. Ein Overlay ist ohne ergänzenden
  Preisachsennachweis des Owners nicht qualifiziert; gleiche Trade-ID oder
  aktuelle EUR-Quote ersetzen ihn nicht.
- Rohwerte der Positionsprojektion sind ohne zusätzliche Währungsqualifikation
  keine Performancekennzahl in der Berichtswährung. Realisiert und unrealisiert
  erhalten getrennte Beschriftung und dürfen nicht zu einer Gesamtrendite werden.

## V10 — Datenqualität bleibt mehrdimensional

Kursfrische, Verfügbarkeit, Identitätsbeleg, Preisart, Historienabdeckung,
Providerbetrieb und fachliche Berechenbarkeit sind getrennte Dimensionen.
Ein fehlender Kurs ist kein Verkaufssignal. Ein gesunder Provider beweist
weder einen frischen Kurs des konkreten Instruments noch vollständige Historie.

Bestehende Zähler werden nur mit ihrer tatsächlichen Einheit und Population
gezeigt: gehaltene Produkte, offene Positionen, Serienpunkte, SELLs oder Trades.
Überlappende Diagnose-/SELL-Zähler werden nicht zu einem Kreisdiagramm oder
100-%-Balken gestapelt. Bei disjunkten Gruppen bleibt deren eigener vollständiger
Nenner sichtbar; zusätzliche Teilgruppen werden nicht nochmals mitgezählt.

UX-3 verantwortet Begriffe, Präsentationspriorität und Warnhinweise; fachliche
Schwere und Blockierungen bleiben beim jeweiligen Domain-Owner. UX-4 macht
diese Informationen räumlich und visuell lesbar und zeigt Datenlücken. Es
entsteht kein eigenes universelles Rot-Gelb-Grün-Gesamturteil und keine neue
globale Qualitätsenum. `LAST_AVAILABLE` beschreibt Verfügbarkeit, nicht
automatisch `STALE`. Eine Ersatzquelle belegt weder Erfolg noch Recovery der
ursprünglichen Route. Der UX-3-Draft liefert einen Präsentationsvorschlag;
konkrete Schnittstelle und Platzierung bleiben vor Integration abzustimmen.

`qualified_success` belegt die Ownerqualifikation eines Checks, nicht allein
einen neuen HTTP-Kontakt. „Provider wieder erreichbar“ benötigt zusätzlich
`provider_reachable=true`. Der vollständige aktuelle Snapshot gilt; ein alter
`recovered_at`-Zeitpunkt überdeckt keine spätere Fehlerfolge.

Prozesslokale Diagnosen sind Momentaufnahmen, keine historische Provider-Uptime.
Auch ein bestehender GET ist nicht automatisch providerfrei: etwa der aktuelle
Monitoring-Health-Pfad kann EODHD lesen und verwendet bei fehlendem
`source_updated_at` die Abrufzeit. Das ist kein exakter Börsenkurszeitbeleg.
Analytics, Phase, Scores und DynamicStop können diesen Health-Pfad mittelbar
ebenfalls aufrufen; „read-only“ bedeutet dort nicht „providerfrei“.
Neue Visualisierungen dürfen beim Öffnen, Fokussieren oder Filterwechsel keine
zusätzliche Providerabfrage, Speicherung oder fachliche Aktion auslösen.

## V11 — Lebenszyklus nur durch eigene Belege

Die Reihenfolge Analyse → Plan → Ausführung → Position → Journal → Lesson ist
eine Orientierung, kein verpflichtender, linear abgearbeiteter Prozess.
Manuelle Pläne und externe Trades sind gültige alternative Ursprünge.

| Schritt | Zulässiger Beleg | Nicht daraus ableiten |
| --- | --- | --- |
| Analyse | Exakte versionierte Analyse/Kandidatenevaluation und Herkunft | Aktuelle Analyse desselben Basiswerts sei die historische Quelle |
| Plan | Gebundene Planversion und ihr eigener Status/Approval | Vorhandener Trade beweise Planfreigabe |
| Ausführung | Wirksame Ausführungen mit Zeitpräzision und Korrekturbezug | Quote, Planmarke oder Alert sei eine tatsächliche Ausführung |
| Position | Zugehörige aktuelle Projektion; geschlossen/offen/storniert getrennt | Storniert sei wirtschaftlich voll abgeschlossen |
| Review / Journal | Exakte Review-/Journalversion, Status und Quellenbindung | Vorhandener Entwurf sei finalisiert oder Materialisierung sei aktuell |
| Lesson | Verknüpfte Evidence, konkrete Lessonversion, Relation und ausdrücklich gelieferter Status | Vorhandene Lesson sei freigegeben, Hypothese sei Modellaktivierung; Reviewstatus ohne passenden Ownerread |

Jeder Schritt zeigt seinen eigenen Lade-/Fehler-/Fehlend-/Versionszustand und
den bestehenden Quellenlink. Spätere Belege setzen frühere Schritte nicht
automatisch auf „erledigt“. Keine Prozentfortschrittsanzeige, keine neue
Statusmaschine, kein automatisch gestartetes Review, Journal, Lesson oder
Materialisierung. Unabhängige Reader bleiben unabhängig; die Oberfläche
behauptet keine atomare gemeinsame Lesezeit.

`DRAFT/FINALIZED`, gespeicherte und heute geprüfte Quellenaktualität,
`source_bound`, historische Evidenceexistenz und aktuelle Materialisierung
sind eigene Achsen. `materialized=false` für eine neue, noch nicht freigabefähige
Reviewversion widerlegt keine ältere Evidence. Der historische Lessonlink
liefert Version, Relation und `is_current_version`, aber keinen Lessonreviewstatus.
Eine abgeschlossene Nachbeobachtung mit 20 tatsächlichen EOD-Beobachtungen
beweist weder eine vollständige Reflexion noch eine freigegebene Lesson.

## V12 — Bedienung, mobile Darstellung und Barrierefreiheit

- Grafik und semantische Daten-/Ereignistabelle bieten denselben fachlichen
  Informationsumfang. Tooltip ist ergänzend, kein alleiniger Zugang zu Preis,
  Zeitpunkt, Quelle, Ausschlussgrund oder Ereignis.
- Native Buttons, Links, Selects und Details bleiben per Tastatur bedienbar.
  Fokus ist sichtbar, bleibt bei Filtern/Neuladen sinnvoll erhalten und springt
  nicht durch verspätete Antworten in fremde Bereiche. Kein Hover-only-Zugriff.
- Farbe erhält mindestens Text, Form oder Linienmuster als zweites Merkmal.
  Positiv/negativ, Frische, fachliche Warnung und Quellenproblem sind nicht
  dieselbe Farbsemantik. BUY-/SELL-Formen bleiben von Marktserien unterscheidbar.
- Prüfung bei 320, 390 und 1280 CSS-Pixeln sowie 200 % Zoom: keine horizontale
  Dokumentrolle, keine abgeschnittenen Einheiten/Legenden oder überdeckten
  Bedienelemente. Eine breite Evidenztabelle darf einen beschrifteten eigenen
  Scrollbereich besitzen. Wesentliche Informationen bleiben ohne Scrollen
  innerhalb eines Grafiktooltips erreichbar.
  Kompakte Hinweisflächen werden gemäß UX-3-Draft zusätzlich bei 400 % Zoom
  geprüft; ihre wesentliche Einschränkung bleibt neben der betroffenen Zahl.
- Tastaturprüfung umfasst Tab/Shift-Tab, Enter/Leertaste und vorhandene
  Diagramm-Pfeiltasten. Für fehlende Scatter-Punktnavigation ist die vollständige
  Tabelle Pflicht; `accessibilityLayer` allein ist kein Abnahmenachweis.
- Textkontrast, grafischer Kontrast, Fokus, lesbare Labels und zugängliche Namen
  konkret prüfen. Keine WCAG- oder Screenreader-Vollabnahme ohne entsprechenden
  tatsächlichen Nachweis behaupten. Animation bleibt entbehrlich/deaktiviert.
- Initiale und unveränderte Hinweise bleiben statisch. Einen vom Host belegten
  neuen/verschlechterten Zustand höchstens einmal ankündigen; Zusammenfassung
  und Detail sprechen nicht doppelt. Kein pauschales `role=alert` allein aus
  „Warnung“ oder „Blocker“, kein Fokuswechsel durch Polling.

## V13 — Wiederverwendung, Ladegrenzen und Integration mit UX-2

`PositionPriceHistory` mit Plot/Evidence bleibt der bestehende UI-Owner der
Positionshistorie; fachlicher Kursdatenowner bleibt Market Data.
`TimeSeriesChart` bleibt der EOD-Renderer. Performance verwendet
`PerformanceWorkspace`, seine Filter-/Antwortguards und die vorhandenen
Berichtskomponenten. Quellen-/Journal-/Lessonansichten behalten ihre Owner.
Keine zweite Positionstimeline, keine zweite Performancefilterung und keine
neue Chartbibliothek ohne begründete Lücke.

UX-2 besitzt Arbeitsbereich, Navigation, Einbindungsposition, Read-Lebensdauer,
Invalidierung und gemeinsame Kontextgrenzen. Die dokumentierte Navigation in
Draft-PR #311 ist ein Vorschlag/Implementierungsstand außerhalb Main, keine
Freigabe eines gemeinsamen UX4-Dashboards. Vor Änderungen an gemeinsamen
Seiten/Komponenten müssen Einbindungsstelle, Props, Ladeowner, Invalidierung,
Anker und Konfliktdateien mit UX-2 konkret abgestimmt sein.

Ein Bereichs-/Hashwechsel desselben Trades erhält Entwürfe und erzeugt keine
zusätzlichen Trade-/Positions-/Timeline-Reads. Ein echter Identitäts-/Versions-
oder Berichtskontextwechsel verwendet die bestehenden Guards; Kontexttoken
belegen nur ihren jeweiligen Owner-Read, keinen globalen Finanzsnapshot.
Erfolgreicher Readback aktualisiert die betroffene Historie ohne Formularreset.

Gemeinsame Darstellung oder URL-Transport verwendet nur eine abgestimmte
schmale öffentliche Grenze in der vorhandenen Shared-Struktur oder bereits
qualifizierte Ownerdaten/-links über typisierte Props. Keine neuen Querimporte
interner Featurekomponenten/-services; ein Reexport-Barrel oder dokumentarisches
`import type` ersetzt diese Architekturprüfung nicht. Finanz-/Quellenvalidatoren
bleiben beim Fachowner. UX-4 baut keine parallelen UX-3-Hinweisrenderer.

Bis dahin dürfen Folgeaufträge vorhandene fachlich lokale Darstellungen
vorbereiten; sie implementieren keine neue gemeinsame Workspace-Komponente.
Die drei Startprompts sind unabhängig voneinander bearbeitbar, aber nicht von
fehlenden Fachverträgen oder der nötigen UX-2/UX-3-Abstimmung befreit.

## V14 — Nachweise, Abnahme und Änderungsgrenze

Die [Prüfmatrix](../implementation/UX4_A_QUALIFICATION.md#prüfmatrix-für-die-spätere-implementierung)
ist die gemeinsame Abnahmegrundlage für Einheiten, Währungen, Zeit, Lücken,
Quellenkonflikte, Historienidentität, Ausführungen, Mobile, Tastatur und
unveränderte Finanzberechnungen. Jeder Folge-PR nennt tatsächlichen Main,
eigenen Head, geänderte Dateien, geprüfte Erwartungen und echte Testergebnisse.

Dokumentiert, implementiert, lokal geprüft, CI-geprüft, fachlich abgestimmt,
integriert, veröffentlicht und installiert sind getrennte Zustände. Alte grüne
Läufe, ein erfolgreicher Build oder ein Softwaretag ersetzen keinen Nachweis
für den eigenen Änderungsstand. Bestehende Gates, Assertions und
Coveragegrenzen bleiben erhalten.

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | UX4-A: bestehende Fachverträge zu einem Draft-Darstellungsvertrag zusammengeführt; keine Runtimeänderung |
