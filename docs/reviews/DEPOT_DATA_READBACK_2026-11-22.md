# Tatsächliche Depotversorgung — passiver PC-Readback vom 22.11.2026

## Ergebnis und Nachweisgrenze

**Die Installation von v1.5.52 und ein vollständiger regulärer V2-Lauf sind
jetzt am tatsächlichen PC belegt. Geeignete Kurse fehlen weiterhin bei allen
vier offenen Positionen.** Drei Positionen haben keine bestätigte
Quellenbindung; bei der vierten ist die JPMorgan-Route bestätigt, aber ein
verwendbarer Bid fehlt und der V2-Verbraucher meldet eine Unterbrechung der
Preisversorgung. Beide V2-Prüfpfade haben vier Datenprobleme und null
technische Positionsfehler. Die vollständige Ursachenmatrix unten ersetzt
die frühere bloße Unzugänglichkeit des aktuellen Verbraucherbestands.

Tatsächliche Käufe und historische Kaufwährungen sind für alle vier
Positionen belegt. Diese Daten müssen nicht erneut aus heutigen Werten
rekonstruiert werden. Dagegen fehlen qualifizierte Produkt-/Kurs-/
Status-/Sitzungsbelege und B06-Grundevidenz. Die strenge B04/B57-Überwachung
ist ausdrücklich deaktiviert; ihre null Bewertungen sind kein positives
Regelergebnis. Keine Position ist als vollständig B58-/B06-abgedeckt belegt.

