# Betrieb der Emittentenkurse ab Version 1.4.0

Diese Anleitung ersetzt die Installationsbefehle der früheren Einzelpakete.
Ein GitHub-Merge aktualisiert den laufenden Server nicht automatisch. Ein bereits
laufender JMBbot bleibt bis zu einem gesonderten Deployment auf seinem installierten
Stand. Bestehende Konfiguration, Datenbank und Zustimmungsspeicher erhalten.

## Quellenwahl bei neuen Optionsscheinen

1. Kanonische ISIN, Emittent und eine eindeutige aktive EUR-Notierung müssen in
   den Stammdaten vorhanden sein. Discovery erfindet oder repariert diese nicht.
2. Bei aktivierter Emittentensuche prüft die Hintergrund-Lane die offizielle
   Produktseite von JPMorgan oder Morgan Stanley. Nur exakte Produktidentität,
   Produkttyp, Bewertungstag, Währung und DOM-Streamkennung ergeben einen Nachweis.
3. Wenn die HTTP-Seite unvollständig ist, darf der private Renderer sie darstellen.
   Zugangssperren, Rate Limits und geänderte Bedingungen werden nicht umgangen.
4. Registrierung und spätere Auswahl prüfen die Stammdaten erneut unter Sperren.
   Der dedizierte Streamadapter holt Kurse; der Quellenabgleich bindet nur geeignete
   verifizierte Routen. Zulässige bestehende Quellen werden erhalten.
5. Bewertungsansicht und Monitoring zeigen Anbieter, Qualität, Kurszeittext und
   Empfangszeit. Ohne verifiziertes Datum/Zeitzone bleibt `quote_observed_at=null`.
   Indikative Regeln folgen ausschließlich der bestätigten Indikations-Policy.

Aktivierung erfolgt ausdrücklich über das optionale Compose-Overlay. Ohne diese
Konfiguration bleiben neue Provider, automatische Auswahl und Discovery aus.
Das Discovery-Intervall beträgt standardmäßig eine Stunde; Diagnose-GETs erzwingen
keinen sofortigen Wiederholungsabruf. `SELECTED` beweist keine neue oder handelbare Quote.

### JPMorgan-Produktseiten ohne DOM-Uhrzeitfeld (ab 1.4.5)

Die Routenerkennung verlangt Geld- und Briefbindung im `staticgrid` mit
`data-source=lightstreamer` und derselben exakten, ISIN-bezogenen Streamkennung.
Das JPMorgan-DOM-Feld `quotetime` ist optional: Ein am 04.10.2026 zurückgemeldeter
Serverlauf enthielt beide Preisbindungen, aber kein solches Zeitfeld. Ist eine
passende Zeitbindung vorhanden, darf sie der Preiskennung weiterhin nicht
widersprechen. Produktmetadaten, Währung und alle übrigen Identitätsgrenzen gelten
unverändert. Morgan Stanley verlangt weiterhin `lastquotetimestamp`.

Dies ist ausschließlich ein Seitennachweis für die technische Route, keine
Kursprüfung. Der Streamadapter behält sein eigenes Schema und seine Prüfungen.
Fehlende Kurszeit bleibt unbekannt; weder Empfangszeit, Bewertungstag noch
Basiswertzeit werden eingesetzt. `execution_usable=false` bleibt erhalten.

Auf älteren Ständen kann das Zustimmungs-Setup nach erfolgreicher Formularbedienung
mit `JPMORGAN_CONSENT_NOT_VERIFIED_NO_STATE_SAVED` und der Ursache
`ISSUER_STREAM_BINDING_UNVERIFIED` abbrechen. Erst die konkreten DOM-Bindungen
unterscheiden diesen Fehler von fehlenden oder widersprüchlichen Preisbindungen.
Keine Speicherung erzwingen, keine Zeitfelder synthetisch ergänzen und keine
Wartezeiten pauschal erhöhen. Backend und Renderer auf denselben korrigierten
Release-Stand bringen; ein neuer Diagnose-Checkout allein ersetzt deren Parser
nicht. Danach den bestehenden freigegebenen Setup-Ablauf mit weiterhin identischem
Bedingungshash erneut ausführen und die Wiederverwendung separat nachweisen.

## Reguläre Konfiguration

`docker/compose.issuer-monitoring.yml` bündelt die bisherigen Emittenten-,
Performance-, Auswahl-, Renderer- und Monitoring-Overlays. Bestehende Frankfurt-,
gettex- und Stuttgart-Konfiguration zusätzlich erhalten. Die neuen Dateien nicht
mit alten Paket-Overlays mischen, die dieselben Werte erneut überschreiben.

Ab 1.4.1 unterstützt der kanonische Starthelfer das Overlay ausdrücklich:

```bash
bash scripts/start-linux.sh --issuer-monitoring --check
bash scripts/start-linux.sh --issuer-monitoring
```

