# Historische Ausführungswährung aus belegten Quellen

## Ausgangspunkt und technische Ursache

Die Ursachenanalyse begann auf Main
`dc89dfa65758dfc1258a8fab657257f6598b0179` (v1.5.29).
Die integrierten PRs [#265](https://github.com/burckhju/trading-workspace/pull/265),
[#266](https://github.com/burckhju/trading-workspace/pull/266),
[#270](https://github.com/burckhju/trading-workspace/pull/270),
[#279](https://github.com/burckhju/trading-workspace/pull/279) und
[#290](https://github.com/burckhju/trading-workspace/pull/290) enthalten bereits
die beiden Performanceberichte, die Wiederverwendung bestätigter Kaufwährungen
und die feste EUR-Berichtsauswahl. Die bei Beginn offenen PRs enthalten keinen
zusätzlichen historischen Währungsresolver.

Während der Qualifikation wurde PR #297 von anderer Stelle in Main integriert.
Der Featurebranch wurde deshalb auf den neuen Main-Stand
`1f6ca802df25b2d508338ac837fdfb39ac79eca2` aktualisiert. Die dort ergänzte
Positionsbewertung verwendet ebenfalls den gemeinsamen Währungsresolver;
ihre Quellenlesung und Herkunftsanzeige werden in diesem Änderungsschnitt
an die historischen Quellen angepasst.

Der bisherige Resolver kennt ausschließlich direkte Buchungsbestätigungen,
gleichseitige Korrekturvorgänger und den vollständigen früheren BUY-Präfix.
Ohne belegten Ausgangskauf bleibt dieser Präfix ungeklärt. Historische BUY-DTOs
enthielten ursprünglich keine gespeicherte Ausführungswährung; dieser Verlust
ist bereits im [Wiederverwendungsnachweis](EXECUTION_CURRENCY_REUSE_QUALIFICATION.md)
dokumentiert.

`WarrantListing` hat eine heutige Notierungswährung, Lifecycle und technische
Erfassungs-/Änderungszeiten. Es fehlt ein belegter historischer Gültigkeitszeitraum.
Die Version ist eine konkurrierende Änderungssperre, keine abrufbare Historie.
Executions besitzen bislang weder Handelsplatz- noch Ausführungsbelegbindung.
Basiswert-Notierungen, Strike-Währung, Monitoringquellen, einzelne historische
Kurse und Produktauswahl-Snapshots beweisen diese fehlenden Ausführungsmerkmale
nicht. Deshalb wäre ein einfacher EUR-Join auf heutige Listings fachlich falsch.

## Ergänzter Quellenvertrag

Die Migration `20261028_0048` ergänzt einen separaten, unveränderlichen
Quellenverlauf. Sie erzeugt **keine** historischen Quellen aus bestehenden
Listings und ändert keine Buchung, Position oder Währungsbestätigung.

| Quelle | Bindung | Tragweite |
|---|---|---|
| `USER_CONFIRMED` | Exakte bestehende Execution-Bestätigung | Ausdrücklich bestätigte Währung dieser Buchung; unveränderter Owner |
| `EXECUTION_DOCUMENT` | Workspace, Produkt, Trade und exakte unveränderliche Execution-ID | Einmal geprüfte Quelle mit Ausführungspreiswährung und/oder tatsächlichem Handelsplatz |
| `HISTORICAL_LISTINGS` | Workspace, Produkt, belegtes Intervall `[valid_from, valid_to)` und historische Handelsplätze | Währungen während des ausdrücklich belegten Intervalls; optional explizit vollständige relevante Notierungsmenge |

Neue Quellen werden über
`GET/POST /api/v1/warrants/{product_id}/currency-evidence` gelesen/erfasst.
Der explizite Speichervorgang verlangt `CONFIRM_SOURCE_REVIEW`. Die feste Herkunft
`USER_VERIFIED_SOURCE` besagt, dass der Nutzer die angegebene Fundstelle geprüft
hat. Sie behauptet keine automatische Dokumentauthentifizierung und keine
automatisch importierte Brokerabrechnung. Ein Broker-PDF-Parser ist nicht Teil
dieses Schnitts. Dokumentreferenzen werden gespeichert, nicht serverseitig abgerufen.

Eine Quelle trägt Referenz/Fundstelle, Erfassungszeit, Actor, unveränderliche ID,
kanonischen Faktenfingerprint und bei Korrektur die Vorgänger-ID. Eine Berichtigung
oder ein Widerruf fügt einen Nachfolger hinzu. Alte Nachweise bleiben lesbar.
Request-ID und Faktenfingerprint sichern identische Retries; dieselbe Request-ID
mit anderen Fakten sowie parallele Nachfolger werden zurückgewiesen. Historisch
inaktive Katalogwährungen und Handelsplätze bleiben als Quellen zulässig.
PostgreSQL schützt Identität, Scope, Referenzen und Unveränderlichkeit zusätzlich.

## Auflösung und Priorität

1. Eigene ausdrückliche Währungsbestätigung der Buchung.
2. Eindeutige Währung aus ihren aktuell wirksamen, exakt zugeordneten
   Ausführungsbelegen. Widersprechende Währungen oder Ausführungsplätze sperren
   den automatischen Pfad.
3. Historisch gültige Notierung für einen aus diesen Belegen eindeutig bekannten
   Ausführungsplatz.
4. Ohne bekannten Ausführungsplatz: vollständige historisch belegte relevante
   Notierungsmenge mit derselben bekannten Währung an allen Plätzen.
5. Andernfalls ungeklärt; heutige Listings erzeugen keine Ersatz-Evidenz.

Die bereits freigegebene Wiederverwendung bestätigter gleichseitiger Vorgänger
und des vollständigen früheren bestätigten BUY-Präfixes bleibt erhalten, wenn
keine eigene Quelle entgegensteht. Diese abgeleiteten Werte heißen weiterhin
`REPLACED_EXECUTION` bzw. `PRIOR_BUYS`; sie werden nicht als neue
`USER_CONFIRMED`-Zeilen gespeichert. Ein eigener Beleg oder historischer Nachweis
der Korrekturbuchung hat Vorrang vor der übernommenen Vorgängerbestätigung.

Automatische Dokument-/Listingableitungen werden weder auf Ersatzbuchungen
kopiert noch außerhalb ihres Zeitraums als BUY-Standard weitervererbt.
Auch eine mehrstufige Korrekturkette darf eine intervenierende Quelle nicht
überspringen und dadurch eine ältere Bestätigung wiederbeleben. Die aktuelle
Ersatzbuchung wird eigenständig geprüft. Ohne ausreichende Quelle bleibt sie
mit konkretem Hinweis ungeklärt; eine eigene explizite Bestätigung kann sie
gezielt korrigieren.

Für Tagesangaben muss eine historische Quelle den ganzen möglichen lokalen
Ausführungstag decken, einschließlich 23-/25-Stunden-Tagen. Der technische
Sortieranker wird nicht als belegte Ausführungsuhrzeit verwendet. Teilweise
überlappende gegensätzliche Quellen bleiben sichtbar. Ein lückenhafter
Handelsplatzumfang wird nicht durch Ausblenden der unbekannten Einträge eindeutig.
Mehrere historische Plätze mit identischer Währung sind zulässig; unterschiedliche
Währungen ohne bekannten Ausführungsplatz bleiben ungeklärt.

## Performance und Reproduzierbarkeit

`PositionProjector.project_with_trace` bleibt der einzige Average-Cost-Rechner.
Die Kostenbasis verwendet sämtliche wirksamen historischen Käufe vor dem Verkauf,
auch vor Beginn des Berichtszeitraums, sowie vorherige Teilverkäufe und Nachkäufe.
Ersetzte Buchungen fließen nicht ein; stornierte Trades bleiben ausgeschlossen.
Ungültige Mengen-/Korrekturhistorien werden nicht durch Währungsevidenz repariert.

Beide Berichte verlangen für alle notwendigen Preisquellen eine bekannte,
einheitliche Währung. Die numerische Freigabe prüft fehlende Währungen unabhängig
von der Herkunftsbezeichnung. Widersprüchliche Nachweise haben einen eigenen
Sperrgrund. Fremdwährungen werden nicht in EUR umgerechnet; `OTHER_CURRENCY`
bleibt ein Ausschluss, gemischte Kostenbasis bleibt nicht berechenbar.

Die Berichte lesen Quellen und Buchungen im selben kurzen PostgreSQL
`REPEATABLE READ READ ONLY`-Snapshot. Neue oder korrigierte Quellen werden bei
jedem Read neu ausgewertet. Antworten tragen die tatsächlich verwendeten
Quellenversionen, Referenzen, Intervalle und Resolverdefinition
`execution-currency-v3`. Quellen und Resolverdefinition gehen in den
deterministischen Basis-Hash ein. Leere neue Quellenhistorien lassen den bisherigen
Basis-Hash unverändert; die finanziellen Berichtsdefinitionen bleiben dieselben.
Lese-/Provenienzgrenzen liefern einen Fehler statt einer abgeschnittenen und
dadurch scheinbar eindeutigen Quellenmenge.

Synthetischer Rechenfall der Regressionen:

| Vorgang | Menge | Stückpreis EUR | Durchschnitt vor Verkauf | Realisierter Beitrag EUR |
|---|---:|---:|---:|---:|
| BUY | 100 | 2,00 | – | – |
| SELL | 20 | 2,50 | 2,00 | 10,00 |
| SELL | 30 | 3,00 | 2,00 | 30,00 |
| BUY | 50 | 4,00 | – | – |
| SELL | 40 | 2,50 | 3,00 | −20,00 |
| SELL | 60 | 3,50 | 3,00 | 30,00 |

Der vollständige Bruttobeitrag beträgt 50,00 EUR. Der Zeitraumbericht berücksichtigt
nur die im gewählten Zeitraum liegenden SELL-Beiträge; der Abschlussbericht
berücksichtigt das gesamte Ergebnis der im Zeitraum abgeschlossenen Trades.

## Bedienung und verbleibende Unklarheiten

Im Produktdetail kann eine belegte historische Notierungsquelle einmal erfasst
werden. Alle passenden Buchungen dieses Produkts werden daraus automatisch
neu bewertet. Heutige Listings werden nicht als geprüfte Historie vorausgefüllt.
Im Buchungskontext kann ein Ausführungsbeleg exakt zugeordnet werden. Quellen
lassen sich berichtigen oder widerrufen; die bestehende ausdrückliche
Buchungsbestätigung bleibt als gezielter Vorrang erhalten.

Die gemeinsame Herkunftsanzeige unterscheidet bestätigt, abgeleitet und ungeklärt.
Sie zeigt konkrete Konflikte, fehlende zeitliche Deckung, unvollständige
Handelsplatzmengen und Korrekturbezüge. Ein automatisch aufgelöster Wert verlangt
keine zusätzliche Bestätigung. Es gibt keine pauschale Aufforderung, alle alten
Buchungen erneut auszufüllen.

Ohne historische Quellen bleiben auch mehrere heute bekannte EUR-Listings
unzureichend. Die gemeldete reale Kohorte wurde nicht aus produktiven Daten gelesen
oder verändert; daher wird keine Anzahl nachträglich entsperrter Nutzerbuchungen
behauptet. Technische Tests mit synthetischen Daten ersetzen diese Datenprüfung nicht.

## Prüfverträge und Integrationsgrenze

Der inzwischen in Main integrierte PR #297 qualifiziert das laufende Positions-PnL.
Dessen Bewertungsreader liest historische Währungsquellen nun im selben Snapshot
und übergibt sie dem Resolver. `BuyCurrencyEvidence` und die gemeinsame
Herkunftsanzeige berücksichtigen die erweiterten Resolutionfelder und Quellenarten.
Quellenrevisionen und Resolverdefinition sind Bestandteil des Basisnachweises.

Diese Anpassung ist fachlich erforderlich: Ein bestätigter EUR-Kauf mit einem
späteren, durch eigenen Beleg als USD nachgewiesenen Kauf darf nicht durch
`PRIOR_BUYS` als einheitlich EUR qualifiziert werden. Die gemeinsame Regression
prüft diesen Fall einschließlich Herkunft und Basis-Hash.

- Bestehende Currency-, Average-Cost-, Zeitraum- und Vollabschlussregressionen
  bleiben erhalten.
- Neue Resolver-/Reporttests prüfen historische Intervalle, gleiche/verschiedene
  Plätze, unvollständige Quellen, Belegkonflikte, Scope, Quellenversionen/Widerruf,
  Tagesgrenzen, mehrstufige Korrekturen, fehlende FX-Evidenz und deterministische Basis.
- Neue Owner-/PostgreSQL-Tests prüfen die Migration ohne Backfill, Datenbankguards,
  Idempotenz, Konkurrenz, Snapshotkonsistenz und GET ohne Businessdatenmutation.
- Oberflächentests prüfen einmalige Quellenverwendung, gezielte Korrektur,
  Quellen-/Buchungskontext, veraltete Antworten und identische Retries bei
  unbekanntem Speicherausgang.

Die tatsächlichen lokalen Ergebnisse und CI-Läufe werden im zugehörigen PR an
den geprüften Head gebunden. Vorherige grüne Läufe gelten nicht als Nachweis
für einen nachträglich geänderten Head. Der Auftrag umfasst Featurebranch und PR;
Merge, Release, Deployment, PC-Update und produktive Datenkorrektur sind nicht
freigegeben und werden hier nicht durchgeführt.