Dieser Nachweis enthält technische, pseudonymisierte Befunde. Die privaten
Rohdateien, Produkt-/Positionskennungen, Beträge, Mengen, Einstandswerte,
Streambindungen und Originaldokumente gehören nicht ins Repository.
P01–P04 sind ausschließlich die lokalen Sammlungslabels dieses Pakets,
keine dauerhafte Produktkennung. Arbeitsstatus und **genau ein nächster
Auftrag** stehen im [Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

## 1. Software, Zeit und tatsächlicher Betrieb

| Gegenstand | Beobachtung | Reichweite |
| --- | --- | --- |
| Main bei erster Readbackauswertung | `febeb922c0f337029baa7f9d792c37f9f72ba02b`, `VERSION=1.5.53` | Die relevanten Backendreader sind gegenüber der installierten Produktbasis unverändert; die Oberflächenänderungen aus #372 sind davon getrennt. |
| Erneut gelesener Main nach #373 | `9a5e59dac3bb219cbc40641e62e75871eb2ed131`, `VERSION=1.5.54`, Merge am 22.11.2026 um 21:35:28 Uhr MEZ | Das gesamte Delta zu febeb922… enthält ausschließlich Versions-/Liefermetadaten und Dokumentation. Der [P02-Fortsetzungsbeleg](#p02-fortsetzung-20261122) und der tatsächliche PC-Stand bleiben getrennt. |
| Tatsächlich installierter Stand | `c7db441de36297a98d47cdf28c64b4e5d9994692`, `VERSION=1.5.52` | Checkout-, Deployment-, Container- und Appimagebezüge vor/nach identisch. Kein angenommener PC-Stand aus Main oder einem Tag. |
| Datenbank | Alembic `20261118_0060` | Tatsächlicher READ-ONLY-SELECT über die konfigurierte Backend-Datenbank. |
| Dienste | Backend, Datenbank, Frontend und Issuer-Renderer jeweils `running`/`healthy`; je null Containerneustarts | Momentaufnahme der bestehenden Containerinstanzen, keine Aussage über sämtliche früheren Neustarts. |
| Sammlung | **22.11.2026, 20:50:41.973–20:50:45.069 Uhr MEZ**; UTC `19:50:41.973546–19:50:45.069933` | Vom Nutzer ausgeführter Collector; fünf unveränderte JSON-Dateien im bereitgestellten privaten Archiv. |
| Letzter regulärer Zyklus | **22.11.2026, 20:44:54.842–20:45:35.942 Uhr MEZ**, Dauer 41,1 s | Runtime vor/nach identisch; V2 aktiv, Zyklus bei Sammlung beendet. |
| V2-Einstand | 4 Positionen ausgewertet, 4 Datenprobleme, 0 technische Positionsfehler | Gespeicherte positionsbezogene Gründe unten; keine beurteilbare Position nachgewiesen. |
| V2-Produktfrist | 4 Positionen ausgewertet, 4 Datenprobleme, 0 technische Positionsfehler | Keine vier fachlichen Fristauslöser, sondern fehlende Fristdaten. |
| Strenger Verlustpfad | `hebeltrader_scope=DISABLED`; 4/4 `NOT_ACTIVATED`, keine Assessments/Episoden | B04/B57 wird nicht ausgewertet. V2 aktiviert die bestätigte Baseline nicht. |
| Zustellung | V2-Reviewzustellung deaktiviert | Ein vorhandener allgemeiner Telegramstatus ist keine aktivierte V2-Zustellung. |

Das Inventar enthält **vier** offene Positionen. Beide Inventarreads stimmen
in Positionen und Bindungen überein. Sämtliche **24 Positionsreads plus sechs
Inventar-/Runtime-/Refreshreads** sind HTTP 200 ohne Diagnosefehler; die
vorhandenen Responseverträge wurden vom Collector geprüft. Die Backend-
Payloadidentität stimmt mit dem veröffentlichten Helfer überein.

Der Refresh arbeitet während der Sammlung weiter; seine beiden Snapshots
sind deshalb nicht byteidentisch. Die sieben positiven Coveragechecks und
die unveränderten Monitoringzyklusmarker ergeben **keinen global atomaren
Datenbanksnapshot**. Sonntägliche Daten werden nicht zu einem belegten offenen
Handelsmarkt erklärt. Aus 26 im Moment fälligen/überfälligen Refreshjobs oder
Fehlern anderer Produkte wird kein Ausfall dieser vier Positionen abgeleitet.

### Alte Assessmentzeit trotz neuem Zyklus

Die letzten gespeicherten V2-Einstandsbewertungen stammen vom 20./21.11.; die
Fristbewertungen ebenfalls. Der Code schreibt bei identischem fachlichem
Fingerprint bewusst keine neue Assessmentzeile. Damit sind diese Zeiten
mit einem erneut erfolgreichen regulären Prüflauf vereinbar. Sie dürfen
weder auf den 22.11. umdatiert noch als Beweis eines seit Tagen gestoppten
Runners ausgegeben werden. Einzelgründe stammen aus den gespeicherten
Assessments, die aktuelle erneute Auswertung aus den getrennten Zykluszählern.
`last_rule_checks` enthält hier die allgemeine Stop-/Zielprüfung und ersetzt
diese acht gespeicherten V2-/Fristbefunde nicht.

Code: [V2-Persistenz](../../backend/app/features/position_monitoring/service/indicative_entry.py),
Z.161–169 und 425–468; [Fristpersistenz](../../backend/app/features/position_monitoring/service/product_deadline_review.py),
Z.162–169 und 200–223. Codezeilen beziehen sich auf den installierten Commit.

## 2. Positionsbezogene Ursachenmatrix

`Nicht auswertbar` bezeichnet hier die jeweilige Regelabdeckung, nicht einen
fehlgeschlagenen GET. Pflichtfelder, Teilbelege und Fehlcodes bleiben getrennt.

| Position | V2-Einstand: tatsächlicher Grund | V2-Produktfrist: tatsächlicher Grund | Einordnung und zuständiger Owner |
| --- | --- | --- | --- |
| P01 | `NO_CONFIRMED_SAVED_QUOTE_SOURCE`; `PRODUCT_REVIEW_UNIT_UNPROVEN`; `REVIEW_CURRENT_PRODUCT_UNIT_CURRENCY_MISMATCH` | `PRODUCT_EXIT_LISTING_MISSING`; `PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING`; `PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE`; `PRODUCT_DEADLINE_PROVENANCE_MISSING` | Nicht auswertbar. Market Data: keine bestätigte Route. Product: Einheit nicht ausreichend belegt; der breite Mismatchcode beweist für sich keinen echten Währungswiderspruch. Persönliche Exitwahl und Terminoriginal fehlen. |
| P02 | `REVIEW_BID_MISSING`; `REVIEW_PRICE_SUPPLY_INTERRUPTED` | Dieselben vier Fristcodes wie P01 | Nicht auswertbar. JPMorgan-Route/Identität bestätigt; kein verwendbarer Bid. Transport-/Parsing-/Quellleere sind mit diesem Export nicht abschließend getrennt. Product/Market Data liefern bereits eine begrenzte V2-Einheits-/Kalenderbasis; historische Kontinuität bleibt dabei eine ausgewiesene Annahme. |
| P03 | Dieselben drei Einstandscodes wie P01 | Dieselben vier Fristcodes wie P01 | Nicht auswertbar. Fehlende Quellenbindung und Produkteinheit; kein unabhängig belegter Währungsfehler. Exitwahl und Terminoriginal fehlen. |
| P04 | `NO_CONFIRMED_SAVED_QUOTE_SOURCE`; `PRODUCT_DOCUMENT_UNDERLYING_MISMATCH`; `PRODUCT_REVIEW_UNIT_UNPROVEN`; `REVIEW_REFERENCE_CALENDAR_NOT_COVERED` | Die vier gemeinsamen Fristcodes plus `PRODUCT_DOCUMENT_UNDERLYING_MISMATCH` | Nicht auswertbar. Zusätzlich Produkt-/Basiswertkonflikt und fehlende Reviewkalenderabdeckung. Originalextraktion, Stammdatenbindung und Dokumentzuordnung müssen beim Product-Owner verglichen werden, bevor eine Korrekturrichtung feststeht. |

**Gemeinsame belegte Teilversorgung:** vier vorhandene wirtschaftliche
Ausführungsbasen und vier belegte historische Kaufwährungen. Dokumentbeschaffung
meldet für alle vier `AVAILABLE` ohne aktuelle Beschaffungsprobleme; das ist
kein Nachweis einer verwendbaren Stückeinheit, korrekten Basiswertbindung,
eines letzten Handelstags oder einer vollständigen Produkthistorie.

**Folgefehler nicht als zusätzliche Ursachen zählen:** Der Code
`REVIEW_CURRENT_PRODUCT_UNIT_CURRENCY_MISMATCH` entsteht bereits, wenn
`current.unit != CURRENCY_PER_WARRANT` oder die Produktwährung fehlt.
P01/P03 dürfen damit nicht ungeprüft durch Änderung ihrer Kaufwährung
„repariert“ werden. Ebenso bedeutet
`EXECUTION_OR_BID_CURRENCY_MISSING` im strengen Vergleich hier nicht, dass
die gesondert nachgewiesene historische Kaufwährung fehlt: schon ein
fehlender Quote oder Bidpreis blockiert diesen Check. Bei P02 ist die
Währung vorhanden; der Bidpreis fehlt.

Code: [V2-Eingänge](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py),
Z.410–438; [strenger Währungscheck](../../backend/app/features/position_monitoring/service/hebeltrader_original_bid_checks.py),
Z.236–249; [Product-Originalvergleich](../../backend/app/features/product/service/review_evidence.py),
Z.114–115 und 323–329. Für P04 enthält der Export nicht die beiden dort
verglichenen ISIN-Werte und keine Originalbytes/Parserfassung. Ein echter
Konfliktcode ist belegt, die richtige Stammdatenänderung daraus noch nicht.

Die aktiven Datenproblemepisoden bestätigen die fortbestehenden Sperren.
Eine frühere P02-Datenepisode wurde mit `INDICATIVE_PRICE_AVAILABLE`
geschlossen; dies belegt ein früheres entsprechendes V2-Ergebnis, keinen
heutigen frischen Quote und keine unveränderte heutige Quellenqualität.
Bestehende Preisepisoden dürfen bei fehlenden Daten nicht als Erholung
geschlossen werden; der Wiederanlauf braucht einen vergleichbaren
qualifizierten Preisbeleg.

## 3. P02: vollständige vorhandene Kette und verbleibende Informationslücke

Die gebundene Route lautet `JPMORGAN`, Listingklasse `ISSUER`, mit aktiver
und verifizierter Identität. Discovery und Quellenwahl sind vorhanden.
Der jüngste enthaltene Abrufversuch vom **22.11.2026, 20:46:35.873 bis
20:47:16.116 Uhr MEZ** ist `INSUFFICIENT`; seine Zusammenfassung lautet
`QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY`. Der gespeicherte
Consumerbestand enthält weder Bid noch Ask noch Originalkurszeit.

Der Provider setzt diesen Zeitstempelhinweis für seinen Streammodus
standardmäßig. Der Parser bildet außerdem JSON-`null`, leere Zeichenfolgen
und den numerischen Wert `0` auf fehlende Preise ab. Deshalb erklärt die sichtbare
Zeitstempelmeldung nicht, warum hier der Bid fehlt. Auch das Fehlen eines
`refresh_error` in dieser Versuchszusammenfassung beweist keinen erfolgreichen
Transport: der Resolver übergibt im `INSUFFICIENT`-Zweig bei fehlendem Bid
weder den konkreten Retention-/Refreshfehler noch dessen vollständigen Kontext.
Ein vorhandener allgemeiner Providerhinweis kann den entscheidenden
Fehler überdecken.

Die regelbezogene Unterbrechung ist eigenständig begründet: V2 berücksichtigt
bei vorhandener Route das gespeicherte Status-/Lückenjournal. Eine jüngere
Lücke wird zur Sperre, sofern es sich nicht lediglich um
`ORIGINAL_MARKET_STATUS_NOT_DELIVERED` handelt. Der Export liefert
`REVIEW_PRICE_SUPPLY_INTERRUPTED`, aber nicht den konkreten
`latest_gap.reason`. Diese Information kann in der vorhandenen Datenbank
stehen; ihr Fehlen im Export ist keine fehlende Quelldatei und kein Beweis
für ein leeres Journal.

### Engste noch fehlende passive Ergänzung

Nur für die bereits bestätigte P02-Route:

1. `RiskMarketDataReader.saved_quote(...)` und `MarketStatusReader.read(...)`
   mit vollständiger bestehender
   `StatusRouteBinding`, `event_at`/`known_at` in UTC, in einer ausdrücklich
   `REPEATABLE READ READ ONLY`-Transaktion mit `autoflush=False` lesen.
   `latest_gap` samt `reason`, `captured_at`, `retrieved_at` und
   `latest_capture`/Identitätsbindung erhalten.
2. Die schon gespeicherte konkrete `IndicativeEntryAssessmentModel`-Zeile
   über ihre private Assessment-ID lesen und
   `inputs.status_observations`/zugehörige Quelleninputs dem damaligen
   Bewertungszeitpunkt zuordnen. Der heutige Journalhead darf einen alten
   Assessmentgrund nicht rückwirkend überschreiben.
3. Beide Fakten privat mit dem bereits gelieferten Paket verbinden.
   Anschließend Rollback; kein Refresh, neuer Regellauf oder Quellenaufruf.

Der vollständige Export wurde rekursiv auf diese Information geprüft:
`source`, Episoden, Original-BID-Reader, beide Inventare und passende
Refreshjobs enthalten den konkreten Gap nicht. Fehler anderer Produkte im
Refreshinventar dürfen nicht P02 zugeschrieben werden. Ein erneuter
unveränderter Lauf des bisherigen Collectors würde diese Informationslücke
nicht schließen. Der nächste Ownerauftrag ist im Backlog auf genau diesen
bestehenden Pfad und eine daraus belegbar abgeleitete Korrektur begrenzt.

### Zeitqualität für eine mögliche Wiederaufnahme

Die JPMorgan-V2-Ausnahme mit unbekannter Originalzeit verlangt einen
**tatsächlichen Empfang höchstens 300 Sekunden vor der Bewertung**; die
Inventargrenze von 3.600 Sekunden ist nicht diese Regelgrenze. Der gespeicherte
leere Quote wurde bereits am 21.11. empfangen. Ein nachträglich eingesetzter
Preis oder eine neue Abrufzeit macht ihn nicht frisch. Der fehlende Bid
beendet die Prüfung vor der Altersentscheidung; das Fehlen eines
`TOO_OLD`-Codes ist daher kein Frischenachweis.

Ein neuer positiver Bid kann die V2-Abdeckung verbessern, wenn Identität,
Listing, Währung, Stückeinheit, zugelassener Quellenmodus, tatsächliche
Empfangsfrische und Freiheit von wirksamen neueren Versorgungslücken
zusammenpassen. Das belegt weiterhin weder Originalzeit noch B58-OPEN.
Eine Verbesserung von null auf eine auswertbare Position ist ein prüfbares
Ziel, kein aus diesem Paket zugesichertes Ergebnis.

| Stufe | Codebeleg im installierten Commit |
| --- | --- |
| Lightstreamer-Felder und Dekodierung | [stream.py](../../backend/app/providers/jpmorgan/stream.py), Z.18–19, 33–79, 83–229: `bid`, `bidsize`, `ask`, `asksize`, `quotetime`; kein verwendetes Originaldatums-/Zeitzonen-/Statusfeld. |
| Preisnormalisierung und allgemeiner Zeitstempelhinweis | [adapter.py](../../backend/app/providers/jpmorgan/adapter.py), Z.30–69, 100–119. |
| Retention und getrennte Lückenbeobachtung | [retained_quotes.py](../../backend/app/features/market_data/service/retained_quotes.py), Z.75–124, 164–181, 196–211. |
| Verlust des spezifischen Fehlers im Versuchsergebnis | [quote_sources.py](../../backend/app/features/position_monitoring/service/quote_sources.py), Z.233–251. |
| Gespeicherter Quote und begrenzter Statusblick | [risk_read.py](../../backend/app/features/market_data/service/risk_read.py), Z.55–216; [Original-BID-Reader](../../backend/app/features/position_monitoring/service/hebeltrader_original_bid.py), Z.129–135. |
| V2-Preis-/Zeit-/Unterbrechungsprüfung | [indicative_entry.py](../../backend/app/features/position_monitoring/domain/indicative_entry.py), Z.55–114; [indicative_entry_inputs.py](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py), Z.449–461. |
| Vorhandene passive Ergänzung | [MarketStatusReader](../../backend/app/features/market_data/service/status_observations.py), Z.178–282; [Assessment-Persistenz](../../backend/app/features/position_monitoring/persistence/indicative_entry.py), Feld `inputs`. |

## 4. Strenge Regeln und historische Anforderungen

| Daten-/Regelbereich | Tatsächlicher Nachweis | Fehlender oder ungeeigneter Teil |
| --- | --- | --- |
| Ausführungen und historische Kaufwährung | 4/4 vorhanden; wirtschaftliche Basis und historische Währung im Trade-Evidence-Read `PRESENT` | Keine Neuerfassung anhand heutiger Stammdaten nötig. Historische Produkteinheit ist davon getrennt. |
| B04/B57-Aktivierung | 4/4 `NOT_ACTIVATED`, null Bewertungen/Episoden | Eigener strenger Umfang deaktiviert; Produktionskatalog qualifizierter B58-Quellen weiterhin leer. |
| Original-BID und Preisvergleich | 0/4 qualifizierter Bid; P02 hat bestätigte Instrumentbindung | Preis, Bidwährung, Originaldatum/-zeit/-zone und Alter ≤900 s sind nicht gemeinsam belegt. Bei den übrigen drei fehlt schon die bestätigte Route. |
| Strenger Produktmaßstab | 0/4 dokumentierter historischer Maßstab | Originalbedingungen/Anpassungen mit Gültigkeit über alle beitragenden Käufe und den Bid. V2-Kontinuitätsannahme von P02 ersetzt dies nicht. |
| Produktsitzung und Basiswertsitzungen | Keine vollständige strenge Sitzungsevidenz je Position | Belegte Produktsitzung an Bid- und Auswertungszeit sowie mindestens 20 schon zur Bidzeit abgeschlossene Basiswertsitzungen. Der V2-Reviewkalender ist ein anderer Teilbeleg. |
| Instrumentstatus B58 | 0/4 qualifizierte Versorgung nachgewiesen | Eigene Statuszeit, Statusgeltung zur Bewertung und freigegebene Semantik fehlen im Nachweis. Der passive Original-BID-Reader liest nicht das ganze unabhängige Statusjournal; „Journal leer“ wäre unbelegt. |
| B06 / F207-2 | Vorhandene Tageshistorien bei drei Positionen; vier Zielreader ohne Assessment | Keine qualifizierte historische Kurs-/Listing-/Maßstabsversorgung; ursprüngliche Ziele, Zieltreffer und persönlicher Basiswerteinstieg sind nicht vollständig belegt. Vollständiger Folgestop hat zusätzlich offene Implementierungsanteile. |
| Produktfristen / B05/B20 | Produktoriginale beschafft; alle vier Fristassessments verfügbar, aber `UNAVAILABLE` | Persönliche Exitlistingwahl, letzter Handelstag mit Originalprovenienz, geeignete Kalenderabdeckung und produktspezifischer Schluss. Eine Beleganzeige zum Produktende ersetzt diese Felder nicht. |

Der strenge Produktkalender ist bei P02 konkret nicht vorhanden. Bei
P01/P03/P04 wurde er wegen der fehlenden Route nicht abgefragt; dort bleibt
sein Bestand unbestimmt. Der Basiswert-Sitzungsbeleg fehlt dagegen im
zugehörigen Read bei allen vier. In der Fristprüfung ist `calculation=null`:
die nachgelagerte Fristkalenderprüfung wurde wegen der vorgelagerten
Produkt-/Listinglücken noch nicht erreicht.

Strenge Code-/Vertragsbelege: [Produktionsregistry](../../backend/app/features/position_monitoring/service/hebeltrader_b58_sources.py),
Z.46; [gesonderter Statusjournal-Read des B04-Commands](../../backend/app/features/position_monitoring/service/hebeltrader_loss.py),
Z.191–204; [B06-Abdeckung](../../backend/app/features/trade_position/service/hebeltrader_coverage.py),
Z.313–422 und 510–605; [Zielhistorien-Reader](../../backend/app/features/position_monitoring/service/hebeltrader_targets.py),
Z.135–186. Der [Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md)
begrenzt F207-2 ausdrücklich auf Zielhistorie und Prüfgrundlage und erhält
den darüber hinausgehenden B06-/F207-5-Umfang.

Bei den drei vorhandenen Tageshistorien sind Anpassungsindizien sichtbar.
Eine Abweichung von `adjusted_close` und `close` oder ein Warntext beweist
keinen bestimmten Split. Ohne konkrete historische Quell- und
Anpassungsbelege wird weder die Reihe noch ein Schutzboden nachträglich
qualifiziert. Fehlende B06-Grundevidenz bleibt von fehlender Umsetzung
weiterer Folgestopbestandteile getrennt.

Der Sonntag erklärt, weshalb aus diesem Snapshot keine laufende
Handelbarkeit folgt. Er erklärt nicht automatisch fehlende Quellenbindungen,
Originalbedingungen, persönliche Exitentscheidungen oder historische
Belege. Insbesondere steht hier kein ausdrücklich belegter
`OUTSIDE_DOCUMENTED_PRODUCT_SESSION` als gemeinsame Ursache.

## 5. Was v1.5.52 nun tatsächlich belegt

Installation, Schema und nachfolgender regulärer V2-Zyklus sind bestätigt.
Alle vier Fristassessments enthalten getrennte `product_end_on` und
`payment_on`; das Produktende liegt jeweils vor dem Zahlungstag und
`current_terms_date_role=PAYMENT`. Der früher beschriebene falsche Vergleich
von Produktende und Zahlungstag (`PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH`)
steht in keiner aktuellen gespeicherten Reasonliste. Das ist eine
beobachtete Veränderung am Verbraucher; die übrig gebliebenen Sperren sind
oben einzeln ausgewiesen. Keine der vier Positionen ist deshalb bereits
vollständig auswertbar.

Der Export enthält jedoch nicht den aktuellen vollständigen KID-Head mit
Parserversion und Originalhash sowie die frühere private Vergleichsrevision.
Daraus folgt kein Nachweis, dass exakt eine v2-Folgerevision aus denselben
Originalbytes erzeugt wurde, und keine vollständige Abnahme der
Idempotenz/des Originalupgrades am PC. Die frühere Diagnose mit vier
Positionen hat ebenfalls keine hier vorliegenden privaten IDs; identische
Positionsanzahl beweist keine identischen Produkte über beide Zeitpunkte.

Auch ein bereitgestellter oder teilweise nutzbarer Reviewkalender beweist
keinen bestimmten lokalen XSTU-Originalimport. Aktuelle Kalenderwirkung,
Originalrevision, Herkunft und historische Importoperation sind getrennte
Aussagen. Der [ausgelieferte Fix](../releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md)
wird weder neu implementiert noch erneut als unveröffentlicht eingeplant.

## 6. Fehlende Information → Versorgung → bestehender Owner → Regel

| Konkrete Lücke | Praktischer Weg | Bestehender Owner / Komponente | Erwartete Verbesserung und Grenze |
| --- | --- | --- | --- |
| Drei unbestätigte Kursrouten | Tatsächliches Produkt und Listing gegen vorhandene öffentliche Emittenten-/Börsenwege prüfen; erst identitäts- und feldgeprüfte Route auswählen | Market Data: Discovery, Mapping, Quellenauswahl, gespeicherte Quote | Bidversorgung für P01/P03/P04 vorbereiten; Produkt-/Kalenderprobleme bleiben gesondert. Konfiguration eines Providers beweist keine Positionsdeckung. |
| P02 ohne verwendbaren Bid und mit Versorgungslücke | Vorhandenen Journalgrund und gespeicherte Assessmentinputs passiv lesen; danach exakt belegten Quell-/Parser-/Resolverfehler derselben Route behandeln | `MarketStatusReader`, `IndicativeEntryAssessmentModel`, `RetainedWarrantQuoteProvider`, `quote_sources`, vorhandener JPMorgan-Adapter | Eindeutige Ursachenklärung; bei tatsächlich qualifiziertem neuem Bid mögliche V2-Abdeckung. Kein künstlicher Zeitstempel und keine zugesagte B58-Freigabe. |
| P01/P03 ohne hinreichenden Einheitennachweis | Vorhandenes KID/Endgültige Bedingungen beim Product-Owner mit Parsergebnis für Einheit/Währung vergleichen; fehlende Originalfelder gezielt ergänzen | `ProductReviewEvidenceReader`, vorhandener Dokumentparser, `ProductPriceScaleEvidenceReader` | Vergleichbare aktuelle V2-Einheit; historische Kontinuität für strenge Regeln zusätzlich belegen. Keine ungeprüfte Währungsänderung. |
| P04 Produkt-/Basiswertkonflikt | Genau die extrahierte und die gebundene Basiswertidentität gegen das Produktoriginal lesen; danach die nachgewiesene falsche Extraktion oder Bindung korrigieren | Product/Market, `review_evidence` | Konflikt eindeutig dem richtigen Owner zuordnen; Namensähnlichkeit genügt nicht. |
| Produktfristen aller vier | Persönliches Exitlisting konkret auswählen; dessen letzten Handelstag und individuellen Schluss aus Produkt-/Listingoriginal belegen | Product: `deadline_choice`, `deadline_listing_terms`; Market Data: Kalender | V2-Fristreview und später B05/B20; Zustimmung zur persönlichen Exitwahl nicht aus einem Kurslisting ableiten. |
| Review-/strenge Kalenderlücken | Passende offizielle Kalender, benötigte Jahre und jeweilige Sitzungspräzision importieren/qualifizieren | `ReviewCalendarReader`, Sitzungsevidenz beim Market-Data-Owner | V2-Tageszählung von strenger zeitgenauer B58-Sitzung getrennt erfüllen. |
| B58-Status und Originalzeiten | Listinggenauen Feed mit dokumentierten Originalfeldern/Gültigkeit und passendem Nutzungsrecht qualifizieren | Vorhandener Provideradapter, Statusjournal und Quellenqualifikationskatalog | Strenger Input; weder zweiter gleicher Webseitenpreis noch allgemeiner Börsenkalender ersetzt Instrumentstatus. |
| B06-Historie | Eigene ursprüngliche Ziel-/Basiswerttradebelege und qualifizierte historische Preis-/Anpassungsreihe beschaffen | Trade Position, Market Data, Monitoring/F207-2 | Historische Grundlage herstellen; noch offene Folgestopverarbeitung ausdrücklich getrennt umsetzen. |

Die [Quellen-/Kostenübersicht für neun Emittenten](ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md)
bleibt der datierte Angebotsnachweis vom 20.11.2026. Kostenlose Ansichten,
erlaubte automatische Nutzung, tatsächliche Produktlieferung und technische
Integration bleiben unterschiedliche Nachweisstufen. Dieses Paket macht
keinen kostenpflichtigen Feed zur Voraussetzung: zuerst bestehende Fakten
und die vorhandene bestätigte Route nutzen, öffentliche geeignete
Alternativen anhand der wirklichen Produkte prüfen.

Für JPMorgan wurden am 22.11.2026 die [offiziellen Nutzungsbedingungen](https://www.jpmorgan-zertifikate.de/nutzungsbedingungen/)
(Seitenstand 03.01.2025, Abschnitte 6/15) erneut gelesen. Sie enthalten
Beschränkungen für Kopie/Caching und lassen gesonderte Verträge unberührt.
Das Diagnosepaket belegt keine zusätzliche Vereinbarung für einen neuen
isolierten Direktabruf. Deshalb wurde bei dieser Auswertung kein neuer
Stream gestartet; bestehende PC-Einstellungen und frühere Zustimmungen
wurden nicht geändert oder zurückgenommen. Für den nächsten passiven
Journalread ist kein neuer Anbieterzugang erforderlich.

## 7. Private Primärbelege und Reproduzierbarkeit

| Beleg | Integritätsbindung | Technische Zugriffsstelle |
| --- | --- | --- |
| Hochgeladenes Archiv, 129.029 Bytes | SHA256 `ea4ee60cbd4d212ac97cf5b140f168d1f959bd2aac48cf344bb4b26839ce73ab` | Genau fünf reguläre JSON-Dateien, keine Links/ausführbaren Archiveinträge; private Rohablage außerhalb Git. |
| `installation-before.json` = `installation-after.json` | Je SHA256 `43d30dc4e02f950749ede5d4935ed3d98f5472488d8285943e419b5363a8cd59` | `/commit`, `/version`, `/containers`, `/scope`; selektive Bindungsprüfung, kein vollständiger Konfigurationsaudit. |
| `schema.json` | SHA256 `bb304f6dc956594ed2ab7806a8d68a03841a1af6a2a86190926cc8724e4c83a6` | `/versions`, `/source`, `/read_only`, `/matches_reviewed_reference`. |
| `summary.json` | SHA256 `11924c4a0a3e2ba90c9b722fe22c2415ee04e8a526cbcd0627bf4cd397cbd811` | Zeitfenster, Payloadhash, drei getrennte Transportkriterien; kein Regelergebnis. |
| `monitoring-private.json`, 1.666.839 Bytes | SHA256 `e10a1b814ed00850c1d03b1694d8c6458797280a3fa5c3b5dd8427bde0e8b8ed` | Die folgenden JSON-Pointer; Datei bleibt privat. |

### Lesepfade im privaten Monitoringbeleg

- `/runtime_before/body/last_result` und `/runtime_after/body/last_result`:
  getrennte V2-/Frist-/technische Zähler; Zykluszeiten in denselben Bodies.
- `/inventory_before/body/summary` und `/inventory_after/body/summary`:
  vier offene, eine gebundene/verifizierte, drei `missing_source`, eine
  `missing_quote`; keine Bestandsannahme aus den historischen 6/6-Zahlen.
- `/positions/0` bis `/positions/3` entsprechen P01 bis P04.
  `reads/indicative-entry/body/latest_assessment` und
  `reads/product-deadline-review/body/latest_assessment` enthalten die
  unveränderten Gründe und eigenen Zeit-/Versionsbezüge.
- `reads/indicative-entry/body/document_readiness` sowie
  `active_episodes`/`recent_episodes`: Beschaffungsstatus und dauerhaft
  gespeicherte Datenprobleme, keine neue Beschaffung beim GET.
- `reads/hebeltrader-original-bid/body`: `economic_basis`, `saved_quote`,
  `bid`, `product_price_scale`, `live_market_status`, `product_sessions`,
  `underlying_sessions`, `checks`.
- `reads/hebeltrader-loss/body`: Aktivierung, Quellenqualifikationsreferenzen,
  null Bewertungen/Episoden; nicht mit einem unauffälligen Verlusttest verwechseln.
- `reads/hebeltrader-targets/body` und
  `reads/hebeltrader-evidence/body`: beide B06-Pflichtreads; vorhandene
  Tagesdaten, Qualifikationslücken, tatsächliche Ausführungsbeiträge und
  historische Ziel-/Basiswerteinstiegsbelege getrennt auswerten.

Dieser öffentliche Bericht genügt zur Prüfung der Schlussfolgerungen und
Codezuständigkeiten. Eine unabhängige Nachrechnung personenbezogener
Einzelwerte benötigt den ausdrücklich privaten Rohbeleg; sie wird nicht
als öffentlich reproduzierbar behauptet.

## 8. Prüfung dieser Fortschreibung

Die fünf Originaldateien wurden unverändert und mit restriktiven
Dateirechten außerhalb des Checkouts abgelegt. Inventar, Readanzahl,
Identitätsbindungen, gespeicherte Gründe und zeitliche Grenzen wurden mit
den tatsächlichen Reader-/Domain-/Persistenzpfaden abgeglichen. Die drei
getrennten Gegenprüfungen betrafen V2/Fristen, strenge Regeln/B06 sowie
Betrieb/Quellenweg. Es gab keinen PC-Schreibzugriff, aktiven Kursabruf,
Regellauf, neue Anbieterzustimmung oder Nachrichtenversand.

Der erste Readbackschnitt ändert Fach-/Betriebsnachweise und den maßgeblichen Backlog,
keinen Anwendungscode oder Regelvertrag. Relative Links/Anker, Markdown-Struktur, Whitespace, unveränderte
historische Roadmap und private Kennungen im neuen Diff wurden geprüft.
Der Abgleich des öffentlichen neuen Textes gegen die Kennungen und
Instrumentbezüge des privaten Archivs ergab keine Treffer. Frühere 19 Collectortests
bleiben an ihren eigenen Code gebunden; sie sind kein zusätzlicher
Anwendungstest dieses Dokumentationsschnitts.

<a id="p02-fortsetzung-20261122"></a>
## 9. Fortsetzung: spezifische Fehlerweitergabe und gezielter Ownerread

Auf den anschließenden Auftrag „nächster Schritt“ wurde derselbe
P02-Schnitt technisch fortgesetzt. Bezugsstand vor dieser Änderung ist
PR370-Commit `8accaebef864cf8a7cb61d9dc3aa31b0ab9f6c15`; Main zu Beginn
war `febeb922c0f337029baa7f9d792c37f9f72ba02b` / v1.5.53.
Während der Prüfung kam PR373 als
`9a5e59dac3bb219cbc40641e62e75871eb2ed131` / v1.5.54 hinzu
(22.11.2026, 21:35:28 Uhr MEZ). Sein gesamtes Delta wurde geprüft:
Versions-/Liefermetadaten und Dokumentation, kein geänderter Backendpfad.
Die Lieferänderungen werden im PR erhalten.
Der in Abschnitt1 belegte PC bleibt unabhängig davon v1.5.52/c7db441… .
Die folgenden lokalen Implementierungsnachweise verändern keinen der
historischen PC-Befunde oben. Der maßgebliche Aufgabenstatus steht weiterhin
ausschließlich im [Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

### Erhaltene Diagnose bis zum Verbraucher

Der vorhandene [Resolver](../../backend/app/features/position_monitoring/service/quote_sources.py)
erhält jetzt bei `INSUFFICIENT` den konkreten Abruffehler, die Währung und
die getrennten Felder `retained`, `provider_reason`, `quote_time_basis`.
Bei gültiger Datenqualität ohne Bid und ohne Referenzpreis wird
`BID_MISSING` primär; die unbekannte Originalzeit bleibt gesondert sichtbar.
Bei ungültiger Qualität bleibt dagegen der bisherige Qualitätsfehler
maßgeblich, auch wenn zusätzlich der Bid fehlt. Die
[DTO](../../backend/app/features/position_monitoring/api/dtos.py),
[API-Projektion](../../backend/app/features/position_monitoring/api/router.py)
und der [Frontendtyp](../../frontend/src/features/trade/types/api.ts)
führen die Felder additiv weiter.

Im bestehenden Legacy-Single-Source-Zweig des Bewertungslesers mit genau
einem Listing und Versuch bedeutet dies `MISSING` für das gültige, aber
preislose Ergebnis; Qualitätsfehler bleiben dort `ERROR`. Der normale
Resolververbraucher aggregiert `INSUFFICIENT` dagegen weiterhin als
`MISSING`, einschließlich solcher Qualitätsfälle, und erhält deren
spezifischen Grund im Versuch. Preis und Monitoring-/Ausführungsfreigabe
bleiben in den beschriebenen preislosen Fällen aus. Ein vorhandener
spezifischer Abruffehler erreicht außerdem die bisherige Refreshdiagnostik,
deren Klassifikation ihn bereits vor allgemeinen Hinweisen priorisiert.
Positive Bids, vorhandene Referenzpreise, Auswahlbindung, Regelaktivierung
und Altersgrenzen wurden nicht geändert. Der Fix beschafft keinen Preis.

### Gezielt lesender Helfer für den bereits installierten Stand

Der [bestehende Collector](../../scripts/collect-depot-data-supply.py) erhält
`--source-gap-from ARCHIV --position-label P02`. Der alte Standardaufruf
bleibt erhalten. Seine bisherigen GET- und Schema-Payloads bleiben
byteidentisch:

| Payload | SHA256 |
| --- | --- |
| Bisherige GET-Sammlung | `b8dee0cd47ccd95a224cf5897eb60233d3195bf9d76700a103acfcfbc5dbafab` |
| Bisheriger Schemaread | `7aba0ec505ed0c1bebbf190faa8c09c888bb1d78a8c3a22db2b2d4c1602f783d` |
| Neuer gezielter Ownerread | `56123ebd72cb83621f706bf13ee2d9a46dc05e54559f8ce51b7b9cf3038134dd` |

Der neue Modus verwendet die im Originalarchiv gebundene Position samt
Produkt, Listing, Auswahl und Bewertung; keinerlei private Kennungen sind
im Helfer oder in seinen Tests festgeschrieben.

Die Hostprüfung liest das begrenzte Archiv nur im Speicher. Der neue
Backendread verwendet die vorhandenen Owner `OpenPositionReader`,
`RiskMarketDataReader`, `MarketStatusReader` und
`IndicativeEntryAssessmentModel` in einer ausdrücklich geprüften
`REPEATABLE READ READ ONLY`-Transaktion. Er nimmt den aktuellen Journalstand
und die tatsächlich gespeicherten damaligen Assessmentinputs getrennt auf.
`autoflush=False`, Statement-/Lock-/Verbindungslimits, explizites SQL-Rollback
und begrenzte Fehlercodes gelten auf Erfolgs- und Fehlerpfaden. Die
Installationsbindung wird vorher/nachher geprüft, Datenbankzugangsdaten
verbleiben im bestehenden Backend.

Das ist kein zusätzlicher Providerzugang und benötigt kein App-Update.
Eine geänderte Produkt-/Quellen-/Auswahlbindung wird als Diagnosefehler
ausgegeben. Ein fehlender Journaldatensatz ist ein ausdrücklicher Befund,
keine behauptete Wiederherstellung. Der Erfolgsstatus
`COMPLETE_PASSIVE_SOURCE_GAP_READ_NOT_PRICE_QUALIFICATION` beschreibt
ausschließlich den vollständigen gebundenen Lesevorgang.
[Ausführung und private Artefakte](../technical/ISSUER_MONITORING_OPERATIONS.md#gezielter-p02-journalread).

### Prüfungen und Grenzen der Fortsetzung

Die isolierte Qualifikation verwendet Python3.12 und unveränderte
`backend/requirements-dev.txt`. Zwei neue Resolverregressionen scheiterten
vor dem Fix am allgemeinen Zeitstempelgrund statt `BID_MISSING`. Die
anschließenden gezielten Prüfungen erfassen fehlenden Bid mit/ohne
Retentionfehler, tatsächliche Qualitätsfehler mit/ohne Bid, Referenzpreise,
positive Retention, Refreshdiagnostik und den ASGI-/DTO-/Bewertungsleser.

| Prüfung | Ergebnis und Grenze |
| --- | --- |
| Gezielte Resolver-/API-/Bewertungs- und Collectortests | **77 bestanden**, zusätzlich 43 erfolgreiche Unterfälle; davon 43 Resolver-/API-/Valuationtests sowie 19 bisherige und 15 neue Collectortests. Eine bestehende Starlette-/AnyIO-Deprecationwarnung. |
| Unabhängiger Code-/Testreview | Keine offenen Blocker; 34 Collectortests erneut ausgeführt, Logging, stdin und umask nach Testende unverändert. Tatsächliche Ownerimports/ORM-Konfiguration und PostgreSQL-SELECT-Kompilierung ohne Netzwerk erfolgreich. |
| Backend-Typprüfung | `mypy app`: **670 Quelldateien ohne Fehler**. |
| Backend-Stilprüfung | Ruff und Black gegen die Projektkonfiguration erfolgreich; Black prüft 1.228 App-/Testdateien. Für den eigenständigen Hostcollector gilt zusätzlich das Python3.10-Ziel. |
| Frontend | Vollständiges `npm run typecheck` und Prettier für den geänderten API-Typ erfolgreich. Unveränderte Lockdatei mit `npm ci` verwendet. |
| Gesamter lokaler Backendlauf mit Coverage | **5.935 bestanden, 290 übersprungen, 44 fehlgeschlagen, 64 Setupfehler**, zusätzlich 43 bestandene Unterfälle; 12 min 38,78 s. Coverage **86,06 %** bei geforderten 85 %. Wegen der folgenden Umgebungsgrenzen ausdrücklich **kein grünes Gesamtgate**. |
| Ursachen der lokalen Gatefehler | 64 Setupfehler ohne PostgreSQL-Testdatenbank; zwei HTTPX-Clientkonstruktionen wegen geerbtem SOCKS-Proxy ohne optionales `socksio`; 42 unveränderte Recoverytests am vorhandenen Schutz gegen private Zustände unter Git-Vorfahren. Der lokal verfügbare Tempbereich erfüllt diesen Schutzvertrag nicht. Kein Guard wurde gelockert. |
| Enge Gegenprobe der HTTPX-Fälle | Beide scheitern auch isoliert ohne neue Collectortests identisch. In einem separaten Prozess ohne Proxyvariablen, bei blockierten Socketverbindungen: zuerst 15 neue Collectortests, danach beide ursprünglichen Fälle, **17 bestanden** und 33 bestandene Unterfälle. Keine aktiven Requests. |
| Private Kennungen / Dokumente | Neue öffentliche Texte und Tests gegen 719 Kennungen/Instrumentbezüge aus dem privaten Beleg geprüft: keine Treffer. Relative Verweise/Anker, Markdown-Struktur und Whitespace geprüft; historische Roadmap unverändert. |

Die Collectorprüfungen verwenden echte Backendtypen mit abgefangenen
Verbindungen und Ownerreads. Sie umfassen Archivgrenzen, Links/Traversal,
Duplikate, vertauschte Identitäten, veränderte Quellenbindung, getrennte
Assessmentheads, fehlende Quotes/leere Journale, Fehlerredaktion,
Transaktionseigenschaften, Rollback, Dateirechte und Installationswechsel.
Sie ersetzen keinen echten PostgreSQL- oder PC-Lauf.
Die Recovery-/Launcherpfade sind gegenüber dem Ausgangscommit unverändert.
Die regulären PR-Gates mit PostgreSQL und einem geeigneten privaten
Tempbereich bleiben vor einer späteren Integration erforderlich; lokale
Teilprüfungen und frühere grüne Heads ersetzen sie nicht.

Reproduzierbarer enger Testaufruf aus dem Repository mit den gepinnten
Entwicklungsabhängigkeiten und einem temporären Verzeichnis außerhalb Git:

```bash
PYTHONPATH=backend:. python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/test_collect_depot_data_supply.py \
  tests/unit/backend/test_collect_depot_source_gap.py \
  tests/unit/backend/features/position_monitoring/test_quote_sources.py \
  tests/unit/backend/features/position_monitoring/test_source_selection_api.py \
  tests/unit/backend/features/position_monitoring/test_product_valuation.py -q
```

Der Hostleser wurde außerdem direkt gegen das **unveränderte Originalarchiv**
mit SHA256 `ea4ee60cbd4d212ac97cf5b140f168d1f959bd2aac48cf344bb4b26839ce73ab`
ausgeführt: Archiv- und P02-Referenzprüfung erfolgreich, keine private
Identität im öffentlichen Ergebnis. Dies prüft die Kompatibilität mit dem
gelieferten Paket, keinen neuen Zugriff auf die PC-Datenbank.

Es gab weiterhin keinen direkten PC-Zugang, neuen Kursabruf oder
Regellauf. Der enge PC-Export und sein Originalgrund sind noch nicht
beobachtet. Eine Quellenreparatur, tatsächliche Verbesserung der
V2-Preisversorgung oder B58-Freigabe wird deshalb nicht behauptet.