Der erste Aufruf ist rein prüfend; der zweite führt das Deployment aus. Vorhandenes
`docker/frankfurt.env` wird automatisch berücksichtigt. Weitere tatsächlich benötigte
Börsen-Overlays auf beiden Aufrufen in bisheriger Reihenfolge mit `--overlay DATEI`
angeben. Weggelassene oder umsortierte frühere Compose-Dateien führen vor Änderungen
zum Abbruch. Alte Paket-Overlays erst nach bewusster manueller Migrationsprüfung
ablösen, nicht zusätzlich mit dem kanonischen Overlay mischen. Details und Grenzen:
[Linux Deployment](LINUX_DEPLOYMENT.md#issuer-monitoring-and-existing-overlay-chains-141).

Der Helper baut auch den Renderer und verlangt dessen Sandbox-Healthcheck vor
Migration/Backend-Neustart. Der Migrationscontainer startet keine Abhängigkeiten.
Für manuelle Compose-Aufrufe im Projektverzeichnis weiterhin:

```bash
export ISSUER_RENDERER_SECCOMP_PATH="$PWD/docker/issuer-renderer/seccomp_profile.json"
```

Den Telegram-Schalter `TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=true`
in der bestehenden privaten `docker/.env` beibehalten, wenn der Versand bereits
freigegeben und eingerichtet ist. Bot-Token und Chat-ID bleiben ausschließlich dort.
Das Overlay versendet selbst keine Testnachricht. Vor einem Deployment die effektive
Compose-Konfiguration prüfen, ohne deren Geheimniswerte öffentlich auszugeben.

Die folgenden Diagnosebeispiele verwenden die Basiskonfiguration zur Auswahl des
bereits laufenden Containers; `exec` rekonstruiert oder ersetzt keinen Dienst:

```bash
docker compose --env-file docker/.env -f docker/compose.yml exec -T backend \
  python -m app.tools.audit_monitoring_performance --wait-seconds 0
```

Zusätzliche Prüfwerkzeuge: `audit_position_source_selection`,
`audit_issuer_route_discovery`, `audit_new_issuer_routes` und `monitoring_resume`.
Die jeweilige `--help`-Ausgabe zeigt Pflichtparameter. Die beiden Runtime-Hash-Audits
benötigen die Hashliste des tatsächlich deployten Commitstands, keine alten
Paket-Hashes. `audit_issuer_monitoring` kann über die normalen Bewertungs-GETs Kurse
aktualisieren; es verändert keine Regeln und versendet keine Meldungen.

Ab 1.4.2 zählt `audit_monitoring_performance` alle aktuellen `ISSUER_QUOTES`-Jobs,
auch für neu entdeckte Produkte. Eine historische ISIN-Liste begrenzt diese
Diagnose nicht mehr. Ein Regelcheck wird anhand seines expliziten Providers oder,
bei fehlender Providerangabe, seiner Instrument-ID in einem solchen Job zugeordnet.
Eine ausdrücklich andere Kursquelle bleibt maßgeblich. Diese Zuordnung ist keine
Änderung oder Bestätigung der benutzergebundenen Quellenentscheidung.

`issuer_refresh_success_isins` erfordert je Produkt einen verfügbaren Job mit
positivem endlichem Geldkurs eines unterstützten Emittenten, Empfangszeit und ohne
Retention/Abruffehler. `issuer_refresh_unverified_isins` nennt die übrigen Produkte.
Die Jobliste zeigt `positive_bid_evidenced` und kompakte Original-Kursfelder, damit
ein verfügbares Ergebnis ohne diesen Nachweis erklärbar bleibt. Empfangszeit ist
weiterhin keine Kurszeit; ein positiver Geldkurs beweist weder Aktualität noch
Ausführbarkeit. `rule_issues` umfasst auch indikative Regelchecks mit Abruffehlern
und erhält deren ursprünglichen Status.

`wait_completed=true` bestätigt Schedulerfortschritt und erfolgte Erstprüfungen
aller aktuellen Emittentenjobs, keine vollständige Kursabdeckung. Monitoring- und
Refresh-Status werden nacheinander gelesen. Ein späterer erfolgreicher Abruf kann
deshalb neben einem noch fehlgeschlagenen Check des letzten Monitoring-Zyklus
stehen. Der nächste reguläre Zyklus liefert den neuen Bewertungsnachweis.

## JPMorgan-Zustimmung

Der Renderer verwendet ausschließlich seinen eigenen privaten Zustand im Volume
`issuer-consent-state`. Eine Zustimmung im Cloud-Browser ist nicht dieser Zustand.
Die unbeaufsichtigte Discovery klickt keine rechtlichen Erklärungen an.

Zur Vorbereitung im laufenden Renderer:

```bash
docker compose --env-file docker/.env -f docker/compose.yml \
  -f docker/compose.issuer-monitoring.yml exec -T issuer-renderer \
  python -m app.tools.setup_jpmorgan_consent
```

Der Betreiber prüft den ausgegebenen aktuellen Text, Hash und seine Erklärungen.
Der explizite Zustimmungslauf benötigt `--accept-current-jpmorgan-terms`,
`--confirm-sha256`, `--confirm-de-at-residence-and-non-us-person` und bei gewünschter
Speicherung `--remember-30-days`. Er läuft unter der vorhandenen Setup-Sperre.
Ein geänderter Hash wird nicht automatisch freigegeben.

Vor erneuter Zustimmung wird ein vorhandener gültiger Zustand mit passendem Hash
in einem frischen Kontext produktgeprüft. Erfolg:
`EXISTING_CONSENT_REUSE_VERIFIED`, `new_acceptance_performed=false`.
Ohne gespeicherten Zustand wird der bestätigte Formularlauf ausgeführt; erst nach
verifizierter Wiederverwendung darf gespeichert werden. Erfolg:
`CONSENT_STORED_PRODUCT_VERIFIED`, `new_acceptance_performed=true`.
Ungültige oder nicht mehr verwendbare vorhandene Zustände werden nicht stillschweigend
überschrieben. Die Größenbegrenzung bleibt bestehen; eine kleinere Variante nur
mit den erfassten Cookies benötigt eine erneute Produktprüfung.

`setup_diagnostics` nennt Phasen, Laufzeiten, begrenzte Fehlerketten und reine
Speichermetadaten. Keine Cookies/Storage-Werte in Berichte kopieren. Wenn Speichern
bereits gelang und nur die Browserbereinigung fehlschlug, macht der Bericht dies
sichtbar; der nächste Lauf prüft die gespeicherte Zustimmung zuerst.

Der Setup-Erfolg erzeugt weder ein Mapping noch eine Testposition. Neue Routen
werden weiterhin durch die Hintergrund-Lane und deren Identitätsprüfungen angelegt.

## Release und Deployment auseinanderhalten

<a id="indicative-entry-operations"></a>
### Gesonderte automatische Einstandsbeobachtung

`INDICATIVE_ENTRY_V1` mit Regelversion `indicative-entry-review-v1` ist ein eigener
freigegebener Prüfumfang. Er nutzt gespeicherte Positionen, effektive Ausführungen,
Einstand und Währung sowie vorhandene Quellen-, Kalender- und Produktbelege.
Z1-Verkauf oder Target-Evidenz sind für diesen Umfang keine Voraussetzung. Neue
oder fehlende Belege werden gezielt als Datenproblem sichtbar; unveränderte
Belege innerhalb ihres Gültigkeitsbereichs werden nicht täglich neu bestätigt.

Der Hintergrundrunner erzeugt drei getrennte Hinweise im vorhandenen
Arbeitsbereich: Einstandsindikation unter persönlichem Bruttoeinstand,
Prüferinnerung nach 20 abgeschlossenen Basiswertsitzungen und Datenproblem.
Wiederholung und Neustart erzeugen keinen zweiten logischen Hinweis für dieselbe
Episode. Eine Datenlücke ist keine Kurserholung. Vollständiger Verkauf beendet
neue Hinweise und noch ausstehende Zustellungen dieser Typen; die Historie bleibt.
Die vorhandenen allgemeinen Stop-/Zielregeln bleiben erhalten.

Ein explizit belegter Original-BID benötigt seine eigene Seitenzeit und mindestens
20 abgeschlossene Sitzungen bereits zu dieser Zeit. Bestehende registrierte
Emittentenindikationen haben dagegen häufig keine verifizierte Originalzeit;
ihre bisherige 300-Sekunden-Grenze betrifft ausschließlich den erfolgreichen
Empfang. Eine fällige Positionsprüfung datiert diesen Preis nicht nachträglich.
Negative Originalstatuspunkte bleiben mit eigener Zeit sichtbar; ihre
Fortgeltung wird nicht erfunden. Die genaue Eingangsqualifikation steht im
[Regelvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-entry-review-v1).

Die einmalige [zentrale PC-Aktivierung](LINUX_LAUNCHER.md#einmaliger-übergang-auf-die-indikative-positionsprüfung)
schaltet den Umfang für bestehende offene Positionen gemeinsam ein.
`REVIEW_NOTIFICATIONS_ENABLED=false` hält neue externe Reviewzustellungen aus;
die Hinweise sind im Arbeitsbereich gespeichert. Vorhandene andere
Benachrichtigungen können gemäß ihrer bereits eingerichteten Konfiguration
weiterlaufen. Aktivierung und Softwareupdate erteilen keine neue Providerfreigabe
und versenden keine Testnachricht.

Die Betriebsanzeige unterscheidet konfigurierten Umfang, gestarteten Runner,
abgeschlossenen Zyklus und dessen tatsächliche Positions-/Datenproblemzähler.
Ein geladener Umfang mit null ausgewerteten Positionen belegt keine
Depotabdeckung; ein Fehler oder Datenproblem bleibt sichtbar. Die passive
Detailansicht liest vorhandene Bewertungen und löst weder Beschaffung noch
Regelauswertung aus. Nach Aktivierung wird der nächste reguläre Prüflauf
abgewartet; tägliche Prüfklicks sind nicht erforderlich.

Die strenge B04/B57-Strecke und `HEBELTRADER_CONFIRMED_BASELINE` werden dadurch
nicht aktiviert. B58 bleibt ohne geeignete reale Originalstatuslieferung offen.
B05 benötigt weiterhin seine eigenständigen belegten Produkttermine und das
feste Ausstiegslisting; ein fehlender BID ist für diese Fristregel kein Hindernis.

### Erweiterter eigener Umfang V2

`INDICATIVE_ENTRY_V2` / `indicative-entry-review-v2` ergänzt den
[V2-Regelvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-rule-v2)
mit den vorhandenen verzögerten Quellen (eigene gemeinsame Quellzeit,
höchstens 30 Minuten) und aktuellen Originalproduktbelegen mit sichtbar
angenommener historischer Kontinuität. Die strenge 900-Sekunden-BID-Grenze und
die weiterhin fehlende B58-Originalstatusversorgung bleiben unverändert.
Beschaffungsprobleme sind getrennte Betriebsdiagnosen und löschen weder alte
Originale noch eine bestehende Verlustepisode. Bekannte Rücknahmen oder
widersprüchliche Bindungen werden nicht durch schwächere Belege übergangen.

Die unabhängige Produktfristprüfung benötigt dokumentiertes Produktende,
letzten Handelstag und ausdrücklich gewähltes Ausstiegslisting. Vorliegende
Originalseiten können einmalig über den kontrollierten Dateiimport übernommen
werden. Ein Börsentagskalender liefert ausschließlich eine Datumserinnerung;
individuelle Handelszeiten/B20 und nicht belegte Kalenderjahre bleiben offen.
Einstands- und Fristergebnisse haben getrennte Zähler. Vorübergehend fehlende
Fristgrundlagen pausieren ausstehende Meldungen, während ein belegter Vollverkauf
diese beendet. Externe Reviewzustellung bleibt im vorbereiteten PC-Übergang aus.

Die [zentrale V2-Aktivierung](LINUX_LAUNCHER.md#erweiterung-der-vorhandenen-installation-auf-v2)
übernimmt vorhandene Positionen gemeinsam; tatsächliche Depotabdeckung wird
anschließend aus einem beobachteten PC-Zyklus beurteilt. Eine vollständige
Hebeltrader-Baseline, B06 oder B08 folgen daraus nicht.

### Softwarestand und Betriebsnachweis

Git-Tag und Paketversion kennzeichnen den Quellstand; Schema, Image und geladene
Konfiguration sind separate Betriebsnachweise. Vor Deployment sichern, beide
Migrationen prüfen, zuerst Renderer-Health bestätigen und anschließend die
vollständige bestehende Stack-Konfiguration verwenden. Keine Löschung von Volumes,
kein Datenbank-Stamp und kein stiller Rollback.

Der Release-PR enthält lokale Prüfergebnisse und GitHub-CI. Die noch offene
JPMorgan-Liveabnahme und fehlende neue Produktabdeckung sind dort ausdrücklich
aufgeführt und dürfen nicht aus grünen Unit-Tests abgeleitet werden.

<a id="lesende-depot-datenversorgungsdiagnose"></a>
## Lesende Diagnose der tatsächlichen Depotversorgung

**Neuester enger Betriebsbeleg, 24.11.2026:** Der
[archivgebundene P02-Read](../reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md)
bestätigt v1.5.54/9a5e59d…, Schema0060 und vier gesunde laufende Dienste.
Die Sammlung um 18:23:08–18:23:10 Uhr MEZ findet eine gespeicherte
V2-Bewertung von 18:21:41 Uhr MEZ mit vorhandenem Bid, 10,456 Sekunden
Empfangsalter und `BELOW_ENTRY`. Der historische Gap ist
`JPMORGAN_SNAPSHOT_TIMEOUT`; der heutige
`ORIGINAL_MARKET_STATUS_NOT_DELIVERED` ist eine Statusdatenlücke, keine
erneute V2-Preisunterbrechung. Der enge Read ist abgeschlossen. Er enthält
keine neue Gesamtinventur, keine neue Fristprüfung und keinen Beleg für
vollständige B58-Inputs. Der Diagnose-/Resolverfix aus PR #370 ist auf
diesem PC nicht installiert und hat diesen Preisbefund nicht bewirkt.

**Letzter vollständiger Verbraucherread, 22.11.2026:** Der Nutzer hat den nachfolgenden
Collector auf v1.5.52/c7db441… ausgeführt. Installation/Schema, 30 erfolgreiche
GETs, vollständiges Vierer-Inventar und unveränderte Monitoringzyklusmarker
sind im [Readbacknachweis](../reviews/DEPOT_DATA_READBACK_2026-11-22.md)
belegt. V2-Einstand und Produktfrist hatten damals jeweils 4/4 Datenprobleme.
Dieser tatsächliche Lauf ergänzt die frühere lokale Helferqualifikation.
Eine erkannte Grenze bleibt: die sechs Positionsreader geben den konkreten
P02-Gapgrund aus dem unabhängigen Statusjournal nicht aus. Der
[gezielte Collectormodus](#gezielter-p02-journalread) hat diese Lücke am
24.11. geschlossen. Seine Anleitung bleibt für die reproduzierbare
Diagnose erhalten; sie ist kein erneuter aktueller P02-Arbeitsauftrag.

Nachgeprüfter Main: `9a5e59dac3bb219cbc40641e62e75871eb2ed131` / `VERSION=1.5.54`, PR373 vom 22.11.2026, 21:35:28 Uhr MEZ. Die verwendeten Backendreader, Docker- und Launcherdateien sind gegenüber der geprüften Produktbasis `c7db441de36297a98d47cdf28c64b4e5d9994692` unverändert. Das zusätzliche Delta zum vorherigen Main febeb922… enthält ausschließlich Versions-/Liefermetadaten und Dokumentation. Die tatsächliche Installation von v1.5.54 ist separat durch das neue private Paket belegt, nicht aus Main abgeleitet. [Fachlicher Datenvertrag und Einzelbelege](../reviews/DEPOT_DATA_SUPPLY_2026-11-20.md); [einziger nächster Arbeitsauftrag](../planning/PRODUCT_BACKLOG.md#naechster-schnitt). Lokale Helferqualifikation, tatsächlich ausgeführter passiver Read und fachliche Regelabdeckung bleiben getrennt.

Es existiert bereits ein geeigneter GET-Inventarread: `/api/v1/market-data/positions/quote-coverage`. Er ermittelt alle offenen, nicht stornierten Positionen aus der DB, einschließlich Positionen ohne Quelle; es gibt keine feste Sechserliste und keinen Bezug nur auf letzte Rulechecks. Er liefert Produkt- und Listingidentitäten sowie source selection. Vor/nach Sammlung werden dessen IDs und Mapping-/Auswahlbezüge verglichen. Für diese Inventur ist kein neuer API-Endpoint, Runner oder installierter Anwendungscode nötig.

Quellbelege: [Inventar-API](../../backend/app/features/market_data/api/quote_coverage.py), Z.51–60; [Projektion](../../backend/app/features/market_data/service/position_quote_coverage.py), Z.131–158; [Positionsinventur](../../backend/app/features/market_data/persistence/position_quote_coverage.py), Z.52–114; [Quellenread](../../backend/app/features/market_data/persistence/quote_coverage.py), Z.25–130. Ausschließlich SELECTs und reine Projektion, keine Provideraufrufe/flush/commit. Die Coverage-Projektion besitzt mehrere kurze Reads, keinen global atomaren Snapshot.

Die dortige Eigenschaft `monitoring_usable` ist **kein** Nachweis der B58-/V2-Regelqualität: sie schließt ausdrücklich STALE/REFERENCE_ONLY/TIMESTAMP_UNKNOWN ein (`service/position_quote_coverage.py:209–229`). Die tatsächlichen gespeicherten Regelbewertungen bleiben maßgeblich.

Der ergänzende vorhandene GET `/api/v1/market-data/warrants/quote-coverage`
liefert bestehende Produktrouten, Mappingzustand, gespeicherte Quotes und
aktuelle Konfiguration für gehaltene Produkte, ohne Provider-I/O oder Jobplanung
([API](../../backend/app/features/market_data/api/quote_coverage.py),
[Service](../../backend/app/features/market_data/service/quote_coverage.py)).
Seine `discovery_reasons` kommen nur aus aktuellen Schedulerjobs für
`FRANKFURT_MAPPING`/`VONTOBEL_MAPPING`, nicht aus vollständiger persistierter
Discoveryhistorie. Frühere Auswahlkandidaten sind im bestehenden
`PositionQuoteSourceSelectionModel.evidence` gespeichert und werden von
beiden GETs nicht ausgegeben; dafür ist ein gezielter lesender SELECT
erforderlich. Leere Runtimegründe belegen keinen früheren Discoveryfehler.
Beide GETs enthalten nur offene Positionen beziehungsweise deren Produkte:
Ein heute fehlender Archivkandidat ist erst mit gespeichertem
`closed_at`/`cancelled_at` als geschlossen/storniert belegt; sonst bleibt
seine Zuordnung ungeklärt.

Diese vorhandenen Quellen ergänzen die Diagnose ungebundener Positionen;
der bestehende `--source-gap-from`-Modus setzt eine bestätigte Route voraus.
Eine künftige gezielte Sammlung für ungebundene Positionen ist damit nicht
bereits implementiert. Für passive DB-Reads keine Owner-Methode mit
`FOR UPDATE` verwenden; insbesondere sperrt
`PositionQuoteSourceSelectionRepository.active_for_position()` die Auswahlzeile.

**Journalgrund fachlich auswerten:** `GAP_PRESENT` allein belegt keinen
Preisausfall. `ORIGINAL_MARKET_STATUS_NOT_DELIVERED` bleibt eine strenge
B58-Lücke, ist aber im freigegebenen V2-Pfad ausdrücklich von
`REVIEW_PRICE_SUPPLY_INTERRUPTED` ausgenommen. Bei Abruffehlern können
Batchcaches denselben Fehler erneut zurückgeben; die Gap-Erfassungszeit
ist deshalb nicht ohne Weiteres die ursprüngliche Netzwerkfehlerzeit.
Ein früherer bidloser Quote und ein später erfasster Timeout sind getrennte
Fakten. Empfangszeit, Originalkurszeit und Statusgeltung bleiben verschieden.

### Ein einzelner lesender Collector außerhalb des Programmordners

Der [Collector `collect-depot-data-supply.py`](../../scripts/collect-depot-data-supply.py)
ist eine eigenständige Datei. Auf dem bestehenden Linux-PC als bisheriger
Installationsbenutzer herunterladen und außerhalb des Programmordners
speichern, beispielsweise im Downloadordner. Ein Checkout-/Releasewechsel
ist für diesen Lesevorgang nicht erforderlich.

```bash
python3 "$HOME/Downloads/collect-depot-data-supply.py"
```

Der Standardbasisordner ist `~/Boerse`; ein bereits gesetztes
`TRADING_WORKSPACE_BASE` beziehungsweise `--base /absoluter/pfad` übernimmt
abweichende Installationsorte. Der Host benötigt Python 3.10 oder neuer
und verwendet ausschließlich dessen Standardbibliothek. Die fachlichen Reader und ihre vorhandenen Abhängigkeiten
laufen im bereits vorhandenen Backendcontainer. Es werden keine Pakete
installiert und keine fehlenden Dienste gestartet.

Der Collector gibt das neue private Diagnoseverzeichnis unmittelbar aus.
Es liegt außerhalb des Repositories, hat Modus `0700`; Dateien und das
abschließend erzeugte `.tar.gz` haben `0600`. Bei unzugänglichem Bestand
oder unvollständigem Abruf bleibt ein Fehlerpaket mit genauer Fehlerklasse
erhalten. Ein fehlender Zugang wird nicht als fehlende fachliche Daten
umgedeutet. Das Archiv privat bereitstellen; keine Rohdatei als PR-Anhang
veröffentlichen.

| Datei im privaten Archiv | Inhalt und Nachweisgrenze |
| --- | --- |
| `installation-before.json`, `installation-after.json` | Selektive Git-/VERSION-/Deployment-Marker und Docker-Container-/Imagebezüge. Vorher/nachher vergleichen; keine `.env`, vollständigen Konfigurationen oder Docker-Inspects. |
| `schema.json` | Tatsächliche Alembic-Revisionswerte über die konfigurierte Backend-Datenbank in einer ausdrücklich lesenden Transaktion. Kein aus dem Release angenommener Schemastand. |
| `monitoring-private.json` | Vollständiges Inventar vor/nach, Runtime-/Refreshstatus vor/nach und sechs vorhandene GET-Reader je aktueller Position samt unveränderten Antworten und Lesefehlern. |
| `summary.json` | Ergebnis der Sammlung, Verfügbarkeit und beobachtete Bindungswechsel. Vollständiger Transport ist keine V2-/B58-/B06-Regelqualifikation. |

**Zulässige Operationen:** Git-Metadaten mit unterdrückten optionalen
Schreiblocks, kleine explizit ausgewählte Deployment-Marker, Docker-
Container-/Imageinspektion mit fest begrenzten Feldern sowie `docker exec`
gegen die zuvor validierte bestehende Backend-ID. Im Backend läuft Python
mit `-B`, um neue Bytecode-Dateien zu vermeiden. Der Schemaread verwendet die
wirklich konfigurierte Datenbank mit `READ ONLY`, begrenzten Wartezeiten und
abschließendem Rollback. Er lässt damit auch einen abweichenden Datenbank-
URL-Zugang korrekt beim vorhandenen Backend; Zugangsdaten werden nicht
in das Paket geschrieben. Die eigentliche Verbrauchersammlung verwendet
im Vollmodus nur die bereits qualifizierten GET-Pfade.

**Ausdrücklich nicht Teil dieses Collectors:** Launcher `status`,
Deploymenthelfer, `docker compose`, Validatorcontainer, Build/Start/Update,
Refresh, Import, Regelausführung, Anbieterzustimmung oder Nachrichtenversand.
Die laufenden Dienste werden weder angehalten noch pausiert. Fehler werden
mit begrenzten Klassen gemeldet; vollständige Containerlogs, Tracebacks,
Providerkeys und Produktoriginalbytes werden nicht gesammelt.

<a id="gezielter-p02-journalread"></a>
### Einmaliger gezielter Journalread nach vollständigem Archiv

Der ergänzte Modus desselben Collectors liest genau eine im alten Paket
gebundene Position. Er wurde am 24.11. gegen die archivierte v1.5.52-Bindung
auf der tatsächlichen v1.5.54-Installation erfolgreich ausgeführt und
benötigt keinen installierten Resolverfix. Die heruntergeladene Datei
im Downloadordner durch die neue Fassung ersetzen; die Archivangabe im
Beispiel durch den tatsächlich vorhandenen Pfad ersetzen:

```bash
python3 "$HOME/Downloads/collect-depot-data-supply.py" \
  --source-gap-from /absoluter/pfad/zum/bisherigen-diagnosepaket.tar.gz \
  --position-label P02
```

`P02` bezeichnet ausschließlich das Pseudonym im **angegebenen alten
Archiv**, keine laufende Nummer der heutigen Positionsliste. Der Helfer
liest fünf begrenzte reguläre JSON-Archiveinträge im Speicher, ohne sie zu
entpacken. Er prüft Transport, Payloadbindung, Inventar, gespeicherte
Quellenroute, Auswahlversion und referenzierte Bewertung. Ungültige,
unvollständige oder mehrdeutige Archive führen zu einem privaten Fehlerpaket.

**Falls `unrecognized arguments` erscheint:** Zeigt die Hilfe nur `--base`,
wird noch eine Collector-Fassung ohne den engen Modus ausgeführt. Die
Argumentprüfung bricht dann vor jeder Sammlung ab. Dies wurde beim
Nutzeraufruf vom 23.11.2026 beobachtet; daraus folgt kein Backend- oder
Datenbankfehler. Die bereitgestellte Fassung aus
[Commit451b10da](https://github.com/burckhju/trading-workspace/blob/451b10daa4b3a838605ad82cdbf6689aed9bb1f2/scripts/collect-depot-data-supply.py)
besitzt beide Optionen. Zur eindeutigen Zuordnung kann dieselbe Datei als
`collect-depot-source-gap-451b10da.py` gespeichert werden; im Aufruf dann
genau diesen Dateinamen verwenden. Die separat bereitgestellte Downloadkopie
ist bytegleich, SHA256
`d9b6997b8e2644b658fc921aba37d45f9eac7e5a226347e024d88a6736a045c2`.
Ein App-Update ist für die Korrektur des lokalen Dateinamens nicht nötig.

Im bestehenden Backend folgen die Installations-/Schemabindung und eine
einzelne `REPEATABLE READ READ ONLY`-Transaktion. Die tatsächlich gesetzten
Transaktionseigenschaften werden vor den Ownerreads kontrolliert;
`autoflush=False`, begrenzte Verbindungs-/Statement-/Lockwartezeiten und
explizites SQL-`ROLLBACK` gelten auch bei Fehlern. Die konfigurierte
Datenbankadresse verbleibt im Backend. Gelesen werden:

- aktuelle offene Position, Produkt und bestätigte Quellenauswahl gegen
  die archivierte Identität;
- der gespeicherte Quote und der vorhandene `MarketStatusReader` mit
  `latest_gap`, `latest_capture` und seinen zeitlich gebundenen Beobachtungen;
- genau die archivierte Bewertung samt damaligen `saved_quote`,
  `status_observations` und `current_refresh_failed`, daneben der aktuelle
  Bewertungskopf. Es erfolgt keine erneute Bewertung oder nachträgliche
  Rekonstruktion historischer Fakten aus dem heutigen Quote.

Bei geänderter Position, Produkt-/Quellenroute oder Auswahlbindung meldet
der Helfer die Abweichung. Er wechselt nicht zu einer anderen Position.
Ein gewöhnlicher Softwarewechsel seit dem Referenzpaket wird gesondert
ausgewiesen; Installation und Container müssen innerhalb des neuen Laufs
unverändert und prüfbar bleiben.

Das neue private Archiv enthält `installation-before.json`,
`installation-after.json`, `schema.json`, `source-gap-private.json` und
`summary.json`. Dieser Modus wiederholt keine der 30 GET-Abfragen und führt
keinen Providerabruf aus. Die bisherigen Verzeichnis-/Dateirechte und
Fehlerpakete bleiben erhalten. Auch ein unvollständiges Paket privat
bereitstellen; vollständige Terminallogs werden nicht benötigt.

`COMPLETE_PASSIVE_SOURCE_GAP_READ_NOT_PRICE_QUALIFICATION` bedeutet, dass
die gebundenen gespeicherten Fakten gelesen wurden. Ein ausdrücklich
leeres Journal ist ein eigener möglicher Befund. Der Status beweist
weder einen neuen Bid noch eine reparierte Quelle oder B58-Konformität.
Die [Prüfbelege](../reviews/DEPOT_DATA_READBACK_2026-11-22.md#p02-fortsetzung-20261122)
und der [einzige Arbeitsauftrag](../planning/PRODUCT_BACKLOG.md#naechster-schnitt)
halten Vorbereitung und tatsächliches PC-Ergebnis getrennt.

### Korrektur des vorbereiteten Ablaufs vom 20.11.2026

Der frühere Dokumentblock begann mit `trading-workspace status`. Dieser
ändert zwar keine Depotregeln, ruft aber den vorhandenen Deploymentvalidator
auf: [Launcher](../../scripts/trading-workspace.sh), Z.105/141, und
[Deploymenthelfer](../../scripts/migrate-legacy-issuer.sh), Z.60–64/101–106,
legen unter anderem Lock-/Wartungsdateien an beziehungsweise starten einen
isolierten Validatorcontainer. Deshalb wird dieser Aufruf aus dem streng
passiven Diagnosepfad entfernt. Der Launcher selbst wird nicht verändert.
Außerdem fehlte bislang ein tatsächlicher DB-Schemabeleg, obwohl die
Backlog-Abnahme ihn verlangt. Der neue getrennte Schemaread schließt diese
Lücke des vorbereiteten Collectors; eine echte PC-Abnahme ist damit noch
nicht erbracht.

Der fachliche GET-Pythonteil des alten Blocks wird unverändert übernommen:
11.191 UTF-8-Bytes, SHA256
`b8dee0cd47ccd95a224cf5897eb60233d3195bf9d76700a103acfcfbc5dbafab`.
Die Prüfung mit den vorhandenen Response-Dataclasses bleibt erhalten.
Die Imports kommen aus der installierten Anwendung und öffnen selbst
keine Datenbanksitzung. Zulässige `null`-Bewertungen und fachliche
MISSING-/UNSUITABLE-Befunde bleiben erhalten; unvollständige HTTP-200-
Antworten sind Diagnosefehler. Die Rohantwort wird durch die Prüfung
nicht ersetzt. Die nachfolgenden Auswertungsregeln gelten weiter.

### Auswertungsregeln

1. Beide Inventarreads erfolgreich und mit dem vorhandenen Responsevertrag validiert, vollständige Object-/List-/Countstruktur und kanonische nichtleere UUIDs, `summary.open_positions == len(items)`, keine doppelten Positions- oder Tradekennungen. Bei fehlerhaftem Inventar werden **keine** Einzelposition-URLs gebildet; IDs werden vor Verwendung validiert und kanonisiert. Jede Position bekommt alle **sechs** vorgesehenen, mit ihren Responseverträgen geprüften Read-Ergebnisse oder einen ausdrücklich benannten Diagnosefehler. Runtime- und Refreshstatus vor/nach der Sammlung müssen ebenfalls zugänglich sein; sonst lautet der Sammelstatus `AUXILIARY_READS_UNAVAILABLE`. Null offene Positionen erhält `NO_OPEN_POSITIONS_NO_COVERAGE_EVIDENCE`; `all_position_reads_available` bleibt false. `latest_assessment=null` kann ein gültiger Readerbefund sein, bedeutet aber fehlende Bewertung und keine Regelabdeckung.
2. Inventar/Bindings und idle Zyklusmarker unverändert: Sammlung ohne beobachteten Zykluswechsel. Das ist keine globale DB-Snapshotgarantie. Bei Wechsel den betroffenen Teil lesend wiederholen, keine laufenden Dienste pausieren. Persönliche Buchungs-/Belegänderungen und Kursrefresh können weiter stattfinden.
3. Für V2: `latest_assessment` vorhanden, `rule_version=indicative-entry-review-v2`, ausgewerteter Zeitpunkt/basis/source sichtbar. `latest_assessment.reasons`, `document_readiness` und aktive `DATA_UNAVAILABLE`-Episode gemeinsam lesen; Erwerbserfolg ist nicht Dokumenteignung. `document_readiness` enthält lediglich Versuchsergebnis/-zeit/-backoff. Es weist **keine** aktuelle KID-Revision, Parserfassung oder erfolgreiche lokale Neubewertung nach.
4. Für v1.5.52-Wirkung: installierten Stand bestätigen, letzte reguläre Bewertung nach Update heranziehen; wegfallender falscher Terms-Mismatch muss von weiter bestehendem echten Datums-/Underlying-Mismatch unterschieden werden. Keine Quote/Einstandsfreigabe allein aus verschwundenem Fehlercode.
5. Für strenge Regeln: Original-BID-/Maßstab-/Kalenderchecks und `hebeltrader-loss.activation_status`/Qualifikationsreferenzen auswerten. Ein reiner `FRESH_QUOTE` oder `monitoring_usable=true` ist keine B58-Eignung. Für B06 sind **beide Pflichtreads** nötig: `hebeltrader-targets` für historische Ziele/Targetzustand sowie `/api/v1/trade-position/trades/{id}/hebeltrader-evidence?position_id=...` für historischen persönlichen Basiswerteinstand, Währung, Ausführungsbezüge und Belegabdeckung. Der zweite Read liefert je Beitrag die Abdeckung/Verknüpfung in `items`/`execution_links` und die wirtschaftliche `valuation_basis`; er gibt die rohe `declaration.underlying_trades` nicht aus. Nur bei konkretem Bedarf an den originalen Einzel-BUY-Belegen zusätzlich dessen vorhandenen `/history`-GET lesen. Fehlende Grundbelege und bekannt unimplementierte Folgestopanteile getrennt ausweisen.
6. Öffentlich ausschließlich Tabelle `Pseudonym | Regel | belegt/teilweise/nicht auswertbar | konkrete Fehlcodes | Kategorie Quelle/Mapping/Import/Verarbeitung/Konfiguration/Fachentscheidung | Owner | Beschaffung`. Private `identity_private`-Map und vollständige Originalreadantworten im privaten Diagnoseverzeichnis belassen. Bei Unterstützung nur über einen ausdrücklich privaten Kanal bereitstellen; Beträge/IDs vor Repositoryübernahme entfernen.

Gezielt ergänzend, nur wenn die vorhandenen Reader eine Ursache nicht liefern: passiver `hebeltrader-targets/qualification-preview` für konkrete historischen Quellen-/Skalenprobleme; `hebeltrader-sessions` für genaue Zeitraumlücken; privater bereits vorhandener Logauszug zum dokumentierten Acquisitionversuch für HTTP403 versus Timeout. Diese sind kein unbedingter weiterer Dauerschritt.

### Grenze des vorhandenen Product-Readbacks bei unklarem Datumswiderspruch

**Genau ein bestehender GET enthält passende Product-Owner-Teilbelege:** der bereits verpflichtend gelesene `/api/v1/position-monitoring/trades/{id}/product-deadline-review?position_id=...`. Seine `latest_assessment.product_evidence` nennt `product_document_revision_id`, `product_end_on`, `payment_on`, `payment_qualifier` und `current_terms_date_role`. Diese Werte beschreiben die **damals ausgewertete** Product-Owner-Evidenz, nicht den unabhängig aktuellen KID-Head. `product_evidence.recorded_at` ist das Maximum von KID-, Exitwahl- und Listingterms-Speicherzeiten; es darf nicht als alleinige KID-Reparsezeit bezeichnet werden (`product/service/review_evidence.py:463–506`; `position_monitoring/service/product_deadline_review_read.py:85–99`).

Der aktuelle Main hat **keinen HTTP-GET**, der den aktuellen KID-Head einschließlich `parser_version`, originalem `retrieved_at` und eigenem `recorded_at` vollständig zurückgibt. `ProductReviewEvidenceReader.current_for_review` ist nur ein interner passiver Ownerread und enthält selbst kein Parserfeld. `latest_document` (`product/service/review_evidence.py:55–74`) liest per SELECT die passende `ProductReviewDocumentModel`-Revision samt Parserfassung, ist aber nicht als GET exponiert. Der vorhandene `deadline-listing-terms/current`-GET betrifft einen anderen Belegtyp und ersetzt diesen KID-Nachweis nicht.

Deshalb gilt: Bleibt nach bestätigt installiertem v1.5.52 und nachfolgendem regulärem Zyklus ein unklarer Terms-Mismatch bestehen, reicht diese GET-Sammlung für die **aktuelle Parserursache** nicht. Dann ist genau ein gezielter passiver KID-Metadatenread beim bestehenden Product-Owner erforderlich (nur Produkt-/Revision-/Terms-ID, Parserfassung, `recorded_at`, `retrieved_at`, Dokumenthash und begrenzte `facts.issues`/Datumsrollen; keine Originalbytes). Dieser Zusatz ist hier **weder ausgeführt noch als vorhandener API-Pfad erfunden**. Ohne ihn bleibt die konkrete Reparsefrage ausdrücklich offen. Kein neuer Spec-, Command-, Import- oder Beschaffungspfad ist Bestandteil des Snippets.

Der ergänzte B06-Reader ist anhand `trade_position/api/hebeltrader_evidence.py:165–175` und `service/hebeltrader_evidence.py:479–511` als `REPEATABLE READ READ ONLY`, ohne Netzwerk/Commands, mit abschließendem Rollback geprüft.

## Git-Versionierung

`VERSION`, `backend/pyproject.toml`, `frontend/package.json` und dessen Lockdatei
werden im Release-PR gemeinsam fortgeschrieben. Der Workflow `Version tag` setzt
`v<VERSION>` erst, wenn Backend, Frontend und End-to-End am selben aktuellen
`main`-Commit vollständig erfolgreich sind. Vorhandene Tags werden niemals
verschoben. Der Workflow übernimmt keine PRs und führt kein Deployment aus.

## Umstieg alter Paket-Overlays (1.4.3)

Ein bestehender Paket-Stack darf nicht allein durch Austausch seiner Compose-Liste
aktualisiert werden: Laufzeitwerte können von `.env` abweichen. Für die geprüfte
Vier-Service-Topologie beschreibt [Linux Deployment](LINUX_DEPLOYMENT.md#reviewed-legacy-issuer-migration-143)
die getrennte Vorbereitung und den Wechsel mit Erhalt tatsächlicher Einstellungen,
Volumes, absolutem Stuttgart-Pfad, Sicherungen und Sandbox. Der ursprüngliche
Checkout bleibt bestehen. Der private Erhaltungs-Overlay gehört anschließend zur
vollständigen Betriebskonfiguration; ihn nicht ins Repository oder Support kopieren.
Ein erfolgreicher Wechsel ersetzt keine JPMorgan-Produktprüfung und keinen
Nachweis vollständiger Monitoring-Zyklen nach dem Cacheaufbau.
