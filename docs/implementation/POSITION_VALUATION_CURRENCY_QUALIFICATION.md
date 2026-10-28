# Laufende Positionsbewertung — Währungsvertrag und Qualifikation

## Auftrag, Quellen und Abgrenzung

Der Auftrag vom 28.10.2026 verlangt, nicht realisiertes Brutto-PnL nur bei
belegter gleicher Währung von wirksamer Kaufkostenbasis und verwendeter Quote
als Geldbetrag auszugeben. Der enge Vertrag wird vor der Implementierung
festgehalten. Arbeitsstatus steht ausschließlich in den bestehenden Einträgen
[PB-016 Positionen](../planning/PRODUCT_BACKLOG.md#pb-016-positions),
[PB-017 Brutto-PnL](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) und
[Operational Workspace](../planning/PRODUCT_BACKLOG.md#operational-workspace).

Die neu geprüfte Ausgangsbasis ist `main`
**`dc89dfa65758dfc1258a8fab657257f6598b0179`**, Softwareversion **1.5.29**.
Die historische Reviewreferenz `f3c067ecdfe99e46f3c8b63c37bb4d283cd5a568` /
1.5.28 bleibt eine frühere Basis. [PR #295](https://github.com/burckhju/trading-workspace/pull/295)
ist inzwischen integriert: Head `36e846cf9bcdaeb47981328597cb05335fe83d1f`,
Merge `13e8d5331abab32d4998118e83aaecbc231dea31` am 28.10.2026.
Der anschließende [Release-PR #296](https://github.com/burckhju/trading-workspace/pull/296)
führt zum genannten Main-Stand. Lesson- und Schedulerkorrekturen bleiben als
Bestandteile dieser Basis erhalten; sie werden nicht erneut implementiert.
Die historischen Prüfergebnisse dieser PRs qualifizieren den neuen Fix nicht.

Fachliche Grundlagen sind der bestehende
[FT-010-Projektionsvertrag](../features/FT-010_TRADE_MANAGEMENT.md),
[ADR-S10-002](../decisions/ADR-S10-002-EFFECTIVE-EXECUTION-HISTORY-AND-POSITION-PROJECTION.md),
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
und dessen [Kaufwährungs-Wiederverwendung](EXECUTION_CURRENCY_REUSE_QUALIFICATION.md).
Die strengere Qualifikation der bestehenden Performanceberichte dient als
Referenz. Ihre Perioden-, Vollabschluss- und Kennzahlenverträge werden nicht
geändert. Der Nutzerauftrag entscheidet die Anwendung der vorhandenen
Kaufbasisqualifikation auf laufende Bewertungen ausdrücklich; dafür bleibt keine
neue Finanzregel offen. Insbesondere werden weder FIFO/Lots noch FX,
Gebühren, Steuern, Nettoergebnisse oder eine neue Modellfamilie ergänzt.

## Ausgangsbefund und Verantwortlichkeit

`ProductPositionValuationService` multipliziert den Produktkurs mit dem offenen
Bestand und zieht danach die numerische `position.cost_basis` ab. Die Währung
der tatsächlichen Kaufkosten wird dabei bisher nicht durch die vorhandenen
Ausführungsbelege qualifiziert. Das betrifft den älteren Evaluationpfad und den
Pfad mit ausdrücklich festgelegter Kursquelle sowie die Analysevariante.
Die Quote kann dadurch eine Geldwährung auf einen nicht belegten Kostenabzug
übertragen. Zehn Stück, Kostenbasis 20 und Quote 2,50 EUR ergeben rechnerisch
25 EUR Marktwert und 5 EUR Differenz, auch wenn eine monetäre EUR-Aussage für
diese Differenz fachlich nicht zulässig ist.

FT-009/010 bleibt der einzige Owner von Executions, Währungsbestätigungen und
Position. `PositionProjector` liefert weiterhin Menge und Kostenbasis aus der
vollständigen effektiven Historie; `resolve_execution_currencies` liefert die
Währungsherkunft. Die Bewertung ergänzt eine Qualifikation dieser vorhandenen
Ergebnisse. Sie führt keine zweite Kostenbasis-/PnL-Projektion ein. Backend und
Frontend dürfen fehlende Währungsbelege nicht aus Listing, Plan, Quote oder
zuletzt bekannter Kaufwährung ersetzen.

## Definition `position-unrealized-gross-v1`

### Wirksame Kaufkostenbasis

Für eine offene Position werden alle effektiven BUYs des Trades in der
bestehenden Reihenfolge `(executed_at, recorded_at, id)` qualifiziert.
Nachkäufe und wirksame wirtschaftliche Korrekturen gehen durch den bestehenden
Projektor ein. Teilverkäufe verändern verbleibende Menge und Durchschnittskosten
nach dem bestehenden Average-Cost-Vertrag; ihre Erlöswährungen sind kein
Kaufkostenbeleg. Frühere SELL-Executions bleiben wegen ihrer Mengenwirkung in
der Herkunft. Ein vollständiger Abschluss kann im selben Trade nicht durch
einen neuen BUY wieder geöffnet werden. Es gibt daher keine neue Lot-Auswahl,
die einzelne frühere BUY-Währungen aus der offenen Durchschnittskostenbasis
entfernen dürfte.

Der vorhandene Resolver verwendet unverändert:

1. die aktuelle direkte Bestätigung der konkreten Execution;
2. andernfalls den bestätigten gleichseitigen Vorgänger entlang der wirksamen
   Korrekturherkunft;
3. andernfalls den vollständig vorhergehenden effektiven BUY-Präfix, wenn alle
   dort benötigten Währungen bekannt und gleich sind.

Ein später bestätigter Kauf bestätigt keinen früheren unbekannten Kauf.
Eine ausdrückliche Abweichung bleibt erhalten. Konkrete Execution- und
Bestätigungs-IDs belegen direkte, wiederverwendete und ersetzte Herkunft.
Unwirksame historische Executions werden nicht als zusätzliche effektive
Kostenbestandteile gerechnet.

### Unabhängige Aussagequalitäten

Marktwert und nicht realisiertes Brutto-PnL besitzen getrennte Qualifikationen.
Die vorhandenen Quote-Felder, Statuswerte und Nutzbarkeitsregeln bleiben erhalten,
einschließlich aktueller, indikativer, veralteter und zuletzt verfügbarer Kurse.
Ein unabhängiger gültiger Marktwert bleibt bei fehlendem PnL verfügbar.

| Kaufkostenbasis gegenüber der verwendeten Quote | PnL-Aussage |
|---|---|
| Mindestens eine erforderliche Kaufwährung unbekannt | Fehlender Betrag; `COST_BASIS_CURRENCY_UNKNOWN` |
| Erforderliche Kaufbasis enthält unterschiedliche belegte Währungen | Fehlender Betrag; `COST_BASIS_CURRENCY_MIXED` |
| Vollständig belegte einheitliche Kaufwährung weicht von der Quote ab | Fehlender Betrag; `COST_BASIS_CURRENCY_MISMATCH` |
| Vollständig belegte einheitliche Kaufwährung entspricht der Quote, Quote für die jeweilige Variante nutzbar | Berechenbarer Betrag; `COST_BASIS_CURRENCY_MATCHED` |
| Weder für aktuelle Bewertung noch Analyse ist eine Quote nutzbar | Fehlender Betrag mit dem vorhandenen Kurs-/Bewertungsgrund |

Sind bereits unterschiedliche belegte Kaufwährungen vorhanden, hat `MIXED`
Vorrang vor einer zusätzlich vorhandenen unbekannten Komponente. Andernfalls
bleibt eine unvollständig belegte Basis `UNKNOWN`. Erst eine vollständig
bekannte einheitliche Kaufbasis kann gegenüber der Quote als passend oder
abweichend qualifiziert werden.

Wenn eine Quote zumindest für Analyse nutzbar ist, wird die Währungsgrundlage
beider PnL-Felder qualifiziert. Eine vorhandene Währungslücke bleibt dann deren
Grund; die unabhängige Kursbegrenzung bleibt in `reason`, `analysis_warning`
und den bisherigen Quote-Flags sichtbar. Bei passender Währung und nur für
Analyse nutzbarer Quote behält das fehlende aktuelle PnL den ursprünglichen
Kursgrund. Das ist eine Priorisierung der Erläuterung, keine Lockerung der
Frische- oder Nutzbarkeitsgrenzen.

Die API ergänzt `unrealized_pnl_usable` und `unrealized_pnl_reason` für
`unrealized_gross_pnl` sowie `analysis_unrealized_pnl_usable` und
`analysis_unrealized_pnl_reason` für `analysis_unrealized_gross_pnl`.
Ein fehlender Betrag wird als `null` übertragen. Ein qualifiziertes exakt
neutrales Ergebnis bleibt ein gemessener Nullbetrag. Ein Quote-Status wie
`AVAILABLE` allein berechtigt keinen Consumer, PnL als nutzbar zu behandeln.

### Gemeinsame Lesebasis und Herkunft

Vor der ersten Fachabfrage beginnt eine kurze, eigene PostgreSQL-Transaktion
mit `REPEATABLE READ READ ONLY`. Sie materialisiert Trade, Positionsidentität,
vollständige Execution-/Korrekturhistorie, aktuelle Währungsbelege sowie die
vorhandenen Listing- und Kursquellenbindungen. Aus diesem Stand verwenden
Projektor und Währungsresolver dieselben effektiven Fakten. Die Transaktion
endet vor dem vorhandenen Quote-Provider-/Resolveraufruf. Globale Isolation,
Command-Sperren und Capture-Verhalten bleiben unverändert.

Der additive `position_basis`-Kontext bindet `definition_version`, einen
deterministischen `basis_id`, die projektierte Position, effektive
Execution-IDs und die Währungsauflösung je benötigtem BUY einschließlich
Quell-Execution-/Bestätigungs-IDs. Kaufkostenwährung und deren
Qualifikationsstatus bleiben getrennt von der Quote-Währung. Quellen- und
Korrekturänderungen führen zu einem entsprechend anderen Basisbezug; der Hash
ist keine dauerhaft wiederherstellbare historische Berichtssitzung.

Die Depotantwort übernimmt Stückzahl und Kostenbasis dieser Bewertungsbasis.
Sie darf keine zuvor separat gelesene alte Position mit einer neueren
Bewertungs-/Währungsbasis kombinieren. Monitoring- und Alertinformationen
behalten ihre eigenen vorhandenen Lesebezüge; es wird kein globaler Snapshot
über fachfremde oder externe Daten behauptet. Kursherkunft, Preisbindung,
Zeitstempel, Mapping-/Auswahlversionen und Frischeinformationen bleiben erhalten.
Auch bei fehlendem Provider oder nicht verfügbarer festgelegter Kursquelle
bleibt die bereits materialisierte Positionsbasis in der Antwort erhalten.

Der Ablauf bleibt lesend: keine Bestätigung, kein Backfill, keine Änderung
historischer Buchungsfakten und kein zusätzlicher Provideraufruf zur vermeintlichen
Währungsreparatur. Die bestehenden erlaubten Quote-Lesewege bleiben bestehen.

## Consumervertrag

Depotzeile und Positionsdetails, Trade-Management und indikative Analysewerte
übernehmen ausschließlich das zur Variante gehörende qualifizierte PnL.
Fehlende Berechenbarkeit wird mit verständlichem Grund angezeigt. Gewinn- und
Verlustfilter, Vorzeichenfarbe und Geldsortierung behandeln einen solchen Wert
als fehlend. Fehlende Werte bleiben auch bei umgekehrter Sortierung zuletzt.
Die vorhandene Workspace-Aktionsliste nennt dieselbe Währungslücke; eine
indikativ nutzbare Quote begründet dort keine pauschale Zusage verfügbarer
PnL-Überwachung.

PnL-Summen und ihre Abdeckungszähler verwenden ausschließlich qualifizierte
PnL-Beiträge. Marktwertsummen und deren Abdeckung werden unabhängig weitergeführt.
Eine Position mit gültigem EUR-Marktwert und unqualifiziertem PnL erhöht die
Marktwertabdeckung, aber weder EUR-PnL-Summe noch PnL-Abdeckung. Bestehende
exakte Aggregation, Währungsgruppierung und Kursqualitäts-/Zeitangaben bleiben
erhalten. Keine neue Finanzberechnung ist im Frontend erforderlich.

## Vorab festgelegte Regressionen

Die folgenden Fälle sind Sollkriterien, noch keine bestandenen Prüfungen:

- Unbekannte Kaufwährung, bestätigter USD-BUY bei EUR-Quote sowie gemischte
  EUR-/USD-BUYs: Marktwert 25 EUR bei zehn Stück und Quote 2,50 EUR bleibt
  erhalten; beide PnL-Varianten fehlen mit verständlichem Grund.
- Vollständig belegtes EUR bei gleicher Quote: positiver, negativer und exakt
  neutraler Wert bleiben qualifiziert und unterscheiden sich von fehlend.
- Ein bestätigter Erstkauf qualifiziert zulässige Nachkäufe über den bestehenden
  Resolver; ein später bestätigter Kauf heilt keinen früheren unbekannten Kauf.
- Teilverkäufe sowie Preis-, Mengen-, Datums- und Währungskorrekturen verwenden
  effektive Historie, unveränderte Ownerarithmetik und genaue Herkunft. Eine
  abweichende frühere SELL-Erlöswährung vergiftet die verbleibenden Kaufkosten nicht.
- Evaluationpfad und festgelegte Kursquelle, indikative und zuletzt verfügbare
  Quotes sowie vorhandene Stale-/Missing-Grenzen bleiben ausdrücklich abgedeckt.
- Backend-/API-/UI-Nachweis bis zu Filtern, Sortierung, Farbe, Summen und
  getrennten Abdeckungszählern. Mindestens ein durchgängiger Fall belegt, dass
  ein unqualifiziertes PnL nicht zur EUR-Gewinnsumme beiträgt, während der
  gültige Marktwert sichtbar bleibt.
- Eine während des Lesens committed Ownerkorrektur erzeugt keine gemischte
  Antwort. Lesen erzeugt keine Bestätigungen und keine zusätzlichen externen
  Aufrufe zur Währungsreparatur.

Schreibende Prüfungen verwenden ausschließlich eindeutig identifizierte
Wegwerfumgebungen, synthetische Daten und abgefangene externe Aufrufe.
Python 3.12, Node 22.16.0 und npm 10.9.2 sowie die bestehenden Backend-,
Frontend-, Integrations- und Browsergates bleiben maßgeblich. Es werden keine
Coverage-Grenzen, Assertions oder Sicherheitsvoraussetzungen abgesenkt.
Fehler, Skips und nicht ausführbare Gates werden mit exaktem Commit-/Treebezug
getrennt von erfolgreichen Nachweisen ausgewiesen.

## Prüfbelege und Übergabegrenze

Die technische Ausführung und ihre exakten Commit-/Runbezüge werden nach den
tatsächlichen Prüfungen ergänzt. Bei Erstellung dieses Vertrags liegt noch
kein Rot-/Grün- oder Gesamtgatenachweis des neuen Fixes vor. Frühere grüne
Prüfungen der Ausgangsbasis sind kein Ersatz.

Der aktuelle Auftrag umfasst Implementierung, Tests, Dokumentation und einen
überprüfbaren Pull Request. Er erlaubt keinen Merge, Release, Tag, Deployment
oder Installation. Technische Reviewbereitschaft ist von menschlicher
Fachabnahme, Softwareauslieferung und beobachtetem Nutzerbetrieb getrennt.
Die Abdeckung realer Nutzerbestände wurde nicht geprüft oder verändert.
